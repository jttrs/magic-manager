"""Tests for the fast add paths (2026-08-30):

  - `mm deck add-precon` builds an in-memory precon checklist and runs it through
    `sets._apply_precon_checklist`, which builds decks + adds inventory. Precon
    unit counts are DERIVED from the `decks` table (V10 source_precon_file_name
    + V11 precon_state built/deconstructed/pool) — there is no ledger. These
    tests pin the in-memory contract (JumpstartParseResult.rows shape) so a
    parser-dataclass change can't silently break the CLI verb, and prove the
    derived 3-bucket counts + deck rows.
  - `mm inventory add-card` resolves SET+CN specs via parsers.resolve (Scryfall
    collection + sync-on-demand) and sums into inventory.

Offline: fake_scryfall/fake_mtgjson monkeypatch the network boundaries.
"""

import pytest


# ---------- add-precon: in-memory _apply_precon_checklist contract ----------

def test_add_precon_derives_count_and_builds_deck(
    tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck,
):
    """The seam add-precon relies on: construct a JumpstartParseResult in-memory,
    call sets._apply_precon_checklist(mode='add'), and get deck+inventory written
    in one shot. The unit count derives from the decks table (no ledger)."""
    from magic_manager import sets as sets_mod, decks, db, parsers

    deck = make_precon_deck(
        "Family Matters", "Commander Deck",
        [{"sid": "blc-sid-1", "name": "Cmd", "set": "blc", "cn": "1", "count": 1, "board": "commander"},
         {"sid": "blc-sid-2", "name": "Body", "set": "blc", "cn": "2", "count": 99, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[
        make_card(id="blc-sid-1", set="blc", collector_number="1", name="Cmd"),
        make_card(id="blc-sid-2", set="blc", collector_number="2", name="Body"),
    ])

    # This is exactly what the CLI verb constructs.
    parsed = parsers.JumpstartParseResult(
        rows=[parsers.JumpstartRow(file_name="FamilyMatters_BLC", theme="Family Matters",
                                   keep_qty=1, deconstructed_qty=0)],
        warnings=[], meta={"kind": "precon", "mode": "add"},
    )
    summary = sets_mod._apply_precon_checklist(parsed, mode="add")

    assert summary["built"] == 1
    assert summary["rows_acted"] == 1
    # Count DERIVED from the decks table (the deck row carries the fileName).
    assert decks.precon_unit_counts_for("FamilyMatters_BLC") == (1, 0, 0)
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM decks").fetchone()[0] == 1
        row = conn.execute(
            "SELECT source_precon_file_name, precon_state FROM decks"
        ).fetchone()
        assert (row["source_precon_file_name"], row["precon_state"]) == ("FamilyMatters_BLC", "built")
        assert conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0] == 2


def test_add_precon_additive_second_copy(
    tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck,
):
    """Re-running add (mode='add') derives count 1→2 and creates a distinct
    second deck slug — the 'I opened another copy' behavior."""
    from magic_manager import sets as sets_mod, decks, db, parsers

    deck = make_precon_deck(
        "Otter Limits", "Starter Kit",
        [{"sid": "blb-sid-1", "name": "Otter", "set": "blb", "cn": "1", "count": 1, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[make_card(id="blb-sid-1", set="blb", collector_number="1", name="Otter")])

    def _run():
        parsed = parsers.JumpstartParseResult(
            rows=[parsers.JumpstartRow(file_name="OtterLimits_BLB", theme="Otter Limits",
                                       keep_qty=1, deconstructed_qty=0)],
            warnings=[], meta={"kind": "precon", "mode": "add"},
        )
        return sets_mod._apply_precon_checklist(parsed, mode="add")

    _run()
    _run()

    assert decks.precon_unit_counts_for("OtterLimits_BLB") == (2, 0, 0)
    with db.connect() as conn:
        slugs = [r[0] for r in conn.execute("SELECT slug FROM decks ORDER BY slug").fetchall()]
    assert slugs == ["otter-limits", "otter-limits-2"]


def test_add_precon_deconstruct_records_deck_rows(
    tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck,
):
    """constructed=0, deconstructed=2 → loose cards + TWO deconstructed deck
    rows, so the torn-down copies are countable as units (derived count (0,2,0))."""
    from magic_manager import sets as sets_mod, decks, db, parsers

    deck = make_precon_deck(
        "Hare Raising", "Starter Kit",
        [{"sid": "blb-sid-9", "name": "Hare", "set": "blb", "cn": "9", "count": 1, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[make_card(id="blb-sid-9", set="blb", collector_number="9", name="Hare")])

    parsed = parsers.JumpstartParseResult(
        rows=[parsers.JumpstartRow(file_name="HareRaising_BLB", theme="Hare Raising",
                                   keep_qty=0, deconstructed_qty=2)],
        warnings=[], meta={"kind": "precon", "mode": "add"},
    )
    summary = sets_mod._apply_precon_checklist(parsed, mode="add")

    assert summary["built"] == 0
    assert summary["deconstructed"] == 2
    assert decks.precon_unit_counts_for("HareRaising_BLB") == (0, 2, 0)
    with db.connect() as conn:
        # Two deck rows, both flagged deconstructed.
        assert conn.execute(
            "SELECT COUNT(*) FROM decks WHERE precon_state = 'deconstructed'"
        ).fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0] == 1


def test_add_precon_modify_lowering_warns_not_deletes(
    tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck,
):
    """A modify ingest lowering a count does NOT delete decks — it warns and
    points at `mm deck delete`. The derived count stays put."""
    from magic_manager import sets as sets_mod, decks, db, parsers

    deck = make_precon_deck(
        "Family Matters", "Commander Deck",
        [{"sid": "blc-sid-1", "name": "Cmd", "set": "blc", "cn": "1", "count": 1, "board": "commander"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[make_card(id="blc-sid-1", set="blc", collector_number="1", name="Cmd")])

    # Build one copy (add), then modify it down to 0.
    add = parsers.JumpstartParseResult(
        rows=[parsers.JumpstartRow(file_name="FamilyMatters_BLC", theme="Family Matters",
                                   keep_qty=1, deconstructed_qty=0)],
        warnings=[], meta={"kind": "precon", "mode": "add"},
    )
    sets_mod._apply_precon_checklist(add, mode="add")
    assert decks.precon_unit_counts_for("FamilyMatters_BLC") == (1, 0, 0)

    down = parsers.JumpstartParseResult(
        rows=[parsers.JumpstartRow(file_name="FamilyMatters_BLC", theme="Family Matters",
                                   keep_qty=0, deconstructed_qty=0)],
        warnings=[], meta={"kind": "precon", "mode": "modify"},
    )
    summary = sets_mod._apply_precon_checklist(down, mode="modify")

    # Warned, built/torn nothing, and the deck row still exists (count unchanged).
    assert summary["built"] == 0 and summary["deconstructed"] == 0
    assert summary["per_row"][0]["warning"] is not None
    assert "mm deck delete" in summary["per_row"][0]["warning"]
    assert decks.precon_unit_counts_for("FamilyMatters_BLC") == (1, 0, 0)


def test_add_precon_pool_state(
    tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck,
):
    """pool_qty=1 → a precon_state='pool' deck row + loose inventory + NO
    deck_assignments (a pool is never pledged); derived count (0,0,1)."""
    from magic_manager import sets as sets_mod, decks, db, parsers

    deck = make_precon_deck(
        "Starter Collection", "Box Set",
        [{"sid": "fdn-sid-1", "name": "Lib", "set": "fdn", "cn": "1", "count": 1, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[make_card(id="fdn-sid-1", set="fdn", collector_number="1", name="Lib")])

    parsed = parsers.JumpstartParseResult(
        rows=[parsers.JumpstartRow(file_name="StarterCollection_FDN", theme="Starter Collection",
                                   keep_qty=0, deconstructed_qty=0, pool_qty=1)],
        warnings=[], meta={"kind": "precon", "mode": "add"},
    )
    summary = sets_mod._apply_precon_checklist(parsed, mode="add")

    assert summary["pool"] == 1 and summary["built"] == 0
    assert decks.precon_unit_counts_for("StarterCollection_FDN") == (0, 0, 1)
    with db.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM decks WHERE precon_state = 'pool'"
        ).fetchone()[0] == 1
        # Pool cards land in inventory but are NOT pledged to the deck.
        assert conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM deck_assignments").fetchone()[0] == 0


# ---------- add-precon: resolver + fuzzy match ----------

def test_resolve_precon_filenames_fuzzy_and_ambiguous(monkeypatch):
    """The CLI resolver: --all returns all; a unique substring returns one; an
    ambiguous substring raises LookupError with candidates."""
    from magic_manager import cli, mtgjson

    variants = [
        {"fileName": "AnimatedArmy_BLC", "name": "Animated Army", "type": "Commander Deck", "code": "BLC"},
        {"fileName": "FamilyMatters_BLC", "name": "Family Matters", "type": "Commander Deck", "code": "BLC"},
    ]
    monkeypatch.setattr(mtgjson, "precon_variants", lambda *a, **k: list(variants))
    # deck() must fail for a set code so we fall through to precon_variants.
    monkeypatch.setattr(mtgjson, "deck", lambda fn: (_ for _ in ()).throw(mtgjson.MtgJsonError("nope")))

    # --all → both
    got = cli._resolve_precon_filenames("blc", None, want_all=True, only_type=None, include_collector=False)
    assert {d["fileName"] for d in got} == {"AnimatedArmy_BLC", "FamilyMatters_BLC"}

    # unique substring → one
    got = cli._resolve_precon_filenames("blc", "family", want_all=False, only_type=None, include_collector=False)
    assert [d["fileName"] for d in got] == ["FamilyMatters_BLC"]

    # ambiguous substring "a" (matches both) → LookupError
    with pytest.raises(LookupError):
        cli._resolve_precon_filenames("blc", "a", want_all=False, only_type=None, include_collector=False)

    # no match → LookupError
    with pytest.raises(LookupError):
        cli._resolve_precon_filenames("blc", "zzzzz", want_all=False, only_type=None, include_collector=False)


def test_resolve_precon_filenames_exact_filename(monkeypatch):
    """An exact fileName (deck() succeeds) resolves to that one deck without
    touching precon_variants."""
    from magic_manager import cli, mtgjson

    monkeypatch.setattr(mtgjson, "deck", lambda fn: {"name": "Family Matters", "type": "Commander Deck", "code": "BLC"})

    got = cli._resolve_precon_filenames("FamilyMatters_BLC", None, want_all=False, only_type=None, include_collector=False)
    assert [d["fileName"] for d in got] == ["FamilyMatters_BLC"]
    assert got[0]["name"] == "Family Matters"


# ---------- add-card: spec parsing + resolution ----------

@pytest.mark.parametrize("spec,expected", [
    ("spg 60", ("spg", "60", "nonfoil", 1)),
    ("blc 123 foil 2", ("blc", "123", "foil", 2)),
    ("blc 123 2", ("blc", "123", "nonfoil", 2)),
    ("blc 123 foil", ("blc", "123", "foil", 1)),
    ("spg:60", ("spg", "60", "nonfoil", 1)),
    ("blc:123:foil:2", ("blc", "123", "foil", 2)),
    ("blc:123::4", ("blc", "123", "nonfoil", 4)),
    ("BLC 123 FOIL", ("blc", "123", "foil", 1)),
])
def test_parse_card_spec_forms(spec, expected):
    from magic_manager import cli
    assert cli._parse_card_spec(spec) == expected


@pytest.mark.parametrize("bad", ["onlyonetoken", "blc 123 foil 0", "blc 123 xyz", "", "blc 123 -1"])
def test_parse_card_spec_rejects_malformed(bad):
    from magic_manager import cli
    with pytest.raises(ValueError):
        cli._parse_card_spec(bad)


def test_add_card_resolves_and_sums(tmp_db, fake_scryfall, monkeypatch, make_card):
    """add-card resolves SET+CN via parsers.resolve and sums into inventory —
    exercised through the resolve+add helpers the CLI uses."""
    from magic_manager import parsers, inventory, db

    card = make_card(id="spg-sid-60", set="spg", collector_number="60", name="Toski")
    # parsers.resolve calls scryfall.collection → return the card as found.
    fake_scryfall(collection_found=[card])

    result = parsers.ParseResult(entries=[
        parsers.Entry(qty=2, raw="spg 60 foil 2", name="", set="spg",
                      collector_number="60", foil=True, section="mainboard"),
    ])
    parsers.resolve(result)
    assert result.entries[0].card is not None

    with db.connect() as conn:
        db.upsert_card(conn, result.entries[0].card)
    r = inventory.inventory_add(card["id"], "foil", 2)
    assert r["new_qty"] == 2
    # additive
    r2 = inventory.inventory_add(card["id"], "foil", 1)
    assert r2["new_qty"] == 3

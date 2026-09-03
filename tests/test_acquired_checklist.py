"""Tests for the ADD-mode single-``acquired_qty`` deck-checklist engine
(``sets._apply_acquired_checklist``, 2026-09-03).

Add-mode jumpstart/precon checklists carry ONE ``acquired_qty`` per row; ingest
splits it deterministically into built / deconstructed / pool so the user never
has to know their prior collection at fill time:

  - pool products (Starter Collection, Scene Box) → all copies pool,
  - net-new buildable → 1 built + rest deconstructed,
  - already own ≥1 built copy → all deconstructed.

Every copy — including jumpstart — gets a tracked ``decks`` row, so built vs
deconstructed counts stay derivable. Offline via fake_scryfall/fake_mtgjson.
"""

from __future__ import annotations


def _jumpstart_slug_fn(set_code):
    from magic_manager import sets as sets_mod
    return lambda name: sets_mod._slug_theme(name, set_code)


def test_net_new_buildable_keeps_one_built_rest_deconstructed(
    tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck,
):
    """acquired_qty=3 of a net-new buildable pack → 1 built (composed) + 2
    deconstructed, all three tracked deck rows, all cards in inventory."""
    from magic_manager import sets as sets_mod, decks, db, parsers

    deck = make_precon_deck(
        "Iron Man", "Jumpstart",
        [{"sid": "msh-1", "name": "Repulsor", "set": "msh", "cn": "1", "count": 1, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[make_card(id="msh-1", set="msh", collector_number="1", name="Repulsor")])

    parsed = parsers.JumpstartParseResult(
        rows=[parsers.JumpstartRow(file_name="IronMan_MSH", theme="Iron Man",
                                   keep_qty=0, deconstructed_qty=0, acquired_qty=3)],
        warnings=[], meta={"kind": "jumpstart", "mode": "add"},
    )
    summary = sets_mod._apply_acquired_checklist(
        parsed, slug_fn=_jumpstart_slug_fn("msh"), deck_format="jumpstart")

    assert summary["built"] == 1
    assert summary["deconstructed"] == 2
    assert summary["pool"] == 0
    pr = summary["per_row"][0]
    assert pr["net_new"] is True
    assert pr["acquired_qty"] == 3
    # Derived counts: 1 built + 2 deconstructed.
    assert decks.precon_unit_counts_for("IronMan_MSH") == (1, 2, 0)
    with db.connect() as conn:
        slugs = [r[0] for r in conn.execute("SELECT slug FROM decks ORDER BY slug").fetchall()]
        # Base slug + -2 + -3, all pack:*-msh, one built + two deconstructed.
        assert slugs == ["pack:iron-man-msh", "pack:iron-man-msh-2", "pack:iron-man-msh-3"]
        # Exactly one physical copy pledged (the built one).
        assert conn.execute("SELECT COUNT(*) FROM deck_assignments").fetchone()[0] >= 1
        states = sorted(r[0] for r in conn.execute("SELECT precon_state FROM decks").fetchall())
        assert states == ["built", "deconstructed", "deconstructed"]


def test_already_built_makes_every_copy_deconstructed(
    tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck,
):
    """If a built copy already exists, a second ingest of acquired_qty=2 adds
    two DECONSTRUCTED copies (no new built) — the MSH-duplicate scenario."""
    from magic_manager import sets as sets_mod, decks, parsers

    deck = make_precon_deck(
        "Wild", "Jumpstart",
        [{"sid": "msh-9", "name": "Beast", "set": "msh", "cn": "9", "count": 1, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[make_card(id="msh-9", set="msh", collector_number="9", name="Beast")])

    def _run(n):
        parsed = parsers.JumpstartParseResult(
            rows=[parsers.JumpstartRow(file_name="Wild_MSH", theme="Wild", acquired_qty=n)],
            warnings=[], meta={"kind": "jumpstart", "mode": "add"},
        )
        return sets_mod._apply_acquired_checklist(
            parsed, slug_fn=_jumpstart_slug_fn("msh"), deck_format="jumpstart")

    _run(1)  # net-new: 1 built
    assert decks.precon_unit_counts_for("Wild_MSH") == (1, 0, 0)

    summary = _run(2)  # already own built → both deconstructed
    assert summary["built"] == 0
    assert summary["deconstructed"] == 2
    assert summary["per_row"][0]["net_new"] is False
    assert decks.precon_unit_counts_for("Wild_MSH") == (1, 2, 0)


def test_pool_product_sends_all_copies_to_pool(
    tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck,
):
    """A pool product (name matches POOL_NAME_PATTERNS) with acquired_qty=2 →
    both copies pool, none built, cards loose (no deck_assignments)."""
    from magic_manager import sets as sets_mod, decks, db, parsers

    deck = make_precon_deck(
        "Starter Collection", "Box Set",
        [{"sid": "fdn-1", "name": "Lib", "set": "fdn", "cn": "1", "count": 1, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[make_card(id="fdn-1", set="fdn", collector_number="1", name="Lib")])

    parsed = parsers.JumpstartParseResult(
        rows=[parsers.JumpstartRow(file_name="StarterCollection_FDN",
                                   theme="Starter Collection", acquired_qty=2)],
        warnings=[], meta={"kind": "precon", "mode": "add"},
    )
    summary = sets_mod._apply_acquired_checklist(
        parsed, slug_fn=decks._slug, deck_format=None)

    assert summary["pool"] == 2
    assert summary["built"] == 0
    assert summary["deconstructed"] == 0
    assert summary["per_row"][0]["net_new"] is False
    assert decks.precon_unit_counts_for("StarterCollection_FDN") == (0, 0, 2)
    with db.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM decks WHERE precon_state = 'pool'").fetchone()[0] == 2
        # Pool cards are loose — never pledged.
        assert conn.execute("SELECT COUNT(*) FROM deck_assignments").fetchone()[0] == 0


def test_acquired_one_is_single_built(
    tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck,
):
    """The common case: acquired_qty=1 of a net-new buildable → exactly 1 built,
    0 deconstructed."""
    from magic_manager import sets as sets_mod, decks, parsers

    deck = make_precon_deck(
        "Fantastic", "Jumpstart",
        [{"sid": "msh-4", "name": "Four", "set": "msh", "cn": "4", "count": 1, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[make_card(id="msh-4", set="msh", collector_number="4", name="Four")])

    parsed = parsers.JumpstartParseResult(
        rows=[parsers.JumpstartRow(file_name="Fantastic_MSH", theme="Fantastic", acquired_qty=1)],
        warnings=[], meta={"kind": "jumpstart", "mode": "add"},
    )
    summary = sets_mod._apply_acquired_checklist(
        parsed, slug_fn=_jumpstart_slug_fn("msh"), deck_format="jumpstart")

    assert (summary["built"], summary["deconstructed"], summary["pool"]) == (1, 0, 0)
    assert decks.precon_unit_counts_for("Fantastic_MSH") == (1, 0, 0)


def test_zero_acquired_is_noop(
    tmp_db, fake_scryfall, fake_mtgjson, make_precon_deck,
):
    """acquired_qty=0 rows don't act."""
    from magic_manager import sets as sets_mod, decks, parsers

    fake_mtgjson(deck=make_precon_deck("Speedy", "Jumpstart", [
        {"sid": "msh-2", "name": "Fast", "set": "msh", "cn": "2", "count": 1, "board": "mainBoard"}]))
    fake_scryfall(search=[])

    parsed = parsers.JumpstartParseResult(
        rows=[parsers.JumpstartRow(file_name="Speedy_MSH", theme="Speedy", acquired_qty=0)],
        warnings=[], meta={"kind": "jumpstart", "mode": "add"},
    )
    summary = sets_mod._apply_acquired_checklist(
        parsed, slug_fn=_jumpstart_slug_fn("msh"), deck_format="jumpstart")

    assert summary["rows_acted"] == 0
    assert decks.precon_unit_counts_for("Speedy_MSH") == (0, 0, 0)

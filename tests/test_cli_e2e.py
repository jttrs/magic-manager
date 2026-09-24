"""End-to-end CLI tests via Typer's CliRunner, against a tmp DB with faked
network. Exercises the real command wiring (arg parsing → module calls →
DB) for the flows most prone to regression."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def app():
    from magic_manager.cli import app as _app
    return _app


def test_deck_ls_empty(tmp_db, app):
    res = runner.invoke(app, ["deck", "ls"])
    assert res.exit_code == 0
    assert "no decks" in res.stdout.lower()


def test_set_sync_populates_cards(tmp_db, app, fake_scryfall, make_card, monkeypatch):
    # `set sync` resolves the code first (sets.resolve → scryfall.all_sets),
    # then iterates scryfall.search — fake both.
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets",
                        lambda: [{"code": "ncc", "parent_set_code": None,
                                  "name": "New Capenna Commander", "set_type": "commander"}])
    fake_scryfall(search=[
        make_card(id="e1", set="ncc", collector_number="1"),
        make_card(id="e2", set="ncc", collector_number="2"),
    ])
    res = runner.invoke(app, ["set", "sync", "ncc"])
    assert res.exit_code == 0, res.stdout
    from magic_manager import db
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM cards WHERE set_code='ncc'").fetchone()[0] == 2


def test_set_sync_all_enumerates_distinct_codes(tmp_db, app, monkeypatch):
    """`set sync-all` syncs every DISTINCT set_code present in cards, and only
    those — enumerated from the table, deduped, not a family resolve."""
    from magic_manager import db, sets as sets_mod
    # Seed cards across two set codes (one code twice) with no network.
    with db.connect() as conn:
        conn.executemany(
            "INSERT INTO cards (scryfall_id, oracle_id, name, set_code, "
            "collector_number, rarity) VALUES (?,?,?,?,?,?)",
            [("a", "oa", "A", "ncc", "1", "rare"),
             ("b", "ob", "B", "ncc", "2", "rare"),
             ("c", "oc", "C", "clb", "1", "mythic")],
        )
    captured = []
    # set_sync_all now calls sync(codes, progress=...); stub accepts the kwarg.
    monkeypatch.setattr(sets_mod, "sync",
                        lambda codes, **kw: captured.append(sorted(codes)) or 0)
    res = runner.invoke(app, ["set", "sync-all"])
    assert res.exit_code == 0, res.stdout
    assert captured == [["clb", "ncc"]]  # distinct, sorted; ncc not duplicated


def test_set_sync_all_dry_run_syncs_nothing(tmp_db, app, monkeypatch):
    from magic_manager import db, sets as sets_mod
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO cards (scryfall_id, oracle_id, name, set_code, "
            "collector_number, rarity) VALUES ('a','oa','A','ncc','1','rare')")
    called = []
    monkeypatch.setattr(sets_mod, "sync", lambda codes, **kw: called.append(codes) or 0)
    res = runner.invoke(app, ["set", "sync-all", "--dry-run"])
    assert res.exit_code == 0, res.stdout
    assert "ncc" in res.stdout and "Would sync 1" in res.stdout
    assert called == []  # dry-run must not sync


def test_set_sync_all_empty_cards_table(tmp_db, app):
    res = runner.invoke(app, ["set", "sync-all"])
    assert res.exit_code == 0, res.stdout
    assert "nothing to sync" in res.stdout.lower()


def test_set_sync_all_repopulates_new_columns(tmp_db, app, fake_scryfall, make_card):
    """End-to-end: a card with NULL legalities gets repopulated by sync-all when
    Scryfall returns fresh data carrying legalities + game_changer (the whole
    point of the un-lazy re-sync)."""
    from magic_manager import db
    # Seed a card with the OLD/empty shape: no legalities, no game_changer.
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO cards (scryfall_id, oracle_id, name, set_code, "
            "collector_number, rarity, legalities, game_changer) "
            "VALUES ('rh','orh','Rhystic Study','clb','1','uncommon', NULL, 0)")
    # sync-all re-pulls clb; Scryfall returns the same card WITH the new fields.
    fake_scryfall(search=[
        make_card(id="rh", set="clb", collector_number="1", name="Rhystic Study",
                  legalities={"commander": "legal"}, game_changer=True),
    ])
    res = runner.invoke(app, ["set", "sync-all"])
    assert res.exit_code == 0, res.stdout
    with db.connect() as conn:
        row = conn.execute(
            "SELECT legalities, game_changer FROM cards WHERE scryfall_id='rh'"
        ).fetchone()
    assert row["legalities"] is not None and "commander" in row["legalities"]
    assert row["game_changer"] == 1


def test_import_precon_e2e_autosync(tmp_db, app, fake_scryfall, fake_mtgjson,
                                    make_card, make_precon_deck):
    """The whole fix, through the CLI: an unsynced family imports cleanly."""
    deck = make_precon_deck(
        "World Shaper", "Commander Deck",
        [{"sid": "ws1", "name": "Cmdr", "set": "ncc", "cn": "1", "count": 1, "board": "commander"},
         {"sid": "ws2", "name": "Card", "set": "ncc", "cn": "2", "count": 99, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[
        make_card(id="ws1", set="ncc", collector_number="1", name="Cmdr"),
        make_card(id="ws2", set="ncc", collector_number="2", name="Card"),
    ])
    res = runner.invoke(app, ["deck", "import-precon", "WorldShaper_NCC"])
    assert res.exit_code == 0, res.stdout
    from magic_manager import db
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM decks WHERE slug='world-shaper'").fetchone()[0] == 1
        assert conn.execute("SELECT COALESCE(SUM(count),0) FROM deck_cards").fetchone()[0] == 100


def test_query_missing_set_e2e(tmp_db, app, fake_scryfall, seed_cards, make_card,
                               monkeypatch, tmp_path):
    """query missing-set on a configured family (tla) emits its report; the
    unowned rare shows up, the owned one doesn't."""
    # missing-set writes artifacts under util.OUTPUT_ROOT (repo-root anchored,
    # so CWD-independent). Redirect that ROOT to a throwaway dir so the test
    # isolates its artifacts instead of polluting the real repo output/ tree.
    import magic_manager.util as util
    monkeypatch.setattr(util, "OUTPUT_ROOT", tmp_path / "output")
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets",
                        lambda: [{"code": "tla", "parent_set_code": None,
                                  "name": "Avatar", "set_type": "expansion"}])
    seed_cards([
        make_card(id="q1", set="tla", collector_number="5", rarity="rare", name="Buyme Rare"),
        make_card(id="q2", set="tla", collector_number="6", rarity="rare", name="Havit Rare"),
    ])
    from magic_manager import db
    with db.connect() as conn:
        conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) "
                     "VALUES ('q2','nonfoil',1,'2025-01-01')")
    res = runner.invoke(app, ["query", "missing-set", "tla"])
    assert res.exit_code == 0, res.stdout
    # headline reflects 1 missing printing
    assert "Missing from set:tla" in res.stdout
    # Artifacts land in the segmented output/missing-set/{checklists,buy-lists}/
    # tree (guards the write path — a regression to a wrong dir fails here).
    checklists = list((tmp_path / "output" / "missing-set" / "checklists").glob(
        "missing-tla-checklist-*.xlsx"))
    assert checklists, "expected a missing-tla checklist under output/missing-set/checklists/"
    buylists = list((tmp_path / "output" / "missing-set" / "buy-lists").glob(
        "missing-tla-*.txt"))
    assert buylists, "expected missing-tla buy-list txt under output/missing-set/buy-lists/"


# ---------- Phase 5: audit/debug commands ----------

def test_set_is_synced_reports_counts(tmp_db, app, seed_cards, make_card, monkeypatch):
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets",
                        lambda: [{"code": "tla", "parent_set_code": None,
                                  "name": "Avatar", "set_type": "expansion"}])
    # unsynced → exit 1
    res = runner.invoke(app, ["set", "is-synced", "tla"])
    assert res.exit_code == 1
    assert "not synced" in res.stdout
    # after seeding → exit 0, count shown
    seed_cards([make_card(id="s1", set="tla", collector_number="1")])
    res2 = runner.invoke(app, ["set", "is-synced", "tla"])
    assert res2.exit_code == 0
    assert "1 cards" in res2.stdout


def test_inventory_add_card_e2e_records_ledger(tmp_db, app, fake_scryfall, make_card):
    """Regression (F1): `mm inventory add-card` through the real CLI wrapper must
    add the card AND its ledger event without the no-op-delete FK crash. The
    batch routes writes through inventory_add(ingest_id=...) (direct record_delta,
    bypassing rec.record), so the no-op check must consult inventory_events, not
    the recorder tallies — else open_ingest_event's DELETE hits the FK and rolls
    everything back."""
    card = make_card(id="ac1", set="tla", collector_number="5", name="Add Me")
    # add-card resolves specs via scryfall.collection.
    fake_scryfall(collection_found=[card])

    res = runner.invoke(app, ["inventory", "add-card", "tla:5:nonfoil:1"])
    assert res.exit_code == 0, res.stdout

    from magic_manager import db, ingest
    with db.connect() as conn:
        # Card landed in inventory.
        assert conn.execute(
            "SELECT quantity FROM inventory WHERE scryfall_id='ac1' AND finish='nonfoil'"
        ).fetchone()["quantity"] == 1
        # Exactly one adhoc event + its inventory_events delta survived (not deleted).
        ev = conn.execute(
            "SELECT ingest_id FROM ingest_events WHERE method='adhoc'"
        ).fetchall()
        assert len(ev) == 1
        assert conn.execute(
            "SELECT COALESCE(SUM(delta),0) s FROM inventory_events WHERE ingest_id=?",
            (ev[0]["ingest_id"],),
        ).fetchone()["s"] == 1
        # Ledger invariant intact.
        assert ingest.reconcile_inventory_ledger(conn) == []


def test_inventory_add_card_e2e_all_unresolved_no_crash(tmp_db, app, fake_scryfall):
    """A batch where every spec fails to resolve records NO deltas → the no-op
    event must be cleanly deleted (no children, so the DELETE is safe) and the
    command must still succeed."""
    fake_scryfall(collection_found=[], collection_not_found=[{"set": "tla", "collector_number": "999"}])
    res = runner.invoke(app, ["inventory", "add-card", "tla:999:nonfoil:1"])
    assert res.exit_code == 0, res.stdout
    from magic_manager import db
    with db.connect() as conn:
        # No dangling adhoc event (deleted as a true no-op).
        assert conn.execute(
            "SELECT COUNT(*) c FROM ingest_events WHERE method='adhoc'"
        ).fetchone()["c"] == 0


def test_audit_deck_inventory_finds_and_fixes_orphan(tmp_db, app):
    from magic_manager import db, decks
    # create an orphan deck (row with no deck_cards) — the pre-fix failure state
    decks.deck_create("orphan-deck", "Orphan")
    res = runner.invoke(app, ["audit", "deck-inventory"])
    assert res.exit_code == 0
    assert "Orphan decks (0 cards): 1" in res.stdout
    assert "orphan-deck" in res.stdout
    # --fix deletes it
    res2 = runner.invoke(app, ["audit", "deck-inventory", "--fix"])
    assert "deleted 1 orphan" in res2.stdout.lower()
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM decks").fetchone()[0] == 0


def test_db_unlock_no_sidecars(tmp_db, app):
    res = runner.invoke(app, ["db", "unlock"])
    assert res.exit_code == 0
    assert "nothing to unlock" in res.stdout.lower()


def _seed_loose_precon(app, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """Seed a 2-card precon's cards + full loose inventory; prime the fakes."""
    from magic_manager import db, inventory
    sids = ["e2e-a", "e2e-b"]
    cards = [
        make_card(id=sids[0], set="tst", collector_number="1", name="A"),
        make_card(id=sids[1], set="tst", collector_number="2", name="B"),
    ]
    with db.connect() as conn:
        db.upsert_cards(conn, cards)
        inventory.inventory_add(sids[0], "nonfoil", 1, conn=conn)
        inventory.inventory_add(sids[1], "nonfoil", 2, conn=conn)
    fake_mtgjson(deck=make_precon_deck(
        "Loose Kit", "Starter Kit",
        [{"sid": sids[0], "name": "A", "set": "tst", "cn": "1", "count": 1, "board": "commander"},
         {"sid": sids[1], "name": "B", "set": "tst", "cn": "2", "count": 2, "board": "mainBoard"}],
    ))
    fake_scryfall(search=cards)
    return sids


def test_construct_from_loose_e2e_happy_path(tmp_db, app, fake_scryfall, fake_mtgjson,
                                             make_card, make_precon_deck):
    _seed_loose_precon(app, fake_scryfall, fake_mtgjson, make_card, make_precon_deck)
    res = runner.invoke(app, ["deck", "construct-from-loose", "LooseKit_TST"])
    assert res.exit_code == 0, res.stdout
    assert "pledged" in res.stdout.lower()
    from magic_manager import db
    with db.connect() as conn:
        assert conn.execute(
            "SELECT precon_state FROM decks WHERE source_precon_file_name='LooseKit_TST'"
        ).fetchone()["precon_state"] == "built"
        assert conn.execute("SELECT COALESCE(SUM(count),0) FROM deck_assignments").fetchone()[0] == 3
        assert conn.execute("SELECT COALESCE(SUM(quantity),0) FROM inventory").fetchone()[0] == 3


def test_construct_from_loose_e2e_dry_run_writes_nothing(tmp_db, app, fake_scryfall, fake_mtgjson,
                                                         make_card, make_precon_deck):
    _seed_loose_precon(app, fake_scryfall, fake_mtgjson, make_card, make_precon_deck)
    res = runner.invoke(app, ["deck", "construct-from-loose", "LooseKit_TST", "--dry-run"])
    assert res.exit_code == 0, res.stdout
    assert "dry run" in res.stdout.lower()
    from magic_manager import db
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM deck_assignments").fetchone()[0] == 0


# ---------- unified SLD identity resolution (earmark add == resolve-product) ----------

def test_resolve_identity_sld_unifies_name_shapes(monkeypatch):
    """The shared checkpoint resolves BOTH the bare drop name and the store /
    sealedProduct name (scaffold + finish marker), preserving the finish — so
    `mm earmark add` and `mm resolve-product sld` accept the same names and the
    two editions of a drop stay distinct. Regression for the resolver seam."""
    from magic_manager import cli, sld
    monkeypatch.setattr(sld, "identify_drop",
                        lambda s: {"name": "Far Out, Man", "release_date": "2022-05-06"})

    # Bare, unmarked drop name → nonfoil, canonical name unchanged.
    nf = cli._resolve_identity("sld", "Far Out, Man")
    assert nf["kind"] == "sld" and nf["subtype"] == "nonfoil"
    assert nf["name"] == "Far Out, Man" and nf["category"] == "secret_lair"

    # Store/sealedProduct name w/ scaffold + finish marker (was broken pre-unify)
    # → foil, canonical name gains a " (Foil Edition)" discriminator.
    foil = cli._resolve_identity(
        "sld", "Secret Lair Drop Secret Lair x Far Out Man Rainbow Foil")
    assert foil["subtype"] == "foil"
    assert foil["name"] == "Far Out, Man (Foil Edition)"

    # The two editions produce DISTINCT canonical names (distinct earmark rows).
    assert nf["name"] != foil["name"]

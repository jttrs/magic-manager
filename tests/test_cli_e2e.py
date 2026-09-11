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
    # missing-set writes artifacts to a relative Path("queries") — chdir into a
    # throwaway dir so the test never pollutes the repo's queries/.
    monkeypatch.chdir(tmp_path)
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
    # headline reflects 1 missing printing; artifacts written to queries/
    assert "Missing from set:tla" in res.stdout


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

"""Deck kind (playable deck vs card pool): classifier, V29 columns, backfill, set-kind."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from magic_manager import db, decks, mtgjson
from magic_manager.cli import app


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr(mtgjson, "_scene_box_component", lambda *a, **k: False)
    monkeypatch.setattr(mtgjson, "deck", lambda fn: (_ for _ in ()).throw(RuntimeError("offline")))


@pytest.mark.parametrize("name,ptype,n,expected", [
    ("Lands", "Bundle Land Pack", 30, "pool"),
    ("Starter Collection", "Box Set", 40, "pool"),
    ("Huge", "Box Set", 387, "pool"),
    ("Drop", "Secret Lair Drop", 5, "pool"),
    ("Drop", "Secret Lair Drop", 60, "deck"),
    ("Generic", "Box Set", 15, "pool"),
    ("Jump", "Jumpstart", 20, "deck"),
    ("Schemes", "Enemy Deck", 0, "deck"),
    ("Schemes", "Archenemy Deck", 0, "deck"),
    ("Cmdr", "Commander Deck", 100, "deck"),
])
def test_precon_kind_rules(offline, name, ptype, n, expected):
    assert mtgjson.precon_kind("X_ABC", name=name, product_type=ptype, playable_cards=n) == expected


def test_precon_kind_scene_box_component(monkeypatch):
    monkeypatch.setattr(mtgjson, "_scene_box_component", lambda *a, **k: True)
    assert mtgjson.precon_kind("X_ABC", name="Black Sun", product_type="Box Set", playable_cards=60) == "pool"


def test_precon_kind_tolerates_failures(offline):
    assert mtgjson.precon_kind("Unknown_XYZ", name="Thing") == "deck"


def test_migration_adds_columns(tmp_db):
    decks.deck_create("a", "A")
    with db.connect() as c:
        info = {r["name"]: r for r in c.execute("PRAGMA table_info(decks)")}
        row = c.execute("SELECT kind, kind_source FROM decks WHERE slug='a'").fetchone()
    assert info["kind"]["dflt_value"] == "'deck'" and "kind_source" in info
    assert (row["kind"], row["kind_source"]) == ("deck", None)
    with pytest.raises(Exception), db.connect() as c:
        c.execute("UPDATE decks SET kind = 'bogus'")


def test_backfill_classifies_respects_overrides_idempotent(tmp_db, seed_cards, make_card, monkeypatch, offline):
    monkeypatch.setattr(mtgjson, "_decklist_by_filename", lambda: {
        "Lands_ABC": {"type": "Bundle Land Pack"}, "Real_ABC": {"type": "Commander Deck"},
        "Mine_ABC": {"type": "Bundle Land Pack"}})
    seed_cards([make_card(id="c1", name="One", collector_number="1")])
    for slug, fn in (("lands", "Lands_ABC"), ("real", "Real_ABC"), ("mine", "Mine_ABC")):
        decks.deck_create(slug, slug, source_precon_file_name=fn)
        decks.deck_add_card(slug, "c1", "main", "nonfoil", 30 if slug == "real" else 5)
    decks.deck_create("imp", "imp")  # non-precon stays deck
    with db.connect() as c:
        c.execute("UPDATE decks SET kind_source = NULL WHERE source_precon_file_name IS NOT NULL")
    assert decks.unclassified_precon_count() == 3
    decks.set_kind("mine", "deck")
    r = decks.backfill_kinds()
    kinds = {d.slug: (d.kind, d.kind_source) for d in decks.deck_list()}
    assert kinds["lands"] == ("pool", "auto") and kinds["real"] == ("deck", "auto")
    assert kinds["mine"] == ("deck", "user") and kinds["imp"] == ("deck", None)
    assert r["classified"] == 2
    assert decks.backfill_kinds()["changed"] == 0


def test_set_kind_cli(tmp_db):
    decks.deck_create("a", "A")
    runner = CliRunner()
    res = runner.invoke(app, ["deck", "set-kind", "a", "pool"])
    assert res.exit_code == 0, res.output
    d = decks.deck_get("a")
    assert (d.kind, d.kind_source) == ("pool", "user")
    assert runner.invoke(app, ["deck", "set-kind", "a", "nope"]).exit_code == 2
    assert runner.invoke(app, ["deck", "set-kind", "zzz", "deck"]).exit_code == 2
    assert "pool" in runner.invoke(app, ["deck", "ls"]).output

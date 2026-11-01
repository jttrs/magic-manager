"""Census reconciliation: a filled add-mode sheet + off-sheet products -> target,
diffed against owned inventory (adds / removals), never below pledged."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

from magic_manager import census, db, decks, ingest, inventory, mtgjson, util

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "census_reconcile_script", ROOT / "scripts" / "census_reconcile.py")
script = importlib.util.module_from_spec(_spec)
sys.modules["census_reconcile_script"] = script
_spec.loader.exec_module(script)

HEADER = ["set", "collector_number", "name", "qty_normal", "qty_foil"]


@pytest.fixture
def world(seed_cards, make_card, tmp_path, monkeypatch):
    seed_cards([
        make_card(id="tst-a", set="tst", collector_number="1", name="Alpha"),
        make_card(id="tst-b", set="tst", collector_number="2", name="Beta"),
        make_card(id="tst-c", set="tst", collector_number="10", name="Gamma"),
        make_card(id="oth-z", set="oth", collector_number="1", name="Outsider"),
    ])
    monkeypatch.setattr(util, "OUTPUT_ROOT", tmp_path / "output")
    return tmp_path


def sheet(tmp_path, rows, name="tst-add-checklist.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "checklist"
    ws.append(HEADER)
    for r in rows:
        ws.append(r)
    path = tmp_path / name
    wb.save(path)
    return path


def recipes(monkeypatch, table):
    def fake(f, **k):
        if f not in table:
            raise mtgjson.MtgJsonError(f"mtgjson.sh deck {f} exited 1")
        return dict(table[f])

    monkeypatch.setattr(decks, "precon_recipe_needs", fake)


def own(sid, finish, qty):
    with db.connect() as c:
        inventory.inventory_add(sid, finish, qty, conn=c)


def owned(sid, finish):
    with db.connect() as c:
        r = c.execute("SELECT quantity FROM inventory WHERE scryfall_id=? AND finish=?",
                      (sid, finish)).fetchone()
    return r["quantity"] if r else 0


def pledge(sid, finish, n, slug="d1"):
    decks.deck_create(slug, slug)
    with db.connect() as c:
        deck_id = c.execute("SELECT deck_id FROM decks WHERE slug=?", (slug,)).fetchone()["deck_id"]
        c.execute("INSERT INTO deck_assignments (deck_id, scryfall_id, finish, count, assigned_at) "
                  "VALUES (?,?,?,?,'2026-01-01')", (deck_id, sid, finish, n))


def by_key(lines):
    return {(ln.scryfall_id, ln.finish): ln for ln in lines}


def test_plan_adds_removals_with_product(world, monkeypatch):
    path = sheet(world, [
        ["tst", 1, "Alpha", 3, None],       # int cn from openpyxl
        ["tst", 2, "Beta", None, 1],
        ["tst", 10, "Gamma", 1, None],
    ])
    recipes(monkeypatch, {"deckA": {("tst-a", "nonfoil"): 1, ("tst-c", "foil"): 2}})
    own("tst-a", "nonfoil", 1)     # target 3+1=4 -> add 3
    own("tst-b", "foil", 5)        # target 1 -> remove 4
    own("tst-c", "nonfoil", 1)     # target 1 -> equal

    p = census.plan(path, ["deckA"])
    assert p.anchor == "tst"
    adds, rems = by_key(p.adds), by_key(p.removals)
    assert adds[("tst-a", "nonfoil")].change == 3
    assert adds[("tst-a", "nonfoil")].products == 1
    # product card whose cell is empty on the sheet still adds
    c_foil = adds[("tst-c", "foil")]
    assert (c_foil.census, c_foil.products, c_foil.change) == (0, 2, 2)
    assert rems[("tst-b", "foil")].change == 4
    assert ("tst-c", "nonfoil") not in adds and ("tst-c", "nonfoil") not in rems
    assert p.below_pledged == []
    assert (p.census_copies, p.product_copies, p.target_copies, p.owned_copies) == (5, 3, 8, 7)
    # sorted by set then numeric cn
    assert [ln.cn for ln in p.adds] == ["1", "10"]
    assert p.to_dict()["totals"]["removal_copies"] == 4
    assert owned("tst-a", "nonfoil") == 1  # dry: nothing written


def test_below_pledged_refused(world, monkeypatch):
    path = sheet(world, [["tst", 1, "Alpha", 1, None]])
    recipes(monkeypatch, {})
    own("tst-a", "nonfoil", 4)
    pledge("tst-a", "nonfoil", 3)  # target 1 -> would leave 1 < pledged 3
    p = census.plan(path, [])
    assert [ln.scryfall_id for ln in p.below_pledged] == ["tst-a"]
    with pytest.raises(census.CensusRefused) as ei:
        census.apply(path, [])
    assert ei.value.plan.below_pledged
    assert owned("tst-a", "nonfoil") == 4
    with db.connect() as c:
        assert c.execute("SELECT COUNT(*) n FROM ingest_events WHERE label LIKE 'census:%'"
                         ).fetchone()["n"] == 0


def test_apply_writes_two_events(world, monkeypatch):
    path = sheet(world, [
        ["tst", 1, "Alpha", 3, None],
        ["tst", 2, "Beta", 1, 1],
        ["tst", 10, "Gamma", None, None],
    ])
    recipes(monkeypatch, {"deckA": {("tst-a", "nonfoil"): 1}})
    own("tst-a", "nonfoil", 1)   # target 4 -> update (+3)
    own("tst-b", "foil", 3)      # target 1 -> update (-2)
    own("tst-c", "nonfoil", 2)   # target 0 -> zeroed
    # tst-b nonfoil: new row (+1)

    result = census.apply(path, ["deckA"])
    assert result["added_copies"] == 4 and result["removed_copies"] == 4

    assert owned("tst-a", "nonfoil") == 4
    assert owned("tst-b", "nonfoil") == 1
    assert owned("tst-b", "foil") == 1
    assert owned("tst-c", "nonfoil") == 0
    with db.connect() as c:
        add_ev = c.execute("SELECT * FROM ingest_events WHERE ingest_id=?",
                           (result["adds_event"],)).fetchone()
        rem_ev = c.execute("SELECT * FROM ingest_events WHERE ingest_id=?",
                           (result["removals_event"],)).fetchone()
        assert (add_ev["method"], add_ev["label"]) == ("import-block", "census:tst loose cards")
        assert (rem_ev["method"], rem_ev["label"]) == ("adhoc", "census:tst over-count removal")
        assert (add_ev["rows_added"], add_ev["rows_updated"]) == (1, 1)
        assert (rem_ev["rows_zeroed"], rem_ev["rows_updated"]) == (1, 1)
        assert ingest.reconcile_inventory_ledger(c) == []
        # one delta per touched pair, not doubled
        assert c.execute("SELECT SUM(delta) s FROM inventory_events WHERE ingest_id=?",
                         (result["adds_event"],)).fetchone()["s"] == 4
    p = census.plan(path, ["deckA"])
    assert p.adds == [] and p.removals == []
    again = census.apply(path, ["deckA"])
    assert again["adds_event"] is None and again["removals_event"] is None


def test_product_outside_sheet(world, monkeypatch):
    path = sheet(world, [["tst", 1, "Alpha", 1, None]])
    recipes(monkeypatch, {"deckX": {("oth-z", "nonfoil"): 1}})
    with pytest.raises(census.CensusError, match="not on the sheet"):
        census.plan(path, ["deckX"])


def test_unresolved_rows_and_bad_input(world, monkeypatch):
    recipes(monkeypatch, {})
    bad = sheet(world, [["tst", 1, "Alpha", 1, None], ["nope", 7, "Ghost", 1, None],
                        ["nope", 8, "Spook", None, None]])
    with pytest.raises(census.CensusError) as ei:
        census.plan(bad, [])
    msg = str(ei.value)
    assert "nope 7 Ghost" in msg and "nope 8 Spook" in msg and "mm set sync nope" in msg

    neg = sheet(world, [["tst", 1, "Alpha", -1, None]], name="neg.xlsx")
    with pytest.raises(census.CensusError, match="Alpha"):
        census.plan(neg, [])
    txt = sheet(world, [["tst", 1, "Alpha", "x", None]], name="txt.xlsx")
    with pytest.raises(census.CensusError, match="non-negative"):
        census.plan(txt, [])

    md = world / "x.md"
    md.write_text("hi")
    with pytest.raises(census.CensusError, match="XLSX"):
        census.read_census(md)


def test_driver_exit_codes(world, monkeypatch, capsys):
    path = sheet(world, [["tst", 1, "Alpha", 2, None]])
    recipes(monkeypatch, {"deckA": {("tst-a", "nonfoil"): 1}})
    monkeypatch.setattr(script, "CHECKLISTS_DIR", world / "elsewhere")

    # dry run -> 0, nothing written, report files exist
    assert script.main([str(path), "--product", "deckA"]) == 0
    assert "adds:" in capsys.readouterr().out
    assert owned("tst-a", "nonfoil") == 0
    assert list((world / "output" / "census" / "reports").glob("tst-census-*.json"))

    # bad input -> 2
    assert script.main([str(world / "missing.xlsx")]) == 2
    assert script.main([str(path), "--product", "unknownDeck"]) == 2
    capsys.readouterr()

    # refused -> 1
    own("tst-b", "nonfoil", 1)
    own("tst-a", "nonfoil", 5)
    pledge("tst-a", "nonfoil", 5)
    assert script.main([str(path)]) == 1
    assert "nothing written" in capsys.readouterr().err
    assert owned("tst-a", "nonfoil") == 5


def test_driver_apply_archives(world, monkeypatch, capsys):
    active = world / "checklists"
    active.mkdir()
    path = sheet(active, [["tst", 1, "Alpha", 2, None]], name="tst-add-checklist.xlsx")
    recipes(monkeypatch, {})
    monkeypatch.setattr(script, "CHECKLISTS_DIR", active)
    monkeypatch.setattr(script, "PROCESSED_DIR", active / "processed")
    monkeypatch.setattr(script.db, "snapshot", lambda label=None, **k: world / f"snap-{label}")

    assert script.main([str(path), "--apply"]) == 0
    out = capsys.readouterr().out
    assert "snap-pre-census-tst" in out
    assert owned("tst-a", "nonfoil") == 2
    assert not path.exists()
    assert len(list((active / "processed").glob("tst-census-*.xlsx"))) == 1

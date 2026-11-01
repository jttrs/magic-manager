"""Census reconciliation: a filled add-mode sheet + off-sheet products -> target,
diffed against owned inventory (adds / removals), never below pledged."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

from magic_manager import census, db, decks, ingest, inventory, mtgjson, sets, util

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


def sheet(tmp_path, rows, name="tst-add-checklist.xlsx", meta=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "checklist"
    ws.append(HEADER)
    for r in rows:
        ws.append(r)
    if meta is not None:
        ms = wb.create_sheet("_meta")
        ms.append(["key", "value"])
        for k, v in meta.items():
            ms.append([k, v])
    path = tmp_path / name
    wb.save(path)
    return path


def recipes(monkeypatch, table, tokens=None):
    """Fake ``decks.precon_recipe_needs``; ``tokens`` = extra token-board cards per
    fileName, returned only for ``include_tokens=True``. Calls are logged on
    ``fake.calls`` as ``(fileName, include_tokens)``."""
    calls = []

    def fake(f, *, include_tokens=False):
        calls.append((f, include_tokens))
        if f not in table:
            raise mtgjson.MtgJsonError(f"mtgjson.sh deck {f} exited 1")
        out = dict(table[f])
        if include_tokens:
            out.update((tokens or {}).get(f, {}))
        return out

    fake.calls = calls
    monkeypatch.setattr(decks, "precon_recipe_needs", fake)
    return fake


def own(sid, finish, qty):
    with db.connect() as c:
        inventory.inventory_add(sid, finish, qty, conn=c)


def owned(sid, finish):
    with db.connect() as c:
        r = c.execute("SELECT quantity FROM inventory WHERE scryfall_id=? AND finish=?",
                      (sid, finish)).fetchone()
    return r["quantity"] if r else 0


def pledge(sid, finish, n, slug="d1", file_name=None):
    """Pledge ``n`` copies to deck ``slug`` (created on first use; ``file_name`` =
    the precon product it is a copy of)."""
    with db.connect() as c:
        exists = c.execute("SELECT 1 FROM decks WHERE slug=?", (slug,)).fetchone()
    if not exists:
        decks.deck_create(slug, slug, source_precon_file_name=file_name)
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


def force_below_pledged(monkeypatch):
    """below_pledged is a safety net that the deck-aware target makes unreachable
    from real data; inject a line to exercise the refusal paths."""
    real = census._build

    def build(*a, **k):
        p = real(*a, **k)
        p.below_pledged = list(p.removals) or p.adds[:1]
        return p

    monkeypatch.setattr(census, "_build", build)


def test_below_pledged_refused(world, monkeypatch):
    path = sheet(world, [["tst", 1, "Alpha", 1, None]])
    recipes(monkeypatch, {})
    own("tst-a", "nonfoil", 4)
    force_below_pledged(monkeypatch)
    p = census.plan(path, [])
    assert [ln.scryfall_id for ln in p.below_pledged] == ["tst-a"]
    with pytest.raises(census.CensusRefused) as ei:
        census.apply(path, [])
    assert ei.value.plan.below_pledged
    assert owned("tst-a", "nonfoil") == 4
    with db.connect() as c:
        assert c.execute("SELECT COUNT(*) n FROM ingest_events WHERE label LIKE 'census:%'"
                         ).fetchone()["n"] == 0


def test_custom_built_deck_pledge_counts_as_off_sheet(world, monkeypatch):
    path = sheet(world, [["tst", 1, "Alpha", 2, None]])
    recipes(monkeypatch, {})
    own("tst-a", "nonfoil", 3)
    pledge("tst-a", "nonfoil", 1, slug="custom")  # a built deck the user did not name
    p = census.plan(path, [])
    assert p.adds == [] and p.removals == [] and p.below_pledged == []
    assert (p.census_copies, p.deck_copies, p.target_copies, p.owned_copies) == (2, 1, 3, 3)
    assert p.to_dict()["totals"]["deck_copies"] == 1
    result = census.apply(path, [])
    assert result["removals_event"] is None and result["removed_copies"] == 0
    assert owned("tst-a", "nonfoil") == 3


def test_deck_pledge_stale_only_adds(world, monkeypatch):
    # a pledge beyond owned can only produce an add (visible + revertible), never a removal
    path = sheet(world, [["tst", 1, "Alpha", 1, None]])
    recipes(monkeypatch, {})
    own("tst-a", "nonfoil", 1)
    pledge("tst-a", "nonfoil", 3, slug="custom")
    p = census.plan(path, [])
    assert p.removals == [] and [(ln.change, ln.in_decks) for ln in p.adds] == [(3, 3)]


def test_named_half_pledged_precon_counts_full_recipe(world, monkeypatch):
    path = sheet(world, [["tst", 1, "Alpha", None, None]])
    recipes(monkeypatch, {"deckA": {("tst-a", "nonfoil"): 2}})
    own("tst-a", "nonfoil", 2)
    pledge("tst-a", "nonfoil", 1, slug="deck-a", file_name="deckA")
    p = census.plan(path, ["deckA"])
    assert p.adds == [] and p.removals == []
    # the recipe, not recipe + pledges: the deck is claimed by the named product
    assert (p.product_copies, p.deck_copies, p.target_copies) == (2, 0, 2)


def test_named_precon_claims_deck_with_most_pledges(world, monkeypatch):
    path = sheet(world, [["tst", 1, "Alpha", None, None]])
    recipes(monkeypatch, {"deckA": {("tst-a", "nonfoil"): 1}})
    own("tst-a", "nonfoil", 4)
    pledge("tst-a", "nonfoil", 1, slug="a-1", file_name="deckA")
    pledge("tst-a", "nonfoil", 3, slug="a-2", file_name="deckA")
    p = census.plan(path, ["deckA"])
    # a-2 (3 pledged) is claimed -> max(1, 3); a-1 is unnamed -> its 1 pledge
    assert (p.product_copies, p.deck_copies, p.target_copies) == (3, 1, 4)
    assert p.adds == [] and p.removals == []


def test_edited_precon_pledge_outside_recipe_is_kept(world, monkeypatch):
    path = sheet(world, [["tst", 1, "Alpha", None, None], ["tst", 2, "Beta", None, None]])
    recipes(monkeypatch, {"deckA": {("tst-a", "nonfoil"): 1}})
    own("tst-a", "nonfoil", 1)
    own("tst-b", "foil", 1)  # swapped into the deck: pledged but not in the recipe
    pledge("tst-a", "nonfoil", 1, slug="deck-a", file_name="deckA")
    pledge("tst-b", "foil", 1, slug="deck-a", file_name="deckA")
    p = census.plan(path, ["deckA"])
    assert p.adds == [] and p.removals == []
    assert p.product_copies == 2


def test_repeated_product_doubles_recipe(world, monkeypatch):
    path = sheet(world, [["tst", 1, "Alpha", 1, None]])
    recipes(monkeypatch, {"deckA": {("tst-a", "nonfoil"): 1}})
    p = census.plan(path, ["deckA", "deckA"])
    (ln,) = p.adds
    assert (ln.census, ln.products, ln.target, ln.change) == (1, 2, 3, 3)


def test_modify_mode_sheet_refused(world, monkeypatch):
    recipes(monkeypatch, {})
    meta = {"kind": "inventory", "mode": "modify", "anchor_code": "tst"}
    path = sheet(world, [["tst", 1, "Alpha", 1, None]], meta=meta)
    with pytest.raises(census.CensusError, match="add-mode.*mm set master-list"):
        census.plan(path, [])
    assert script.main([str(path)]) == 2
    other = sheet(world, [["tst", 1, "Alpha", 1, None]], name="m.xlsx",
                  meta={"kind": "missing", "mode": "add"})
    with pytest.raises(census.CensusError, match="kind=missing"):
        census.plan(other, [])


def test_token_sheet_counts_product_tokens(world, monkeypatch):
    fake = recipes(monkeypatch, {"deckA": {("tst-a", "nonfoil"): 1}},
                   tokens={"deckA": {("tst-c", "nonfoil"): 1}})
    own("tst-a", "nonfoil", 1)
    own("tst-c", "nonfoil", 1)  # the product's token, kept off the sheet
    rows = [["tst", 1, "Alpha", None, None], ["tst", 10, "Gamma", None, None]]
    with_tokens = sheet(world, rows, meta={"kind": "inventory", "mode": "add",
                                           "anchor_code": "tst", "include_tokens": "1"})
    p = census.plan(with_tokens, ["deckA"])
    assert p.adds == [] and p.removals == []
    assert fake.calls[-1] == ("deckA", True)
    result = census.apply(with_tokens, ["deckA"])
    assert result["removed_copies"] == 0 and owned("tst-c", "nonfoil") == 1

    plain = sheet(world, rows, name="plain.xlsx", meta={"kind": "inventory", "mode": "add",
                                                        "anchor_code": "tst", "include_tokens": "0"})
    p = census.plan(plain, ["deckA"])
    assert fake.calls[-1] == ("deckA", False)
    assert [ln.scryfall_id for ln in p.removals] == ["tst-c"]


def test_master_list_roundtrip_uses_meta_anchor(world, monkeypatch):
    recipes(monkeypatch, {})
    out = world / "tst-add-checklist.xlsx"
    sets.write_master_list_xlsx(["oth", "tst"], out, anchor_code="tst",
                                prepopulate_from_inventory=False)
    p = census.plan(out, [])
    assert p.anchor == "tst"  # from _meta, not the first row's set
    assert p.adds == [] and p.removals == []
    assert p.census_copies == 0


def test_revert_both_census_events(world, monkeypatch):
    path = sheet(world, [["tst", 1, "Alpha", 3, None], ["tst", 2, "Beta", None, 1]])
    recipes(monkeypatch, {})
    own("tst-a", "nonfoil", 1)
    own("tst-b", "foil", 3)
    result = census.apply(path, [])
    assert owned("tst-a", "nonfoil") == 3 and owned("tst-b", "foil") == 1
    assert result["adds_event"] and result["removals_event"]
    for key in ("removals_event", "adds_event"):
        ingest.revert_event(result[key], dry_run=False)
    assert owned("tst-a", "nonfoil") == 1 and owned("tst-b", "foil") == 3
    with db.connect() as c:
        assert ingest.reconcile_inventory_ledger(c) == []


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
    own("tst-a", "nonfoil", 5)
    force_below_pledged(monkeypatch)
    assert script.main([str(path)]) == 1
    assert "nothing written" in capsys.readouterr().err
    assert owned("tst-a", "nonfoil") == 5


def test_driver_json_refused_and_apply_refusal(world, monkeypatch, capsys):
    path = sheet(world, [["tst", 1, "Alpha", 1, None]])
    recipes(monkeypatch, {})
    monkeypatch.setattr(script, "CHECKLISTS_DIR", world / "elsewhere")
    snaps = []
    monkeypatch.setattr(script.db, "snapshot", lambda **k: snaps.append(k) or world / "snap")
    own("tst-a", "nonfoil", 4)
    force_below_pledged(monkeypatch)

    assert script.main([str(path), "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "refused" and out["totals"]["below_pledged"] == 1

    assert script.main([str(path), "--json", "--apply"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "refused" and "applied" not in out
    assert script.main([str(path), "--apply"]) == 1
    assert "nothing written" in capsys.readouterr().err
    assert snaps == [] and path.exists()
    assert owned("tst-a", "nonfoil") == 4
    with db.connect() as c:
        assert c.execute("SELECT COUNT(*) n FROM ingest_events WHERE label LIKE 'census:%'"
                         ).fetchone()["n"] == 0


def test_driver_json_status_ok_and_applied(world, monkeypatch, capsys):
    path = sheet(world, [["tst", 1, "Alpha", 2, None]])
    recipes(monkeypatch, {})
    monkeypatch.setattr(script, "CHECKLISTS_DIR", world / "elsewhere")
    monkeypatch.setattr(script.db, "snapshot", lambda label=None, **k: world / f"snap-{label}")
    assert script.main([str(path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
    assert script.main([str(path), "--json", "--apply", "--no-archive"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "applied" and out["applied"]["added_copies"] == 2


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

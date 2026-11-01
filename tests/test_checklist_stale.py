"""Modify-checklist staleness guard: ``ingest_inventory_from_xlsx`` (replace mode)
refuses when the ledger shows a row it would change moved since the file's
``_meta.generated_at`` — a stale sheet would silently set it back."""
from __future__ import annotations

import json

import pytest

from magic_manager import db, ingest, inventory, sets

GENERATED = "2021-01-01T00:00:00+00:00"


def _qty(sid, fin):
    with db.connect() as c:
        r = c.execute("SELECT quantity FROM inventory WHERE scryfall_id=? AND finish=?", (sid, fin)).fetchone()
        return r["quantity"] if r else 0


def _event_count():
    with db.connect() as c:
        return c.execute("SELECT COUNT(*) FROM ingest_events").fetchone()[0]


def _md(path, rows, generated_at=GENERATED, mode="modify", extra_meta=""):
    """MD checklist (rows: (cn, nonfoil, foil)); ``generated_at=None`` → no frontmatter."""
    head = ""
    if generated_at is not None:
        head = f"---\nmode: {mode}\nanchor_code: tst\n{extra_meta}generated_at: {generated_at}\n---\n"
    path.write_text(head + "\n".join(f"- (TST) {cn} [N:{n} F:{f}] — card {cn}" for cn, n, f in rows) + "\n",
                    encoding="utf-8")
    return path


@pytest.fixture
def stale_db(seed_cards, make_card, fake_scryfall):
    cards = [make_card(id=sid, name=name, collector_number=cn)
             for sid, name, cn in (("a", "Alpha", "1"), ("b", "Beta", "2"), ("c", "Gamma", "3"))]
    seed_cards(cards)
    fake_scryfall(collection_found=cards)
    inventory.inventory_add("a", "nonfoil", 3)
    inventory.inventory_add("c", "foil", 1)
    with db.connect() as c:   # the seed ledger predates the sheet
        c.execute("UPDATE inventory_events SET at = '2020-01-01T00:00:00+00:00'")
        c.execute("UPDATE ingest_events SET at = '2020-01-01T00:00:00+00:00'")
    # The collection moves AFTER the sheet was generated: a 3 → 4.
    inventory.inventory_add("a", "nonfoil", 1)


def test_stale_row_refused_and_nothing_written(stale_db, tmp_path):
    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 5, 0), ("2", 2, 0)])
    events_before = _event_count()
    with pytest.raises(sets.StaleCounts) as e:
        sets.ingest_inventory_from_xlsx(md, mode="replace", label="set:tst")
    assert e.value.rows == [{"scryfall_id": "a", "finish": "nonfoil", "expected": 3, "current": 4}]
    assert "1 row(s) changed since this checklist was generated" in str(e.value)
    assert (_qty("a", "nonfoil"), _qty("b", "nonfoil")) == (4, 0)   # the fresh row "b" was not written either
    assert _event_count() == events_before
    with db.connect() as c:
        assert ingest.reconcile_inventory_ledger(c) == []


def test_allow_stale_applies(stale_db, tmp_path):
    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 5, 0), ("2", 2, 0)])
    res = sets.ingest_inventory_from_xlsx(md, mode="replace", label="set:tst", allow_stale=True)
    assert (res["added"], res["updated"]) == (1, 1)
    assert (_qty("a", "nonfoil"), _qty("b", "nonfoil")) == (5, 2)


def test_changed_row_already_at_sheet_value_is_not_stale(stale_db, tmp_path):
    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 4, 0), ("2", 2, 0)])
    res = sets.ingest_inventory_from_xlsx(md, mode="replace", label="set:tst")
    assert (res["added"], res["updated"]) == (1, 0)
    assert (_qty("a", "nonfoil"), _qty("b", "nonfoil")) == (4, 2)


def test_file_without_generated_at_skips_the_check(stale_db, tmp_path):
    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 5, 0)], generated_at=None)
    assert sets.ingest_inventory_from_xlsx(md, mode="replace", label="set:tst")["updated"] == 1
    assert _qty("a", "nonfoil") == 5


def test_generated_after_the_change_is_fresh(stale_db, tmp_path):
    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 5, 0)], generated_at="2999-01-01T00:00:00+00:00")
    assert sets.ingest_inventory_from_xlsx(md, mode="replace", label="set:tst")["updated"] == 1


def test_zero_untouched_reports_absent_row_that_moved(stale_db, tmp_path):
    inventory.inventory_add("c", "foil", 2)       # absent from the file, changed since generation
    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 4, 0)])   # "a" already at 4 → fine
    events_before = _event_count()
    with pytest.raises(sets.StaleCounts) as e:
        sets.ingest_inventory_from_xlsx(md, mode="replace", zero_untouched=True, label="set:tst")
    assert e.value.rows == [{"scryfall_id": "c", "finish": "foil", "expected": 1, "current": 3}]
    assert _qty("c", "foil") == 3 and _event_count() == events_before
    # Without zero_untouched the absent row isn't touched, so nothing is stale.
    assert sets.ingest_inventory_from_xlsx(md, mode="replace", label="set:tst")["updated"] == 0


def test_cli_stale_exit_code_and_json(stale_db, tmp_path):
    from typer.testing import CliRunner
    from magic_manager.cli import app, EXIT_STALE_CHECKLIST

    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 5, 0)])
    runner = CliRunner()
    res = runner.invoke(app, ["set", "ingest", "--path", str(md), "--no-zero-untouched", "--json"])
    assert res.exit_code == EXIT_STALE_CHECKLIST == 5, res.output
    out = json.loads(res.stdout)
    assert out["status"] == "stale" and out["rows"][0]["expected"] == 3
    assert md.exists() and _qty("a", "nonfoil") == 4

    res = runner.invoke(app, ["set", "ingest", "--path", str(md), "--no-zero-untouched"])
    assert res.exit_code == 5
    assert "sheet 3 → now 4" in res.output and "--allow-stale" in res.output


def test_additive_sheet_is_never_checked(stale_db, tmp_path):
    md = _md(tmp_path / "tst-add-checklist.md", [("1", 2, 0), ("2", 1, 0)], mode="add")
    res = sets.ingest_inventory_from_xlsx(md, mode="additive", label="set:tst")   # no StaleCounts
    assert (res["added"], res["updated"]) == (1, 1)
    assert (_qty("a", "nonfoil"), _qty("b", "nonfoil")) == (6, 1)    # 4 + 2: qty += cell


def test_card_listed_twice_keeps_sequential_semantics_and_reports_once(stale_db, tmp_path):
    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 5, 0), ("1", 2, 0)])
    with pytest.raises(sets.StaleCounts) as e:
        sets.ingest_inventory_from_xlsx(md, mode="replace", label="set:tst")
    # One row, with the REAL stored count as `current` (not the projection of the first line).
    assert e.value.rows == [{"scryfall_id": "a", "finish": "nonfoil", "expected": 3, "current": 4}]
    assert _qty("a", "nonfoil") == 4
    sets.ingest_inventory_from_xlsx(md, mode="replace", label="set:tst", allow_stale=True)
    assert _qty("a", "nonfoil") == 2                                  # sequential SETs: the later line wins


def test_card_listed_twice_with_net_no_change_is_not_stale(stale_db, tmp_path):
    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 5, 0), ("1", 4, 0)])
    sets.ingest_inventory_from_xlsx(md, mode="replace", label="set:tst")   # ends where it started
    assert _qty("a", "nonfoil") == 4


def test_cli_allow_stale_applies_and_archives(stale_db, tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from magic_manager.cli import app

    monkeypatch.chdir(tmp_path)
    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 5, 0)])
    res = CliRunner().invoke(app, ["set", "ingest", "--path", str(md), "--no-zero-untouched", "--allow-stale"])
    assert res.exit_code == 0, res.output
    assert _qty("a", "nonfoil") == 5 and not md.exists()


def test_cli_stale_json_carries_labels_and_a_regenerate_command(stale_db, tmp_path):
    from typer.testing import CliRunner
    from magic_manager.cli import app

    md = _md(tmp_path / "tst-modify-checklist.md", [("1", 5, 0)],
             extra_meta="set_codes: tst\nrarity_filter: rare\nkind: inventory\n")
    res = CliRunner().invoke(app, ["set", "ingest", "--path", str(md), "--no-zero-untouched", "--json"])
    assert res.exit_code == 5, res.output
    out = json.loads(res.stdout)
    assert (out["status"], out["anchor"], out["mode"], out["kind"]) == ("stale", "tst", "modify", "inventory")
    assert out["rows"] == [{"scryfall_id": "a", "finish": "nonfoil", "expected": 3, "current": 4,
                            "set": "tst", "cn": "1", "name": "Alpha"}]
    cmd = out["regenerate"]
    assert cmd.startswith("uv run mm set master-list tst ")
    for part in ("--only tst", "--rarity rare", "--mode modify", "--format md", f"--out {md}", "--force"):
        assert part in cmd
    # The same labels and both ways out in the text rendering.
    res = CliRunner().invoke(app, ["set", "ingest", "--path", str(md), "--no-zero-untouched"])
    assert res.exit_code == 5
    assert "TST 1 Alpha [nonfoil]: sheet 3 → now 4" in res.output
    assert "regenerate (discards any edits in this file): uv run mm set master-list" in res.output
    assert "add --allow-stale" in res.output

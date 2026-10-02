"""Phase 1 — collection CSV adapter: read_csv / write_csv / resolve_rows.

Offline: the only network boundary (``scryfall.collection``) is monkeypatched via
the ``fake_scryfall`` fixture. ManaBox CSVs carry a Scryfall ID, so resolution is
the id tier (one call), which the fake serves from ``collection_found``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from magic_manager import collection_sync as cs
from magic_manager import config as config_mod

FIXTURES = Path(__file__).parent / "fixtures" / "collection"


# ---------- config/collection_formats.toml ----------

def test_collection_formats_loads_and_has_manabox():
    fmts = config_mod.collection_formats()
    assert "manabox" in fmts
    mb = fmts["manabox"]
    # The load-bearing keys collection_sync depends on.
    assert mb["has_scryfall_id"] is True
    assert mb["confidence"] in ("high", "low")
    for field in ("quantity", "finish", "scryfall_id", "set", "collector_number"):
        assert field in mb["columns"], f"manabox columns missing {field!r}"
    assert mb["write"]["order"]
    assert mb["write"]["condition_default"]


def test_service_format_unknown_raises():
    import pytest as _pytest
    with _pytest.raises(LookupError):
        cs.service_format("nope")


# ---------- read_csv ----------

def test_read_csv_manabox_maps_columns_and_finish():
    rows = cs.read_csv(FIXTURES / "manabox_sample.csv", "manabox")
    assert len(rows) == 3
    by_cn = {r.collector_number: r for r in rows}

    sol = by_cn["263"]
    assert sol.name == "Sol Ring"
    assert sol.set == "c21"            # lowercased
    assert sol.finish == "nonfoil"     # "normal" → nonfoil
    assert sol.qty == 1
    assert sol.scryfall_id == "4cbc6901-6a4a-4d0a-83ea-7eefa3b35021"
    assert sol.condition == "near_mint"
    assert sol.purchase_price == "2.50"

    solemn = by_cn["264"]
    assert solemn.finish == "foil"     # "foil" → foil
    assert solemn.qty == 2
    assert solemn.condition == "mint"


def test_read_csv_unknown_service_raises():
    with pytest.raises(LookupError):
        cs.read_csv(FIXTURES / "manabox_sample.csv", "bogus")


def test_read_csv_skips_zero_qty_and_identityless(tmp_path):
    # A row with qty 0 and a row with no id/set+cn are both dropped.
    p = tmp_path / "edge.csv"
    p.write_text(
        "Name,Set code,Collector number,Foil,Quantity,Scryfall ID,Condition,Purchase price\n"
        "Zero Qty,c21,1,normal,0,,near_mint,\n"            # qty 0 → skip
        "No Identity,,,normal,2,,near_mint,\n"             # no id, no set+cn → skip
        "Keeper,c21,5,normal,1,,near_mint,\n"             # set+cn → kept
    )
    rows = cs.read_csv(p, "manabox")
    assert [r.name for r in rows] == ["Keeper"]


# ---------- resolve_rows (id tier) ----------

def test_resolve_rows_fills_id_and_upserts(tmp_db, make_card, fake_scryfall):
    card = make_card(id="4cbc6901-6a4a-4d0a-83ea-7eefa3b35021",
                     name="Sol Ring", set="c21", collector_number="263")
    fake_scryfall(collection_found=[card])
    rows = [cs.CollectionRow(qty=1, finish="nonfoil",
                             scryfall_id="4cbc6901-6a4a-4d0a-83ea-7eefa3b35021",
                             set="c21", collector_number="263", name="Sol Ring")]
    res = cs.resolve_rows(rows)
    assert len(res.resolved) == 1
    assert not res.not_found
    # Card was upserted into the cards table.
    from magic_manager import db
    with db.connect() as conn:
        got = conn.execute("SELECT name FROM cards WHERE scryfall_id = ?",
                            (card["id"],)).fetchone()
    assert got["name"] == "Sol Ring"


def test_resolve_rows_reports_not_found(tmp_db, fake_scryfall):
    fake_scryfall(collection_found=[], collection_not_found=[{"id": "missing"}])
    rows = [cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id="missing",
                             set="c21", collector_number="999", name="Ghost")]
    res = cs.resolve_rows(rows)
    assert not res.resolved
    assert len(res.not_found) == 1
    assert res.not_found[0]["name"] == "Ghost"


# ---------- write_csv + round-trip ----------

def test_write_csv_round_trip(tmp_path):
    rows = [
        cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id="sid-1",
                         set="c21", collector_number="263", name="Sol Ring",
                         condition="near_mint", purchase_price="2.50"),
        cs.CollectionRow(qty=2, finish="foil", scryfall_id="sid-2",
                         set="c21", collector_number="264", name="Solemn Simulacrum",
                         condition="mint"),
    ]
    text = cs.write_csv(rows, "manabox")
    p = tmp_path / "out.csv"
    p.write_text(text)

    back = cs.read_csv(p, "manabox")
    assert len(back) == 2
    b = {r.collector_number: r for r in back}
    # Finish survives the invert→map round trip.
    assert b["263"].finish == "nonfoil"
    assert b["264"].finish == "foil"
    assert b["263"].qty == 1 and b["264"].qty == 2
    assert b["263"].scryfall_id == "sid-1"
    assert b["263"].condition == "near_mint"


def test_write_csv_defaults_missing_condition():
    rows = [cs.CollectionRow(qty=1, finish="nonfoil", scryfall_id="sid-1",
                             set="c21", collector_number="263", name="Sol Ring")]
    text = cs.write_csv(rows, "manabox")
    data_line = text.splitlines()[1]
    assert "near_mint" in data_line  # [write].condition_default

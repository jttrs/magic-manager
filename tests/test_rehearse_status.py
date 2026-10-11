"""rehearse_migration's per-table status classification."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("rehearse_migration", ROOT / "scripts" / "rehearse_migration.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_table_status():
    st = _load()._table_status
    assert st(0, "<absent>", 0, "h") == "NEW"
    assert st(3, "abc", 3, "abc") == "OK"
    assert st(3, "abc", 3, "xyz") == "DIVERGED"
    assert st(3, "abc", 2, "abc") == "DIVERGED"
    assert st(0, "<absent>", 2, "h") == "DIVERGED"  # absent before but populated after


def test_precious_tables_protect_earmark_price_history_from_v32():
    pt = _load()._precious_tables
    assert "earmark_prices" not in pt(31)  # created + seeded by V32 — can't be byte-compared across it
    assert {"earmarked_products", "earmark_links", "earmark_targets", "earmark_prices"} <= set(pt(33))
    assert "ingest_events" in pt(19) and "ingest_events" not in pt(18)


def test_post_merge_upgrade_fingerprints_earmark_price_history():
    spec = importlib.util.spec_from_file_location("post_merge_upgrade", ROOT / "scripts" / "post_merge_upgrade.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "earmark_prices" in dict(mod.OWNERSHIP)

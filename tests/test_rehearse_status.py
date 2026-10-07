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

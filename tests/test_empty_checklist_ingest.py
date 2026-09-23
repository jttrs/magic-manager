"""Regression (F4): a checklist ingest that produces ZERO applicable writes
must NOT leave a status='success' ingest_events row stamped with the file SHA —
otherwise a later legitimate re-ingest of the corrected same-SHA file is falsely
refused as a duplicate.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _write_md(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_noop_checklist_ingest_leaves_no_event(tmp_db, fake_scryfall, tmp_path):
    """A markdown checklist whose only card doesn't resolve produces zero writes
    → the checklist event is deleted, not persisted as success."""
    from magic_manager import db, sets as sets_mod, ingest

    fake_scryfall(collection_found=[])  # nothing resolves → no writes
    md = tmp_path / "empty-add-checklist.md"
    _write_md(md, [
        "- (ZZZ) 999 [N:1 F:0] — [Ghost Card](https://scryfall.com/card/zzz/999)",
    ])

    result = sets_mod.ingest_inventory_from_xlsx(md, mode="additive",
                                                 label="set:zzz", source_sha256="deadfeed")
    assert result["added"] == 0 and result["updated"] == 0 and result["zeroed"] == 0
    assert result["ingest_id"] is None  # engine signalled the no-op

    with db.connect() as conn:
        # No dangling event, and nothing findable by the file SHA.
        assert conn.execute(
            "SELECT COUNT(*) c FROM ingest_events WHERE source_sha256='deadfeed'"
        ).fetchone()["c"] == 0
        assert ingest.find_events_by_sha(conn, "deadfeed") == []
        assert ingest.reconcile_inventory_ledger(conn) == []


def test_real_checklist_ingest_still_records_event(tmp_db, seed_cards, make_card,
                                                   fake_scryfall, tmp_path):
    """A checklist that DOES write keeps its event (guards against the no-op fix
    over-deleting)."""
    from magic_manager import db, sets as sets_mod

    card = make_card(id="rc1", set="tst", collector_number="1", name="Real")
    seed_cards([card])
    # ingest_inventory_from_xlsx → parsers.resolve → scryfall.collection.
    fake_scryfall(collection_found=[card])
    md = tmp_path / "real-add-checklist.md"
    _write_md(md, [
        "- (TST) 1 [N:2 F:0] — [Real](https://scryfall.com/card/tst/1)",
    ])

    result = sets_mod.ingest_inventory_from_xlsx(md, mode="additive",
                                                 label="set:tst", source_sha256="beefcafe")
    assert result["added"] == 1
    assert result["ingest_id"] is not None
    with db.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) c FROM ingest_events WHERE source_sha256='beefcafe'"
        ).fetchone()["c"] == 1
        assert conn.execute(
            "SELECT quantity FROM inventory WHERE scryfall_id='rc1'"
        ).fetchone()["quantity"] == 2

"""One-off historical backfill for the V19 provenance ledger.

After V19 ships, ``inventory_events`` is EMPTY while ``inventory`` holds real
quantities. This script reconstructs the ledger from ground truth so the
invariant ``inventory.quantity == SUM(inventory_events.delta)`` holds EXACTLY,
attributing each copy to the most credible source and dumping the honest
"can't attribute" remainder into a single ``unattributed-backfill`` event.

Attribution sources, highest-confidence first (each capped so the running total
per ``(scryfall_id, finish)`` never exceeds the current inventory quantity — we
never invent copies):

  1. **Precon imports** — every ``decks`` row carrying ``source_precon_file_name``
     is one physical copy of that precon. Its MTGJSON decklist (all boards,
     mirroring ``import_precon``) × the number of such deck rows is the
     contribution. Highest confidence: the decklist is mechanical.
  2. **Checklist ingests** — the carried-over ``ingest_events`` rows (method
     ``checklist``) whose archived XLSX/MD still exists under
     ``checklists/processed/``; the filled quantities are mined per printing.
  3. **Unattributed remainder** — whatever current inventory still has beyond
     (1)+(2) lands on ONE synthetic ``unattributed-backfill`` event. This is the
     honest "provenance unknown" bucket surfaced by ``mm audit provenance``.

Guards: refuses to run if ``inventory_events`` is already populated (unless
``--force``, which first clears backfill-origin events). Idempotent in effect —
a second run reproduces the same ledger. Prints a per-source summary and
asserts exact reconciliation before committing.

Usage
-----
    uv run python scripts/backfill_provenance.py [--force] [--dry-run]

``--dry-run`` computes and reports attribution WITHOUT writing (rolls back).
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

# src/ layout: allow ``python scripts/backfill_provenance.py`` directly.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import db, ingest as ingest_mod  # noqa: E402

PROCESSED_DIR = Path("checklists/processed")


def _current_inventory(conn) -> dict[tuple[str, str], int]:
    return {
        (r["scryfall_id"], r["finish"]): r["quantity"]
        for r in conn.execute("SELECT scryfall_id, finish, quantity FROM inventory")
    }


def _known_sids(conn) -> set[str]:
    return {r["scryfall_id"] for r in conn.execute("SELECT scryfall_id FROM cards")}


def _sid_by_set_cn(conn) -> dict[tuple[str, str], str]:
    """(lower set_code, collector_number) -> scryfall_id, for checklist matching."""
    return {
        (r["set_code"].lower(), str(r["collector_number"])): r["scryfall_id"]
        for r in conn.execute("SELECT set_code, collector_number, scryfall_id FROM cards")
    }


def _precon_contributions(conn) -> dict[tuple[str, str], int]:
    """Sum every precon-sourced deck copy's MTGJSON decklist into per-printing
    contributions. ``count of deck rows for fileName`` × ``decklist qty``.

    Reuses ``decks.precon_recipe_needs(include_tokens=True)`` — the single home
    for the MTGJSON board-walk (tokens INCLUDED here because import_precon writes
    them to inventory too), rather than forking the board keys + extraction."""
    from magic_manager import decks as decks_mod

    file_counts: dict[str, int] = defaultdict(int)
    for r in conn.execute(
        "SELECT source_precon_file_name AS fn, COUNT(*) AS n FROM decks "
        "WHERE source_precon_file_name IS NOT NULL GROUP BY source_precon_file_name"
    ):
        file_counts[r["fn"]] = r["n"]

    contrib: dict[tuple[str, str], int] = defaultdict(int)
    for file_name, copies in file_counts.items():
        try:
            needs = decks_mod.precon_recipe_needs(file_name, include_tokens=True)
        except Exception as e:  # missing/renamed precon JSON — skip, don't crash
            print(f"  warn: could not fetch MTGJSON deck {file_name!r}: {e!r}",
                  file=sys.stderr)
            continue
        for (sid, finish), qty in needs.items():
            contrib[(sid, finish)] += qty * copies
    return contrib


def _checklist_contributions(conn) -> dict[tuple[str, str], int]:
    """Mine filled quantities from the archived files of carried-over checklist
    ingest events. Matches printings by (set, collector_number) against the
    local cards table — no network."""
    from magic_manager import parsers

    sid_index = _sid_by_set_cn(conn)
    contrib: dict[tuple[str, str], int] = defaultdict(int)

    rows = conn.execute(
        "SELECT archived_path FROM ingest_events "
        "WHERE method = 'checklist' AND archived_path IS NOT NULL "
        "AND status = 'success'"
    ).fetchall()
    for r in rows:
        p = Path(r["archived_path"])
        if not p.exists():
            print(f"  warn: archived checklist missing, skipped: {p}", file=sys.stderr)
            continue
        try:
            fmt = parsers.detect_format(p)
            if fmt == "xlsx":
                result = parsers.parse_master_list_xlsx(p)
            elif fmt == "md":
                result = parsers.parse_master_list_md(p)
            else:
                result = parsers.parse_text(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  warn: could not parse {p}: {e!r}", file=sys.stderr)
            continue
        for entry in result.entries:
            if entry.qty <= 0:
                continue
            set_code = (entry.set or "").lower()
            cn = str(entry.collector_number) if entry.collector_number is not None else None
            if not set_code or cn is None:
                continue
            sid = sid_index.get((set_code, cn))
            if sid is None:
                continue
            finish = "foil" if entry.foil else "nonfoil"
            contrib[(sid, finish)] += entry.qty
    return contrib


def _cap_and_record(rec, contrib, current, remaining, known_sids):
    """Record deltas for one source, capped so cumulative attribution never
    exceeds current inventory. Mutates ``remaining`` (per-key headroom).
    Returns copies actually attributed."""
    attributed = 0
    for key, want in contrib.items():
        if key not in current:
            continue  # source references a card not (or no longer) in inventory
        sid, finish = key
        if sid not in known_sids:
            continue  # FK safety: inventory_events.scryfall_id must exist in cards
        take = min(want, remaining.get(key, 0))
        if take <= 0:
            continue
        rec.record(sid, finish, take, old_qty=0, new_qty=take)
        remaining[key] -= take
        attributed += take
    return attributed


def run(*, force: bool, dry_run: bool) -> int:
    with db.connect() as conn:
        existing = conn.execute("SELECT COUNT(*) AS n FROM inventory_events").fetchone()["n"]
        if existing and not force:
            print(f"refusing: inventory_events already has {existing} row(s). "
                  f"Pass --force to clear backfill-origin events and rebuild.",
                  file=sys.stderr)
            return 2
        if existing and force:
            # Clear ONLY backfill-origin ledger rows + their events, so a re-run
            # is clean without touching live post-V19 writes.
            conn.execute(
                "DELETE FROM inventory_events WHERE ingest_id IN "
                "(SELECT ingest_id FROM ingest_events "
                " WHERE method IN ('migration-backfill','unattributed-backfill') "
                "    OR status = 'backfill')"
            )
            conn.execute(
                "DELETE FROM ingest_events "
                "WHERE method IN ('migration-backfill','unattributed-backfill') "
                "   OR status = 'backfill'"
            )

        current = _current_inventory(conn)
        known = _known_sids(conn)
        remaining = dict(current)  # per-key headroom
        total_current = sum(current.values())

        precon = _precon_contributions(conn)
        checklist = _checklist_contributions(conn)

        # 1. Precon attribution (one backfill event, method 'precon').
        precon_id = ingest_mod.create_event(
            conn, "precon", label="backfill:precon",
            status="backfill",
            notes="reconstructed precon decklist contributions (V19 backfill)",
        )
        precon_rec = ingest_mod.IngestRecorder(ingest_id=precon_id, conn=conn)
        precon_attr = _cap_and_record(precon_rec, precon, current, remaining, known)

        # 2. Checklist attribution.
        checklist_id = ingest_mod.create_event(
            conn, "checklist", label="backfill:checklist",
            status="backfill",
            notes="reconstructed archived-checklist quantities (V19 backfill)",
        )
        checklist_rec = ingest_mod.IngestRecorder(ingest_id=checklist_id, conn=conn)
        checklist_attr = _cap_and_record(checklist_rec, checklist, current, remaining, known)

        # 3. Unattributed remainder → one honest bucket.
        unattr_id = ingest_mod.create_event(
            conn, "unattributed-backfill", label="backfill:unattributed",
            status="backfill",
            notes="best-effort reconstruction residual (provenance unknown)",
        )
        unattr_rec = ingest_mod.IngestRecorder(ingest_id=unattr_id, conn=conn)
        unattr_attr = 0
        for key, left in remaining.items():
            if left <= 0:
                continue
            sid, finish = key
            if sid not in known:
                continue
            unattr_rec.record(sid, finish, left, old_qty=0, new_qty=left)
            unattr_attr += left

        # Finalize event counts.
        for rid, r in ((precon_id, precon_rec), (checklist_id, checklist_rec),
                       (unattr_id, unattr_rec)):
            ingest_mod.finalize_event(conn, rid, rows_added=r.rows_added)

        # Verify EXACT reconciliation before committing.
        drift = ingest_mod.reconcile_inventory_ledger(conn)

        print(f"Backfill summary (current inventory: {total_current} copies):")
        print(f"  precon attributed:       {precon_attr}")
        print(f"  checklist attributed:    {checklist_attr}")
        print(f"  unattributed remainder:  {unattr_attr}")
        pct = (unattr_attr / total_current * 100) if total_current else 0.0
        print(f"  → unattributed is {pct:.1f}% of the collection")
        if drift:
            print(f"\nFAIL: ledger != inventory after backfill "
                  f"({len(drift)} printing(s) drift). Rolling back.", file=sys.stderr)
            raise SystemExit(1)  # rolls back via connect()'s except path

        if dry_run:
            print("\n--dry-run: computed attribution but rolling back (no write).")
            raise _Rollback()

        print("\nOK: SUM(ledger) == inventory exactly. Committing ledger.")
    return 0


class _Rollback(Exception):
    """Sentinel to abort the transaction on --dry-run without signalling failure."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="backfill_provenance",
        description="Reconstruct the V19 provenance ledger from ground truth.",
    )
    parser.add_argument("--force", action="store_true",
                        help="Clear existing backfill events and rebuild.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute + report attribution without writing.")
    args = parser.parse_args(argv)

    try:
        return run(force=args.force, dry_run=args.dry_run)
    except _Rollback:
        return 0


if __name__ == "__main__":
    sys.exit(main())

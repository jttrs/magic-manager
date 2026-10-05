"""Post-merge upgrade for the REAL collection DB, with proof nothing you own changed.

The web-app branches (PRs #78–#84) added schema versions and one-off backfills
that must run once against your live DB after you pull them:

  V27  cards.released_at          → sets.backfill_released_at()   (mm set backfill-dates)
  V28  scryfall tag cache         → scryfall_tags.sync()          (mm scryfall tags sync)
  V29  decks.kind / kind_source   → decks.backfill_kinds()        (mm deck backfill-kinds)
  V30  cards.illustration_id + art tags → scryfall_art.backfill_illustration_ids()
                                    (mm set backfill-illustrations) and
                                    scryfall_tags.sync_kinds()      (mm scryfall tags sync — oracle + art)
  —    'built' follows pledges     → decks.backfill_built_state()  (mm deck backfill-built)
                                    data-only: imported / hand-built decks with nothing pledged → not built;
                                    precons keep ONE built copy (extra unpledged built copies → not built)

Every step is additive: migrations add columns/tables, backfills fill only the
new ones. This script makes that verifiable instead of assumed:

1. fingerprint the ownership data — inventory, the provenance ledger
   (ingest_events / inventory_events), wishlist, deck compositions, pledges and
   deck identity — hashing only the columns that existed BEFORE the upgrade;
2. run the migrations (on connect) and the backfills;
3. re-fingerprint and require byte-equality, and require the ledger to still
   reconcile (``inventory == SUM(inventory_events.delta)``).

Usage
-----
    uv run python scripts/post_merge_upgrade.py            # rehearse on a temp COPY (default; live DB untouched)
    uv run python scripts/post_merge_upgrade.py --apply    # snapshot to db/bak/, then upgrade the live DB in place
    uv run python scripts/post_merge_upgrade.py --db db/bak/<old>.bak   # rehearse on a copy of an older DB

Exit 0 = upgraded (or rehearsed) and every ownership table is identical.
Exit 1 = something differed; with --apply the pre-upgrade snapshot path is printed for `mm db restore`.
Network: steps 2b–2e read Scryfall / MTGJSON through the sanctioned cached wrappers.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

from magic_manager import db

# (table, identity columns we must never change). None = every pre-upgrade column.
OWNERSHIP: tuple[tuple[str, tuple[str, ...] | None], ...] = (
    ("inventory", None),
    ("ingest_events", None),
    ("inventory_events", None),
    ("wishlist_entries", None),
    ("deck_cards", None),
    ("deck_assignments", None),
    ("deck_versions", None),
    ("decks", None),
)


# Columns a registered backfill is ALLOWED to change (verified by their own check
# below instead of byte-equality). decks.precon_state is derived from pledges.
CORRECTED: dict[str, frozenset[str]] = {"decks": frozenset({"precon_state"})}


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def _fingerprint(conn: sqlite3.Connection, cols_by_table: dict[str, list[str]] | None = None) -> dict[str, tuple[int, str, list[str]]]:
    out: dict[str, tuple[int, str, list[str]]] = {}
    for table, _ in OWNERSHIP:
        cols = (cols_by_table or {}).get(table) or [c for c in _columns(conn, table) if c not in CORRECTED.get(table, ())]
        if not cols:
            continue
        rows = conn.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
        canon = sorted("\x1f".join("" if v is None else str(v) for v in r) for r in rows)
        h = hashlib.sha256("\x1e".join(canon).encode("utf-8")).hexdigest()
        out[table] = (len(rows), h, cols)
    return out


def _step(label: str, fn) -> None:
    t = time.time()
    print(f"  · {label} …", flush=True)
    result = fn()
    print(f"    {result}  ({time.time() - t:.1f}s)", flush=True)


def run(path: Path) -> int:
    os.environ["MAGIC_MANAGER_DB"] = str(path)
    raw = sqlite3.connect(path)
    before = _fingerprint(raw)
    raw.close()
    print(f"before: {', '.join(f'{t}={n}' for t, (n, _, _) in before.items())}")

    print("upgrading:")
    with db.connect() as conn:  # applies pending migrations (V27–V30), snapshotting first
        version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] if _columns(conn, "schema_version") else "?"
    print(f"  · schema at V{version}")
    from magic_manager import decks, scryfall_art, scryfall_tags, sets
    _step("V27 backfill release dates", lambda: f"{sets.backfill_released_at()} card rows filled")
    _step("V28 + V30 sync Scryfall oracle + art tags", lambda: scryfall_tags.sync_kinds())
    # Classification hits MTGJSON per precon (~3.5 min); skip when every precon row is already classified.
    _step("V29 classify decks vs card pools",
          lambda: decks.backfill_kinds() if decks.unclassified_precon_count() else "already classified — skipped")
    _step("V30 backfill printing illustration ids",
          lambda: f"{scryfall_art.backfill_illustration_ids()} card rows filled")
    _step("built follows pledges (unpledged imports → not built)",
          lambda: decks.backfill_built_state() if (decks.unpledged_built_count() or decks.extra_built_precon_count()) else "nothing to correct — skipped")

    raw = sqlite3.connect(path)
    after = _fingerprint(raw, {t: cols for t, (_, _, cols) in before.items()})
    from magic_manager import ingest
    drift = ingest.reconcile_inventory_ledger(raw)
    kinds = raw.execute("SELECT kind, COUNT(*) FROM decks GROUP BY kind").fetchall() if "kind" in _columns(raw, "decks") else []
    # CORRECTED columns: precon_state may change, but only toward the rule
    # "a non-precon deck is built iff something is pledged to it".
    unpledged_built = raw.execute(
        "SELECT COUNT(*) FROM decks d WHERE d.precon_state = 'built' AND d.source_precon_file_name IS NULL "
        "AND NOT EXISTS (SELECT 1 FROM deck_assignments a WHERE a.deck_id = d.deck_id)").fetchone()[0]
    from magic_manager import decks as _decks
    unpledged_built += _decks.extra_built_precon_count(conn=raw)
    raw.close()

    bad = [t for t in before if before[t][:2] != after.get(t, (None, None))[:2]]
    print("verify:")
    for t, (n, h, _) in before.items():
        print(f"  {'✓' if t not in bad else '✗'} {t}: {n} rows {'unchanged' if t not in bad else f'CHANGED → {after[t][0]} rows'}")
    print(f"  {'✓' if not drift else '✗'} ledger reconciles (inventory == SUM(delta)): {len(drift)} drifting pairs")
    print(f"  {'✓' if not unpledged_built else '✗'} 'built' is consistent (no unpledged imports; one built copy per precon unless pledged): {unpledged_built} off")
    print(f"  decks by kind: {dict(kinds)}")
    return 1 if bad or drift or unpledged_built else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="upgrade the LIVE DB in place (after a db/bak snapshot)")
    ap.add_argument("--db", type=Path, help="rehearse against this DB file instead of the live one (always a copy)")
    args = ap.parse_args(argv)
    if args.db and args.apply:
        ap.error("--db is rehearsal-only; --apply always targets the live DB")
    os.environ.pop("MAGIC_MANAGER_DB", None)
    live = args.db or db.db_path()
    if not live.exists():
        print(f"no DB at {live}")
        return 0
    if args.apply:
        snap = db.snapshot(label="pre-post-merge-upgrade")
        print(f"live DB: {live}\nsnapshot: {snap}  (restore with: uv run mm db restore {snap.name})")
        code = run(live)
        if code:
            print(f"\nFAILED — restore the snapshot: uv run mm db restore {snap.name}")
        return code
    with tempfile.TemporaryDirectory() as d:
        copy = Path(d) / "rehearsal.db"
        src = sqlite3.connect(live)
        dst = sqlite3.connect(copy)
        src.backup(dst)  # consistent copy even with -wal pending
        src.close()
        dst.close()
        print(f"REHEARSAL on a copy of {live} (live DB untouched; --apply to upgrade it)")
        code = run(copy)
        shutil.rmtree(d, ignore_errors=True)
        return code


if __name__ == "__main__":
    sys.exit(main())

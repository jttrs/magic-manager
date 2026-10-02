"""Collection import/export driver — dry-run review by default, ``--apply`` to write.

Thin orchestration over ``magic_manager.collection_sync`` (the deterministic
core). Mirrors ``trueup_pools.py``'s dry-run/``--apply`` shape: read the service
CSV → resolve against Scryfall → diff vs the landing state → write review
artifacts (JSON + XLSX) + print a summary. Nothing is written to the DB until
``--apply`` recomputes the diff and applies it, under one of the three modes.

Direction:
  import  (default)  CSV → local inventory. Landing = local inventory. The three
                     modes (add/modify/overwrite) shape the inventory mutation.
  export             local inventory → a service CSV. Landing = a service CSV
                     supplied via ``--against`` (or empty). Export NEVER writes
                     the DB — it emits a reconciled CSV artifact.

Dedup: the CSV's sha256 is checked against prior ``collection-import`` events
(``ingest.find_events_by_sha``); re-importing an identical file is refused
without ``--force`` (exactly like the checklist ingest paths).

Usage
-----
    uv run python scripts/collection_sync.py import <service> <csv>
        [--mode add|modify|overwrite] [--apply] [--force] [--json]
    uv run python scripts/collection_sync.py export <service>
        [--against <csv>] [--apply] [--json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import collection_sync as cs  # noqa: E402
from magic_manager import db, ingest  # noqa: E402

# Exit codes (mirror the read-side _materialize_or_die + checklist dedup):
EXIT_OK = 0
EXIT_BAD_INPUT = 2        # unknown service / unreadable file / parse error
EXIT_DUPLICATE = 3        # identical file already imported (no --force)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------

def run_import(service: str, csv_path: str, *, mode: str, apply: bool,
               force: bool, json_out: bool) -> int:
    path = Path(csv_path)
    if not path.is_file():
        print(f"error: no such file: {path}", file=sys.stderr)
        return EXIT_BAD_INPUT
    try:
        rows = cs.read_csv(path, service)
    except LookupError as e:  # unknown service
        print(f"error: {e}", file=sys.stderr)
        return EXIT_BAD_INPUT

    sha = _sha256(path)
    # Dedup gate — refuse a re-import of the identical file without --force.
    if not force:
        with db.connect() as conn:
            prior = [e for e in ingest.find_events_by_sha(conn, sha)
                     if e["method"] == "collection-import" and e["status"] == "success"]
        if prior:
            p = prior[0]
            msg = (f"this file was already imported (ingest #{p['id']} at {p['at']}, "
                   f"mode={p['mode']}). Re-run with --force to import again.")
            if json_out:
                json.dump({"duplicate": True, "prior": p, "sha256": sha}, sys.stdout, indent=2, default=str)
                sys.stdout.write("\n")
            else:
                print(f"refused: {msg}", file=sys.stderr)
            return EXIT_DUPLICATE

    resolved = cs.resolve_rows(rows)
    diff = cs.diff_collections(resolved.resolved)
    stamp = _stamp()
    arts = cs.write_diff_artifacts(diff, direction="import", service=service,
                                   stamp=stamp, mode=mode)

    applied = None
    if apply:
        applied = cs.apply_import(
            resolved.resolved, mode=mode, diff=diff,
            label=f"collection import ({service})",
            source_path=str(path), source_sha256=sha,
        )
        # The invariant guard: after any apply the ledger must reconcile.
        with db.connect() as conn:
            drift = ingest.reconcile_inventory_ledger(conn)
        if drift:
            print(f"ERROR: ledger drift after apply: {drift}", file=sys.stderr)
            return 1

    _report_import(service, mode, diff, resolved, arts, applied,
                   json_out=json_out, apply=apply)
    return EXIT_OK


def _report_import(service, mode, diff, resolved, arts, applied, *,
                   json_out, apply):
    if json_out:
        json.dump({
            "direction": "import", "service": service, "mode": mode,
            "summary": cs.diff_summary_line(diff),
            "not_found": resolved.not_found,
            "artifacts": {k: str(v) for k, v in arts.items()},
            "applied": applied,
        }, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return
    print(cs.diff_markdown(diff, direction="import", service=service, mode=mode))
    print()
    if resolved.not_found:
        print(f"not resolved ({len(resolved.not_found)}) — skipped, not imported:")
        for nf in resolved.not_found[:20]:
            print(f"  {nf.get('name') or '?'} ({nf.get('set')}) "
                  f"{nf.get('collector_number')} {nf.get('finish')}  — {nf['reason']}")
        if len(resolved.not_found) > 20:
            print(f"  …and {len(resolved.not_found) - 20} more")
    print(f"\nartifacts: {arts['xlsx']}\n           {arts['json']}")
    if applied:
        print(f"\nAPPLIED (mode={mode}): {applied['added']} added, "
              f"{applied['updated']} updated, {applied['zeroed']} zeroed "
              f"(ingest #{applied['ingest_id']}). Ledger reconciles.")
    else:
        print(f"\n(dry-run — no DB writes. Review the diff above, then re-run with "
              f"--apply to import under mode={mode}.)")


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def run_export(service: str, *, against: str | None, apply: bool,
               json_out: bool) -> int:
    try:
        incoming = cs._landing_from_inventory()  # local inventory IS the incoming
        landing = cs.read_csv(Path(against), service) if against else []
    except LookupError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_BAD_INPUT
    if against and not Path(against).is_file():
        print(f"error: no such --against file: {against}", file=sys.stderr)
        return EXIT_BAD_INPUT

    diff = cs.diff_collections(incoming, landing)
    stamp = _stamp()
    arts = cs.write_diff_artifacts(diff, direction="export", service=service, stamp=stamp)

    # The reconciled CSV = the local inventory rendered in the service's format.
    # Export never writes our DB; --apply just emits the CSV file.
    csv_text = cs.write_csv(incoming, service)
    csv_path = None
    if apply:
        from magic_manager import util
        csv_path = util.output_dir("collection-sync", "exports") / f"{service}-{stamp}.csv"
        csv_path.write_text(csv_text, encoding="utf-8")

    if json_out:
        json.dump({
            "direction": "export", "service": service,
            "summary": cs.diff_summary_line(diff),
            "artifacts": {k: str(v) for k, v in arts.items()},
            "csv": str(csv_path) if csv_path else None,
        }, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return EXIT_OK

    print(cs.diff_markdown(diff, direction="export", service=service))
    print(f"\nartifacts: {arts['xlsx']}\n           {arts['json']}")
    if csv_path:
        print(f"\nAPPLIED: reconciled collection CSV written to {csv_path}")
    else:
        print(f"\n(dry-run — no CSV written. Re-run with --apply to emit the "
              f"reconciled {service} CSV.)")
    return EXIT_OK


# ---------------------------------------------------------------------------
# diff (read-only, either direction)
# ---------------------------------------------------------------------------

def run_diff(service: str, csv_path: str, *, direction: str, json_out: bool) -> int:
    path = Path(csv_path)
    if not path.is_file():
        print(f"error: no such file: {path}", file=sys.stderr)
        return EXIT_BAD_INPUT
    try:
        rows = cs.read_csv(path, service)
    except LookupError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_BAD_INPUT
    if direction == "import":
        resolved = cs.resolve_rows(rows)
        diff = cs.diff_collections(resolved.resolved)
    else:  # export: inventory vs the CSV
        diff = cs.diff_collections(cs._landing_from_inventory(), rows)
    stamp = _stamp()
    arts = cs.write_diff_artifacts(diff, direction=direction, service=service, stamp=stamp)
    if json_out:
        json.dump({"direction": direction, "service": service,
                   "summary": cs.diff_summary_line(diff),
                   "artifacts": {k: str(v) for k, v in arts.items()}},
                  sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        print(cs.diff_markdown(diff, direction=direction, service=service))
        print(f"\nartifacts: {arts['xlsx']}\n           {arts['json']}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="collection_sync")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("import", help="CSV → local inventory (dry-run unless --apply).")
    pi.add_argument("service")
    pi.add_argument("csv")
    pi.add_argument("--mode", choices=["add", "modify", "overwrite"], default="add")
    pi.add_argument("--apply", action="store_true")
    pi.add_argument("--force", action="store_true", help="Re-import an identical file.")
    pi.add_argument("--json", action="store_true")

    pe = sub.add_parser("export", help="local inventory → service CSV (dry-run unless --apply).")
    pe.add_argument("service")
    pe.add_argument("--against", default=None, help="Service CSV = the landing state to diff against.")
    pe.add_argument("--apply", action="store_true")
    pe.add_argument("--json", action="store_true")

    pd = sub.add_parser("diff", help="Read-only diff in either direction.")
    pd.add_argument("service")
    pd.add_argument("csv")
    pd.add_argument("--direction", choices=["import", "export"], default="import")
    pd.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "import":
        return run_import(args.service, args.csv, mode=args.mode, apply=args.apply,
                          force=args.force, json_out=args.json)
    if args.cmd == "export":
        return run_export(args.service, against=args.against, apply=args.apply,
                          json_out=args.json)
    if args.cmd == "diff":
        return run_diff(args.service, args.csv, direction=args.direction,
                        json_out=args.json)
    return EXIT_BAD_INPUT


if __name__ == "__main__":
    sys.exit(main())

"""Census reconciliation CLI — thin driver over :mod:`magic_manager.census`.

    uv run python scripts/census_reconcile.py PATH [--product FILENAME ...]
        [--apply] [--json] [--no-archive]

PATH is a filled add-mode master-list XLSX of ALL loose cards; ``--product``
(repeatable; list a fileName twice for two copies) names products kept OFF the
sheet. Dry run by default. Exit codes: 0 ok, 1 refused (removals would drop
below pledged), 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from magic_manager import census, db, util  # noqa: E402
from magic_manager.cli import CHECKLISTS_DIR, PROCESSED_DIR  # noqa: E402

TABLE_CAP = 50


def _table(title: str, lines: list[census.CensusLine], cap: int | None = TABLE_CAP) -> list[str]:
    out = [f"### {title} ({len(lines)} rows)", ""]
    if not lines:
        return out + ["(none)", ""]
    out += ["| set | cn | name | finish | census | products | owned | → target |",
            "|---|---|---|---|---:|---:|---:|---:|"]
    for ln in lines[:cap]:
        out.append(f"| {ln.set} | {ln.cn} | {ln.name} | {ln.finish} | {ln.census} | "
                   f"{ln.products} | {ln.owned} | → {ln.target} |")
    if cap is not None and len(lines) > cap:
        out.append(f"\n…and {len(lines) - cap} more")
    return out + [""]


def _summary(p: census.CensusPlan) -> list[str]:
    d = p.to_dict()["totals"]
    return [
        f"## Census reconciliation — {p.anchor}", "",
        f"- census copies:  {d['census_copies']}",
        f"- product copies: {d['product_copies']} ({len(p.products)} product(s))",
        f"- target copies:  {d['target_copies']}",
        f"- owned copies:   {d['owned_copies']} (over the sheet's printings)",
        f"- adds:           {d['add_rows']} rows / {d['add_copies']} copies",
        f"- removals:       {d['removal_rows']} rows / {d['removal_copies']} copies",
        f"- below pledged:  {d['below_pledged']}", "",
    ]


def _report(p: census.CensusPlan, full: bool) -> str:
    cap = None if full else TABLE_CAP
    lines = _summary(p) + _table("Adds", p.adds, cap) + _table("Removals", p.removals, cap)
    if p.below_pledged:
        lines += _table("Below pledged (would be refused)", p.below_pledged, cap)
    return "\n".join(lines)


def _write_report(p: census.CensusPlan, extra: dict) -> tuple[Path, Path]:
    out = util.output_dir("census", "reports")
    stem = f"{p.anchor}-census-{datetime.now():%Y%m%d-%H%M%S}"
    md, js = out / f"{stem}.md", out / f"{stem}.json"
    md.write_text(_report(p, True) + "\n", encoding="utf-8")
    js.write_text(json.dumps({**p.to_dict(), **extra}, indent=2) + "\n", encoding="utf-8")
    return md, js


def _archive(path: Path) -> Path | None:
    """Move a checklist out of the active checklists dir into ``processed/``."""
    if path.resolve().parent != CHECKLISTS_DIR.resolve():
        return None
    stem = path.stem
    for tail in ("-add-checklist", "-checklist"):
        if stem.endswith(tail):
            stem = stem[: -len(tail)]
            break
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dest = PROCESSED_DIR / f"{stem}-census-{datetime.now():%Y-%m-%d}{path.suffix}"
    if dest.exists():
        dest = PROCESSED_DIR / f"{stem}-census-{datetime.now():%Y-%m-%d-%H%M%S}{path.suffix}"
    shutil.move(str(path), str(dest))
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="census_reconcile")
    parser.add_argument("path", help="Filled add-mode master-list XLSX (all loose cards).")
    parser.add_argument("--product", action="append", default=[], metavar="FILENAME",
                        help="MTGJSON fileName of a product kept OFF the sheet "
                             "(repeatable; repeat for multiple copies).")
    parser.add_argument("--apply", action="store_true", help="Write (default is dry-run).")
    parser.add_argument("--json", action="store_true", help="Print the plan as JSON.")
    parser.add_argument("--no-archive", action="store_true",
                        help="Leave the sheet in place after --apply.")
    args = parser.parse_args(argv)

    path = Path(args.path)
    try:
        p = census.plan(path, args.product)
    except census.CensusError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    extra: dict = {}
    if args.apply:
        if p.below_pledged:
            print("Refused: these removals would drop below the copies pledged to built decks.",
                  file=sys.stderr)
            print("\n".join(_table("Below pledged", p.below_pledged)), file=sys.stderr)
            print("nothing written", file=sys.stderr)
            return 1
        snap = db.snapshot(label=f"pre-census-{p.anchor}")
        try:
            result = census.apply(path, args.product)
        except census.CensusRefused as e:
            print(f"Refused: {e}", file=sys.stderr)
            return 1
        except census.CensusError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        extra = {"applied": result, "snapshot": str(snap)}
        if not args.no_archive:
            moved = _archive(path)
            if moved:
                extra["archived"] = str(moved)

    md, js = _write_report(p, extra)
    if args.json:
        print(json.dumps({**p.to_dict(), **extra}, indent=2))
        return 0
    print(_report(p, False))
    print(f"report: {md}\n        {js}")
    if args.apply:
        r = extra["applied"]
        print(f"applied: adds event {r['adds_event']} ({r['added_copies']} copies), "
              f"removals event {r['removals_event']} ({r['removed_copies']} copies)")
        print(f"snapshot: {extra['snapshot']}")
        print(f"archived: {extra.get('archived', '(not archived)')}")
        print("undo either event with: uv run mm ingest revert <id> --apply")
    elif p.below_pledged:
        print("Refused: the removals above marked 'Below pledged' would drop below the "
              "copies pledged to built decks — --apply would refuse; nothing written", file=sys.stderr)
        return 1
    else:
        print("dry run — rerun with --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())

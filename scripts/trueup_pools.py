"""Product coverage CLI — thin driver over :mod:`magic_manager.trueup`.

    uv run python scripts/trueup_pools.py [--from-unattributed | --all | <target>]
        [--apply] [--pick fileName,…] [--refute fileName,…]
        [--sld-partial-threshold 0.9] [--json]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from magic_manager.trueup import run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trueup_pools")
    parser.add_argument("target", nargs="?", default=None,
                        help="Set code/family or product-name substring to scope to.")
    parser.add_argument("--from-unattributed", action="store_true",
                        help="(default) only sets with unattributed-backfill copies.")
    parser.add_argument("--all", action="store_true", help="Every set with loose cards.")
    parser.add_argument("--apply", action="store_true", help="Write (default is dry-run).")
    parser.add_argument("--pick", default="", help="Comma-separated fileNames/slugs to claim from conflicts.")
    parser.add_argument("--refute", default="",
                        help="Comma-separated fileNames/slugs you did NOT buy — dropped from "
                             "candidates (their cards stay available for other products).")
    parser.add_argument("--sld-partial-threshold", type=float, default=0.9)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    mode = "all" if args.all else ("target" if args.target else "from-unattributed")
    picks = {s.strip() for s in args.pick.split(",") if s.strip()}
    refute = {s.strip() for s in args.refute.split(",") if s.strip()}
    return run(mode=mode, target=args.target, apply=args.apply, picks=picks,
               sld_threshold=args.sld_partial_threshold, json_out=args.json, refute=refute)


if __name__ == "__main__":
    sys.exit(main())

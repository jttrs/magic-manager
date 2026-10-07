"""Keep the browser companion's generated files in sync, and package it.

Thin driver over :mod:`magic_manager.companion` (the single source of truth).

    uv run python scripts/build_extension.py            # regenerate stores.js + manifest permissions
    uv run python scripts/build_extension.py --check    # exit 1 if they're stale (CI / tests)
    uv run python scripts/build_extension.py --zip out.zip   # reproducible zip of extension/
    uv run python scripts/build_extension.py --bookmarklet   # print the cart bookmarklet URL
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from magic_manager import companion


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="Fail if generated files are stale; write nothing.")
    ap.add_argument("--zip", metavar="PATH", help="Write the reproducible extension zip here.")
    ap.add_argument("--bookmarklet", action="store_true", help="Print the cart bookmarklet javascript: URL.")
    args = ap.parse_args()

    if args.check:
        stale = companion.stale_files()
        for p in stale:
            print(f"stale: {p.relative_to(companion.EXT_DIR.parent)} — run scripts/build_extension.py", file=sys.stderr)
        return 1 if stale else 0
    if args.bookmarklet:
        print(companion.bookmarklet_href())
        return 0
    for p in companion.write_generated():
        print(f"wrote {p.relative_to(companion.EXT_DIR.parent)}", file=sys.stderr)
    if args.zip:
        data = companion.build_zip()
        Path(args.zip).write_bytes(data)
        print(f"{args.zip}: {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

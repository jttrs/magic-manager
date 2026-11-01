"""Keep the browser companion's generated files in sync, and package it.

Thin driver over :mod:`magic_manager.companion` (the single source of truth).

    uv run python scripts/build_extension.py            # regenerate stores.js, tokens.css, icons + manifest permissions
    uv run python scripts/build_extension.py --check    # exit 1 if they're stale (CI / tests)
    uv run python scripts/build_extension.py --zip out.zip   # reproducible zip of extension/ (unzips to a folder)
    uv run python scripts/build_extension.py --store-zip out.zip   # the same, manifest at the root (Chrome Web Store upload)
    uv run python scripts/build_extension.py --bookmarklet   # print the cart bookmarklet URL
    uv run python scripts/build_extension.py --bump patch    # bump the manifest version (major|minor|patch)
    uv run python scripts/build_extension.py --print-version # the manifest version (release workflow)

Releasing to the Chrome Web Store: docs/browser-companion.md § Chrome Web Store.
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
    ap.add_argument("--store-zip", metavar="PATH", help="Write the Chrome Web Store upload zip (manifest at the root) here.")
    ap.add_argument("--bookmarklet", action="store_true", help="Print the cart bookmarklet javascript: URL.")
    ap.add_argument("--bump", choices=("major", "minor", "patch"), help="Bump the manifest version first.")
    ap.add_argument("--print-version", action="store_true", help="Print the manifest version and exit.")
    args = ap.parse_args()

    if args.print_version:
        print(companion.version())
        return 0
    if args.bump:
        print(f"version {companion.bump_version(args.bump)}", file=sys.stderr)

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
    for path, store in ((args.zip, False), (args.store_zip, True)):
        if path:
            data = companion.build_zip(store=store)
            Path(path).write_bytes(data)
            print(f"{path}: {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

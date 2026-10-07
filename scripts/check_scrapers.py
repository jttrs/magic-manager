"""Run every pinned deterministic-scrape test in one go — the dev's "is
everything still reading right?" check.

Offline by default (saved pages only, no network):
  * Python: the vendor recipes (tests/test_vendor_recipes.py), the deck-import
    parsers (tests/test_decksource.py) and the browser companion chain
    (tests/test_companion.py).
  * Real Chromium: the companion's page readers against saved pages
    (web/e2e/companion-readers.spec.ts) and the real extension end to end
    (web/e2e/companion-extension.spec.ts).

``--live`` also reads every vendor's ``sample_url`` today (the nightly canary,
scripts/vendor_canary.py) — the only step that touches the network.

    uv run python scripts/check_scrapers.py           # offline pins
    uv run python scripts/check_scrapers.py --live    # + live store canary
    MM_E2E_PORT=5191 uv run python scripts/check_scrapers.py   # parallel worktrees: your own e2e port

When something fails, follow .claude/skills/scrape-doctor/SKILL.md.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PYTEST = ["tests/test_vendor_recipes.py", "tests/test_decksource.py", "tests/test_companion.py"]
E2E = ["companion-readers", "companion-extension"]


def _run(label: str, cmd: list[str], **kw) -> bool:
    print(f"\n── {label}: {' '.join(cmd)}", flush=True)
    ok = subprocess.run(cmd, cwd=ROOT, **kw).returncode == 0
    print(f"── {label}: {'ok' if ok else 'FAILED'}", flush=True)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--live", action="store_true", help="Also run the live vendor canary (network).")
    ap.add_argument("--no-browser", action="store_true", help="Skip the Chromium suites.")
    args = ap.parse_args()

    results = {
        "generated files": _run("generated files", ["uv", "run", "python", "scripts/build_extension.py", "--check"]),
        "python pins": _run("python pins", ["uv", "run", "pytest", "-q", "-p", "no:warnings", *PYTEST]),
    }
    if not args.no_browser:
        env = {**os.environ, "MM_E2E_PORT": os.environ.get("MM_E2E_PORT", "5174")}
        results["browser pins"] = _run("browser pins", ["npm", "--prefix", "web", "run", "e2e", "--", *E2E], env=env)
    if args.live:
        results["live canary"] = _run("live canary", ["uv", "run", "python", "scripts/vendor_canary.py"])

    print("\nSummary:")
    for k, ok in results.items():
        print(f"  {'✓' if ok else '✗'} {k}")
    if not all(results.values()):
        print("\nSomething stopped reading right — see .claude/skills/scrape-doctor/SKILL.md.")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

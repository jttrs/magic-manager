"""Run every pinned deterministic-scrape test in one go — the dev's "is
everything still reading right?" check.

Offline by default (saved pages only, no network):
  * Python: the vendor recipes (tests/test_vendor_recipes.py), the deck-import
    parsers (tests/test_decksource.py) and the browser companion chain
    (tests/test_companion.py).
  * Real Chromium: the companion's page readers against saved pages
    (web/e2e/companion-readers.spec.ts) and the real extension end to end
    (web/e2e/companion-extension.spec.ts).

``--live`` also reads a known public sample for EVERY scraper, per site, today
(magic_manager.scrape_canary: store recipes, deck importers, EDHREC, and — in a
real Chrome — open-tab stores, Moxfield and the Mana Pool cart reader). It's the
only step that touches the network. ``--record`` writes each outcome to the
scraper-health file the app reads ("temporarily down" notices), ``--notify``
posts a macOS notification when a scraper goes down or recovers.

    uv run python scripts/check_scrapers.py           # offline pins
    uv run python scripts/check_scrapers.py --live    # + live canary for every scraper
    uv run python scripts/check_scrapers.py --live --no-pins --record --notify   # the scheduled run (launchd)
    MM_E2E_PORT=5191 uv run python scripts/check_scrapers.py   # parallel worktrees: your own e2e port

When something fails, follow .claude/skills/scrape-doctor/SKILL.md.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PYTEST = ["tests/test_vendor_recipes.py", "tests/test_decksource.py", "tests/test_companion.py",
          "tests/test_scraper_health.py"]
E2E = ["companion-readers", "companion-extension"]


def _run(label: str, cmd: list[str], **kw) -> bool:
    print(f"\n── {label}: {' '.join(cmd)}", flush=True)
    ok = subprocess.run(cmd, cwd=ROOT, **kw).returncode == 0
    print(f"── {label}: {'ok' if ok else 'FAILED'}", flush=True)
    return ok


def _notify(title: str, text: str) -> None:
    """A macOS notification (no-op elsewhere / when osascript is missing)."""
    esc = lambda t: t.replace("\\", "\\\\").replace('"', '\\"')  # noqa: E731
    try:
        subprocess.run(["osascript", "-e", f'display notification "{esc(text)}" with title "{esc(title)}"'],
                       check=False, capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _live(args) -> bool:
    """Every live canary, printed; optionally recorded + notified. ok/unverified
    pass; any ``fail`` (a page changed) fails the step."""
    from magic_manager import scrape_canary, scraper_health
    print("\n── live canary: every scraper, per site", flush=True)
    checks = scrape_canary.run(browser=not args.no_browser, headed=not args.no_window,
                               progress=lambda m: print(f"   reading {m}…", flush=True))
    mark = {"ok": "ok  ", "fail": "DOWN", "unverified": "??  "}
    for c in checks:
        print(f"{mark[c.outcome]} {c.key:34} {c.code or '':22} {(c.message or '')[:90]}")
    if args.json:
        print(json.dumps([c.__dict__ for c in checks], indent=2, default=str))
    if args.record:
        changes = scraper_health.record([c.record() for c in checks])
        print(f"── recorded {len(checks)} checks → {scraper_health.path()}")
        for t in changes:
            print(f"   {t.change}: {t.label} {t.code or ''}")
            if args.notify:
                what = {"down": "is temporarily down", "recovered": "is reading again",
                        "sample_gone": "needs a new canary sample"}[t.change]
                _notify("magic-manager scrapers", f"{t.label} {what}" + (f" — {t.message}" if t.message and t.change != "recovered" else ""))
    ok = not any(c.outcome == "fail" for c in checks)
    print(f"── live canary: {'ok' if ok else 'FAILED'}", flush=True)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--live", action="store_true", help="Also run the live canary for every scraper (network).")
    ap.add_argument("--no-browser", action="store_true", help="Skip the Chromium suites (and the live browser checks).")
    ap.add_argument("--no-pins", action="store_true", help="Skip the offline pins (the scheduled run: --live only).")
    ap.add_argument("--no-window", action="store_true", help="Live: never open a visible Chrome window (blocked checks stay unverified).")
    ap.add_argument("--record", action="store_true", help="Live: write outcomes to the scraper-health file the app reads.")
    ap.add_argument("--notify", action="store_true", help="Live: macOS notification when a scraper goes down / recovers.")
    ap.add_argument("--json", action="store_true", help="Live: also print every check as JSON.")
    args = ap.parse_args()

    results = {}
    if not args.no_pins:
        results["generated files"] = _run("generated files", ["uv", "run", "python", "scripts/build_extension.py", "--check"])
        results["python pins"] = _run("python pins", ["uv", "run", "pytest", "-q", "-p", "no:warnings", *PYTEST])
        if not args.no_browser:
            env = {**os.environ, "MM_E2E_PORT": os.environ.get("MM_E2E_PORT", "5174")}
            results["browser pins"] = _run("browser pins", ["npm", "--prefix", "web", "run", "e2e", "--", *E2E], env=env)
    if args.live:
        results["live canary"] = _live(args)

    print("\nSummary:")
    for k, ok in results.items():
        print(f"  {'✓' if ok else '✗'} {k}")
    if not all(results.values()):
        print("\nSomething stopped reading right — see .claude/skills/scrape-doctor/SKILL.md.")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Push a local deck to Moxfield by driving the deck-builder UI (BEST-EFFORT).

⚠️  FRAGILE UI AUTOMATION — READ THIS.
    Moxfield has NO sanctioned write API. The only way to create a deck
    programmatically is to drive the deck-builder web UI with a real browser.
    That means this script depends on Moxfield's DOM: button labels, the
    bulk-import textarea selector, and the save flow. Any of those can change
    without notice and silently break this. Treat a success here as "probably
    created — go confirm on Moxfield", not a guarantee. The read paths
    (import_deck.py) are robust; this write path is not.

WHAT IT DOES
    Reads a Moxfield import-text block on STDIN (the `<qty> Name (SET) CN *F*`
    format produced by the existing exporter — DRY, no re-rendering here):

        uv run mm export deck:<slug> --target moxfield \\
            | uv run python scripts/moxfield_push.py --name "My Deck"

    Then, using the shared authenticated Playwright context (moxfield_session.py),
    it opens the deck-builder, pastes the block into the bulk-import box, saves,
    and prints the resulting deck URL to stdout.

SCOPE (v1)
    Create-new only. Updating an EXISTING Moxfield deck is out of scope — it would
    require persisting a Moxfield deck-id per local deck (a schema column); noted
    as a follow-up, not built here.

Allow-listed past the Moxfield network guard by path.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

NEW_DECK_URL = "https://www.moxfield.com/decks/personal/new"


def main() -> int:
    ap = argparse.ArgumentParser(description="Push a deck to Moxfield (best-effort UI automation).")
    ap.add_argument("--name", help="Name for the new Moxfield deck.")
    ap.add_argument("--format", default="commander", help="Moxfield deck format (default: commander).")
    ap.add_argument("--fresh", action="store_true", help="Force Moxfield re-login.")
    args = ap.parse_args()

    block = sys.stdin.read().strip()
    if not block:
        print("moxfield_push: empty decklist on stdin — nothing to push", file=sys.stderr)
        return 2

    from moxfield_session import MoxfieldSession

    with MoxfieldSession(fresh=args.fresh, headless=False) as ctx:
        page = ctx.new_page()
        page.goto(NEW_DECK_URL, wait_until="domcontentloaded")

        # Open the bulk-import affordance. Moxfield labels it "Bulk edit" /
        # "Import". We try a few selectors and bail loudly if none match — a
        # missing selector means the UI drifted, which the user must know about.
        opened = _try_click(page, [
            "button:has-text('Bulk edit')",
            "button:has-text('Bulk Edit')",
            "button:has-text('Import')",
            "a:has-text('Import')",
        ])
        if not opened:
            print(
                "moxfield_push: couldn't find the bulk-import/edit button — Moxfield's "
                "UI likely changed. Paste this block manually into a new deck instead:\n"
                "----\n" + block + "\n----",
                file=sys.stderr,
            )
            return 1

        textarea = page.locator("textarea").first
        try:
            textarea.wait_for(timeout=10_000)
            textarea.fill(block)
        except Exception as e:  # noqa: BLE001
            print(f"moxfield_push: could not fill the import textarea ({e}) — UI drift. "
                  "Paste manually:\n----\n" + block + "\n----", file=sys.stderr)
            return 1

        if args.name:
            _try_fill(page, ["input[name='name']", "input[placeholder*='name' i]"], args.name)

        saved = _try_click(page, [
            "button:has-text('Save')",
            "button:has-text('Create')",
            "button[type='submit']",
        ])
        if not saved:
            print("moxfield_push: filled the import box but couldn't find a Save button — "
                  "finish the save in the open browser window.", file=sys.stderr)
            # Give the human a chance to finish manually.
            try:
                input("Press Enter after saving in the browser…")
            except EOFError:
                pass

        page.wait_for_load_state("networkidle")
        url = page.url
        if "/decks/" in url:
            print(url)
            print(f"moxfield_push: deck pushed → {url}", file=sys.stderr)
            return 0
        print(f"moxfield_push: save flow finished but landed on {url!r}; confirm on Moxfield.",
              file=sys.stderr)
        return 0


def _try_click(page, selectors: list[str]) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                loc.click(timeout=5_000)
                return True
        except Exception:
            continue
    return False


def _try_fill(page, selectors: list[str], value: str) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                loc.fill(value, timeout=5_000)
                return True
        except Exception:
            continue
    return False


if __name__ == "__main__":
    raise SystemExit(main())

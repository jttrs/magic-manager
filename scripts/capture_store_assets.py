"""Capture the Chrome Web Store screenshots + promo tile from the REAL extension pages.

    uv run python scripts/capture_store_assets.py          # writes extension/store/{screenshots/*.png,promo-small.png}

Loads a temp copy of ``extension/`` into headless Chromium (Playwright), seeds the
same storage the extension itself writes — a pairing, and one pending cart read
from the pinned Mana Pool cart golden (``tests/fixtures/companion``) — and
screenshots the approval window and the settings page at 1280×800, plus a
440×280 small promo tile drawn with the extension's own tokens and icon.
Nothing here ships in the extension zip. Listing copy: ``extension/store/listing.md``.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from magic_manager import companion

ROOT = companion.EXT_DIR.parent
OUT = companion.STORE_DIR
CART = ROOT / "tests" / "fixtures" / "companion" / "manapool-cart.expected.json"
APP = "http://localhost:8765"

PROMO_HTML = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="src/tokens.css">
<style>
  html, body { margin: 0; width: 440px; height: 280px; }
  body { background: var(--theme-chrome); color: var(--theme-on-chrome); font-family: var(--font-guide); display: flex; align-items: center; gap: 22px; padding: 0 30px; box-sizing: border-box; }
  img { width: 96px; height: 96px; flex: none; }
  h1 { margin: 0 0 10px; font-size: 30px; line-height: 1; font-variation-settings: 'wdth' var(--font-width-condensed); font-weight: 700; letter-spacing: -0.01em; }
  p { margin: 0; font-size: 15px; line-height: 1.35; color: var(--theme-on-chrome-muted); max-width: 24ch; }
  b { color: var(--theme-accent); font-weight: 600; }
</style></head><body>
<img src="icons/icon-128.png" alt="">
<div><h1>magic-manager companion</h1><p>Your carts and decks, read in your browser. Sent only <b>when you approve</b>.</p></div>
</body></html>"""


def main() -> int:
    cart = json.loads(CART.read_text())
    data = {"store": "manapool", "items": cart["items"], "warnings": []}
    shots = OUT / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        ext = Path(tmp) / "ext"
        shutil.copytree(companion.EXT_DIR, ext, ignore=shutil.ignore_patterns("store"))
        (ext / "promo.html").write_text(PROMO_HTML)
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                str(Path(tmp) / "profile"), channel="chromium", headless=True,
                viewport={"width": 1280, "height": 800}, color_scheme="light",
                args=[f"--disable-extensions-except={ext}", f"--load-extension={ext}"])
            worker = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
            ext_id = worker.url.split("/")[2]
            base = f"chrome-extension://{ext_id}"
            page = ctx.new_page()
            page.goto(f"{base}/src/options.html")
            page.evaluate("""async ({ app, data }) => {
                const { packData, summarize } = await import('./protocol.js');
                await chrome.storage.local.set({ appOrigin: app, lastHello: { origin: app, at: Date.now() } });
                await chrome.storage.session.set({ pending: { id: 'store-demo', kind: 'cart', tabId: -1, origin: app,
                    packed: await packData(data), summary: summarize('cart', data), created: Date.now(), stage: 'send' } });
            }""", {"app": APP, "data": data})
            page.goto(f"{base}/src/approve.html?id=store-demo")
            page.wait_for_selector("#approve:enabled")   # Send unlocks after a short guard delay
            page.evaluate("document.activeElement?.blur()")   # no focus ring in the shot
            page.screenshot(path=str(shots / "1-approve.png"))
            page.evaluate("chrome.storage.session.remove('pending')")
            page.goto(f"{base}/src/options.html")
            page.wait_for_timeout(500)
            page.screenshot(path=str(shots / "2-settings.png"))
            page.set_viewport_size({"width": 440, "height": 280})
            page.goto(f"{base}/promo.html")
            page.wait_for_timeout(300)
            page.screenshot(path=str(OUT / "promo-small.png"))
            ctx.close()
    for p in sorted(OUT.rglob("*.png")):
        print(p.relative_to(ROOT), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

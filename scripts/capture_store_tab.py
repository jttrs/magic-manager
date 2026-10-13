"""Capture an open-tab (``rendered``) store page as a recipe fixture.

Reads ONE product page the way the app does in real life — with BOTH open-tab
read paths, so a recipe is pinned against each:

* ``extract`` — the browser companion's reader (``extension/src/readers/store-page.js``),
  exactly what the extension sends;
* ``tab``     — the AppleScript tab read (``storefetch._TAB_JS``: head tags + JSON-LD +
  the full visible text), reduced: head keeps only ``<title>``/``<meta>``/JSON-LD, the
  text stops before customer reviews (third-party names, not needed by any recipe).

    # a live page, in a fresh throwaway Chrome profile (headless; --headed for stores
    # that wall headless browsers — never your own profile, never past a captcha)
    uv run python scripts/capture_store_tab.py amazon-1p --url https://www.amazon.com/dp/B0FP42WVL7

    # a page YOU saved from your own Chrome (File → Save Page As → "Webpage, HTML Only"),
    # for stores that wall every automated browser (Walmart). Its scripts are dropped.
    uv run python scripts/capture_store_tab.py walmart-1p --html ~/Downloads/page.html \\
        --url https://www.walmart.com/ip/123 --redact "Seattle=Springfield" --redact "98103=00000"

Writes ``tests/fixtures/vendors/rendered/<name>.json.gz``. ``--redact OLD=NEW``
(repeatable) replaces personal text (your town, ZIP, store) everywhere; the
capture refuses to write while any OLD is still present. Read the output before
committing it (``.claude/skills/scrape-doctor/SKILL.md`` § 3).
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from magic_manager import storefetch

ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / "extension/src/readers/store-page.js"
OUT_DIR = ROOT / "tests/fixtures/vendors/rendered"
_REVIEWS = re.compile(r"^(?:Customer reviews|Top reviews from|Reviews with images|Ratings and reviews|Customer ratings? (?:&|and) reviews|Guest ratings (?:&|and) reviews|Reviews\n+Rating [\d.]+ out of 5 stars)\b", re.M | re.I)
_KEEP_HEAD = re.compile(r"<title[^>]*>.*?</title>|<meta\b[^>]*>|<script[^>]+application/ld\+json[^>]*>.*?</script>", re.S | re.I)


def reduce_tab(tab: dict) -> dict:
    head = "".join(_KEEP_HEAD.findall(tab.get("head") or ""))
    text = tab.get("text") or ""
    m = _REVIEWS.search(text)
    return {"title": tab.get("title") or "", "head": head, "ld": tab.get("ld") or [], "text": text[:m.start()] if m else text}


def redact(obj, pairs: list[tuple[str, str]]):
    if isinstance(obj, str):
        for old, new in pairs:
            obj = obj.replace(old, new)
        return obj
    if isinstance(obj, list):
        return [redact(v, pairs) for v in obj]
    if isinstance(obj, dict):
        return {k: redact(v, pairs) for k, v in obj.items()}
    return obj


def capture(url: str, *, html: str | None, headed: bool, wait_ms: int) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=not headed)
        page = browser.new_context(locale="en-US", viewport={"width": 1366, "height": 900}).new_page()
        if html is not None:
            body = re.sub(r"<script(?![^>]*ld\+json)[^>]*>.*?</script>", "", html, flags=re.S | re.I)
            host = urlsplit(url).hostname or ""
            page.route(re.compile(rf"^https?://(?:[^/]*\.)?{re.escape(host.removeprefix('www.'))}/"),
                       lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=body)
                       if r.request.url == url else r.abort())
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(wait_ms)
        tab = json.loads(page.evaluate(storefetch._TAB_JS))
        page.add_script_tag(content=READER.read_text())
        extract = page.evaluate("readStorePage(document)")
        final = page.url
        browser.close()
    if final != url and html is None:
        print(f"note: the page moved to {final}", file=sys.stderr)
    return {"url": url, "captured": date.today().isoformat(), "source": "saved page" if html is not None else "live page",
            "extract": extract, "tab": reduce_tab(tab)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("name", help="fixture name, <vendor>-<case> (e.g. amazon-third-party)")
    ap.add_argument("--url", required=True, help="the product page URL (a saved page is served at it)")
    ap.add_argument("--html", type=Path, help="a page saved from your own browser, instead of loading it live")
    ap.add_argument("--headed", action="store_true", help="show the throwaway browser (stores that wall headless)")
    ap.add_argument("--wait", type=int, default=8000, help="ms to let the page render (default 8000)")
    ap.add_argument("--redact", action="append", default=[], metavar="OLD=NEW", help="replace personal text (repeatable)")
    args = ap.parse_args()
    pairs = [tuple(r.split("=", 1)) for r in args.redact]
    if any(len(p) != 2 or not p[0] for p in pairs):
        ap.error("--redact takes OLD=NEW")
    html = args.html.expanduser().read_text(errors="replace") if args.html else None
    data = redact(capture(args.url, html=html, headed=args.headed, wait_ms=args.wait), pairs)
    raw = json.dumps(data, indent=1, ensure_ascii=False)
    left = [old for old, _ in pairs if old in raw]
    if left:
        print(f"refusing to write: still contains {left}", file=sys.stderr)
        return 1
    if re.search(r"robot or human|attention required|just a moment", data["tab"]["title"], re.I):
        print(f"refusing to write: the store served a bot wall ({data['tab']['title']!r})", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.name}.json.gz"
    out.write_bytes(gzip.compress(raw.encode(), mtime=0))
    print(f"wrote {out.relative_to(ROOT)}  title={data['tab']['title'][:70]!r}", file=sys.stderr)
    print(data["extract"]["text"][:1200])
    return 0


if __name__ == "__main__":
    sys.exit(main())

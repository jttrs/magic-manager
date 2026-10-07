"""Fetch a store product page for its recipe — politely, or from your open tab.

* Server modes (``shopify`` / ``meta``): one GET per page with an honest
  User-Agent, at most one request per host per ``PACE_SECONDS``, a short disk
  cache (prices move; 30 min), and bot-wall detection (:class:`storepage.Blocked`).
* ``rendered``: the page already open in your Chrome tab is read in place via
  AppleScript ``execute javascript`` (its head tags, JSON-LD and visible text).
  Needs Chrome → View → Developer → *Allow JavaScript from Apple Events*;
  without it :class:`JsEventsOff` explains the one-time fix. Never fetched
  server-side (docs/deals-scraping.md).
"""
from __future__ import annotations

import hashlib
import html as htmllib
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlsplit

import httpx

from . import storepage, vendors

PACE_SECONDS = 1.0
CACHE_SECONDS = 30 * 60
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36 magic-manager/0.1"

_last_hit: dict[str, float] = {}
_pace_lock = threading.Lock()


class JsEventsOff(RuntimeError):
    """Chrome refuses JavaScript from Apple Events (off by default)."""


class TabGone(RuntimeError):
    """The tab was closed (or navigated away) before it could be read."""


def _cache_dir() -> Path:
    d = Path(os.environ.get("MM_VENDOR_CACHE") or Path(tempfile.gettempdir()) / "mm-vendor-cache")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _pace(host: str) -> None:
    with _pace_lock:
        wait = PACE_SECONDS - (time.monotonic() - _last_hit.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        _last_hit[host] = time.monotonic()


def _get(url: str, *, fresh: bool = False, client: httpx.Client | None = None) -> tuple[int, str]:
    key = _cache_dir() / hashlib.sha256(url.encode()).hexdigest()
    if not fresh and key.exists() and time.time() - key.stat().st_mtime < CACHE_SECONDS:
        status, _, body = key.read_text().partition("\n")
        return int(status), body
    _pace(urlsplit(url).hostname or "")
    try:
        r = (client or httpx).get(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
                                  timeout=20, follow_redirects=True)
    except httpx.TimeoutException as e:
        raise storepage.Blocked("the store didn’t answer (timed out) — it may block automated reads") from e
    if r.status_code < 500:
        key.write_text(f"{r.status_code}\n{r.text}")
    return r.status_code, r.text


def shopify_js_url(url: str) -> str:
    """Canonical ``/products/<handle>.js`` (collection-scoped product URLs too)."""
    parts = urlsplit(url)
    m = re.search(r"/products/([^/?#.]+)", parts.path)
    if not m:
        raise ValueError(f"not a Shopify product URL: {url}")
    return f"{parts.scheme}://{parts.netloc}/products/{m.group(1)}.js"


# ---------- rendered: read the open tab ----------

_TAB_JS = (
    "JSON.stringify({"
    "head: document.head ? document.head.innerHTML.slice(0, 400000) : '',"
    "ld: Array.from(document.querySelectorAll('script[type=\\'application/ld+json\\']')).map(function(s){return s.textContent}),"
    "text: document.body ? document.body.innerText.slice(0, 40000) : '',"
    "title: document.title})"
)

_TAB_SCRIPT = '''
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t) is "{url}" then
        return execute t javascript "{js}"
      end if
    end repeat
  end repeat
  return "__GONE__"
end tell
'''


def _osascript(script: str) -> str:
    res = subprocess.run(["osascript", "-e", script], text=True, capture_output=True, check=False)
    if res.returncode != 0:
        err = res.stderr.strip()
        if "turned off" in err.lower() or "allow javascript from apple events" in err.lower():
            raise JsEventsOff("Chrome blocks reading open tabs. Turn on Chrome → View → Developer → "
                              "Allow JavaScript from Apple Events (once), then read again.")
        raise RuntimeError(f"Couldn’t read the tab: {err or 'osascript failed'}")
    return res.stdout.strip()


def read_tab(url: str, *, runner: Callable[[str], str] | None = None) -> tuple[str, str]:
    """``(html, text)`` of the open tab showing ``url``: its head tags + JSON-LD
    as HTML (for the tag parsers) and its visible text (for price patterns)."""
    esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')  # noqa: E731
    out = (runner or _osascript)(_TAB_SCRIPT.format(url=esc(url), js=esc(_TAB_JS)))
    if out == "__GONE__" or not out:
        raise TabGone("This store is read from your open tab — open the page in Chrome, then read again.")
    return page_from_extract(json.loads(out))


def page_from_extract(data: dict) -> tuple[str, str]:
    """``(html, text)`` for the recipe parsers from a rendered tab's extract
    ``{title, head, ld[], text}`` — read here by AppleScript, or in the user's
    own browser by the browser companion (same shape, so one parser path)."""
    title = htmllib.escape(str(data.get("title") or ""))
    html = str(data.get("head") or "") + "".join(
        f'<script type="application/ld+json">{ld}</script>' for ld in (data.get("ld") or []) if isinstance(ld, str))
    html = f"<html><head><title>{title}</title>{html}</head></html>"
    return html, str(data.get("text") or "")


# ---------- one listing ----------

def read(url: str, *, fresh: bool = False, client: httpx.Client | None = None,
         tab_runner: Callable[[str], str] | None = None,
         rendered: dict | None = None) -> tuple[vendors.Vendor, storepage.Listing]:
    """Read ``url`` with its store's recipe. ``rendered`` = the extract the
    browser companion read from the user's open tab (open-tab stores only).
    Raises :class:`LookupError` for an uncatalogued store,
    :class:`storepage.Blocked`, :class:`JsEventsOff`, :class:`TabGone`."""
    parts = urlsplit(url)
    m = vendors.classify(parts.hostname or "", parts.path)
    if m.vendor is None or m.kind != "product":
        raise LookupError("not a product page of a catalogued store")
    v = m.vendor
    if v.mode == "rendered":
        html, text = page_from_extract(rendered) if rendered is not None else read_tab(url, runner=tab_runner)
        storepage.check_blocked(html)
        return v, vendors.read_listing(v, html, text=text)
    if v.mode == "shopify":
        status, body = _get(shopify_js_url(url), fresh=fresh, client=client)
        if status == 404:
            raise LookupError("the store no longer has this product")
        storepage.check_blocked(body if status != 200 else "", status)
        variant = (parse_qs(parts.query).get("variant") or [None])[0]
        return v, vendors.read_listing(v, json.loads(body), variant=variant)
    status, body = _get(url, fresh=fresh, client=client)
    if status == 404:
        raise LookupError("the store no longer has this product")
    storepage.check_blocked(body, status)
    return v, vendors.read_listing(v, body)

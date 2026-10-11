"""Launch a Playwright browser that real sites treat like a person's.

Prefers the installed Chrome channel: bundled headless Chromium trips bot walls
(Cloudflare's "Attention Required!"), while real Chrome — especially headed —
clears managed challenges with no interaction. Shared by the Moxfield session
(``scripts/moxfield_session.py``) and the scrape canary (``scrape_canary``).
"""
from __future__ import annotations

ARGS = ["--disable-blink-features=AutomationControlled"]  # drops the most obvious automation tell


def launch(pw, *, headless: bool):
    """``pw`` = a started ``sync_playwright()``; returns a Browser."""
    for channel in ("chrome", None):
        try:
            kw = {"headless": headless, "args": ARGS}
            if channel:
                kw["channel"] = channel
            return pw.chromium.launch(**kw)
        except Exception:  # noqa: BLE001 — try the next channel
            continue
    return pw.chromium.launch(headless=headless)

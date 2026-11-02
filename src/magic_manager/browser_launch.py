"""Launch a Playwright browser that real sites treat like a person's.

Prefers the installed Chrome channel: bundled headless Chromium trips bot walls
(Cloudflare's "Attention Required!"), while real Chrome — especially headed —
clears managed challenges with no interaction. Shared by the Moxfield session
(``scripts/moxfield_session.py``) and the scrape canary (``scrape_canary``).
"""
from __future__ import annotations

import os

# Set (to "1") for a process that must never open a browser on this machine: the hosted web
# app's deck fetch for a member (owner_machine "decks.moxfield_server"). Checked here, at the one
# launch seam, and by scripts/moxfield_session.py + scripts/import_deck.py before they start one.
NO_SERVER_BROWSER_ENV = "MM_NO_SERVER_BROWSER"
NO_SERVER_BROWSER_MESSAGE = ("Moxfield decks are read in your own browser here: use the browser companion "
                             "(it reads the deck signed in as you, and you approve what it sends).")


class ServerBrowserRefused(RuntimeError):
    """A browser launch in a process that was started with NO_SERVER_BROWSER_ENV."""


def refused() -> bool:
    return os.environ.get(NO_SERVER_BROWSER_ENV) == "1"


ARGS = ["--disable-blink-features=AutomationControlled"]  # drops the most obvious automation tell


def launch(pw, *, headless: bool):
    """``pw`` = a started ``sync_playwright()``; returns a Browser."""
    if refused():
        raise ServerBrowserRefused(NO_SERVER_BROWSER_MESSAGE)
    for channel in ("chrome", None):
        try:
            kw = {"headless": headless, "args": ARGS}
            if channel:
                kw["channel"] = channel
            return pw.chromium.launch(**kw)
        except Exception:  # noqa: BLE001 — try the next channel
            continue
    return pw.chromium.launch(headless=headless)

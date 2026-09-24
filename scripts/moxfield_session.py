"""Shared Playwright authenticated-session helper for Moxfield.

Moxfield has no sanctioned API and its ``api2.moxfield.com`` deck endpoint sits
behind Cloudflare bot-protection that fingerprints the TLS handshake + a JS
challenge — a plain ``curl``/``urllib`` client gets HTTP 403 even with a real
browser User-Agent. A real browser engine (Playwright + Chromium) executes the
challenge JS and presents a browser TLS fingerprint, so it passes. This module
owns that browser context so both the deck reader (``import_deck.py``) and the
deck pusher (``moxfield_push.py``) share ONE auth cascade (DRY).

Auth cascade (most→least convenient), per the design locked with the user:
  1. PERSISTED  — reuse ``.deck-sessions/moxfield.json`` (a Playwright
     storage_state = cookies incl. cf_clearance + the Moxfield session). Launch
     headless; if the deck fetch comes back as a login redirect / 401, fall to (2).
  2. AUTO-LOGIN — if MOXFIELD_EMAIL/MOXFIELD_PASSWORD are in .env, fill the login
     form headless. If a Cloudflare Turnstile / captcha is detected, fall to (3).
  3. HEADED     — launch a visible browser, ask the user to log in by hand, wait
     for them to press Enter, then persist the storage_state for next time.

SECURITY: credentials are read from the gitignored .env and used only to fill the
login form in-memory; they are never written or logged. The persisted
storage_state contains a live session and MUST stay gitignored (``.deck-sessions/``).

This module is import-only plumbing (no ``__main__``); it is allow-listed past the
Moxfield network guard by path.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = ROOT / ".deck-sessions"
SESSION_FILE = SESSION_DIR / "moxfield.json"

LOGIN_URL = "https://www.moxfield.com/account/signin"
HOME_URL = "https://www.moxfield.com/"


def _load_env() -> dict:
    """Read .env (repo root); env vars override. Mirrors manapool_cart._load_env."""
    import os

    env: dict[str, str] = {}
    envfile = ROOT / ".env"
    if envfile.exists():
        for line in envfile.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    for k in ("MOXFIELD_EMAIL", "MOXFIELD_PASSWORD"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def _require_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print(
            "moxfield: Playwright is not installed. Run `uv sync` then "
            "`uv run playwright install chromium`. (Or use the bookmarklet / "
            "UI-export fallback — see the import-deck skill.)",
            file=sys.stderr,
        )
        raise SystemExit(2)
    from playwright.sync_api import sync_playwright
    return sync_playwright


def _looks_logged_in(page) -> bool:
    """Heuristic: the signed-in Moxfield chrome shows an account menu, not a
    'Sign in' link. Defensive — treat absence of a sign-in affordance as OK."""
    try:
        return page.locator("text=Sign in").count() == 0
    except Exception:
        return True


def _captcha_present(page) -> bool:
    """Detect a Cloudflare Turnstile / generic captcha iframe on the login page."""
    try:
        sel = "iframe[src*='challenges.cloudflare.com'], iframe[title*='captcha' i]"
        return page.locator(sel).count() > 0
    except Exception:
        return False


class MoxfieldSession:
    """Context manager yielding an authenticated Playwright ``context``.

    Usage:
        with MoxfieldSession(fresh=False) as ctx:
            resp = ctx.request.get("https://api2.moxfield.com/v3/decks/all/<id>")
    """

    def __init__(self, *, fresh: bool = False, headless: bool = True,
                 anonymous: bool = False):
        # anonymous=True skips the login cascade entirely and yields a fresh,
        # logged-OUT context — enough to clear Cloudflare and read a PUBLIC deck.
        # This is the default first attempt for reads; callers escalate to a
        # full (authenticated) session only when the anonymous fetch 401/403s.
        self.fresh = fresh
        self.headless = headless
        self.anonymous = anonymous
        self._pw = None
        self._browser = None
        self.context = None

    def __enter__(self):
        sync_playwright = _require_playwright()
        self._pw = sync_playwright().start()
        self._browser = self._launch()
        if self.anonymous:
            self.context = self._new_context(with_state=False)
            self.context.new_page().goto(HOME_URL, wait_until="domcontentloaded")
        else:
            self.context = self._authenticate()
        return self.context

    def __exit__(self, *exc):
        try:
            if self.context is not None and not self.anonymous:
                self._persist()
        finally:
            if self._browser is not None:
                self._browser.close()
            if self._pw is not None:
                self._pw.stop()

    # -- internals --------------------------------------------------------

    def _launch(self):
        """Launch Chromium, preferring the real installed Chrome channel — the
        bundled headless Chromium trips Cloudflare's bot interstitial ("Attention
        Required!"), whereas real Chrome (esp. headed) clears the managed
        challenge automatically. Falls back to bundled Chromium if Chrome is
        absent. ``--disable-blink-features=AutomationControlled`` drops the most
        obvious automation tell."""
        args = ["--disable-blink-features=AutomationControlled"]
        for channel in ("chrome", None):
            try:
                kw = {"headless": self.headless, "args": args}
                if channel:
                    kw["channel"] = channel
                return self._pw.chromium.launch(**kw)
            except Exception:
                continue
        # last resort: default bundled chromium, no channel
        return self._pw.chromium.launch(headless=self.headless)

    def _new_context(self, *, with_state: bool):
        kwargs = {
            # a realistic UA/viewport further reduces the automation fingerprint
            "viewport": {"width": 1280, "height": 900},
        }
        if with_state and SESSION_FILE.exists():
            kwargs["storage_state"] = str(SESSION_FILE)
        return self._browser.new_context(**kwargs)

    def _authenticate(self):
        # (1) persisted session
        if not self.fresh and SESSION_FILE.exists():
            ctx = self._new_context(with_state=True)
            page = ctx.new_page()
            page.goto(HOME_URL, wait_until="domcontentloaded")
            if _looks_logged_in(page):
                print("moxfield: using persisted session", file=sys.stderr)
                page.close()
                return ctx
            print("moxfield: persisted session stale — re-authenticating", file=sys.stderr)
            page.close()
            ctx.close()

        env = _load_env()
        email, password = env.get("MOXFIELD_EMAIL"), env.get("MOXFIELD_PASSWORD")

        # (2) headless credential auto-login
        if self.headless and email and password:
            ctx = self._new_context(with_state=False)
            page = ctx.new_page()
            page.goto(LOGIN_URL, wait_until="domcontentloaded")
            if _captcha_present(page):
                print("moxfield: captcha on login — falling back to headed manual login", file=sys.stderr)
                page.close(); ctx.close()
                return self._headed_login()
            try:
                page.fill("input[type='email'], input[name='userName'], input[name='email']", email)
                page.fill("input[type='password'], input[name='password']", password)
                page.click("button[type='submit'], button:has-text('Sign in')")
                page.wait_for_load_state("networkidle")
            except Exception as e:  # noqa: BLE001
                print(f"moxfield: auto-login failed ({e}) — falling back to headed login", file=sys.stderr)
                page.close(); ctx.close()
                return self._headed_login()
            if _looks_logged_in(page):
                print("moxfield: logged in via stored credentials", file=sys.stderr)
                page.close()
                return ctx
            print("moxfield: auto-login did not take — falling back to headed login", file=sys.stderr)
            page.close(); ctx.close()

        # (3) headed manual login
        return self._headed_login()

    def _headed_login(self):
        """Relaunch a VISIBLE browser and wait for the user to log in by hand."""
        if self.headless:
            # We were headless; relaunch the browser visibly.
            self._browser.close()
            self._browser = self._pw.chromium.launch(headless=False)
            self.headless = False
        ctx = self._new_context(with_state=False)
        page = ctx.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        print(
            "\nmoxfield: a browser window has opened. Log in to Moxfield (solve any "
            "captcha), then return here and press Enter to continue…",
            file=sys.stderr,
        )
        try:
            input()
        except EOFError:
            print("moxfield: no interactive stdin for manual login — aborting", file=sys.stderr)
            raise SystemExit(2)
        page.close()
        return ctx

    def _persist(self):
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self.context.storage_state(path=str(SESSION_FILE))
        except Exception as e:  # noqa: BLE001
            print(f"moxfield: could not persist session ({e})", file=sys.stderr)

"""The live scrape canary — read a known public sample for every scraper, per
site, and check it still reads the way it did when it was validated.

Deterministic and unattended (no agent): ``scripts/check_scrapers.py --live
--record`` runs it on a schedule (launchd, daily) and records the outcome in
``scraper_health``; the nightly GitHub workflow runs the store half
(``scripts/vendor_canary.py``). Each check returns ``ok`` / ``fail`` (the page
changed → the scraper is flagged down) / ``unverified`` (blocked, offline, or
the sample is gone → no flag).

* **HTTP** (no browser): every server-read store recipe (``shopify``/``meta``,
  each vendor's ``sample_url``), the Archidekt / MTGGoldfish / ManaBox /
  Scryfall deck importers (through the same ``scripts/import_deck.py`` the app
  runs) and EDHREC's commander / card / ranking pages.
* **Browser** (a real Chrome window opens briefly): open-tab stores with a
  sample page, Moxfield (the server import's deck response AND the companion's
  reader in one visit) and the companion's cart readers (Mana Pool, TCGplayer,
  Card Kingdom) on a guest (empty) cart. Readers are the extension's own files, injected verbatim.

Samples + expectations: ``config/vendors.toml`` (stores) and
``config/scraper_canaries.toml`` (everything else). Design: docs/scraper-health.md.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator
from urllib.parse import urlsplit

from . import scraper_health as health
from .scraper_health import Outcome

ROOT = Path(__file__).resolve().parents[2]
READERS = ROOT / "extension" / "src" / "readers"

Progress = Callable[[str], None]


@dataclass
class Check:
    key: str
    outcome: Outcome
    code: str | None = None
    message: str | None = None
    detail: dict = field(default_factory=dict)

    def record(self) -> tuple:
        return (self.key, self.outcome, self.code, self.message, self.detail)


def _fail(key: str, code: str, message: str | None = None, **detail) -> Check:
    return Check(key, "fail", code, message or health.reason(code), detail)


def _unverified(key: str, code: str, message: str | None = None, **detail) -> Check:
    return Check(key, "unverified", code, message or health.reason(code), detail)


@contextmanager
def _fresh() -> Iterator[None]:
    """Bypass the 24h response caches of the sanctioned wrappers for this run —
    a canary must read today's page, not yesterday's copy."""
    keys = {"EDHREC_CACHE_TTL": "0", "SCRYFALL_CACHE_TTL": "0"}
    old = {k: os.environ.get(k) for k in keys}
    os.environ.update(keys)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ---------- stores (server-read recipes) ----------

def check_store(vendor) -> Check:
    """One server-read store's sample product, read with its recipe."""
    import httpx

    from . import storefetch, storepage
    key = health.store_key(vendor.key)
    url = vendor.sample_url
    try:
        _, listing = storefetch.read(url, fresh=True)
    except LookupError as e:
        if type(e) is not LookupError:   # a KeyError/IndexError is a parser crash, not a 404
            return _fail(key, "scrape.error", f"{type(e).__name__}: {e}", url=url)
        return _unverified(key, "scrape.sample_gone", f"{health.reason('scrape.sample_gone')} ({e})", url=url)
    except storepage.Blocked as e:
        return _unverified(key, "scrape.blocked", str(e), url=url)
    except httpx.HTTPError as e:
        return _unverified(key, "scrape.unreachable", f"{type(e).__name__}: {e}", url=url)
    except Exception as e:  # noqa: BLE001 — a crash in the parser is a changed page
        return _fail(key, "scrape.error", f"{type(e).__name__}: {e}", url=url)
    detail = {"url": url, "price": listing.price, "available": listing.available, "title": listing.title}
    if listing.price is None:
        return _fail(key, "scrape.no_price", **detail)
    if not listing.title:
        return _fail(key, "scrape.no_title", **detail)
    return Check(key, "ok", detail=detail)


def check_stores(progress: Progress | None = None) -> list[Check]:
    from . import vendors
    out = []
    for v in vendors.catalog():
        if v.mode == "rendered" or not v.sample_url:
            continue
        if progress:
            progress(f"store {v.name}")
        out.append(check_store(v))
    return out


# ---------- deck importers ----------

def _names(cards: list[dict], board: str | None = None) -> set[str]:
    out = set()
    for c in cards:
        if board and c.get("board") != board:
            continue
        n = (c.get("name") or "").casefold()
        out |= {n, n.split(" // ")[0]}
    return out


def validate_deck(key: str, payload: dict, sample: dict) -> Check:
    """A fetched deck payload against its sample's validated expectations."""
    cards = payload.get("cards") or []
    total = sum(int(c.get("qty") or 0) for c in cards)
    detail = {"url": sample.get("url"), "name": payload.get("name"), "rows": len(cards), "cards": total}
    if not cards:
        return _fail(key, "scrape.no_cards", **detail)
    if any(not (c.get("name") or c.get("scryfall_id") or c.get("set")) for c in cards):
        return _fail(key, "scrape.shape_changed", "Some cards came back without a name or printing.", **detail)
    want = int(sample.get("min_cards") or 1)
    if total < want:
        return _fail(key, "scrape.expectation", f"Read {total} cards; the sample had at least {want}.", **detail)
    card = sample.get("card")
    if card and card.casefold() not in _names(cards):
        return _fail(key, "scrape.expectation", f"{card} is missing from the sample deck.", **detail)
    cmd = sample.get("commander")
    if cmd and cmd.casefold() not in _names(cards, "commander"):
        return _fail(key, "scrape.expectation", f"{cmd} no longer reads as the commander.", **detail)
    return Check(key, "ok", detail=detail)


def check_deck(source: str, sample: dict) -> Check:
    """One deck importer, through the same fetcher the app runs."""
    from . import addcards
    key = health.deck_key(source)
    try:
        payload = addcards.fetch_deck_payload(sample["url"])
    except RuntimeError as e:
        outcome, code = health.classify_error(str(e), unknown="fail")
        return Check(key, outcome, code, str(e), {"url": sample["url"]})
    except ValueError as e:  # the fetcher printed something that isn't JSON
        return _fail(key, "scrape.shape_changed", str(e), url=sample["url"])
    return validate_deck(key, payload, sample)


def check_decks(progress: Progress | None = None) -> list[Check]:
    decks = health.canary_samples().get("deck", {})
    out = []
    for src in health.DECK_SOURCES:
        if src == "moxfield" or not (decks.get(src) or {}).get("url"):
            continue
        if progress:
            progress(f"deck import {src}")
        out.append(check_deck(src, decks[src]))
    return out


# ---------- EDHREC ----------

def _edhrec_rows(cardviews: list[dict], key: str, want: int, what: str, *, need_pot: bool) -> Check:
    fields = ("name", "num_decks", "potential_decks") if need_pot else ("name", "num_decks")
    good = [cv for cv in cardviews if all(cv.get(f) not in (None, "") for f in fields)]
    detail = {"rows": len(cardviews), "complete": len(good)}
    if not cardviews:
        return _fail(key, "scrape.shape_changed", f"No {what} found on the page.", **detail)
    if len(good) < want:
        return _fail(key, "scrape.expectation", f"Only {len(good)} {what} carry {', '.join(fields)}; "
                     f"the sample had at least {want}.", **detail)
    return Check(key, "ok", detail=detail)


def check_edhrec(progress: Progress | None = None) -> list[Check]:
    from . import edhrec
    ed = health.canary_samples().get("edhrec") or {}
    if not ed:
        return []
    out = []

    def guarded(key: str, fn) -> Check:
        try:
            return fn()
        except edhrec.EdhrecError as e:
            outcome, code = health.classify_error(str(e), missing="fail", unknown="fail")
            return Check(key, outcome, code, str(e)[:500])
        except Exception as e:  # noqa: BLE001
            return _fail(key, "scrape.error", f"{type(e).__name__}: {e}")

    cmd, card = ed.get("commander"), ed.get("card")
    if cmd:
        if progress:
            progress("EDHREC commander page")
        lists = lambda: edhrec.cardlists(edhrec.commander_page(edhrec.slugify(cmd)))  # noqa: E731
        out.append(guarded("edhrec-commander/edhrec", lambda: _edhrec_rows(
            [cv for t, cvs in lists().items() if t in edhrec.COMMANDER_CARD_TAGS for cv in cvs],
            "edhrec-commander/edhrec", int(ed.get("min_cards", 50)), "recommended cards", need_pot=True)))
    if card:
        if progress:
            progress("EDHREC card page")
        clists = lambda: edhrec.cardlists(edhrec.card_page(edhrec.slugify(card)))  # noqa: E731
        out.append(guarded("edhrec-card/edhrec", lambda: _edhrec_rows(
            [cv for t, cvs in clists().items() if t in edhrec.CARD_COMMANDER_TAGS for cv in cvs],
            "edhrec-card/edhrec", int(ed.get("min_commanders", 10)), "commanders", need_pot=False)))
    if progress:
        progress("EDHREC rankings")
    out.append(guarded("edhrec-rankings/edhrec", lambda: _edhrec_rows(
        edhrec._plan_rankings("commanders", "week", color=None, tag=None, set_family=None).cardviews,
        "edhrec-rankings/edhrec", int(ed.get("min_ranked", 50)), "ranked commanders", need_pot=False)))
    return out


# ---------- browser: open-tab stores, Moxfield, the carts ----------

def _reader(name: str) -> str:
    return (READERS / name).read_text(encoding="utf-8")


def _settle(page, ms: int = 15_000) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=ms)
    except Exception:  # noqa: BLE001 — busy pages never go idle; read what rendered
        pass


def _bot_wall(page) -> bool:
    from . import storepage
    try:
        storepage.check_blocked(f"<html><head><title>{page.title()}</title></head></html>")
    except storepage.Blocked:
        return True
    return False


def check_rendered_store(ctx, vendor, url: str) -> Check:
    from . import storefetch, storepage
    key = health.store_key(vendor.key)
    page = ctx.new_page()
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        _settle(page)
        if resp is not None and resp.status == 404:
            return _unverified(key, "scrape.sample_gone", url=url)
        if _bot_wall(page) or (resp is not None and resp.status in (401, 403, 429)):
            return _unverified(key, "scrape.blocked", url=url)
        page.add_script_tag(content=_reader("store-page.js"))
        extract = page.evaluate("() => readStorePage(document)")
        _, listing = storefetch.read(url, rendered=extract)
    except storepage.Blocked as e:
        return _unverified(key, "scrape.blocked", str(e), url=url)
    except Exception as e:  # noqa: BLE001
        return _unverified(key, "scrape.unreachable", f"{type(e).__name__}: {e}"[:300], url=url)
    finally:
        page.close()
    detail = {"url": url, "price": listing.price, "available": listing.available, "title": listing.title}
    if listing.price is None:
        return _fail(key, "scrape.no_price", **detail)
    if not listing.title:
        return _fail(key, "scrape.no_title", **detail)
    return Check(key, "ok", detail=detail)


def check_moxfield(ctx, sample: dict) -> list[Check]:
    """One visit to a public Moxfield deck checks both the server import (the
    deck page's own deck-API response → ``decksource.parse_moxfield``) and the
    companion's reader (run in the page, then the app's strict request model)."""
    from . import decksource
    from .api import companion as companion_api
    url = sample["url"]
    deck_id = decksource.deck_id_from_url(url)
    server_key, reader_key = health.deck_key("moxfield"), "companion-deck/moxfield"
    page = ctx.new_page()
    try:
        try:
            with page.expect_response(lambda r: "/decks/all/" in r.url and deck_id in r.url, timeout=45_000) as info:
                page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            resp = info.value
        except Exception:  # noqa: BLE001 — no deck call: a bot wall or an SPA that changed
            blocked = _bot_wall(page)
            code = "scrape.blocked" if blocked else "scrape.shape_changed"
            msg = None if blocked else "The deck page no longer asks for the deck data where we listen."
            mk = _unverified if blocked else _fail
            return [mk(server_key, code, msg, url=url), mk(reader_key, code, msg, url=url)]
        status = resp.status
        if status == 404:
            return [_unverified(k, "scrape.sample_gone", url=url) for k in (server_key, reader_key)]
        if status in (401, 403, 429):
            return [_unverified(k, "scrape.blocked", url=url) for k in (server_key, reader_key)]
        checks = []
        try:
            data = resp.json()
            checks.append(validate_deck(server_key, decksource.payload_from_moxfield(data, deck_id), sample))
        except Exception as e:  # noqa: BLE001
            checks.append(_fail(server_key, "scrape.shape_changed", f"{type(e).__name__}: {e}"[:300], url=url))
        page.add_script_tag(content=_reader("moxfield-deck.js"))
        out = page.evaluate("id => readMoxfieldDeck(id)", deck_id)
        if not out.get("ok"):
            code = out.get("code") or "moxfield.changed"
            mk = _fail if code == "moxfield.changed" else _unverified
            checks.append(mk(reader_key, code if code == "moxfield.changed" else "scrape.blocked",
                             f"The reader said {code}.", url=url))
        else:
            try:
                req = companion_api.DeckFromBrowserIn(source="moxfield", deck=out["deck"])
                payload = decksource.payload_from_moxfield(req.deck.model_dump(), req.deck.publicId)
                checks.append(validate_deck(reader_key, payload, sample))
            except Exception as e:  # noqa: BLE001 — the reader's output no longer fits the app
                checks.append(_fail(reader_key, "moxfield.changed", f"{type(e).__name__}: {e}"[:300], url=url))
        return checks
    finally:
        page.close()


# The companion's cart readers per store: (reader file, global function).
CART_READERS = {
    "manapool": ("manapool-cart.js", "readManaPoolCart"),
    "tcgplayer": ("tcgplayer-cart.js", "readTcgplayerCart"),
    "cardkingdom": ("cardkingdom-cart.js", "readCardKingdomCart"),
}


def check_cart(ctx, sample: dict, store: str = "manapool") -> Check:
    key = f"companion-cart/{store}"
    file, fn = CART_READERS[store]
    url = sample["url"]
    page = ctx.new_page()
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        _settle(page)
        if _bot_wall(page) or (resp is not None and resp.status in (401, 403, 429)):
            return _unverified(key, "scrape.blocked", url=url)
        page.add_script_tag(content=_reader(file))
        out = page.evaluate(f"() => {fn}(document)")
    except Exception as e:  # noqa: BLE001
        return _unverified(key, "scrape.unreachable", f"{type(e).__name__}: {e}"[:300], url=url)
    finally:
        page.close()
    detail = {"url": url, "reader_code": out.get("code"), "path": urlsplit(url).path}
    want = sample.get("expect_code", "cart.empty")
    if out.get("ok") or out.get("code") == want:
        return Check(key, "ok", detail=detail)
    if out.get("code") == "cart.page_changed":
        return _fail(key, "cart.page_changed", **detail)
    return _fail(key, "scrape.expectation", f"The reader said {out.get('code')}; it used to say {want}.", **detail)


def detail_note(c: Check) -> str:
    return f"Headless read said {c.code}; needs a visible browser to confirm."


def _browser_targets(only: set[str] | None = None) -> list[tuple[str, list[str], Callable]]:
    """``(label, keys, run(ctx) -> list[Check])`` for every browser-only scraper
    with a sample, optionally narrowed to the ones covering ``only`` keys."""
    from . import vendors
    samples = health.canary_samples()
    out: list[tuple[str, list[str], Callable]] = []
    for v in vendors.catalog():
        url = v.sample_url or (samples.get("store", {}).get(v.key) or {}).get("url")
        if v.mode == "rendered" and url:
            out.append((f"store {v.name} (browser)", [health.store_key(v.key)],
                        lambda ctx, v=v, url=url: [check_rendered_store(ctx, v, url)]))
    mox = samples.get("deck", {}).get("moxfield") or {}
    if mox.get("url"):
        out.append(("Moxfield deck (browser)", [health.deck_key("moxfield"), "companion-deck/moxfield"],
                    lambda ctx: check_moxfield(ctx, mox)))
    for store, name in health.CART_STORES.items():
        cart = samples.get("cart", {}).get(store) or {}
        if cart.get("url") and store in CART_READERS:
            out.append((f"{name} cart (browser)", [f"companion-cart/{store}"],
                        lambda ctx, cart=cart, store=store: [check_cart(ctx, cart, store)]))
    return [t for t in out if only is None or set(t[1]) & only]


def _browser_pass(targets, *, headless: bool, progress: Progress | None) -> list[Check]:
    from . import browser_launch
    keys = [k for _, ks, _ in targets for k in ks]
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
    except Exception as e:  # noqa: BLE001
        return [_unverified(k, "scrape.browser_unavailable", f"{type(e).__name__}: {e}") for k in keys]
    out: list[Check] = []
    try:
        browser = browser_launch.launch(pw, headless=headless)
        try:
            for label, _, run_one in targets:
                if progress:
                    progress(label + ("" if headless else " — window"))
                ctx = browser.new_context(viewport={"width": 1280, "height": 900}, bypass_csp=True)
                try:
                    out.extend(run_one(ctx))
                finally:
                    ctx.close()
        finally:
            browser.close()
    except Exception as e:  # noqa: BLE001 — the browser itself failed
        done = {c.key for c in out}
        out += [_unverified(k, "scrape.browser_unavailable", f"{type(e).__name__}: {e}"[:300])
                for k in keys if k not in done]
    finally:
        pw.stop()
    return out


def check_browser(progress: Progress | None = None, *, headed: bool = True) -> list[Check]:
    """Every browser-only scraper with a sample: headless first (no window);
    anything that didn't read is retried once in a visible real Chrome window,
    and that verdict stands — bot defenses serve headless browsers a stripped
    page (Target hides the price; Best Buy drops the connection), so a headless
    failure alone never flags a scraper. ``headed=False`` skips the retry: those
    checks are then reported unverified, never down."""
    targets = _browser_targets()
    if not targets:
        return []
    first = _browser_pass(targets, headless=True, progress=progress)
    redo = {c.key for c in first if c.outcome != "ok"}
    if not redo:
        return first
    if not headed:
        return [c if c.outcome == "ok" else _unverified(c.key, "scrape.blocked", detail_note(c)) for c in first]
    retry = _browser_pass(_browser_targets(redo), headless=False, progress=progress)
    again = {c.key for c in retry}
    return [c for c in first if c.key not in again] + retry


# ---------- everything ----------

def run(*, browser: bool = True, headed: bool = True, progress: Progress | None = None) -> list[Check]:
    """Every live check, HTTP first. Never raises per check. ``browser=False``
    skips the browser checks (CI); ``headed=False`` never opens a window."""
    with _fresh():
        out = check_stores(progress) + check_decks(progress) + check_edhrec(progress)
        if browser:
            out += check_browser(progress, headed=headed)
    return out

"""Scraper health — is each site's scrape still reading the way it was validated?

Every function that reads a third-party page, per site, is one :class:`Scraper`
(``<scraper>/<site>``): the Deals store recipes (one per store in
``config/vendors.toml``, picked up generically), the deck importers, the browser
companion's readers and EDHREC's unofficial JSON. Its health is set by

* the scheduled **canary** (``magic_manager.scrape_canary`` via
  ``scripts/check_scrapers.py --live --record``), which reads a known public
  sample and asserts the originally-validated shape, and
* **real use**: a read in the app that finds the page changed (``fail``) or
  reads fine (``ok``) — the backup for scrapes the canary can't reach.

A failed check flags the scraper **down** (the app shows a "temporarily down"
notice where it's offered); the next passing check clears it. A check that
couldn't run (blocked, offline, sample removed) is **unverified** — never a
down flag, and it never clears one either.

State is a small JSON file beside the collection DB (``scraper_health.json``,
``MM_SCRAPER_HEALTH`` overrides) — not the collection DB, not precious: delete
it and the next run rebuilds it. Design: docs/scraper-health.md.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Literal

from . import config, db, vendors

FILE_NAME = "scraper_health.json"
VERSION = 1

Status = Literal["ok", "down", "unverified", "unknown"]
Outcome = Literal["ok", "fail", "unverified"]
CanaryKind = Literal["http", "browser", "none"]

# Every reason a check can report: code → (plain message, what fixes it).
# Companion codes (cart.*, moxfield.*) live in extension/errors.json; they're
# accepted here as reasons too (see REPORTABLE_CODES).
REASONS: dict[str, tuple[str, str]] = {
    "scrape.no_price": ("The page no longer shows a price where the recipe looks.",
                        "Update the store's recipe in config/vendors.toml and re-capture its fixture."),
    "scrape.no_title": ("The page no longer shows a product title where the recipe looks.",
                        "Update the store's recipe in config/vendors.toml and re-capture its fixture."),
    "scrape.no_cards": ("The deck page returned no cards — its format changed.",
                        "Fix the parser in decksource.py against a fresh copy of the page."),
    "scrape.shape_changed": ("The page's data no longer has the fields we read.",
                             "Fix the parser against a fresh copy of the page."),
    "scrape.expectation": ("The page reads, but not what it showed when it was validated.",
                           "Check the sample by hand; fix the parser, or update the sample's expectation."),
    "scrape.error": ("Reading the page crashed.",
                     "A code bug or a changed page — run the scraper by hand and read the traceback."),
    "scrape.blocked": ("The site blocked the automated check.",
                       "Nothing to fix yet — the check couldn't run. Use the app as usual."),
    "scrape.sample_gone": ("The sample page the check reads was removed.",
                           "Pick a new sample (vendors.toml sample_url or config/scraper_canaries.toml)."),
    "scrape.unreachable": ("The site couldn't be reached.",
                           "Usually temporary. The next check retries."),
    "scrape.browser_unavailable": ("No browser to run the check in.",
                                   "Install Chrome, or run `uv run playwright install chromium`."),
    "cart.page_changed": ("Mana Pool's cart page changed — the reader found no cart.",
                          "Follow the scrape-doctor skill: recapture the cart page and fix the reader."),
    "moxfield.changed": ("Moxfield's deck data changed format.",
                         "Follow the scrape-doctor skill: update the reader and decksource.parse_moxfield."),
    "orders.page_changed": ("The store's order history page changed — the reader found no orders or lines.",
                            "Follow the scrape-doctor skill: recapture the order page (de-personalised) and fix the reader."),
}

# Failures the browser companion reports from the user's own browser
# (POST /api/scrapers/report): a code that means the PAGE changed → the scraper
# it flags. User-situation codes (empty cart, private deck, …) never flag.
REPORTABLE_CODES: dict[str, str] = {
    "cart.page_changed": "companion-cart/manapool",
    "moxfield.changed": "companion-deck/moxfield",
    "orders.page_changed": "companion-orders/{store}",   # per store (report carries `store`)
}
ORDER_STORES = {"manapool": "Mana Pool", "tcgplayer": "TCGplayer", "cardkingdom": "Card Kingdom"}


def reported_key(code: str, store: str | None = None) -> str:
    """The scraper a reported companion code flags (order codes are per store)."""
    key = REPORTABLE_CODES[code]
    if "{store}" in key:
        if store not in ORDER_STORES:
            raise ValueError("an order-history report names its store")
        key = key.format(store=store)
    return key

DECK_SOURCES = ("archidekt", "mtggoldfish", "manabox", "scryfall", "moxfield")
_DECK_SITE_NAMES = {"archidekt": "Archidekt", "mtggoldfish": "MTGGoldfish", "manabox": "ManaBox",
                    "scryfall": "Scryfall", "moxfield": "Moxfield"}


@dataclass(frozen=True)
class Scraper:
    key: str             # "<scraper>/<site>"
    scraper: str         # store-price | deck-import | companion-cart | companion-deck | companion-orders | edhrec-*
    site: str            # vendor key / deck source / manapool / edhrec
    site_name: str
    label: str           # what it reads, in plain words
    where: str           # where the app offers it
    canary: CanaryKind   # how the scheduled check reaches it
    sample: str | None = None


@dataclass
class Health:
    scraper: Scraper
    status: Status = "unknown"
    since: str | None = None        # when the current status began
    checked_at: str | None = None   # last check of any outcome
    last_ok: str | None = None
    code: str | None = None
    message: str | None = None
    fix: str | None = None
    via: str | None = None          # canary | use
    detail: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Transition:
    key: str
    label: str
    change: Literal["down", "recovered", "sample_gone"]
    code: str | None
    message: str | None


# ---------- the registry ----------

def canary_samples() -> dict:
    return config.load_toml("scraper_canaries.toml")


def registry() -> list[Scraper]:
    """Every scraper, per site. Stores come straight from the vendor catalog, so
    a store added to config/vendors.toml is covered with no change here."""
    samples = canary_samples()
    out: list[Scraper] = []
    for v in vendors.catalog():
        sample = v.sample_url or (samples.get("store", {}).get(v.key) or {}).get("url")
        kind: CanaryKind = "none" if not sample else ("browser" if v.mode == "rendered" else "http")
        where = "Deals · your open tab" if v.mode == "rendered" else "Deals"
        out.append(Scraper(f"store-price/{v.key}", "store-price", v.key, v.name,
                           f"{v.name} prices", where, kind, sample))
    decks = samples.get("deck", {})
    for src in DECK_SOURCES:
        sample = (decks.get(src) or {}).get("url")
        kind = "none" if not sample else ("browser" if src == "moxfield" else "http")
        out.append(Scraper(f"deck-import/{src}", "deck-import", src, _DECK_SITE_NAMES[src],
                           f"{_DECK_SITE_NAMES[src]} deck import", "Add cards · Decks import", kind, sample))
    out.append(Scraper("companion-deck/moxfield", "companion-deck", "moxfield", "Moxfield",
                       "Moxfield deck read in your browser", "Add cards · Decks import (companion)",
                       "browser" if (decks.get("moxfield") or {}).get("url") else "none",
                       (decks.get("moxfield") or {}).get("url")))
    cart = (samples.get("cart", {}).get("manapool") or {}).get("url")
    out.append(Scraper("companion-cart/manapool", "companion-cart", "manapool", "Mana Pool",
                       "Mana Pool cart read in your browser", "Collection · cart check",
                       "browser" if cart else "none", cart))
    # Order history pages are signed in: no public sample → real use only (canary none).
    for site, name in ORDER_STORES.items():
        out.append(Scraper(f"companion-orders/{site}", "companion-orders", site, name,
                           f"{name} order history read in your browser", "Purchase history · Read my orders", "none"))
    ed = samples.get("edhrec") or {}
    for scr, label, sample in (("edhrec-commander", "EDHREC commander pages", ed.get("commander")),
                               ("edhrec-card", "EDHREC card pages", ed.get("card")),
                               ("edhrec-rankings", "EDHREC rankings", "commanders · week")):
        out.append(Scraper(f"{scr}/edhrec", scr, "edhrec", "EDHREC", label, "Explore",
                           "http" if ed else "none", sample))
    return out


def by_key() -> dict[str, Scraper]:
    return {s.key: s for s in registry()}


def deck_key(source: str) -> str:
    return f"deck-import/{source}"


def store_key(vendor_key: str) -> str:
    return f"store-price/{vendor_key}"


# ---------- the state file ----------

def path() -> Path:
    override = os.environ.get("MM_SCRAPER_HEALTH")
    return Path(override) if override else db.db_dir() / FILE_NAME


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read(p: Path) -> dict:
    try:
        data = json.loads(p.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"version": VERSION, "scrapers": {}}
    if not isinstance(data, dict) or not isinstance(data.get("scrapers"), dict):
        return {"version": VERSION, "scrapers": {}}
    return data


@contextmanager
def _locked(p: Path) -> Iterator[dict]:
    """Read-modify-write the state under an exclusive lock; written atomically."""
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = _read(p)
        yield state
        state["version"] = VERSION
        state["updated_at"] = _now()
        fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".scraper_health.", suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, p)


def _apply(rec: dict, outcome: Outcome, *, code, message, via, at, detail) -> str | None:
    """Fold one check into a scraper's record; returns the transition, if any."""
    prev = rec.get("status", "unknown")
    rec["checked_at"] = at
    if outcome == "ok":
        rec.update(status="ok", code=None, message=None, via=via, detail=detail or {})
        rec["last_ok"] = at
        if prev != "ok":
            rec["since"] = at
        return "recovered" if prev == "down" else None
    if outcome == "fail":
        if prev != "down":
            rec["since"] = at
        rec.update(status="down", code=code, message=message, via=via, detail=detail or {})
        return "down" if prev != "down" else None
    # unverified: the check couldn't run — it neither flags nor clears a flag.
    if prev == "down":
        rec.setdefault("detail", {})["last_unverified"] = {"at": at, "code": code}
        return None
    if prev != "unverified" or rec.get("code") != code:
        rec["since"] = at
    rec.update(status="unverified", code=code, message=message, via=via, detail=detail or {})
    return "sample_gone" if code == "scrape.sample_gone" and prev != "unverified" else None


def record(results: list[tuple[str, Outcome, str | None, str | None, dict | None]], *,
           via: str = "canary", at: str | None = None) -> list[Transition]:
    """Record many checks at once — ``(key, outcome, code, message, detail)`` —
    and return the changes worth telling the owner about."""
    at = at or _now()
    known = by_key()
    out: list[Transition] = []
    with _locked(path()) as state:
        recs = state["scrapers"]
        for key, outcome, code, message, detail in results:
            change = _apply(recs.setdefault(key, {}), outcome, code=code, message=message,
                            via=via, at=at, detail=detail)
            if change:
                label = known[key].label if key in known else key
                out.append(Transition(key, label, change, code, message))  # type: ignore[arg-type]
    return out


def record_use(key: str, outcome: Outcome, code: str | None = None, message: str | None = None) -> None:
    """A real read in the app. Never raises — health must never break a feature.
    ``unverified`` uses (blocked, private deck, offline) aren't recorded."""
    record_uses([(key, outcome, code, message)])


def record_uses(uses: list[tuple[str, Outcome, str | None, str | None]]) -> None:
    """Many real reads at once (one file write) — see :func:`record_use`."""
    rows = [(k, o, c, m, None) for k, o, c, m in uses if o != "unverified"]
    if not rows:
        return
    try:
        # A read that confirms what's already recorded needs no write (bulk syncs
        # call this per card).
        recs = _read(path())["scrapers"]
        if all(o == "ok" and (recs.get(k) or {}).get("status") == "ok" for k, o, *_ in rows):
            return
        record(rows, via="use")
    except Exception:  # noqa: BLE001
        pass


def health() -> list[Health]:
    """Every scraper with its current status (``unknown`` until first checked)."""
    recs = _read(path())["scrapers"]
    out = []
    for s in registry():
        r = recs.get(s.key) or {}
        code = r.get("code")
        out.append(Health(
            scraper=s, status=r.get("status", "unknown"), since=r.get("since"),
            checked_at=r.get("checked_at"), last_ok=r.get("last_ok"), code=code,
            message=r.get("message") or (REASONS.get(code, (None, None))[0] if code else None),
            fix=REASONS.get(code, (None, None))[1] if code else None,
            via=r.get("via"), detail=r.get("detail") or {}))
    return out


def down() -> list[Health]:
    return [h for h in health() if h.status == "down"]


def reason(code: str | None) -> str | None:
    return REASONS.get(code, (None, None))[0] if code else None


_HTTP = re.compile(r"HTTP(?: Error)? (\d{3})")


def classify_error(text: str, *, missing: Outcome = "unverified",
                   unknown: Outcome = "unverified") -> tuple[Outcome, str]:
    """A fetch/parse failure message → ``(outcome, code)``. Only failures that
    mean the PAGE changed are ``fail``; blocks, outages and user situations
    (private, removed) are ``unverified``. ``missing`` = what a 404 means (a
    removed sample, or — for a fixed endpoint like EDHREC's — a moved one)."""
    t = text or ""
    if re.search(r"no cards parsed", t, re.I):
        return "fail", "scrape.no_cards"
    if re.search(r"non-JSON|JSONDecodeError|KeyError|TypeError|AttributeError|IndexError", t):
        return "fail", "scrape.shape_changed"
    m = _HTTP.search(t)
    status = int(m.group(1)) if m else None
    if status == 404:
        return missing, ("scrape.sample_gone" if missing == "unverified" else "scrape.shape_changed")
    if status in (401, 403, 429) or re.search(r"cloudflare|interstitial|blocked|never fired|private", t, re.I):
        return "unverified", "scrape.blocked"
    if (status and status >= 500) or re.search(r"urlopen error|curl failed|timed? ?out|connection|"
                                               r"name resolution|network", t, re.I):
        return "unverified", "scrape.unreachable"
    return unknown, "scrape.error"

"""Scraper health surface of the typed API (see :mod:`magic_manager.scraper_health`).

``GET /api/scrapers/health`` — every scraper, per site, with its status; the app
shows a "temporarily down" notice wherever a down scraper is offered.
``POST /api/scrapers/report`` — the browser companion found a page changed in the
user's own browser (only page-changed codes are accepted; they flag the scraper).

Health is global, so hosted only an admin's report flags anything (a member's is
dropped — :func:`may_report`) and only an admin sees a check's raw message;
everyone else sees the reason catalog's plain message for its code.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import scraper_health


class ScraperHealthOut(BaseModel):
    key: str = Field(description="`<scraper>/<site>`, e.g. `store-price/manyrealms`, `deck-import/moxfield`.")
    scraper: str
    site: str
    site_name: str
    label: str
    where: str = Field(description="Where the app offers it.")
    canary: Literal["http", "browser", "none"] = Field(description="How the scheduled check reaches it (`none` = real use only).")
    status: Literal["ok", "down", "unverified", "unknown"]
    since: str | None = Field(None, description="UTC ISO time the current status began.")
    checked_at: str | None = None
    last_ok: str | None = None
    code: str | None = Field(None, description="Reason code (`scrape.*`, or a companion code).")
    message: str | None = None
    fix: str | None = None
    via: Literal["canary", "use"] | None = None


class ScrapersHealthOut(BaseModel):
    scrapers: list[ScraperHealthOut]
    down: int = Field(description="How many are flagged temporarily down.")


class ScraperReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: Literal["cart.page_changed", "moxfield.changed", "moxfield.collection_changed", "archidekt.changed", "orders.page_changed"]
    store: Literal["manapool", "tcgplayer", "cardkingdom"] | None = Field(None, description="Cart and order-history reports: which store's reader (a cart report without one is Mana Pool's).")


def may_report() -> bool:
    """May the bound user's report flag a scraper? Always locally; admins only hosted."""
    from .. import owner_machine
    return owner_machine.is_admin()


def _out(h: scraper_health.Health, *, raw: bool = True) -> ScraperHealthOut:
    s = h.scraper
    message = h.message if raw else scraper_health.reason(h.code)
    return ScraperHealthOut(key=s.key, scraper=s.scraper, site=s.site, site_name=s.site_name, label=s.label,
                            where=s.where, canary=s.canary, status=h.status, since=h.since,
                            checked_at=h.checked_at, last_ok=h.last_ok, code=h.code, message=message,
                            fix=h.fix, via=h.via if h.via in ("canary", "use") else None)


def health() -> ScrapersHealthOut:
    """Every scraper's status — with each check's own message for an admin (always
    locally), else only the plain message of its reason code."""
    raw = may_report()
    rows = [_out(h, raw=raw) for h in scraper_health.health()]
    return ScrapersHealthOut(scrapers=rows, down=sum(r.status == "down" for r in rows))


def report(req: ScraperReportIn) -> ScraperHealthOut:
    key = scraper_health.reported_key(req.code, req.store)
    scraper_health.record([(key, "fail", req.code, scraper_health.reason(req.code), None)], via="use")
    return next(_out(h) for h in scraper_health.health() if h.scraper.key == key)

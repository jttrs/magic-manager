"""Scraper health routes (docs/scraper-health.md)."""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import Response

from ..api import scrapers as scrapers_api

log = logging.getLogger("magic_manager.web")

router = APIRouter(prefix="/api/scrapers", tags=["scrapers"])


@router.get("/health", response_model=scrapers_api.ScrapersHealthOut)
def scrapers_health():
    return scrapers_api.health()


# Not behind the write guard: health isn't undoable user data (like consent).
# The app-wide same-origin guard still refuses cross-site posts.
# Hosted, health is everyone's: only an admin's report flags a scraper. A member's
# is dropped with a 204 (logged by code only), so no member can mark a site down
# for everyone.
@router.post("/report", response_model=scrapers_api.ScraperHealthOut,
             responses={204: {"description": "Not recorded: only an admin's report flags a scraper (hosted)."}})
def scrapers_report(body: scrapers_api.ScraperReportIn):
    if not scrapers_api.may_report():
        log.info("member scraper report dropped: %s (%s)", body.code, body.store or "-")
        return Response(status_code=204)
    return scrapers_api.report(body)

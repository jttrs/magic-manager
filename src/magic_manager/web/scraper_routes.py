"""Scraper health routes (docs/scraper-health.md)."""
from __future__ import annotations

from fastapi import APIRouter

from ..api import scrapers as scrapers_api

router = APIRouter(prefix="/api/scrapers", tags=["scrapers"])


@router.get("/health", response_model=scrapers_api.ScrapersHealthOut)
def scrapers_health():
    return scrapers_api.health()


# Not behind the write guard: health isn't undoable user data (like consent).
# The app-wide same-origin guard still refuses cross-site posts.
@router.post("/report", response_model=scrapers_api.ScraperHealthOut)
def scrapers_report(body: scrapers_api.ScraperReportIn):
    return scrapers_api.report(body)

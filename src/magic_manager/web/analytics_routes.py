"""Analytics routes (docs/analytics.md): consent, client ingest, delete-my-data, dashboards."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query

from .. import features as features_engine
from ..api import analytics as analytics_api

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/consent", response_model=analytics_api.ConsentOut)
def analytics_consent():
    return analytics_api.get_consent()


@router.put("/consent", response_model=analytics_api.ConsentOut)
def analytics_set_consent(body: analytics_api.ConsentIn):
    return analytics_api.set_consent(body)


@router.post("/events", response_model=analytics_api.EventsOut)
def analytics_events(body: analytics_api.EventsIn, x_mm_session: Annotated[str | None, Header()] = None):
    return analytics_api.ingest(body, x_mm_session)


@router.delete("/my-data", response_model=analytics_api.ForgetOut)
def analytics_forget():
    return analytics_api.forget()


@router.get("/catalog", response_model=list[analytics_api.CatalogEventOut])
def analytics_catalog():
    return analytics_api.catalog_events()


@router.get("/summary", response_model=analytics_api.SummaryOut)
def analytics_summary(days: Annotated[int, Query(ge=1, le=400)] = 30):
    try:
        return analytics_api.summary(days)
    except features_engine.FeatureDisabled as e:
        raise HTTPException(403, str(e)) from e


@router.get("/trace/{ref}", response_model=list[analytics_api.EventOut])
def analytics_trace(ref: str):
    try:
        return analytics_api.trace(ref)
    except features_engine.FeatureDisabled as e:
        raise HTTPException(403, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

"""Analytics surface of the typed API (see :mod:`magic_manager.analytics`, docs/analytics.md).

Consent, client-event ingest and delete-my-data are for every user; the
dashboard reads (summary, trace) are behind the internal ``analytics`` flag.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .. import analytics, features
from ..analytics import catalog, consent, dashboard

PropValue = str | int | float | bool


class ConsentOut(BaseModel):
    errors: bool = Field(description="Error/reliability telemetry (legitimate interest; opt-out).")
    usage: bool = Field(description="Usage analytics (opt-in when hosted).")
    asked: bool = Field(description="Whether the user has made a choice (hosted asks once).")
    mode: str = Field(description="local | hosted")
    disabled: bool = Field(description="MM_ANALYTICS=off: nothing is recorded on this server.")


class ConsentIn(BaseModel):
    errors: bool | None = None
    usage: bool | None = None


class ClientEventIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    props: dict[str, PropValue] = Field(default_factory=dict, max_length=16)
    ts: int | None = Field(default=None, description="Epoch milliseconds when it happened (≤ 24 h ago).")


class EventsIn(BaseModel):
    events: list[ClientEventIn] = Field(max_length=analytics.MAX_BATCH)


class Rejection(BaseModel):
    index: int
    reason: str


class EventsOut(BaseModel):
    accepted: int
    rejected: list[Rejection]
    dropped_props: int
    skipped_by_consent: int


class ForgetOut(BaseModel):
    deleted: int = Field(description="Raw events removed. Daily counts carry no user key and stay.")


class CatalogPropOut(BaseModel):
    name: str
    type: str
    required: bool
    values: list[str]


class CatalogEventOut(BaseModel):
    name: str
    version: int
    category: str
    source: str
    owner: str
    purpose: str
    props: list[CatalogPropOut]


class DayCount(BaseModel):
    day: str
    n: int


class ErrorGroup(BaseModel):
    name: str
    dims: dict[str, str]
    n: int
    first_seen: str
    last_seen: str


class EventOut(BaseModel):
    event_id: str
    name: str
    ts: str
    request_id: str | None
    session_id: str | None
    category: str | None = None
    props: dict[str, str]


class ViewUsage(BaseModel):
    view: str
    narrow: int
    wide: int
    n: int


class FeatureUsage(BaseModel):
    name: str
    dims: dict[str, str]
    n: int
    last_seen: str


class SessionsOut(BaseModel):
    by_day: list[DayCount]
    median_minutes: float | None
    median_events: float | None


class FunnelStep(BaseModel):
    step: str
    sessions: int


class JobOutcome(BaseModel):
    job: str
    runs: int
    failures: int
    mean_ms: int | None


class RetentionCell(BaseModel):
    cohort: str
    week: str
    users: int


class Totals(BaseModel):
    errors: int
    usage: int
    sessions: int
    sessions_with_errors: int


class StoreOut(BaseModel):
    path: str
    schema_version: int
    last_pruned: str | None
    events: dict[str, int]
    first_day: str | None


class SummaryOut(BaseModel):
    days: int
    since: str
    until: str
    totals: Totals
    error_trend: list[DayCount]
    top_errors: list[ErrorGroup]
    recent_errors: list[EventOut]
    views: list[ViewUsage]
    features: list[FeatureUsage]
    sessions: SessionsOut
    funnel: list[FunnelStep]
    jobs: list[JobOutcome]
    retention: list[RetentionCell]
    store: StoreOut
    consent: ConsentOut
    retention_policy: dict[str, int]


def get_consent() -> ConsentOut:
    return ConsentOut(**consent.get().public())


def set_consent(body: ConsentIn) -> ConsentOut:
    return ConsentOut(**consent.update(errors=body.errors, usage=body.usage).public())


def ingest(body: EventsIn, session_id: str | None) -> EventsOut:
    r = analytics.ingest_client([e.model_dump() for e in body.events], session_id=session_id)
    return EventsOut(accepted=r.accepted, rejected=[Rejection(**x) for x in r.rejected],
                     dropped_props=r.dropped_props, skipped_by_consent=r.skipped_by_consent)


def forget() -> ForgetOut:
    return ForgetOut(deleted=analytics.forget_user())


def catalog_events() -> list[CatalogEventOut]:
    cat = catalog.load()
    return [CatalogEventOut(name=e.name, version=e.version, category=e.category, source=e.source,
                            owner=e.owner, purpose=e.purpose,
                            props=[CatalogPropOut(name=p.name, type=p.type, required=p.required,
                                                  values=list(cat.views if p.type == "view" else p.values))
                                   for p in e.props.values()])
            for e in cat.events.values()]


def summary(days: int) -> SummaryOut:
    features.require("analytics")
    return SummaryOut(**dashboard.summary(days))


def trace(ref: str) -> list[EventOut]:
    features.require("analytics")
    return [EventOut(**e) for e in dashboard.trace(ref)]

"""Self-hosted product analytics: a typed event catalog, a separate event store,
consent split by purpose, and dashboards over portable SQL (docs/analytics.md).

The one write seam is :func:`record` (server events) / :func:`ingest_client`
(client batches). Both validate against the catalog, honor consent, attach only
linking IDs (``event_id``, ``session_id``, ``request_id``, the HMAC user key) and
never raise into the caller — analytics must not be able to break the app.
"""
from __future__ import annotations

import contextvars
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from . import catalog, consent, identity, store

log = logging.getLogger("magic_manager.analytics")

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MAX_BATCH = 50
CLIENT_MAX_AGE = timedelta(hours=24)
CLIENT_MAX_SKEW = timedelta(minutes=5)


@dataclass(frozen=True)
class Context:
    request_id: str | None = None
    session_id: str | None = None


_ctx: contextvars.ContextVar[Context] = contextvars.ContextVar("mm_analytics_ctx", default=Context())


def current() -> Context:
    return _ctx.get()


def bind(ctx: Context) -> contextvars.Token:
    return _ctx.set(ctx)


def reset(token: contextvars.Token) -> None:
    _ctx.reset(token)


def session_id_or_none(value: str | None) -> str | None:
    """A client session id is only ever a random UUID; anything else is dropped."""
    v = (value or "").strip().lower()
    return v if _UUID.match(v) else None


class _Bucket:
    """Global token bucket: caps how fast client events are accepted (flood guard)."""

    def __init__(self, per_minute: int = 600) -> None:
        self.capacity = float(per_minute)
        self.tokens = float(per_minute)
        self.rate = per_minute / 60.0
        self.at = time.monotonic()
        self.lock = threading.Lock()

    def take(self) -> bool:
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.at) * self.rate)
            self.at = now
            if self.tokens < 1:
                return False
            self.tokens -= 1
            return True


_bucket = _Bucket()


def _row(checked: catalog.Checked, ctx: Context, at: datetime | None = None) -> store.Row:
    row = store.Row(checked=checked, session_id=ctx.session_id, request_id=ctx.request_id,
                    user_key=identity.user_key(), key_version=identity.key_version())
    if at is not None:
        row.at = at
    return row


def record(name: str, props: dict | None = None, *, ctx: Context | None = None) -> bool:
    """Record one SERVER event if the catalog and the user's consent allow it."""
    try:
        if consent.disabled():
            return False
        checked = catalog.validate(name, props, source="server")
        if not consent.get().allows(checked.event.category):
            return False
        store.insert([_row(checked, ctx or current())])
        return True
    except Exception as e:  # noqa: BLE001 — analytics never breaks the caller
        log.warning("analytics: could not record %s (%s: %s)", name, type(e).__name__, e)
        return False


def record_response(route: str | None, method: str, status: int, code: str | None, *, ctx: Context | None = None) -> None:
    """Server events derived from an API response: ``api.error`` for 4xx/5xx, and
    any catalog event whose ``triggers`` name this route for a 2xx."""
    if not route:
        return
    if status >= 400:
        record("api.error", {"route": route, "method": method, "status": status,
                             "code": code or f"http_{status}"}, ctx=ctx)
    elif 200 <= status < 300:
        try:
            triggered = catalog.load().triggers_for(route)
        except Exception:  # noqa: BLE001
            return
        for ev, constants in triggered:
            record(ev.name, dict(constants), ctx=ctx)


@dataclass
class IngestResult:
    accepted: int = 0
    rejected: list[dict] = field(default_factory=list)
    dropped_props: int = 0
    skipped_by_consent: int = 0


def ingest_client(events: list[dict], *, session_id: str | None) -> IngestResult:
    """Validate and record a batch of CLIENT events. Each rejection names its reason."""
    out = IngestResult()
    if consent.disabled():
        out.skipped_by_consent = len(events)
        return out
    c = consent.get()
    ctx = Context(session_id=session_id_or_none(session_id), request_id=current().request_id)
    now = datetime.now(UTC)
    rows: list[store.Row] = []
    for i, raw in enumerate(events[:MAX_BATCH]):
        name = raw.get("name") if isinstance(raw, dict) else None
        try:
            if not isinstance(name, str):
                raise ValueError("event has no name")
            checked = catalog.validate(name, raw.get("props") or {}, source="client")
            if not c.allows(checked.event.category):
                out.skipped_by_consent += 1
                continue
            at = now
            ts = raw.get("ts")
            if ts is not None:
                if isinstance(ts, bool) or not isinstance(ts, (int, float)):
                    raise ValueError("ts must be epoch milliseconds")
                at = datetime.fromtimestamp(ts / 1000, UTC)
                if at < now - CLIENT_MAX_AGE or at > now + CLIENT_MAX_SKEW:
                    raise ValueError("ts is outside the accepted window (last 24 hours)")
            if not _bucket.take():
                raise ValueError("rate limited")
        except ValueError as e:
            out.rejected.append({"index": i, "reason": str(e)})
            continue
        out.dropped_props += len(checked.dropped)
        rows.append(_row(checked, ctx, at))
    for i in range(MAX_BATCH, len(events)):
        out.rejected.append({"index": i, "reason": f"batch is limited to {MAX_BATCH} events"})
    try:
        out.accepted = store.insert(rows)
    except Exception as e:  # noqa: BLE001
        log.warning("analytics: could not store a client batch (%s: %s)", type(e).__name__, e)
        out.rejected.extend({"index": -1, "reason": "store unavailable"} for _ in rows)
    return out


def forget_user(user_id: str = identity.LOCAL_USER) -> int:
    """Delete-my-data: remove every raw event under this user's current key."""
    return store.forget(identity.user_key(user_id))


__all__ = ["Context", "bind", "catalog", "consent", "current", "forget_user", "identity",
           "ingest_client", "record", "record_response", "reset", "session_id_or_none", "store"]

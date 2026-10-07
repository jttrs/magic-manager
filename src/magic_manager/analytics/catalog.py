"""The analytics event catalog: the closed, typed list of events the app may record.

``config/analytics_events.toml`` is the single source of truth (see its header and
docs/analytics.md). :func:`validate` is the one gate every event passes — server
or client: unknown events are rejected, unknown properties dropped, and every
value checked against its declared type. There is no free-text type, so nothing
a user typed (card names, notes, URLs, emails) can be recorded.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from .. import config

CATALOG_FILE = "analytics_events.toml"
CATEGORIES = ("error", "usage")
SOURCES = ("server", "client")
TYPES = ("enum", "int", "code", "route", "view", "job_id", "ingest_id")

# A dotted snake_case code: letters first, ≤ 64 chars, no long digit runs (so it
# can't smuggle an id, phone number or IP).
_CODE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
_ROUTE = re.compile(r"^[a-z][a-z0-9_]*$")
_JOB_ID = re.compile(r"^[0-9a-f]{32}$")
_DIGIT_RUN = re.compile(r"\d{5,}")


class CatalogError(ValueError):
    """The catalog file itself is malformed."""


@dataclass(frozen=True)
class Prop:
    name: str
    type: str
    required: bool = False
    values: tuple[str, ...] = ()
    min: int | None = None
    max: int | None = None


@dataclass(frozen=True)
class Event:
    name: str
    version: int
    category: str
    source: str
    owner: str
    purpose: str
    props: dict[str, Prop] = field(default_factory=dict)
    dims: tuple[str, ...] = ()
    triggers: dict[str, dict[str, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Catalog:
    events: dict[str, Event]
    views: tuple[str, ...]
    retention: dict[str, int] = field(default_factory=dict)

    def triggers_for(self, route: str) -> list[tuple[Event, dict[str, str]]]:
        return [(e, e.triggers[route]) for e in self.events.values() if route in e.triggers]


def _prop(name: str, raw: dict) -> Prop:
    t = raw.get("type")
    if t not in TYPES:
        raise CatalogError(f"property {name!r}: unknown type {t!r} (allowed: {', '.join(TYPES)})")
    if t == "enum" and not raw.get("values"):
        raise CatalogError(f"property {name!r}: an enum needs values")
    return Prop(name=name, type=t, required=bool(raw.get("required", False)),
                values=tuple(str(v) for v in raw.get("values", ())),
                min=raw.get("min"), max=raw.get("max"))


def parse(data: dict) -> Catalog:
    views = tuple(data.get("views", {}).get("values", ()))
    if not views:
        raise CatalogError("[views] values is required")
    events: dict[str, Event] = {}
    for name, raw in (data.get("events") or {}).items():
        if not _CODE.match(name):
            raise CatalogError(f"event name {name!r} must be a dotted snake_case code")
        for key in ("version", "category", "source", "owner", "purpose"):
            if key not in raw:
                raise CatalogError(f"event {name!r}: missing {key!r}")
        if raw["category"] not in CATEGORIES:
            raise CatalogError(f"event {name!r}: category must be one of {CATEGORIES}")
        if raw["source"] not in SOURCES:
            raise CatalogError(f"event {name!r}: source must be one of {SOURCES}")
        props = {p: _prop(p, v) for p, v in (raw.get("props") or {}).items()}
        dims = tuple(raw.get("dims", ()))
        for d in dims:
            if d not in props:
                raise CatalogError(f"event {name!r}: dim {d!r} is not a property")
            if props[d].type in ("job_id", "ingest_id"):
                raise CatalogError(f"event {name!r}: record ids can't be aggregate dims")
        triggers = {r: {k: str(v) for k, v in (c or {}).items()} for r, c in (raw.get("triggers") or {}).items()}
        if triggers and raw["source"] != "server":
            raise CatalogError(f"event {name!r}: only server events have route triggers")
        ev = Event(name=name, version=int(raw["version"]), category=raw["category"],
                   source=raw["source"], owner=str(raw["owner"]), purpose=str(raw["purpose"]),
                   props=props, dims=dims, triggers=triggers)
        cat_views = views
        for route, constants in triggers.items():
            for k, v in constants.items():
                if k not in props or check_value(props[k], v, cat_views) is None:
                    raise CatalogError(f"event {name!r}: trigger {route!r} sets invalid {k}={v!r}")
        events[name] = ev
    retention = {k: int(v) for k, v in (data.get("retention") or {}).items()}
    for k in ("error_days", "usage_days", "aggregate_days"):
        if retention.get(k, 0) <= 0:
            raise CatalogError(f"[retention] {k} must be a positive number of days")
    return Catalog(events=events, views=views, retention=retention)


@lru_cache(maxsize=1)
def load() -> Catalog:
    return parse(config.load_toml(CATALOG_FILE, required=True))


def check_value(prop: Prop, value: object, views: tuple[str, ...]) -> str | None:
    """The value as stored text, or None when it doesn't fit the property's type."""
    t = prop.type
    if t in ("enum", "view"):
        allowed = prop.values if t == "enum" else views
        return value if isinstance(value, str) and value in allowed else None
    if t in ("int", "ingest_id"):
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        lo = prop.min if prop.min is not None else (1 if t == "ingest_id" else None)
        if (lo is not None and value < lo) or (prop.max is not None and value > prop.max):
            return None
        return str(value)
    if not isinstance(value, str):
        return None
    if t == "code":
        ok = len(value) <= 64 and _CODE.match(value) and not _DIGIT_RUN.search(value)
        return value if ok else None
    if t == "route":
        return value if len(value) <= 64 and _ROUTE.match(value) else None
    if t == "job_id":
        return value if _JOB_ID.match(value) else None
    return None


@dataclass
class Checked:
    event: Event
    props: dict[str, str]
    dropped: list[str]


def validate(name: str, props: dict | None, *, source: str, catalog: Catalog | None = None) -> Checked:
    """Check one event against the catalog. Raises ``ValueError`` (with a specific
    reason) when the event can't be recorded; drops unknown or invalid optional
    properties and lists them in ``dropped``."""
    cat = catalog or load()
    ev = cat.events.get(name)
    if ev is None:
        raise ValueError(f"unknown event {name!r}")
    if ev.source != source:
        raise ValueError(f"event {name!r} is a {ev.source} event")
    out: dict[str, str] = {}
    dropped: list[str] = []
    for key, value in (props or {}).items():
        prop = ev.props.get(key)
        text = check_value(prop, value, cat.views) if prop else None
        if text is None:
            dropped.append(key)
        else:
            out[key] = text
    missing = [p.name for p in ev.props.values() if p.required and p.name not in out]
    if missing:
        raise ValueError(f"event {name!r}: missing or invalid {', '.join(missing)}")
    return Checked(event=ev, props=out, dropped=dropped)


def dims_key(ev: Event, props: dict[str, str]) -> str:
    """Canonical aggregate key: ``k=v;k=v`` in catalog dim order."""
    return ";".join(f"{d}={props.get(d, '')}" for d in ev.dims)


def parse_dims(key: str) -> dict[str, str]:
    return dict(part.split("=", 1) for part in key.split(";") if "=" in part)


def to_code(name: str) -> str:
    """``StaleCounts`` / ``HTTPException`` → ``stale_counts`` / ``http_exception``."""
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()
    s = re.sub(r"[^a-z0-9_]+", "_", s).strip("_")
    s = re.sub(r"\d{5,}", "", s) or "unknown"
    if not s[0].isalpha():
        s = "e_" + s
    return s[:64]

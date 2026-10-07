"""Dashboards over the analytics store — the saved, portable SQL in ``queries/``.

The same named queries back the in-app Analytics view, ``mm analytics`` and any
notebook (``mm analytics sql <name>`` prints one to paste into DuckDB or a
notebook). This module only runs them and shapes rows; every number is SQL.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from importlib import resources
from statistics import median

from . import catalog as cat_mod, consent, store


def query_names() -> list[str]:
    return sorted(p.name[:-4] for p in resources.files(__package__).joinpath("queries").iterdir()
                  if p.name.endswith(".sql"))


def sql(name: str) -> str:
    if name not in query_names():
        raise LookupError(f"no saved query {name!r} (have: {', '.join(query_names())})")
    return resources.files(__package__).joinpath("queries", f"{name}.sql").read_text()


def since_day(days: int, *, today: date | None = None) -> str:
    return ((today or datetime.now(UTC).date()) - timedelta(days=max(days, 1) - 1)).isoformat()


def run(name: str, *, days: int = 30, limit: int = 50, request_id: str = "", today: date | None = None) -> list[dict]:
    """Run one saved query with the standard parameters (unused ones are ignored)."""
    text = sql(name)
    params = {"since": since_day(days, today=today), "limit": limit, "request_id": request_id}
    with store.connect() as conn:
        return [dict(r) for r in conn.execute(text, {k: v for k, v in params.items() if f":{k}" in text})]


def _group_props(rows: list[dict]) -> list[dict]:
    """Fold (event, key, value) rows from a LEFT JOIN into one dict per event."""
    out: dict[str, dict] = {}
    for r in rows:
        ev = out.setdefault(r["event_id"], {k: r[k] for k in r if k not in ("key", "value", "ts_ms")} | {"props": {}})
        if r.get("key") is not None:
            ev["props"][r["key"]] = r["value"]
    return list(out.values())


def trace(request_id: str) -> list[dict]:
    rid = request_id.strip().lower()
    if len(rid) < 6 or not all(c in "0123456789abcdef" for c in rid):
        raise ValueError("a request ref is at least 6 hex characters")
    return _group_props(run("trace", request_id=rid))


def summary(days: int = 30, *, today: date | None = None) -> dict:
    """Everything the dashboard shows for the last ``days`` days."""
    today = today or datetime.now(UTC).date()
    cat = cat_mod.load()
    start = date.fromisoformat(since_day(days, today=today))
    all_days = [(start + timedelta(days=i)).isoformat() for i in range((today - start).days + 1)]

    trend_rows = run("error_trend", days=days, today=today)
    per_day: dict[str, int] = {d: 0 for d in all_days}
    for r in trend_rows:
        per_day[r["day"]] = per_day.get(r["day"], 0) + r["n"]

    top = [{"name": r["name"], "dims": cat_mod.parse_dims(r["dims"]), "n": r["n"],
            "first_seen": r["first_seen"], "last_seen": r["last_seen"]}
           for r in run("top_errors", days=days, limit=25, today=today)]
    recent = _group_props(run("recent_errors", days=days, limit=30, today=today))

    views: dict[str, dict] = {}
    features: list[dict] = []
    for r in run("usage_by_event", days=days, today=today):
        dims = cat_mod.parse_dims(r["dims"])
        if r["name"] == "page.viewed":
            v = views.setdefault(dims.get("view", "other"), {"view": dims.get("view", "other"), "narrow": 0, "wide": 0, "n": 0})
            v[dims.get("viewport", "wide")] = v.get(dims.get("viewport", "wide"), 0) + r["n"]
            v["n"] += r["n"]
        else:
            features.append({"name": r["name"], "dims": dims, "n": r["n"], "last_seen": r["last_seen"]})

    lengths = run("session_lengths", days=days, today=today)
    minutes = [(r["end_ms"] - r["start_ms"]) / 60000 for r in lengths]
    sessions_by_day = {r["day"]: r["sessions"] for r in run("sessions_by_day", days=days, today=today)}
    funnel = (run("funnel_collection_buylist", days=days, today=today) or [{"viewed_collection": 0, "exported_buylist": 0}])[0]

    return {
        "days": days,
        "since": all_days[0],
        "until": all_days[-1],
        "totals": {
            "errors": sum(per_day.values()),
            "usage": sum(v["n"] for v in views.values()) + sum(f["n"] for f in features),
            "sessions": len(lengths),
            "sessions_with_errors": sum(1 for r in lengths if r["errors"]),
        },
        "error_trend": [{"day": d, "n": per_day.get(d, 0)} for d in all_days],
        "top_errors": top,
        "recent_errors": recent,
        "views": sorted(views.values(), key=lambda v: -v["n"]),
        "features": features,
        "sessions": {
            "by_day": [{"day": d, "n": sessions_by_day.get(d, 0)} for d in all_days],
            "median_minutes": round(median(minutes), 1) if minutes else None,
            "median_events": median([r["events"] for r in lengths]) if lengths else None,
        },
        "funnel": [
            {"step": "Opened Collection", "sessions": funnel["viewed_collection"]},
            {"step": "Exported a buy-list", "sessions": funnel["exported_buylist"]},
        ],
        "jobs": [{"job": r["job"], "runs": r["runs"], "failures": r["failures"],
                  "mean_ms": round(r["mean_ms"]) if r["mean_ms"] is not None else None}
                 for r in run("job_outcomes", days=days, today=today)],
        "retention": run("retention_weekly", days=max(days, 56), today=today),
        "store": store.stats(),
        "consent": consent.get().public(),
        "retention_policy": dict(cat.retention),
    }

"""Consent: what this user lets us record, split by purpose (docs/analytics.md § Consent).

* **errors** — reliability telemetry, legitimate interest: ON unless the user opts out.
* **usage** — product analytics: ON by default in local mode (it's the owner's own
  machine); OFF until the user opts in when hosted (``MM_MODE=hosted``).

The choice is stored in the collection DB's ``settings`` table (key
``analytics.consent``) — a user table, so in the hosted layout it lives in that
user's own file. ``MM_ANALYTICS=off`` disables all recording (CI, demos).
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass

from .. import db

SETTING_KEY = "analytics.consent"
CACHE_SECONDS = 30.0

_cache: dict[str, tuple[float, "Consent"]] = {}
_lock = threading.Lock()


@dataclass(frozen=True)
class Consent:
    errors: bool
    usage: bool
    asked: bool
    mode: str
    disabled: bool = False

    def allows(self, category: str) -> bool:
        if self.disabled:
            return False
        return self.errors if category == "error" else self.usage

    def public(self) -> dict:
        return asdict(self)


def mode() -> str:
    return "hosted" if os.environ.get("MM_MODE", "local").strip().lower() == "hosted" else "local"


def disabled() -> bool:
    return os.environ.get("MM_ANALYTICS", "").strip().lower() in ("off", "0", "false", "no")


def _defaults(m: str) -> dict:
    return {"errors": True, "usage": m == "local", "asked": m == "local"}


def get(*, fresh: bool = False) -> Consent:
    m = mode()
    key = f"{db.db_path()}|{m}"
    now = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and not fresh and now - hit[0] < CACHE_SECONDS and hit[1].disabled == disabled():
            return hit[1]
    stored: dict = {}
    with db.connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (SETTING_KEY,)).fetchone()
    if row and row["value"]:
        try:
            stored = json.loads(row["value"])
        except ValueError:
            stored = {}
    merged = {**_defaults(m), **{k: bool(v) for k, v in stored.items() if k in ("errors", "usage", "asked")}}
    c = Consent(mode=m, disabled=disabled(), **merged)
    with _lock:
        _cache[key] = (now, c)
    return c


def update(*, errors: bool | None = None, usage: bool | None = None) -> Consent:
    """Record the user's choice (marks it as asked). Takes effect immediately."""
    cur = get(fresh=True)
    value = {"errors": cur.errors if errors is None else bool(errors),
             "usage": cur.usage if usage is None else bool(usage),
             "asked": True}
    with db.connect() as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                     "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                     (SETTING_KEY, json.dumps(value, sort_keys=True)))
    clear_cache()
    return get(fresh=True)


def clear_cache() -> None:
    with _lock:
        _cache.clear()

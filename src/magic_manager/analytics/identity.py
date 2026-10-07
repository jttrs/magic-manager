"""Pseudonymous user key: ``HMAC-SHA256(user_id, server secret)`` — one-way.

Analytics rows carry only this key, never a user id. Linking a key back to a user
needs the app's user table AND the secret; rotating the secret (a new value)
makes every older key unlinkable, which is the same as anonymizing them.

The secret comes from ``MM_ANALYTICS_SECRET`` (the host's secret store when
hosted), else a random per-install file ``analytics.secret`` (mode 0600) beside the
collection DB — never beside the analytics DB, so read access to analytics alone
can't re-identify anyone. Local mode has one user, ``local``.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets as pysecrets
import threading
from pathlib import Path

from .. import db

LOCAL_USER = "local"
SECRET_FILE = "analytics.secret"
_lock = threading.Lock()


def _secret_file() -> Path:
    return db.db_dir() / SECRET_FILE


def secret() -> bytes:
    env = os.environ.get("MM_ANALYTICS_SECRET")
    if env:
        return env.encode()
    p = _secret_file()
    with _lock:
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(pysecrets.token_hex(32))
        return p.read_text().strip().encode()


def key_version() -> str:
    """A short fingerprint naming which secret produced a key (reveals nothing)."""
    return hashlib.sha256(b"mm-analytics-key-version:" + secret()).hexdigest()[:8]


def user_key(user_id: str = LOCAL_USER) -> str:
    return hmac.new(secret(), user_id.encode(), hashlib.sha256).hexdigest()[:32]

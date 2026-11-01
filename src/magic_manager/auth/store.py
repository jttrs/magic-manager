"""``auth.db``: users, linked sign-in identities, sessions and invite codes.

A SEPARATE SQLite file (never the collection DB, never a ``db.MIGRATIONS`` entry)
with its own ``meta.schema_version``, like the analytics store. It lives in the data
dir — beside the collection DB in the single layout, beside ``catalog.db`` in the
split layout — and ``MM_AUTH_DB`` overrides the path (tests).

Only what §25.1 H10 allows is stored: the provider's subject id, a display name and
an email. Secrets are stored hashed: a session token and an invite code are random
256-bit values handed out ONCE; only their SHA-256 lives here, so a copy of this file
can't sign anyone in. Provider access tokens are never stored.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets as pysecrets
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .. import db

SCHEMA_VERSION = 1
FILE_NAME = "auth.db"

SESSION_IDLE = timedelta(days=14)
SESSION_ABSOLUTE = timedelta(days=30)
# last_seen_at is refreshed at most this often (one write per minute, not per request).
TOUCH_EVERY = timedelta(minutes=1)
INVITE_DEFAULT = timedelta(days=7)
PROVIDERS = ("discord", "google")

_SCHEMA = [
    "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    """CREATE TABLE IF NOT EXISTS users (
        id           TEXT PRIMARY KEY CHECK (length(id) = 16 AND id NOT GLOB '*[^a-z0-9]*'),
        display_name TEXT NOT NULL,
        email        TEXT,
        is_admin     INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
        created_at   TEXT NOT NULL,
        disabled_at  TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS identities (
        provider TEXT NOT NULL CHECK (provider IN ('discord', 'google')),
        subject  TEXT NOT NULL,
        user_id  TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE (provider, subject)
    )""",
    "CREATE INDEX IF NOT EXISTS identities_user ON identities (user_id)",
    """CREATE TABLE IF NOT EXISTS sessions (
        token_hash   TEXT PRIMARY KEY,
        user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        csrf_token   TEXT NOT NULL,
        created_at   TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        expires_at   TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS sessions_user ON sessions (user_id)",
    """CREATE TABLE IF NOT EXISTS invites (
        code_hash  TEXT PRIMARY KEY,
        created_by TEXT,
        is_admin   INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
        expires_at TEXT NOT NULL,
        used_by    TEXT REFERENCES users(id) ON DELETE SET NULL,
        used_at    TEXT
    )""",
]

_lock = threading.Lock()
_ready: set[str] = set()


class InviteInvalid(Exception):
    """The invite can't be used (one plain message: no oracle for guessing codes)."""


def path() -> Path:
    override = os.environ.get("MM_AUTH_DB")
    if override:
        return Path(override)
    return db.data_dir() / FILE_NAME


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).isoformat(timespec="seconds")


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_token() -> str:
    """256 random bits, URL-safe."""
    return pysecrets.token_urlsafe(32)


def new_user_id() -> str:
    """16 chars of ``[a-z2-7]`` (80 random bits) — safe as ``users/<id>.db``."""
    return base64.b32encode(pysecrets.token_bytes(10)).decode().lower()


@contextmanager
def connect(p: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Autocommit connection (writes that must be atomic use :func:`_tx`)."""
    target = p or path()
    target.parent.mkdir(parents=True, exist_ok=True)
    existed = target.exists()
    conn = sqlite3.connect(target, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        key = str(target.resolve())
        if key not in _ready or not existed:
            with _lock:
                if not existed:
                    os.chmod(target, 0o600)
                conn.execute("PRAGMA journal_mode = WAL")
                for stmt in _SCHEMA:
                    conn.execute(stmt)
                conn.execute("INSERT INTO meta (key, value) VALUES ('schema_version', ?) "
                             "ON CONFLICT (key) DO UPDATE SET value = excluded.value", (str(SCHEMA_VERSION),))
                _ready.add(key)
        yield conn
    finally:
        conn.close()


@contextmanager
def _tx(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


# ---------- users ----------

@dataclass(frozen=True)
class User:
    id: str
    display_name: str
    email: str | None
    is_admin: bool
    created_at: str
    disabled_at: str | None

    @property
    def disabled(self) -> bool:
        return self.disabled_at is not None


def _user(row: sqlite3.Row) -> User:
    return User(row["id"], row["display_name"], row["email"], bool(row["is_admin"]),
                row["created_at"], row["disabled_at"])


def get_user(user_id: str) -> User | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user(row) if row else None


def users() -> list[tuple[User, list[str]]]:
    """Every user with the providers linked to them, oldest first."""
    with connect() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at, id").fetchall()
        links: dict[str, list[str]] = {}
        for r in conn.execute("SELECT user_id, provider FROM identities ORDER BY provider"):
            links.setdefault(r["user_id"], []).append(r["provider"])
    return [(_user(r), links.get(r["id"], [])) for r in rows]


def user_for_identity(provider: str, subject: str) -> User | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT u.* FROM identities i JOIN users u ON u.id = i.user_id WHERE i.provider = ? AND i.subject = ?",
            (provider, subject)).fetchone()
    return _user(row) if row else None


def update_profile(user_id: str, display_name: str, email: str | None) -> None:
    """Keep the stored name/email current with the provider's (H10: nothing else)."""
    with connect() as conn:
        conn.execute("UPDATE users SET display_name = ?, email = ? WHERE id = ?", (display_name, email, user_id))


def revoke(user_id: str, *, disable: bool = False) -> int:
    """Sign a user out everywhere (and optionally disable them). Returns sessions ended."""
    with connect() as conn, _tx(conn):
        if conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
            raise LookupError(f"no user {user_id!r}")
        if disable:
            conn.execute("UPDATE users SET disabled_at = COALESCE(disabled_at, ?) WHERE id = ?", (_iso(_now()), user_id))
        return conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,)).rowcount


# ---------- invites ----------

@dataclass(frozen=True)
class Invite:
    code: str          # shown ONCE; only its hash is stored
    is_admin: bool
    expires_at: str


def create_invite(*, is_admin: bool, expires_in: timedelta = INVITE_DEFAULT, created_by: str | None = None) -> Invite:
    if expires_in <= timedelta(0):
        raise ValueError("an invite must expire in the future")
    code = new_token()
    expires = _iso(_now() + expires_in)
    with connect() as conn:
        conn.execute("INSERT INTO invites (code_hash, created_by, is_admin, expires_at) VALUES (?, ?, ?, ?)",
                     (hash_secret(code), created_by, int(is_admin), expires))
    return Invite(code, is_admin, expires)


def invite_is_admin(code: str) -> bool:
    """The admin flag of a usable invite; raises InviteInvalid otherwise."""
    with connect() as conn:
        return bool(_usable_invite(conn, code)["is_admin"])


def _usable_invite(conn: sqlite3.Connection, code: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM invites WHERE code_hash = ?", (hash_secret(code),)).fetchone()
    if row is None or row["used_at"] is not None or _parse(row["expires_at"]) <= _now():
        raise InviteInvalid("That invite link can't be used — it may have been used already or expired.")
    return row


def redeem_invite(code: str, provider: str, subject: str, display_name: str, email: str | None) -> User:
    """Create a user from an invite and link the identity — one transaction; the code is spent."""
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider!r}")
    with connect() as conn, _tx(conn):
        inv = _usable_invite(conn, code)
        if conn.execute("SELECT 1 FROM identities WHERE provider = ? AND subject = ?", (provider, subject)).fetchone():
            raise InviteInvalid("This account already has a profile — sign in without the invite.")
        uid = new_user_id()
        now = _iso(_now())
        conn.execute("INSERT INTO users (id, display_name, email, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
                     (uid, display_name, email, inv["is_admin"], now))
        conn.execute("INSERT INTO identities (provider, subject, user_id) VALUES (?, ?, ?)", (provider, subject, uid))
        conn.execute("UPDATE invites SET used_by = ?, used_at = ? WHERE code_hash = ?", (uid, now, inv["code_hash"]))
        return _user(conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone())


# ---------- sessions ----------

@dataclass(frozen=True)
class Session:
    user: User
    csrf_token: str
    token_hash: str


@dataclass(frozen=True)
class NewSession:
    token: str         # goes into the cookie; never stored
    csrf_token: str
    expires_at: datetime


def create_session(user_id: str, *, replaces: str | None = None) -> NewSession:
    """A fresh session. Rotation: the presented old token, if any, is deleted."""
    token, csrf = new_token(), new_token()
    now = _now()
    expires = now + SESSION_ABSOLUTE
    with connect() as conn, _tx(conn):
        # Sign-ins are rare: sweep every expired session here, so abandoned ones don't pile up.
        conn.execute("DELETE FROM sessions WHERE expires_at <= ? OR last_seen_at <= ?",
                     (_iso(now), _iso(now - SESSION_IDLE)))
        if replaces:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_secret(replaces),))
        conn.execute("INSERT INTO sessions (token_hash, user_id, csrf_token, created_at, last_seen_at, expires_at) "
                     "VALUES (?, ?, ?, ?, ?, ?)", (hash_secret(token), user_id, csrf, _iso(now), _iso(now), _iso(expires)))
    return NewSession(token, csrf, expires)


def session_for(token: str | None) -> Session | None:
    """The live session behind a cookie token, else None. Expired sessions and those of
    disabled users are deleted on sight."""
    if not token:
        return None
    th = hash_secret(token)
    now = _now()
    with connect() as conn:
        row = conn.execute("SELECT s.token_hash, s.csrf_token, s.last_seen_at, s.expires_at, u.* "
                           "FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?", (th,)).fetchone()
        if row is None:
            return None
        if (row["disabled_at"] is not None or _parse(row["expires_at"]) <= now
                or _parse(row["last_seen_at"]) + SESSION_IDLE <= now):
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (th,))
            return None
        if _parse(row["last_seen_at"]) + TOUCH_EVERY <= now:
            conn.execute("UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?", (_iso(now), th))
        return Session(_user(row), row["csrf_token"], th)


def end_session(token: str | None) -> bool:
    if not token:
        return False
    with connect() as conn:
        return conn.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_secret(token),)).rowcount > 0


def prune_sessions() -> int:
    """Delete expired sessions (absolute or idle)."""
    now = _now()
    with connect() as conn:
        return conn.execute("DELETE FROM sessions WHERE expires_at <= ? OR last_seen_at <= ?",
                            (_iso(now), _iso(now - SESSION_IDLE))).rowcount


def csrf_matches(session: Session, presented: str | None) -> bool:
    """Constant-time compare of the session's CSRF token with the request header."""
    if not presented:
        return False
    return hmac.compare_digest(session.csrf_token.encode(), presented.encode())

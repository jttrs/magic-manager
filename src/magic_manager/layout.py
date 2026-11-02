"""Which file each table lives in, and which files a connection opens.

Phase 3 (docs/webapp-architecture-decision.md §25, H1/H2/H11) splits the one
SQLite file into a shared **catalog** (cards, prices, Tagger/art tags, EDHREC,
MTGJSON-derived caches) and one small **user** file per person (their
collection, ledger, decks, wishlist, earmarks, settings). This module is the
ONE registry of that split plus the layout switch; it is framework-free and
never opens a database itself (``db.connect`` does).

Layouts (``MM_LAYOUT``):

* ``single`` (default) — today's one file (``db/magic_manager.db``).
* ``split`` — ``<MM_DATA_DIR>/users/<user>.db`` opened as ``main`` with
  ``<MM_DATA_DIR>/catalog.db`` attached as ``catalog``. ``MM_DATA_DIR``
  defaults to the DB directory. ``<user>`` is the user BOUND to the current
  context (:func:`as_user` / :func:`bind_user` — the hosted web layer binds the
  signed-in user per request, the job runner binds a job's submitter), else
  ``MM_USER`` (default ``owner``; CLI and local only).

**Fail closed (hosted).** The hosted web server calls :func:`set_strict` at
start: from then on a connection with NO bound user raises :class:`NoUserBound`
instead of falling back to ``MM_USER``, and the single layout is refused (every
user would share one file). The engine never takes a user parameter (§25.3).

``MAGIC_MANAGER_DB`` always forces a single file (CLI, skills, tests,
rehearsals). ``MM_MODE`` (login on/off) is a separate switch and is not read
here.
"""
from __future__ import annotations

import contextvars
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

# Your data, parents before children (undo copies them in this order).
USER_TABLES: tuple[str, ...] = (
    "settings", "set_targets", "imports",
    "ingest_events", "inventory", "inventory_events",
    "decks", "deck_cards", "deck_versions", "deck_assignments",
    "wishlist_entries", "earmarked_products", "earmark_links", "earmark_prices", "earmark_targets",
    "purchases", "purchase_lines", "card_earmarks",
)

# Shared, rebuildable caches — the same for every user.
CATALOG_TABLES: frozenset[str] = frozenset({
    "cards",
    "scryfall_tags", "card_oracle_tags", "illustration_art_tags",
    "edhrec_pages", "edhrec_commander_cards", "edhrec_card_commanders", "edhrec_rankings",
    "front_cards",
    "catalog_settings",
})

# SQLite/bookkeeping tables every file carries for itself. Unqualified names
# resolve to ``main`` (the user file) in the split layout.
INFRA_TABLES: frozenset[str] = frozenset({"schema_version", "sqlite_sequence"})

# Pre-V2 ``lists`` / ``list_rows``: read only by the V2/V4 migrations (and
# ``scripts/rehearse_migration.py``); nothing else reads them. Not carried
# into the split layout.
LEGACY_TABLES: frozenset[str] = frozenset({"lists", "list_rows"})

# Bookkeeping Litestream creates in every file it replicates (hosted, §25.4 step 8):
# a sequence counter and an always-empty lock table — never user data. Not part of
# the code's schema; readers that list a file's tables skip them.
LITESTREAM_TABLES: frozenset[str] = frozenset({"_litestream_seq", "_litestream_lock"})

CATALOG_SCHEMA = "catalog"
CATALOG_FILENAME = "catalog.db"
USERS_SUBDIR = "users"
DEFAULT_USER = "owner"
LAYOUTS = ("single", "split")

_USER_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
# Hosted users are auth ids (``auth.store`` CHECK: 16 of [a-z0-9]); in strict mode a
# bound user must match before any path is built from it.
AUTH_ID_RE = re.compile(r"[a-z0-9]{16}")


class LayoutError(ValueError):
    """A layout setting is invalid, or the split files aren't ready."""


class NoUserBound(LayoutError):
    """Strict (hosted) mode: a connection was asked for with no user bound."""


_bound: contextvars.ContextVar[str | None] = contextvars.ContextVar("mm_user", default=None)
_strict = False


def set_strict(on: bool) -> None:
    """Process-wide: the hosted web server turns this on (a local app turns it off)."""
    global _strict
    _strict = bool(on)


def strict() -> bool:
    return _strict


def check_user(user: str) -> str:
    """``user`` if it is safe as a file name (and, in strict mode, an auth id)."""
    if not isinstance(user, str) or not _USER_RE.fullmatch(user):
        raise LayoutError(f"invalid user name {user!r} (letters, digits, '-' and '_' only)")
    if _strict and not AUTH_ID_RE.fullmatch(user):
        raise LayoutError("invalid user id")
    return user


def bound_user() -> str | None:
    """The user bound to this context, or None."""
    return _bound.get()


def bind_user(user: str) -> contextvars.Token:
    return _bound.set(check_user(user))


def reset_user(token: contextvars.Token) -> None:
    _bound.reset(token)


@contextmanager
def as_user(user: str | None) -> Iterator[None]:
    """Bind ``user`` for the body (``None`` leaves the context as it is)."""
    if user is None:
        yield
        return
    token = bind_user(user)
    try:
        yield
    finally:
        reset_user(token)


def classify(table: str) -> str:
    """``user`` | ``catalog`` | ``infra`` | ``legacy``; KeyError if unclassified."""
    if table in USER_TABLES:
        return "user"
    if table in CATALOG_TABLES:
        return "catalog"
    if table in INFRA_TABLES:
        return "infra"
    if table in LEGACY_TABLES:
        return "legacy"
    raise KeyError(f"table {table!r} is not classified in magic_manager.layout")


@dataclass(frozen=True)
class Layout:
    kind: str                      # 'single' | 'split'
    path: Path                     # single: the file; split: the user file (main)
    catalog: Path | None = None    # split only
    user: str | None = None        # split only


def user_db_path(data_dir: Path, user: str) -> Path:
    if not _USER_RE.fullmatch(user):
        raise LayoutError(f"invalid user name {user!r} (letters, digits, '-' and '_' only)")
    return data_dir / USERS_SUBDIR / f"{user}.db"


def kind_of(env: Mapping[str, str]) -> str:
    """``single`` | ``split`` for this environment (no user resolution)."""
    if env.get("MAGIC_MANAGER_DB"):
        return "single"
    kind = (env.get("MM_LAYOUT") or "single").strip().lower()
    if kind not in LAYOUTS:
        raise LayoutError(f"MM_LAYOUT must be one of {', '.join(LAYOUTS)} (got {kind!r})")
    return kind


def data_dir_of(env: Mapping[str, str], default_dir: Path) -> Path:
    """The split data dir (``MM_DATA_DIR``, else ``default_dir``)."""
    return Path(env.get("MM_DATA_DIR") or default_dir)


def resolve(env: Mapping[str, str], *, single_path: Path, default_dir: Path) -> Layout:
    """The layout for this context. ``single_path`` is ``db.db_path()``."""
    kind = kind_of(env)
    if _strict and kind != "split":
        raise LayoutError("hosted mode needs the split layout (MM_LAYOUT=split): one file can't hold several users")
    if kind == "single":
        return Layout("single", single_path)
    data_dir = data_dir_of(env, default_dir)
    user = _bound.get()
    if user is None:
        if _strict:
            raise NoUserBound("no signed-in user is bound to this request")
        user = env.get("MM_USER") or DEFAULT_USER
    return Layout("split", user_db_path(data_dir, check_user(user)), data_dir / CATALOG_FILENAME, user)

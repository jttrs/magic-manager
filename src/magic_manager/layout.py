"""Which file each table lives in, and which files a connection opens.

Phase 3 (docs/webapp-architecture-decision.md §25, H1/H2/H11) splits the one
SQLite file into a shared **catalog** (cards, prices, Tagger/art tags, EDHREC,
MTGJSON-derived caches) and one small **user** file per person (their
collection, ledger, decks, wishlist, earmarks, settings). This module is the
ONE registry of that split plus the layout switch; it is framework-free and
never opens a database itself (``db.connect`` does).

Layouts (``MM_LAYOUT``):

* ``single`` (default) — today's one file (``db/magic_manager.db``).
* ``split`` — ``<MM_DATA_DIR>/users/<MM_USER>.db`` opened as ``main`` with
  ``<MM_DATA_DIR>/catalog.db`` attached as ``catalog``. ``MM_DATA_DIR``
  defaults to the DB directory, ``MM_USER`` to ``owner`` (the web layer will
  pick the user per request later).

``MAGIC_MANAGER_DB`` always forces a single file (CLI, skills, tests,
rehearsals). ``MM_MODE`` (login on/off) is a separate switch and is not read
here.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# Your data, parents before children (undo copies them in this order).
USER_TABLES: tuple[str, ...] = (
    "settings", "set_targets", "imports",
    "ingest_events", "inventory", "inventory_events",
    "decks", "deck_cards", "deck_versions", "deck_assignments",
    "wishlist_entries", "earmarked_products", "earmark_links", "earmark_prices", "earmark_targets",
    "purchases", "purchase_lines",
)

# Shared, rebuildable caches — the same for every user.
CATALOG_TABLES: frozenset[str] = frozenset({
    "cards",
    "scryfall_tags", "card_oracle_tags", "illustration_art_tags",
    "edhrec_pages", "edhrec_commander_cards", "edhrec_card_commanders", "edhrec_rankings",
    "front_cards",
})

# SQLite/bookkeeping tables every file carries for itself. Unqualified names
# resolve to ``main`` (the user file) in the split layout.
INFRA_TABLES: frozenset[str] = frozenset({"schema_version", "sqlite_sequence"})

# Pre-V2 ``lists`` / ``list_rows``: read only by the V2/V4 migrations (and
# ``scripts/rehearse_migration.py``); nothing else reads them. Not carried
# into the split layout.
LEGACY_TABLES: frozenset[str] = frozenset({"lists", "list_rows"})

CATALOG_SCHEMA = "catalog"
CATALOG_FILENAME = "catalog.db"
USERS_SUBDIR = "users"
DEFAULT_USER = "owner"
LAYOUTS = ("single", "split")

_USER_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")


class LayoutError(ValueError):
    """A layout setting is invalid, or the split files aren't ready."""


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


def resolve(env: Mapping[str, str], *, single_path: Path, default_dir: Path) -> Layout:
    """The layout for this process. ``single_path`` is ``db.db_path()``."""
    if env.get("MAGIC_MANAGER_DB"):
        return Layout("single", single_path)
    kind = (env.get("MM_LAYOUT") or "single").strip().lower()
    if kind not in LAYOUTS:
        raise LayoutError(f"MM_LAYOUT must be one of {', '.join(LAYOUTS)} (got {kind!r})")
    if kind == "single":
        return Layout("single", single_path)
    data_dir = Path(env.get("MM_DATA_DIR") or default_dir)
    user = env.get("MM_USER") or DEFAULT_USER
    return Layout("split", user_db_path(data_dir, user), data_dir / CATALOG_FILENAME, user)

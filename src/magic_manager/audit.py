"""Consistency checks over the DB that no constraint enforces.

``catalog_refs`` replaces the user tables' FOREIGN KEYs into ``cards`` that V36
dropped (in the split layout ``cards`` lives in another file, where SQLite
can't enforce them): it lists user rows whose ``scryfall_id`` has no ``cards``
row. Works in the single and split layouts (unqualified ``cards`` resolves to
the catalog file). CLI: ``mm audit catalog-refs``.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from . import db
from .layout import USER_TABLES


@dataclass
class CatalogRefs:
    table: str
    rows: int = 0                                          # user rows with no card
    scryfall_ids: list[str] = field(default_factory=list)  # distinct missing printings, sorted


def card_ref_tables(conn: sqlite3.Connection) -> list[str]:
    """User tables that carry a ``scryfall_id`` (registry order)."""
    out = []
    for t in USER_TABLES:
        cols = {r[1] for r in conn.execute(f'PRAGMA main.table_info("{t}")')}
        if "scryfall_id" in cols:
            out.append(t)
    return out


def catalog_refs(conn: sqlite3.Connection | None = None) -> list[CatalogRefs]:
    """Per user table with a ``scryfall_id``: rows pointing at a printing the
    catalog doesn't have (NULL ids aren't references)."""
    with db.transaction(conn) as c:
        out = []
        for t in card_ref_tables(c):
            found = CatalogRefs(t)
            for sid, n in c.execute(
                f'SELECT u.scryfall_id, COUNT(*) FROM main."{t}" u '
                f"WHERE u.scryfall_id IS NOT NULL "
                f"AND NOT EXISTS (SELECT 1 FROM cards c WHERE c.scryfall_id = u.scryfall_id) "
                f"GROUP BY u.scryfall_id ORDER BY u.scryfall_id"
            ):
                found.rows += n
                found.scryfall_ids.append(sid)
            out.append(found)
    return out

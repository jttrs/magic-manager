"""Wishlist CRUD + value math.

Wishlist entries live in the V4 ``wishlist_entries`` table — one row per
``(scryfall_id, finish, category)``. The single-table-with-category shape
replaces the V1 ``wishlist:*`` / ``buy:*`` / ``idea:*`` label-prefix split
(see plan §"Notes / decisions"): any of those former prefixes is now just
a free-text ``category`` value, while keeping the same semantic intent
("a card I want, organized by purpose").

This module mirrors :mod:`magic_manager.lists` shape-for-shape but reads
and writes the new table. ``lists.py`` stays in place until Phase 4e.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import db


_ALLOWED_FINISHES = ("nonfoil", "foil", "either")


# ---------- row shape ----------

@dataclass
class WishlistRow:
    scryfall_id: str
    finish: str            # 'nonfoil' | 'foil' | 'either'
    category: str
    qty_wanted: int
    priority: int | None
    notes: str | None
    added_at: str
    name: str
    flavor_name: str | None
    set_code: str
    collector_number: str
    rarity: str
    prices_usd: float | None
    prices_usd_foil: float | None
    cmc: float | None

    @property
    def unit_price(self) -> float | None:
        # finish='either' uses prices_usd (the cheaper-finish convention:
        # if the user is finish-agnostic, value the line at the nonfoil
        # price since that's typically the floor).
        if self.finish == "foil":
            return self.prices_usd_foil
        return self.prices_usd

    @property
    def line_value(self) -> float | None:
        p = self.unit_price
        return p * self.qty_wanted if p is not None else None

    @property
    def display_name(self) -> str:
        """Render as ``<flavor_name> / <oracle_name>`` for reskin printings,
        otherwise just the oracle name. Mirrors the V1.7 reskin display rule
        documented at lists.py:47.
        """
        return f"{self.flavor_name} / {self.name}" if self.flavor_name else self.name


# ---------- read helpers ----------

def wishlist_show(category: str | None = None) -> list[WishlistRow]:
    """Every wishlist entry, optionally filtered to one category.

    Joined to ``cards`` so callers get display fields. Ordered by
    category, set_code, collector_number, finish for determinism.
    """
    sql = """
        SELECT we.scryfall_id, we.finish, we.category, we.qty_wanted,
               we.priority, we.notes, we.added_at,
               c.name, c.flavor_name, c.set_code, c.collector_number,
               c.rarity, c.prices_usd, c.prices_usd_foil, c.cmc
        FROM wishlist_entries we
        JOIN cards c ON c.scryfall_id = we.scryfall_id
        {where}
        ORDER BY we.category, c.set_code, c.collector_number, we.finish
    """
    args: tuple
    if category is None:
        sql = sql.format(where="")
        args = ()
    else:
        sql = sql.format(where="WHERE we.category = ?")
        args = (category,)
    with db.connect() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [WishlistRow(**dict(r)) for r in rows]


def wishlist_categories() -> list[dict]:
    """Distinct categories with row counts and total quantities.

    Returns a list of ``{"category": str, "rows": int, "total_qty": int}``
    ordered by category name.
    """
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT category,
                   COUNT(*) AS rows,
                   COALESCE(SUM(qty_wanted), 0) AS total_qty
            FROM wishlist_entries
            GROUP BY category
            ORDER BY category
            """
        ).fetchall()
    return [dict(r) for r in rows]


def wishlist_value(category: str | None = None) -> dict:
    """Total wishlist value, mirroring :func:`lists.list_value` shape.

    Returns ``{"total": float, "rows": int, "missing_price": list[tuple]}``
    where each missing-price tuple is ``(display_name, set_code,
    collector_number, finish)``.
    """
    rows = wishlist_show(category)
    total = 0.0
    missing_price: list[tuple] = []
    for r in rows:
        if r.line_value is None and r.qty_wanted > 0:
            missing_price.append(
                (r.display_name, r.set_code, r.collector_number, r.finish)
            )
        else:
            total += r.line_value or 0.0
    return {"total": total, "rows": len(rows), "missing_price": missing_price}


# ---------- write helpers ----------

def _validate(finish: str, qty: int | None, *, allow_qty_none: bool = False) -> None:
    if finish not in _ALLOWED_FINISHES:
        raise ValueError(
            f"finish must be one of {_ALLOWED_FINISHES}, got {finish!r}"
        )
    if qty is None:
        if not allow_qty_none:
            raise ValueError("qty must be a positive integer")
        return
    if not isinstance(qty, int) or qty <= 0:
        raise ValueError(f"qty must be a positive integer, got {qty!r}")


def _normalize_category(category: str) -> str:
    if category is None or category == "":
        return "default"
    return category


def wishlist_add(
    scryfall_id: str,
    finish: str,
    category: str,
    qty: int,
    *,
    priority: int | None = None,
    notes: str | None = None,
) -> dict:
    """Insert-or-sum a wishlist entry.

    On first INSERT, ``added_at`` is stamped to ``_utcnow_iso()``. Subsequent
    matching rows have their ``qty_wanted`` summed; ``added_at`` is NOT
    updated (the original add-time is preserved). ``priority`` and ``notes``
    on the merge path overwrite only when the caller passes a non-None value.

    Returns ``{"action": "inserted"|"updated", "old_qty": int|None,
    "new_qty": int}``.
    """
    _validate(finish, qty)
    category = _normalize_category(category)

    with db.connect() as conn:
        existing = conn.execute(
            "SELECT qty_wanted, priority, notes FROM wishlist_entries "
            "WHERE scryfall_id = ? AND finish = ? AND category = ?",
            (scryfall_id, finish, category),
        ).fetchone()

        if existing is None:
            now = db._utcnow_iso()
            conn.execute(
                """
                INSERT INTO wishlist_entries
                    (scryfall_id, finish, category, qty_wanted,
                     priority, notes, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (scryfall_id, finish, category, qty, priority, notes, now),
            )
            return {"action": "inserted", "old_qty": None, "new_qty": qty}

        old_qty = existing["qty_wanted"]
        new_qty = old_qty + qty
        new_priority = priority if priority is not None else existing["priority"]
        new_notes = notes if notes is not None else existing["notes"]
        conn.execute(
            """
            UPDATE wishlist_entries
            SET qty_wanted = ?, priority = ?, notes = ?
            WHERE scryfall_id = ? AND finish = ? AND category = ?
            """,
            (new_qty, new_priority, new_notes,
             scryfall_id, finish, category),
        )
        return {"action": "updated", "old_qty": old_qty, "new_qty": new_qty}


def wishlist_remove(
    scryfall_id: str,
    finish: str,
    category: str,
    qty: int | None = None,
) -> dict:
    """Remove (or decrement) a wishlist entry.

    - ``qty=None``: delete the row outright.
    - ``qty>0``: subtract ``qty`` from the existing ``qty_wanted``. If the
      result is <= 0 (would violate the CHECK constraint), the row is
      deleted instead.

    Returns ``{"action": "deleted"|"decremented"|"not_found",
    "old_qty": int|None, "new_qty": int}``. ``new_qty`` is 0 when the row
    was deleted or didn't exist.
    """
    _validate(finish, qty, allow_qty_none=True)
    category = _normalize_category(category)

    with db.connect() as conn:
        existing = conn.execute(
            "SELECT qty_wanted FROM wishlist_entries "
            "WHERE scryfall_id = ? AND finish = ? AND category = ?",
            (scryfall_id, finish, category),
        ).fetchone()

        if existing is None:
            return {"action": "not_found", "old_qty": None, "new_qty": 0}

        old_qty = existing["qty_wanted"]

        if qty is None or old_qty - qty <= 0:
            conn.execute(
                "DELETE FROM wishlist_entries "
                "WHERE scryfall_id = ? AND finish = ? AND category = ?",
                (scryfall_id, finish, category),
            )
            return {"action": "deleted", "old_qty": old_qty, "new_qty": 0}

        new_qty = old_qty - qty
        conn.execute(
            "UPDATE wishlist_entries SET qty_wanted = ? "
            "WHERE scryfall_id = ? AND finish = ? AND category = ?",
            (new_qty, scryfall_id, finish, category),
        )
        return {"action": "decremented", "old_qty": old_qty, "new_qty": new_qty}


def wishlist_set(
    scryfall_id: str,
    finish: str,
    category: str,
    qty: int,
    *,
    priority: int | None = None,
    notes: str | None = None,
) -> dict:
    """Atomic replace: ``qty=0`` deletes, ``qty>0`` upserts.

    Unlike :func:`wishlist_add` (insert-or-sum), this overwrites
    ``qty_wanted`` to exactly ``qty``. Returns the same shape as
    :func:`wishlist_add`: ``{"action": ..., "old_qty": ..., "new_qty": ...}``,
    with ``action`` of ``"deleted"`` when ``qty=0`` clears an existing row,
    ``"not_found"`` when ``qty=0`` and the row didn't exist.
    """
    if not isinstance(qty, int) or qty < 0:
        raise ValueError(f"qty must be a non-negative integer, got {qty!r}")
    if finish not in _ALLOWED_FINISHES:
        raise ValueError(
            f"finish must be one of {_ALLOWED_FINISHES}, got {finish!r}"
        )
    category = _normalize_category(category)

    with db.connect() as conn:
        existing = conn.execute(
            "SELECT qty_wanted, priority, notes, added_at FROM wishlist_entries "
            "WHERE scryfall_id = ? AND finish = ? AND category = ?",
            (scryfall_id, finish, category),
        ).fetchone()

        if qty == 0:
            if existing is None:
                return {"action": "not_found", "old_qty": None, "new_qty": 0}
            conn.execute(
                "DELETE FROM wishlist_entries "
                "WHERE scryfall_id = ? AND finish = ? AND category = ?",
                (scryfall_id, finish, category),
            )
            return {
                "action": "deleted",
                "old_qty": existing["qty_wanted"],
                "new_qty": 0,
            }

        if existing is None:
            now = db._utcnow_iso()
            conn.execute(
                """
                INSERT INTO wishlist_entries
                    (scryfall_id, finish, category, qty_wanted,
                     priority, notes, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (scryfall_id, finish, category, qty, priority, notes, now),
            )
            return {"action": "inserted", "old_qty": None, "new_qty": qty}

        # Upsert path: replace qty_wanted; overwrite priority/notes only when
        # caller provides a non-None value (preserves prior metadata otherwise).
        old_qty = existing["qty_wanted"]
        new_priority = priority if priority is not None else existing["priority"]
        new_notes = notes if notes is not None else existing["notes"]
        conn.execute(
            """
            INSERT INTO wishlist_entries
                (scryfall_id, finish, category, qty_wanted,
                 priority, notes, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scryfall_id, finish, category) DO UPDATE SET
                qty_wanted = ?,
                priority   = ?,
                notes      = ?
            """,
            (scryfall_id, finish, category, qty,
             new_priority, new_notes, existing["added_at"],
             qty, new_priority, new_notes),
        )
        return {"action": "updated", "old_qty": old_qty, "new_qty": qty}

"""Inventory: physical-card ownership CRUD + value math.

This is the V2 replacement for the ``set:*`` / ``owned:*`` label conventions
in :mod:`magic_manager.lists`. The ``inventory`` table holds ONE row per
``(scryfall_id, finish)`` and is the single source of truth for "do I own
this card?". See plan §1.1 for the schema and §2.1 for this module's contract.

Pure CRUD + value math. No CLI, no Typer, no printing — the CLI layer
(Phase 4a) wraps these.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import db


# ---------- row dataclass ----------

@dataclass
class InventoryRow:
    scryfall_id: str
    finish: str  # 'nonfoil' | 'foil'
    quantity: int
    name: str
    flavor_name: str | None
    set_code: str
    collector_number: str
    rarity: str
    prices_usd: float | None
    prices_usd_foil: float | None
    cmc: float | None
    acquired_at: str | None
    notes: str | None

    @property
    def unit_price(self) -> float | None:
        return self.prices_usd_foil if self.finish == "foil" else self.prices_usd

    @property
    def line_value(self) -> float | None:
        p = self.unit_price
        return p * self.quantity if p is not None else None

    @property
    def display_name(self) -> str:
        """Render as ``<flavor_name> / <oracle_name>`` for reskin printings,
        otherwise just the oracle name. Matches the convention used by the
        master-list XLSX writer (sets.py:369) so users see consistent names
        across `mm inventory show`, intake REPL feedback, and inventory
        checklists.
        """
        return f"{self.flavor_name} / {self.name}" if self.flavor_name else self.name


# ---------- read paths ----------

_SELECT_COLUMNS = """
    inv.scryfall_id, inv.finish, inv.quantity,
    c.name, c.flavor_name, c.set_code, c.collector_number, c.rarity,
    c.prices_usd, c.prices_usd_foil, c.cmc,
    inv.acquired_at, inv.notes
"""


def inventory_show() -> list[InventoryRow]:
    """Every row in the inventory table, joined to cards.

    Ordered by ``set_code, collector_number, finish`` for deterministic output.
    """
    with db.connect() as conn:
        rows = conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM inventory inv
            JOIN cards c ON c.scryfall_id = inv.scryfall_id
            ORDER BY c.set_code, c.collector_number, inv.finish
            """
        ).fetchall()
    return [InventoryRow(**dict(r)) for r in rows]


def inventory_value() -> dict:
    """Total inventory value with missing-price diagnostics.

    Returns ``{"total": float, "rows": int, "missing_price": [(display_name,
    set_code, collector_number, finish), ...]}``. Mirrors :func:`lists.list_value`.
    """
    rows = inventory_show()
    total = 0.0
    missing_price: list[tuple] = []
    for r in rows:
        if r.line_value is None and r.quantity > 0:
            # Use display_name so reskin printings show as "<flavor> / <oracle>".
            missing_price.append((r.display_name, r.set_code, r.collector_number, r.finish))
        else:
            total += r.line_value or 0.0
    return {"total": total, "rows": len(rows), "missing_price": missing_price}


def inventory_summary(*, top_n: int = 5) -> dict:
    """Snapshot of the inventory for the readout / collision UX.

    Returns ``{"distinct_rows": N, "total_qty": N, "total_value": float,
    "top_value": [InventoryRow, ...]}`` covering only rows with quantity > 0
    (the inventory table's CHECK already enforces this, but the filter keeps
    the contract stable if that ever loosens).
    """
    rows = [r for r in inventory_show() if r.quantity > 0]
    rows_by_value = sorted(
        rows, key=lambda r: (r.line_value or 0.0), reverse=True,
    )
    return {
        "distinct_rows": len(rows),
        "total_qty": sum(r.quantity for r in rows),
        "total_value": sum((r.line_value or 0.0) for r in rows),
        "top_value": rows_by_value[:top_n],
    }


# ---------- write paths ----------

_VALID_FINISHES = ("nonfoil", "foil")


def _validate_finish(finish: str) -> None:
    if finish not in _VALID_FINISHES:
        raise ValueError(
            f"finish must be one of {_VALID_FINISHES!r}, got {finish!r}"
        )


def _validate_qty_positive(qty: int) -> None:
    if not isinstance(qty, int) or qty <= 0:
        raise ValueError(f"quantity must be a positive integer, got {qty!r}")


def inventory_add(
    scryfall_id: str,
    finish: str,
    qty: int,
    *,
    replace: bool = False,
    notes: str | None = None,
) -> dict:
    """Insert or merge an inventory row.

    Default behavior (``replace=False``) sums the new ``qty`` into any
    existing quantity, mirroring V1 free-form-list semantics. With
    ``replace=True``, the existing quantity is overwritten with ``qty``.

    On first INSERT, ``acquired_at`` is set to the current UTC timestamp
    and is never updated on subsequent merges — it represents when the
    card was first added to the inventory, not the most-recent edit.

    Raises ``ValueError`` for invalid ``finish`` or non-positive ``qty``.

    Returns ``{"action": "inserted"|"updated", "old_qty": int|None,
    "new_qty": int}``.
    """
    _validate_finish(finish)
    _validate_qty_positive(qty)

    with db.connect() as conn:
        existing = conn.execute(
            "SELECT quantity FROM inventory WHERE scryfall_id = ? AND finish = ?",
            (scryfall_id, finish),
        ).fetchone()

        if existing is None:
            now = db._utcnow_iso()
            conn.execute(
                """
                INSERT INTO inventory (scryfall_id, finish, quantity, acquired_at, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (scryfall_id, finish, qty, now, notes),
            )
            return {"action": "inserted", "old_qty": None, "new_qty": qty}

        old_qty = existing["quantity"]
        new_qty = qty if replace else old_qty + qty
        # CHECK quantity > 0 always holds here: replace path requires qty>0
        # (validated above), additive path is old_qty + qty where both are >0.
        if notes is not None:
            conn.execute(
                """
                UPDATE inventory
                SET quantity = ?, notes = ?
                WHERE scryfall_id = ? AND finish = ?
                """,
                (new_qty, notes, scryfall_id, finish),
            )
        else:
            conn.execute(
                """
                UPDATE inventory
                SET quantity = ?
                WHERE scryfall_id = ? AND finish = ?
                """,
                (new_qty, scryfall_id, finish),
            )
        return {"action": "updated", "old_qty": old_qty, "new_qty": new_qty}


def inventory_remove(
    scryfall_id: str,
    finish: str,
    qty: int | None = None,
) -> dict:
    """Remove inventory: full delete (``qty=None``) or decrement.

    - ``qty=None`` deletes the row entirely.
    - ``qty>0`` subtracts from the existing quantity; if the result is
      ``<= 0``, the row is deleted (the CHECK ``quantity > 0`` would
      reject any zero-or-negative UPDATE anyway).

    Returns ``{"action": "deleted"|"decremented"|"not_found", "old_qty":
    int|None, "new_qty": int}``. ``new_qty`` is 0 for delete/not_found.
    """
    _validate_finish(finish)
    if qty is not None:
        _validate_qty_positive(qty)

    with db.connect() as conn:
        existing = conn.execute(
            "SELECT quantity FROM inventory WHERE scryfall_id = ? AND finish = ?",
            (scryfall_id, finish),
        ).fetchone()

        if existing is None:
            return {"action": "not_found", "old_qty": None, "new_qty": 0}

        old_qty = existing["quantity"]

        if qty is None or old_qty - qty <= 0:
            conn.execute(
                "DELETE FROM inventory WHERE scryfall_id = ? AND finish = ?",
                (scryfall_id, finish),
            )
            return {"action": "deleted", "old_qty": old_qty, "new_qty": 0}

        new_qty = old_qty - qty
        conn.execute(
            """
            UPDATE inventory
            SET quantity = ?
            WHERE scryfall_id = ? AND finish = ?
            """,
            (new_qty, scryfall_id, finish),
        )
        return {"action": "decremented", "old_qty": old_qty, "new_qty": new_qty}


def inventory_set(
    scryfall_id: str,
    finish: str,
    qty: int,
    *,
    notes: str | None = None,
) -> dict:
    """Atomic replace: cell-driven set used by ``mm set ingest`` (Phase 4c).

    - ``qty == 0`` deletes the row (matching the XLSX cell-emptied semantic).
    - ``qty > 0`` upserts the row to exactly ``qty``.

    On first INSERT, ``acquired_at`` is stamped; on update, it is preserved
    via ``COALESCE``-equivalent branch logic (we don't touch ``acquired_at``
    on the UPDATE path).

    Raises ``ValueError`` for invalid ``finish`` or negative ``qty``.

    Returns the same dict shape as :func:`inventory_add`. For the delete
    path: ``{"action": "deleted", "old_qty": int|None, "new_qty": 0}``.
    """
    _validate_finish(finish)
    if not isinstance(qty, int) or qty < 0:
        raise ValueError(f"quantity must be a non-negative integer, got {qty!r}")

    with db.connect() as conn:
        existing = conn.execute(
            "SELECT quantity FROM inventory WHERE scryfall_id = ? AND finish = ?",
            (scryfall_id, finish),
        ).fetchone()

        if qty == 0:
            if existing is None:
                return {"action": "not_found", "old_qty": None, "new_qty": 0}
            conn.execute(
                "DELETE FROM inventory WHERE scryfall_id = ? AND finish = ?",
                (scryfall_id, finish),
            )
            return {"action": "deleted", "old_qty": existing["quantity"], "new_qty": 0}

        if existing is None:
            now = db._utcnow_iso()
            conn.execute(
                """
                INSERT INTO inventory (scryfall_id, finish, quantity, acquired_at, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (scryfall_id, finish, qty, now, notes),
            )
            return {"action": "inserted", "old_qty": None, "new_qty": qty}

        old_qty = existing["quantity"]
        if notes is not None:
            conn.execute(
                """
                UPDATE inventory
                SET quantity = ?, notes = ?
                WHERE scryfall_id = ? AND finish = ?
                """,
                (qty, notes, scryfall_id, finish),
            )
        else:
            conn.execute(
                """
                UPDATE inventory
                SET quantity = ?
                WHERE scryfall_id = ? AND finish = ?
                """,
                (qty, scryfall_id, finish),
            )
        return {"action": "updated", "old_qty": old_qty, "new_qty": qty}

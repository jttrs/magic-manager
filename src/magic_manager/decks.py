"""Decks: CRUD over the V4 ``decks`` and ``deck_cards`` tables.

A deck is a composition (a name, format, archetype, notes) plus per-board card
rows. Decks are independent of inventory — owning a card and putting it in a
deck are two separate facts. This module is the read/write layer; CLI wiring
lives in ``cli.py`` and arrives in a later phase.

Mirrors the public shape of ``lists.py`` (``ListRow`` → ``DeckCardRow``) so
existing tooling that consumed ``ListRow`` can transition with minimal churn.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import db, inventory as inv_mod, mtgjson as mtgjson_mod


# Allowed values mirror the V4 CHECK constraints on ``deck_cards``.
_ALLOWED_BOARDS = ("main", "side", "commander", "companion", "maybe")
_ALLOWED_FINISHES = ("nonfoil", "foil", "either")

# Canonical board ordering for ``deck_show``: commanders first, then the
# main 60/100, then companion (sits beside the deck during play), then side,
# then maybe. Stable regardless of insertion order.
_BOARD_ORDER_SQL = (
    "CASE board "
    "WHEN 'commander' THEN 0 "
    "WHEN 'main' THEN 1 "
    "WHEN 'companion' THEN 2 "
    "WHEN 'side' THEN 3 "
    "WHEN 'maybe' THEN 4 "
    "END"
)


# ---------- dataclasses ----------

@dataclass
class Deck:
    deck_id: int
    slug: str
    name: str
    format: str | None
    archetype: str | None
    notes: str | None
    created_at: str
    updated_at: str


@dataclass
class DeckCardRow:
    deck_id: int
    slug: str
    scryfall_id: str
    board: str
    finish: str
    count: int
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
        # finish='either' has no clear foil/nonfoil intent; fall back to the
        # nonfoil price (cheaper, more conservative for valuation).
        if self.finish == "foil":
            return self.prices_usd_foil
        return self.prices_usd

    @property
    def line_value(self) -> float | None:
        p = self.unit_price
        return p * self.count if p is not None else None

    @property
    def display_name(self) -> str:
        """Render as ``<flavor_name> / <oracle_name>`` for reskin printings,
        otherwise just the oracle name. Matches ``ListRow.display_name``.
        """
        return f"{self.flavor_name} / {self.name}" if self.flavor_name else self.name


# ---------- internal helpers ----------

def _validate_board(board: str) -> None:
    if board not in _ALLOWED_BOARDS:
        raise ValueError(
            f"invalid board {board!r}; expected one of {_ALLOWED_BOARDS}"
        )


def _validate_finish(finish: str) -> None:
    if finish not in _ALLOWED_FINISHES:
        raise ValueError(
            f"invalid finish {finish!r}; expected one of {_ALLOWED_FINISHES}"
        )


def _deck_row_to_dataclass(row) -> Deck:
    return Deck(
        deck_id=row["deck_id"],
        slug=row["slug"],
        name=row["name"],
        format=row["format"],
        archetype=row["archetype"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _fetch_deck(conn, slug: str):
    return conn.execute(
        "SELECT deck_id, slug, name, format, archetype, notes, "
        "created_at, updated_at FROM decks WHERE slug = ?",
        (slug,),
    ).fetchone()


def _touch_deck(conn, deck_id: int) -> None:
    """Bump ``updated_at`` on a deck row."""
    conn.execute(
        "UPDATE decks SET updated_at = ? WHERE deck_id = ?",
        (db._utcnow_iso(), deck_id),
    )


# ---------- deck CRUD ----------

def deck_create(
    slug: str,
    name: str,
    *,
    format: str | None = None,
    archetype: str | None = None,
    notes: str | None = None,
) -> Deck:
    """Insert a new deck. Raises ``ValueError`` if ``slug`` is already in use."""
    now = db._utcnow_iso()
    with db.connect() as conn:
        existing = _fetch_deck(conn, slug)
        if existing is not None:
            raise ValueError(f"deck with slug {slug!r} already exists")
        cur = conn.execute(
            """
            INSERT INTO decks (slug, name, format, archetype, notes,
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (slug, name, format, archetype, notes, now, now),
        )
        deck_id = cur.lastrowid
    return Deck(
        deck_id=deck_id,
        slug=slug,
        name=name,
        format=format,
        archetype=archetype,
        notes=notes,
        created_at=now,
        updated_at=now,
    )


def deck_list() -> list[Deck]:
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT deck_id, slug, name, format, archetype, notes,
                   created_at, updated_at
            FROM decks
            ORDER BY slug
            """
        ).fetchall()
    return [_deck_row_to_dataclass(r) for r in rows]


def deck_get(slug: str) -> Deck | None:
    with db.connect() as conn:
        row = _fetch_deck(conn, slug)
    return _deck_row_to_dataclass(row) if row else None


def deck_show(slug: str) -> list[DeckCardRow]:
    """Every card in the deck, all boards, joined to ``cards``.

    Ordering: canonical board order (commander → main → companion → side →
    maybe), then by set_code, collector_number, finish.
    """
    with db.connect() as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        rows = conn.execute(
            f"""
            SELECT dc.deck_id, d.slug, dc.scryfall_id, dc.board, dc.finish,
                   dc.count,
                   c.name, c.flavor_name, c.set_code, c.collector_number,
                   c.rarity, c.prices_usd, c.prices_usd_foil, c.cmc
            FROM deck_cards dc
            JOIN decks d ON d.deck_id = dc.deck_id
            JOIN cards c ON c.scryfall_id = dc.scryfall_id
            WHERE d.slug = ?
            ORDER BY {_BOARD_ORDER_SQL}, c.set_code, c.collector_number, dc.finish
            """,
            (slug,),
        ).fetchall()
    return [DeckCardRow(**dict(r)) for r in rows]


def deck_value(slug: str) -> dict:
    """Total deck value, mirroring ``lists.list_value``.

    Returns ``{"total": float, "rows": int, "missing_price": [(display_name,
    set_code, collector_number, finish), ...]}``.
    """
    rows = deck_show(slug)
    total = 0.0
    missing_price: list[tuple] = []
    for r in rows:
        if r.line_value is None and r.count > 0:
            missing_price.append(
                (r.display_name, r.set_code, r.collector_number, r.finish)
            )
        else:
            total += r.line_value or 0.0
    return {"total": total, "rows": len(rows), "missing_price": missing_price}


def deck_delete(slug: str) -> int:
    """Delete a deck. ON DELETE CASCADE drops its ``deck_cards``."""
    with db.connect() as conn:
        n = conn.execute("DELETE FROM decks WHERE slug = ?", (slug,)).rowcount
    return n


def deck_update(
    slug: str,
    *,
    name: str | None = None,
    format: str | None = None,
    archetype: str | None = None,
    notes: str | None = None,
) -> Deck:
    """Partial update of deck metadata. Only fields explicitly passed (i.e.
    not ``None``) get written. Bumps ``updated_at``. Raises ``LookupError``
    if the slug is unknown.
    """
    updates: list[str] = []
    params: list = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if format is not None:
        updates.append("format = ?")
        params.append(format)
    if archetype is not None:
        updates.append("archetype = ?")
        params.append(archetype)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)

    with db.connect() as conn:
        existing = _fetch_deck(conn, slug)
        if existing is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        # Always touch updated_at — even a no-op update reflects "the user
        # checked in on this deck recently". (Matches the spirit of
        # ``upsert_list`` always bumping its updated_at.)
        updates.append("updated_at = ?")
        params.append(db._utcnow_iso())
        params.append(slug)
        conn.execute(
            f"UPDATE decks SET {', '.join(updates)} WHERE slug = ?",
            params,
        )
        row = _fetch_deck(conn, slug)
    return _deck_row_to_dataclass(row)


# ---------- deck_cards CRUD ----------

def deck_add_card(
    slug: str,
    scryfall_id: str,
    board: str,
    finish: str,
    count: int,
) -> dict:
    """Add ``count`` of a printing to a deck's board+finish slot.

    If a row already exists for ``(deck_id, scryfall_id, board, finish)`` the
    count is summed (insert-or-add semantics). Returns ``{"action":
    "inserted"|"updated", "old_count": int|None, "new_count": int}``.
    """
    _validate_board(board)
    _validate_finish(finish)
    if count <= 0:
        raise ValueError(f"count must be > 0, got {count}")

    with db.connect() as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        deck_id = deck["deck_id"]
        existing = conn.execute(
            """
            SELECT count FROM deck_cards
            WHERE deck_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
            """,
            (deck_id, scryfall_id, board, finish),
        ).fetchone()
        if existing is None:
            old_count = None
            new_count = count
            action = "inserted"
        else:
            old_count = existing["count"]
            new_count = old_count + count
            action = "updated"
        conn.execute(
            """
            INSERT INTO deck_cards (deck_id, scryfall_id, board, finish, count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(deck_id, scryfall_id, board, finish) DO UPDATE SET
                count = ?
            """,
            (deck_id, scryfall_id, board, finish, new_count, new_count),
        )
        _touch_deck(conn, deck_id)

    return {"action": action, "old_count": old_count, "new_count": new_count}


def deck_remove_card(
    slug: str,
    scryfall_id: str,
    board: str,
    finish: str,
    count: int | None = None,
) -> dict:
    """Remove ``count`` from a slot, or delete the row entirely if ``count``
    is ``None`` or the resulting count would be ``<= 0``.

    Returns ``{"action": "deleted"|"decremented"|"not_found", "old_count":
    int|None, "new_count": int}``. ``new_count`` is 0 for deletes/not-found.
    """
    _validate_board(board)
    _validate_finish(finish)
    if count is not None and count <= 0:
        raise ValueError(f"count must be > 0 or None, got {count}")

    with db.connect() as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        deck_id = deck["deck_id"]
        existing = conn.execute(
            """
            SELECT count FROM deck_cards
            WHERE deck_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
            """,
            (deck_id, scryfall_id, board, finish),
        ).fetchone()
        if existing is None:
            return {"action": "not_found", "old_count": None, "new_count": 0}
        old_count = existing["count"]
        if count is None or old_count - count <= 0:
            conn.execute(
                """
                DELETE FROM deck_cards
                WHERE deck_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
                """,
                (deck_id, scryfall_id, board, finish),
            )
            _touch_deck(conn, deck_id)
            return {"action": "deleted", "old_count": old_count, "new_count": 0}
        new_count = old_count - count
        conn.execute(
            """
            UPDATE deck_cards SET count = ?
            WHERE deck_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
            """,
            (new_count, deck_id, scryfall_id, board, finish),
        )
        _touch_deck(conn, deck_id)
    return {"action": "decremented", "old_count": old_count, "new_count": new_count}


def deck_set_card(
    slug: str,
    scryfall_id: str,
    board: str,
    finish: str,
    count: int,
) -> dict:
    """Atomic replace. ``count == 0`` deletes the row; ``count > 0`` upserts.

    Returns ``{"action": "deleted"|"inserted"|"updated"|"not_found",
    "old_count": int|None, "new_count": int}``.
    """
    _validate_board(board)
    _validate_finish(finish)
    if count < 0:
        raise ValueError(f"count must be >= 0, got {count}")

    with db.connect() as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        deck_id = deck["deck_id"]
        existing = conn.execute(
            """
            SELECT count FROM deck_cards
            WHERE deck_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
            """,
            (deck_id, scryfall_id, board, finish),
        ).fetchone()
        old_count = existing["count"] if existing else None

        if count == 0:
            if existing is None:
                return {"action": "not_found", "old_count": None, "new_count": 0}
            conn.execute(
                """
                DELETE FROM deck_cards
                WHERE deck_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
                """,
                (deck_id, scryfall_id, board, finish),
            )
            _touch_deck(conn, deck_id)
            return {"action": "deleted", "old_count": old_count, "new_count": 0}

        action = "updated" if existing else "inserted"
        conn.execute(
            """
            INSERT INTO deck_cards (deck_id, scryfall_id, board, finish, count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(deck_id, scryfall_id, board, finish) DO UPDATE SET
                count = ?
            """,
            (deck_id, scryfall_id, board, finish, count, count),
        )
        _touch_deck(conn, deck_id)
    return {"action": action, "old_count": old_count, "new_count": count}


# ---------- assignment (V5) ----------
#
# Composition lives in ``deck_cards`` (the recipe). Physical fulfillment lives
# in ``deck_assignments`` (which inventory copies currently stand in for the
# recipe). These are two independent facts: a deck can have a recipe and no
# assignments (composition exists but the cards are loose), full assignments
# (physically built), or partial (some cards on hand, some still to acquire).
#
# Invariant enforced by every write path here: for each (scryfall_id, finish),
# SUM(deck_assignments.count) <= inventory.quantity. SQLite CHECK can't span
# tables, so the write paths enforce it in Python inside the transaction and
# raise ``AssignmentOverflow`` (which triggers ``db.connect``'s rollback).


class AssignmentOverflow(ValueError):
    """Raised when an assignment would exceed a per-printing bound.

    Two bounds are enforced:
      1. Inventory: SUM(assignments across finishes) <= inventory.quantity
         at that finish (checked per (sid, finish)).
      2. Recipe: SUM(assignments across finishes for a printing on a deck)
         <= SUM(deck_cards.count across boards+finishes for that printing).

    ``rows`` contains ``{scryfall_id, finish, need, free, kind}`` where
    ``kind`` is ``"inventory"`` or ``"recipe"``.
    """

    def __init__(self, rows: list[dict]):
        self.rows = rows
        pairs = ", ".join(
            f"[{r.get('kind','inventory')}] {r['scryfall_id']}/{r['finish']}: "
            f"need {r['need']}, free {r['free']}"
            for r in rows[:5]
        )
        more = f" (+{len(rows) - 5} more)" if len(rows) > 5 else ""
        super().__init__(f"assignment overflow — {pairs}{more}")


def deck_assign_batch(
    slug: str,
    rows: list[tuple[str, str, int]],
    *,
    allow_shortfall: bool = False,
) -> dict:
    """Assign multiple ``(scryfall_id, finish, qty)`` rows to a deck at once.

    All rows apply in a single transaction. Before writing, checks that
    ``free_quantity(sid, finish) >= qty`` for every row; if any row would
    overflow, raises :class:`AssignmentOverflow` and no rows are written
    (unless ``allow_shortfall=True``, in which case shortfall rows are
    silently skipped and the rest write).

    Returns ``{"assigned_rows": int, "assigned_qty": int, "shortfalls":
    [{scryfall_id, finish, need, free}, ...]}``.
    """
    from .inventory import free_quantity

    # Coalesce duplicate (sid, finish) inputs so overflow accounting is per-pair.
    deltas: dict[tuple[str, str], int] = {}
    for sid, finish, qty in rows:
        _validate_finish(finish)
        if finish == "either":
            raise ValueError(
                "deck_assignments.finish must be 'nonfoil' or 'foil'; "
                "collapse 'either' upstream before assigning."
            )
        if qty <= 0:
            raise ValueError(f"assign qty must be > 0, got {qty} for {sid!r}")
        deltas[(sid, finish)] = deltas.get((sid, finish), 0) + qty

    with db.connect() as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        deck_id = deck["deck_id"]

        # Recipe cap: an assignment for a printing can't exceed what the
        # deck's recipe (deck_cards, summed across all boards+finishes for
        # that scryfall_id) calls for, minus what's already assigned to this
        # deck for the same printing. This catches "compose the same deck
        # twice" — inventory might still have free copies, but the recipe
        # already has as many pledged as it wants.
        recipe_caps: dict[str, int] = {}
        for r in conn.execute(
            "SELECT scryfall_id, SUM(count) AS total FROM deck_cards "
            "WHERE deck_id = ? GROUP BY scryfall_id",
            (deck_id,),
        ).fetchall():
            recipe_caps[r["scryfall_id"]] = r["total"]

        already_assigned: dict[str, int] = {}
        for r in conn.execute(
            "SELECT scryfall_id, SUM(count) AS total FROM deck_assignments "
            "WHERE deck_id = ? GROUP BY scryfall_id",
            (deck_id,),
        ).fetchall():
            already_assigned[r["scryfall_id"]] = r["total"]

        # Sum requested deltas per printing (finish-agnostic for the cap).
        per_printing_delta: dict[str, int] = {}
        for (sid, _finish), qty in deltas.items():
            per_printing_delta[sid] = per_printing_delta.get(sid, 0) + qty

        shortfalls: list[dict] = []
        recipe_blocked: set[str] = set()
        for sid, delta in per_printing_delta.items():
            cap = recipe_caps.get(sid, 0)
            have = already_assigned.get(sid, 0)
            headroom = cap - have
            if delta > headroom:
                shortfalls.append({
                    "scryfall_id": sid,
                    "finish": "*",
                    "need": delta,
                    "free": max(0, headroom),
                    "kind": "recipe",
                })
                recipe_blocked.add(sid)

        writable: list[tuple[str, str, int]] = []
        for (sid, finish), need in deltas.items():
            if sid in recipe_blocked:
                continue
            free = free_quantity(sid, finish, conn=conn)
            if need > free:
                shortfalls.append({
                    "scryfall_id": sid,
                    "finish": finish,
                    "need": need,
                    "free": free,
                    "kind": "inventory",
                })
            else:
                writable.append((sid, finish, need))

        if shortfalls and not allow_shortfall:
            raise AssignmentOverflow(shortfalls)

        now = db._utcnow_iso()
        assigned_rows = assigned_qty = 0
        for sid, finish, qty in writable:
            conn.execute(
                """
                INSERT INTO deck_assignments (deck_id, scryfall_id, finish, count, assigned_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(deck_id, scryfall_id, finish) DO UPDATE SET
                    count = count + excluded.count
                """,
                (deck_id, sid, finish, qty, now),
            )
            assigned_rows += 1
            assigned_qty += qty
        if assigned_rows:
            _touch_deck(conn, deck_id)
            db.record_ingest_log(
                conn,
                label=f"deck-assigned:{slug}",
                mode="additive",
                source_path=f"deck:{slug}",
                archived_path=None,
                file_sha256=_assignment_hash(writable),
                rows_added=assigned_rows,
                rows_updated=0,
                rows_zeroed=0,
                status="success",
            )

    return {
        "assigned_rows": assigned_rows,
        "assigned_qty": assigned_qty,
        "shortfalls": shortfalls,
    }


def deck_unassign_batch(
    slug: str,
    rows: list[tuple[str, str, int]] | str,
) -> dict:
    """Unassign rows from a deck. Pass ``'all'`` to strip every assignment.

    With an explicit row list, each ``(sid, finish, qty)`` decrements the
    matching ``deck_assignments`` row; qty>=stored deletes the row. Missing
    rows are counted as ``not_found`` and reported.

    Returns ``{"unassigned_rows": int, "unassigned_qty": int, "not_found":
    [(sid, finish), ...]}``.
    """
    with db.connect() as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        deck_id = deck["deck_id"]

        unassigned_rows = unassigned_qty = 0
        not_found: list[tuple[str, str]] = []

        if rows == "all":
            summed = conn.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(count), 0) AS q "
                "FROM deck_assignments WHERE deck_id = ?",
                (deck_id,),
            ).fetchone()
            unassigned_rows = summed["n"]
            unassigned_qty = summed["q"]
            conn.execute("DELETE FROM deck_assignments WHERE deck_id = ?", (deck_id,))
        else:
            assert isinstance(rows, list)
            for sid, finish, qty in rows:
                _validate_finish(finish)
                if finish == "either":
                    raise ValueError("unassign finish cannot be 'either'")
                if qty <= 0:
                    raise ValueError(f"unassign qty must be > 0, got {qty}")
                existing = conn.execute(
                    "SELECT count FROM deck_assignments "
                    "WHERE deck_id = ? AND scryfall_id = ? AND finish = ?",
                    (deck_id, sid, finish),
                ).fetchone()
                if existing is None:
                    not_found.append((sid, finish))
                    continue
                old = existing["count"]
                if qty >= old:
                    conn.execute(
                        "DELETE FROM deck_assignments "
                        "WHERE deck_id = ? AND scryfall_id = ? AND finish = ?",
                        (deck_id, sid, finish),
                    )
                    unassigned_rows += 1
                    unassigned_qty += old
                else:
                    conn.execute(
                        "UPDATE deck_assignments SET count = count - ? "
                        "WHERE deck_id = ? AND scryfall_id = ? AND finish = ?",
                        (qty, deck_id, sid, finish),
                    )
                    unassigned_qty += qty
                    unassigned_rows += 1

        if unassigned_rows:
            _touch_deck(conn, deck_id)
            db.record_ingest_log(
                conn,
                label=f"deck-unassigned:{slug}",
                mode="additive",
                source_path=f"deck:{slug}",
                archived_path=None,
                file_sha256=_assignment_hash(
                    [] if rows == "all" else rows  # type: ignore[arg-type]
                ),
                rows_added=0,
                rows_updated=unassigned_rows,
                rows_zeroed=0,
                status="success",
            )

    return {
        "unassigned_rows": unassigned_rows,
        "unassigned_qty": unassigned_qty,
        "not_found": not_found,
    }


def deck_assignments_list(slug: str) -> list[DeckCardRow]:
    """Every assignment row for a deck, joined to ``cards``.

    Returns the same ``DeckCardRow`` shape as :func:`deck_show` for uniform
    downstream consumption, with ``board`` fixed to ``'main'`` (assignments
    don't record per-board intent — the recipe's board is separate).
    """
    with db.connect() as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        rows = conn.execute(
            """
            SELECT da.deck_id, d.slug, da.scryfall_id,
                   'main' AS board, da.finish, da.count AS count,
                   c.name, c.flavor_name, c.set_code, c.collector_number,
                   c.rarity, c.prices_usd, c.prices_usd_foil, c.cmc
            FROM deck_assignments da
            JOIN decks d ON d.deck_id = da.deck_id
            JOIN cards c ON c.scryfall_id = da.scryfall_id
            WHERE d.slug = ?
            ORDER BY c.set_code, c.collector_number, da.finish
            """,
            (slug,),
        ).fetchall()
    return [DeckCardRow(**dict(r)) for r in rows]


def deck_compose_plan(slug: str, *, foil_first: bool = False) -> dict:
    """Preview what a full-composition assign would do without writing.

    Reads the recipe from ``deck_cards``, picks a concrete finish for every
    ``'either'`` slot (nonfoil-first by default; ``foil_first=True`` inverts
    that), aggregates by ``(scryfall_id, finish)``, and reports current free
    inventory. Callers use this both for dry-run display and as the input to
    :func:`deck_assign_batch`.

    Returns ``{"rows": [{scryfall_id, finish, need, free}, ...], "shortfalls":
    [same shape], "either_choices": [{scryfall_id, chose_finish, reason}]}``.
    """
    from .inventory import free_quantity

    recipe = deck_show(slug)  # already validates the slug

    # Collapse recipe rows into per-(sid, finish) needs, resolving 'either'.
    needs: dict[tuple[str, str], int] = {}
    either_choices: list[dict] = []
    with db.connect() as conn:
        for r in recipe:
            if r.finish in ("nonfoil", "foil"):
                needs[(r.scryfall_id, r.finish)] = (
                    needs.get((r.scryfall_id, r.finish), 0) + r.count
                )
                continue
            # 'either': prefer the requested primary, fall back to the other.
            primary = "foil" if foil_first else "nonfoil"
            secondary = "nonfoil" if foil_first else "foil"
            free_primary = free_quantity(r.scryfall_id, primary, conn=conn)
            already_needed_primary = needs.get((r.scryfall_id, primary), 0)
            if free_primary - already_needed_primary >= r.count:
                chose = primary
                reason = "primary"
            else:
                chose = secondary
                reason = "primary-short-fallback"
            needs[(r.scryfall_id, chose)] = needs.get((r.scryfall_id, chose), 0) + r.count
            either_choices.append({
                "scryfall_id": r.scryfall_id,
                "chose_finish": chose,
                "reason": reason,
            })

        rows_out: list[dict] = []
        shortfalls: list[dict] = []
        for (sid, finish), need in needs.items():
            free = free_quantity(sid, finish, conn=conn)
            entry = {"scryfall_id": sid, "finish": finish, "need": need, "free": free}
            rows_out.append(entry)
            if need > free:
                shortfalls.append(entry)

    return {
        "rows": rows_out,
        "shortfalls": shortfalls,
        "either_choices": either_choices,
    }


def deck_assign_from_composition(
    slug: str,
    *,
    foil_first: bool = False,
    allow_shortfall: bool = False,
) -> dict:
    """Assign the entire recipe of ``slug`` to the deck in one shot.

    Uses :func:`deck_compose_plan` to resolve ``'either'`` slots and then
    delegates to :func:`deck_assign_batch`. Returns the batch result plus
    the ``either_choices`` list so callers can surface the resolution.
    """
    plan = deck_compose_plan(slug, foil_first=foil_first)
    rows = [(r["scryfall_id"], r["finish"], r["need"]) for r in plan["rows"]]
    result = deck_assign_batch(slug, rows, allow_shortfall=allow_shortfall)
    result["either_choices"] = plan["either_choices"]
    return result


def _assignment_hash(rows: list[tuple[str, str, int]]) -> str:
    """Stable SHA-256 of the sorted (sid, finish, qty) tuples.

    Populates ``ingest_log.file_sha256`` for assignment ops so the existing
    ``ingest_log_hash_idx`` can dedupe repeated identical runs during audits.
    Not currently used as a hard idempotence guard — the overflow check is
    the real protection against double-assigning.
    """
    import hashlib
    h = hashlib.sha256()
    for sid, finish, qty in sorted(rows):
        h.update(f"{sid}\x1f{finish}\x1f{qty}\x1e".encode("utf-8"))
    return h.hexdigest()


# ---------- precon / pack import ----------

# MTGJSON deck JSON has these board keys; map to our V4 ``deck_cards.board``.
_BOARD_KEY_TO_NAME = (
    ("commander", "commander"),
    ("mainBoard", "main"),
    ("sideBoard", "side"),
)


def _slug(s: str) -> str:
    raw = "".join(c if c.isalnum() else "-" for c in s.lower())
    while "--" in raw:
        raw = raw.replace("--", "-")
    return raw.strip("-")


def import_precon(
    file_name: str,
    *,
    slug: str | None = None,
    name: str | None = None,
    format: str | None = None,
    copies: int = 1,
    add_inventory: bool = True,
    deconstruct: bool = False,
    merge_inventory: bool = False,
) -> dict:
    """Import an MTGJSON precon (or Jumpstart pack — same shape) into the DB.

    V5 semantics: creates exactly ONE deck composition regardless of ``copies``.
    ``copies=N`` still multiplies the per-card inventory addition by N (so
    "I opened 3 copies of this precon" adds 3× each card to inventory). Under
    the pre-V5 model this created ``-2``, ``-3`` slug clones; that was the
    design bug the deck_assignments / recipe split fixes. If the caller
    genuinely wants N distinct compositions (rare — e.g. two variants of the
    same precon list), they run ``import-precon`` N times with distinct
    ``--slug`` overrides.

    ``merge_inventory=True`` skips deck creation entirely and only adds
    inventory. Use when the composition already exists (imported earlier)
    and you're now pouring in extra physical copies.

    Returns a summary dict with these fields:
      - ``deck_name``       (str) display name used
      - ``effective_slugs`` (list[str]) deck slugs created (0 or 1 entry;
                            empty under deconstruct or merge_inventory)
      - ``deck_added``      (int) deck_cards rows inserted
      - ``deck_updated``    (int) deck_cards rows updated
      - ``deck_card_qty``   (int) total card-qty written across deck_cards
      - ``inv_added``       (int) inventory rows inserted
      - ``inv_updated``     (int) inventory rows updated
      - ``inv_qty_total``   (int) total card-qty added to inventory
      - ``inv_distinct``    (int) distinct (printing, finish) pairs touched
      - ``copies``          (int) copies parameter (preserved for caller)
      - ``missing_sids``    (list[dict]) entries with no scryfallId, skipped

    Raises:
      - ``mtgjson_mod.MtgJsonError`` if the deck JSON cannot be fetched
      - ``ValueError`` if the slug cannot be derived or the slug conflicts
    """
    deck_data = mtgjson_mod.deck(file_name)

    deck_name = name or deck_data.get("name") or file_name
    base_slug = slug or _slug(deck_name)
    if not base_slug:
        raise ValueError(
            f"could not derive slug from name {deck_name!r}; pass slug= explicitly"
        )

    # V5: one composition per import, regardless of copies. Callers who
    # genuinely want a second composition run import-precon a second time
    # with --slug <other>.
    effective_slugs: list[str] = []
    if not deconstruct and not merge_inventory:
        if deck_get(base_slug) is not None:
            raise ValueError(
                f"deck slug {base_slug!r} already exists; pass --slug to name a "
                f"variant, --merge-inventory to skip the deck insert and add "
                f"only inventory, or delete the existing deck first."
            )
        effective_slugs.append(base_slug)
    elif merge_inventory:
        if deck_get(base_slug) is None:
            raise ValueError(
                f"--merge-inventory requires an existing deck at slug "
                f"{base_slug!r}; use plain `import-precon` to create one."
            )

    # Create deck rows (skipped under deconstruct or merge_inventory).
    fmt = format
    if fmt is None:
        fmt = "commander" if deck_data.get("type", "").lower().startswith("commander") else None
    for s in effective_slugs:
        deck_create(s, deck_name, format=fmt)

    # Walk boards: write deck_cards for the single composition, accumulate
    # inventory aggregates scaled by ``copies``.
    deck_added = deck_updated = 0
    deck_card_qty = 0
    inv_aggregate: dict[tuple[str, str], int] = {}
    missing_sids: list[dict] = []
    for mj_key, board_name in _BOARD_KEY_TO_NAME:
        for entry in deck_data.get(mj_key, []) or []:
            sid = (entry.get("identifiers") or {}).get("scryfallId")
            if not sid:
                missing_sids.append({
                    "name": entry.get("name"),
                    "set": entry.get("setCode"),
                    "cn": entry.get("number"),
                    "board": board_name,
                })
                continue
            count = int(entry.get("count", 1) or 1)
            finish = "foil" if entry.get("isFoil") else "nonfoil"
            for s in effective_slugs:
                r = deck_add_card(s, sid, board_name, finish, count)
                deck_card_qty += count
                if r["action"] == "inserted":
                    deck_added += 1
                else:
                    deck_updated += 1
            inv_aggregate[(sid, finish)] = inv_aggregate.get((sid, finish), 0) + count * copies

    inv_added = inv_updated = 0
    inv_qty_total = 0
    if add_inventory:
        for (sid, finish), qty in inv_aggregate.items():
            r = inv_mod.inventory_add(sid, finish, qty)
            inv_qty_total += qty
            if r["action"] == "inserted":
                inv_added += 1
            else:
                inv_updated += 1

    return {
        "deck_name": deck_name,
        "effective_slugs": effective_slugs,
        "deck_added": deck_added,
        "deck_updated": deck_updated,
        "deck_card_qty": deck_card_qty,
        "inv_added": inv_added,
        "inv_updated": inv_updated,
        "inv_qty_total": inv_qty_total,
        "inv_distinct": len(inv_aggregate),
        "copies": copies,
        "missing_sids": missing_sids,
    }

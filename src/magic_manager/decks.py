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

from . import db


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

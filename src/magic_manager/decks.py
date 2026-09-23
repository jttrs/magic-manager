"""Decks: CRUD over the V4 ``decks`` and ``deck_cards`` tables.

A deck is a composition (a name, format, archetype, notes) plus per-board card
rows. Decks are independent of inventory — owning a card and putting it in a
deck are two separate facts. This module is the read/write layer; CLI wiring
lives in ``cli.py`` and arrives in a later phase.

Mirrors the public shape of ``lists.py`` (``ListRow`` → ``DeckCardRow``) so
existing tooling that consumed ``ListRow`` can transition with minimal churn.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from . import db, ingest as ingest_mod, inventory as inv_mod, mtgjson as mtgjson_mod


# Allowed values mirror the V4 CHECK constraints on ``deck_cards``.
_ALLOWED_BOARDS = ("main", "side", "commander", "companion", "maybe", "token")
_ALLOWED_FINISHES = ("nonfoil", "foil", "either")

# V11 precon states (see the Deck dataclass). 'built' = assembled deck (pledged),
# 'deconstructed' = torn-down deck (loose).
_PRECON_STATES = ("built", "deconstructed")

# V17 composition-lifecycle statuses (per deck VERSION, not the deck). 'brew' =
# in-progress list; 'tuned' = locked-in (finalized, legality/bracket recorded).
# Mirrors the deck_versions.status CHECK constraint.
_VERSION_STATUSES = ("brew", "tuned")

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
    "WHEN 'token' THEN 5 "
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
    # V10/V11: precon provenance. source_precon_file_name is the MTGJSON deck
    # fileName this deck was imported from (NULL for hand-built decks); it's
    # the join key that makes precon unit counts derivable. precon_state is one
    # of 'built' (assembled deck, cards pledged) or 'deconstructed' (a deck torn
    # down for parts — recipe kept, cards loose).
    source_precon_file_name: str | None = None
    precon_state: str = "built"
    # V17: pointer to the deck's CURRENT version (deck_versions.deck_version_id).
    # Every deck_cards read resolves composition through this. NULL only in the
    # (invalid) window before a deck's first version exists.
    current_version_id: int | None = None


@dataclass
class DeckVersion:
    """One SCD-2 version of a deck's composition (a ``deck_versions`` row).

    A deck's card composition (``deck_cards``) hangs off ``deck_version_id``,
    so each version is an immutable snapshot. ``status`` is the composition-
    lifecycle label (``brew`` → ``tuned``); ``is_current`` + ``effective_from``
    / ``effective_to`` are the SCD-2 dating (exactly one current version per
    deck, its ``effective_to`` NULL). ``legality_report`` / ``bracket_detail``
    are JSON blobs written when the version is finalized (NULL until then);
    ``suggested_bracket`` is duplicated out of ``bracket_detail`` as an INTEGER
    column for cheap listing/querying.
    """

    deck_version_id: int
    deck_id: int
    version_number: int
    status: str
    is_current: int
    effective_from: str
    effective_to: str | None
    change_reason: str | None
    legality_report: str | None
    suggested_bracket: int | None
    bracket_detail: str | None
    created_at: str


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
    keys = row.keys()
    return Deck(
        deck_id=row["deck_id"],
        slug=row["slug"],
        name=row["name"],
        format=row["format"],
        archetype=row["archetype"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        # These columns exist from V10/V11 on; guard for rows selected without them.
        source_precon_file_name=(row["source_precon_file_name"]
                                 if "source_precon_file_name" in keys else None),
        precon_state=(row["precon_state"] if "precon_state" in keys else "built"),
        current_version_id=(row["current_version_id"]
                            if "current_version_id" in keys else None),
    )


def _fetch_deck(conn, slug: str):
    return conn.execute(
        "SELECT deck_id, slug, name, format, archetype, notes, "
        "created_at, updated_at, source_precon_file_name, precon_state, "
        "current_version_id "
        "FROM decks WHERE slug = ?",
        (slug,),
    ).fetchone()


def _version_row_to_dataclass(row) -> DeckVersion:
    return DeckVersion(
        deck_version_id=row["deck_version_id"],
        deck_id=row["deck_id"],
        version_number=row["version_number"],
        status=row["status"],
        is_current=row["is_current"],
        effective_from=row["effective_from"],
        effective_to=row["effective_to"],
        change_reason=row["change_reason"],
        legality_report=row["legality_report"],
        suggested_bracket=row["suggested_bracket"],
        bracket_detail=row["bracket_detail"],
        created_at=row["created_at"],
    )


# ---------- current-version resolution (V17/V18) ----------
#
# Composition is version-scoped: deck_cards hangs off deck_version_id. Every
# read path resolves "the deck's cards" through decks.current_version_id (a fast
# indexed pointer to the one current deck_versions row). These helpers DRY that
# hop so no consumer hand-writes the join.


def _current_version_id(conn, deck_id: int) -> int:
    """The deck's current ``deck_version_id`` via the ``current_version_id``
    pointer. Raises ``LookupError`` if the deck has no current version (an
    invariant violation — every deck gets a v1 at creation / V17 backfill)."""
    row = conn.execute(
        "SELECT current_version_id FROM decks WHERE deck_id = ?", (deck_id,)
    ).fetchone()
    if row is None:
        raise LookupError(f"no deck with deck_id {deck_id}")
    if row["current_version_id"] is None:
        raise LookupError(f"deck {deck_id} has no current version")
    return row["current_version_id"]


def _current_version_id_for_slug(conn, slug: str) -> tuple[int, int]:
    """``(deck_id, current_version_id)`` for a slug in one hop. Raises
    ``LookupError`` if the slug is unknown or has no current version."""
    row = conn.execute(
        "SELECT deck_id, current_version_id FROM decks WHERE slug = ?", (slug,)
    ).fetchone()
    if row is None:
        raise LookupError(f"deck with slug {slug!r} not found")
    if row["current_version_id"] is None:
        raise LookupError(f"deck {slug!r} has no current version")
    return row["deck_id"], row["current_version_id"]


def _touch_deck(conn, deck_id: int) -> None:
    """Bump ``updated_at`` on a deck row."""
    conn.execute(
        "UPDATE decks SET updated_at = ? WHERE deck_id = ?",
        (db._utcnow_iso(), deck_id),
    )


def _insert_version(
    conn,
    deck_id: int,
    *,
    version_number: int,
    status: str,
    change_reason: str | None,
    now: str,
) -> int:
    """Insert a ``deck_versions`` row, clear any prior current flag for the
    deck (cutting its ``effective_to``), mark the new row current, and repoint
    ``decks.current_version_id``. Returns the new ``deck_version_id``.

    The single place the "exactly one current version per deck" invariant is
    maintained — used by both :func:`deck_create` (v1) and :func:`create_version`.
    """
    if status not in _VERSION_STATUSES:
        raise ValueError(f"invalid status {status!r}; expected one of {_VERSION_STATUSES}")
    # Retire the previous current version (if any).
    conn.execute(
        "UPDATE deck_versions SET is_current = 0, effective_to = ? "
        "WHERE deck_id = ? AND is_current = 1",
        (now, deck_id),
    )
    cur = conn.execute(
        "INSERT INTO deck_versions "
        "(deck_id, version_number, status, is_current, effective_from, "
        " effective_to, change_reason, created_at) "
        "VALUES (?, ?, ?, 1, ?, NULL, ?, ?)",
        (deck_id, version_number, status, now, change_reason, now),
    )
    version_id = cur.lastrowid
    conn.execute(
        "UPDATE decks SET current_version_id = ? WHERE deck_id = ?",
        (version_id, deck_id),
    )
    return version_id


# ---------- deck CRUD ----------

def deck_create(
    slug: str,
    name: str,
    *,
    format: str | None = None,
    archetype: str | None = None,
    notes: str | None = None,
    source_set_code: str | None = None,
    source_precon_file_name: str | None = None,
    precon_state: str = "built",
    status: str = "brew",
    conn=None,
) -> Deck:
    """Insert a new deck. Raises ``ValueError`` if ``slug`` is already in use.

    Pass ``conn`` to enlist in a caller's open transaction (e.g. ``import_precon``
    creating the deck + its cards atomically); omit it for a standalone insert.

    ``source_set_code`` is the set the deck came from (e.g. 'ncc' for a New
    Capenna Commander precon) — the hard link used by family-scoped queries.
    NULL for hand-created decks.

    ``source_precon_file_name`` (V10) is the MTGJSON deck fileName the deck was
    imported from — the join key that makes precon unit counts derivable.
    ``precon_state`` (V11) is one of ``built`` / ``deconstructed`` (see the
    ``Deck`` dataclass).

    ``status`` (V17) seeds the deck's initial (v1) composition-lifecycle state
    (``brew``/``tuned``). Every new deck gets exactly one ``deck_versions`` row
    here, and ``decks.current_version_id`` is pointed at it, so the deck has a
    resolvable current version from creation on.
    """
    if precon_state not in _PRECON_STATES:
        raise ValueError(f"invalid precon_state {precon_state!r}; expected one of {_PRECON_STATES}")
    if status not in _VERSION_STATUSES:
        raise ValueError(f"invalid status {status!r}; expected one of {_VERSION_STATUSES}")
    now = db._utcnow_iso()
    with db.transaction(conn) as conn:
        existing = _fetch_deck(conn, slug)
        if existing is not None:
            raise ValueError(f"deck with slug {slug!r} already exists")
        cur = conn.execute(
            """
            INSERT INTO decks (slug, name, format, archetype, notes,
                               source_set_code, source_precon_file_name,
                               precon_state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (slug, name, format, archetype, notes,
             (source_set_code or None), (source_precon_file_name or None),
             precon_state, now, now),
        )
        deck_id = cur.lastrowid
        # V17: every deck has a v1 version from birth; point the deck at it.
        version_id = _insert_version(
            conn, deck_id, version_number=1, status=status,
            change_reason="initial version", now=now,
        )
    return Deck(
        deck_id=deck_id,
        slug=slug,
        name=name,
        format=format,
        archetype=archetype,
        notes=notes,
        created_at=now,
        updated_at=now,
        source_precon_file_name=(source_precon_file_name or None),
        precon_state=precon_state,
        current_version_id=version_id,
    )


def deck_list() -> list[Deck]:
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT deck_id, slug, name, format, archetype, notes,
                   created_at, updated_at, source_precon_file_name, precon_state,
                   current_version_id
            FROM decks
            ORDER BY slug
            """
        ).fetchall()
    return [_deck_row_to_dataclass(r) for r in rows]


def deck_get(slug: str, *, conn=None) -> Deck | None:
    with db.transaction(conn) as conn:
        row = _fetch_deck(conn, slug)
    return _deck_row_to_dataclass(row) if row else None


def deck_show(
    slug: str,
    *,
    exclude_boards: tuple[str, ...] = (),
    version_id: int | None = None,
) -> list[DeckCardRow]:
    """Every card in one version of the deck, joined to ``cards``.

    Ordering: canonical board order (commander → main → companion → side →
    maybe → token), then by set_code, collector_number, finish.

    ``exclude_boards`` drops rows on the named boards. Callers that treat the
    deck as its PLAYABLE recipe (compose/pledge, value, the ``deck:`` selector
    feeding exports) pass ``("token",)`` so token/emblem rows — which ride the
    deck for record-keeping but aren't pledged, bought, or exported as deck
    cards — don't leak in. ``deck show`` itself passes nothing (shows all boards).

    ``version_id`` (V18) selects a specific ``deck_versions`` snapshot; the
    default (``None``) resolves the deck's CURRENT version via
    ``decks.current_version_id``. Composition is version-scoped, so ``deck_cards``
    is joined on ``deck_version_id``.
    """
    board_filter = ""
    extra_params: list = []
    if exclude_boards:
        placeholders = ",".join("?" for _ in exclude_boards)
        board_filter = f" AND dc.board NOT IN ({placeholders})"
        extra_params.extend(exclude_boards)
    with db.connect() as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        vid = version_id if version_id is not None else deck["current_version_id"]
        if vid is None:
            return []  # deck with no current version (invalid state) → empty
        rows = conn.execute(
            f"""
            SELECT ? AS deck_id, ? AS slug, dc.scryfall_id, dc.board, dc.finish,
                   dc.count,
                   c.name, c.flavor_name, c.set_code, c.collector_number,
                   c.rarity, c.prices_usd, c.prices_usd_foil, c.cmc
            FROM deck_cards dc
            JOIN cards c ON c.scryfall_id = dc.scryfall_id
            WHERE dc.deck_version_id = ?{board_filter}
            ORDER BY {_BOARD_ORDER_SQL}, c.set_code, c.collector_number, dc.finish
            """,
            [deck["deck_id"], slug, vid, *extra_params],
        ).fetchall()
    return [DeckCardRow(**dict(r)) for r in rows]


def deck_value(slug: str) -> dict:
    """Total deck value, mirroring ``lists.list_value``.

    Returns ``{"total": float, "rows": int, "missing_price": [(display_name,
    set_code, collector_number, finish), ...]}``.

    Token/emblem boards are EXCLUDED — a deck's $ reflects its playable cards,
    not the tokens that ride along (which are usually $0 and not what a
    collector values the deck by).
    """
    rows = deck_show(slug, exclude_boards=("token",))
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


def backfill_source_set_codes(*, conn=None) -> int:
    """Set ``source_set_code`` for decks where it's NULL, from the deck's
    dominant card set (the modal ``cards.set_code`` across its ``deck_cards``,
    count-weighted). Idempotent: only touches NULL rows; re-running is a no-op
    once every deck is linked. Returns the number of decks updated.

    Existing precon decks (imported before the V6 hard link) get their family
    tie this way; hand-created decks with no cards stay NULL. New imports set
    the column at creation time via ``import_precon`` and never reach here.
    """
    with db.transaction(conn) as conn:
        null_decks = conn.execute(
            "SELECT deck_id FROM decks WHERE source_set_code IS NULL"
        ).fetchall()
        updated = 0
        for row in null_decks:
            deck_id = row["deck_id"]
            # Composition is version-scoped (V18): weigh the deck's CURRENT
            # version's cards. A deck with no current version contributes nothing.
            modal = conn.execute(
                """
                SELECT LOWER(c.set_code) AS sc, SUM(dc.count) AS n
                FROM deck_cards dc
                JOIN decks d ON d.current_version_id = dc.deck_version_id
                JOIN cards c ON c.scryfall_id = dc.scryfall_id
                WHERE d.deck_id = ?
                GROUP BY LOWER(c.set_code)
                ORDER BY n DESC, sc ASC
                LIMIT 1
                """,
                (deck_id,),
            ).fetchone()
            if modal and modal["sc"]:
                conn.execute(
                    "UPDATE decks SET source_set_code = ? WHERE deck_id = ?",
                    (modal["sc"], deck_id),
                )
                updated += 1
    return updated


def backfill_token_board(*, conn=None) -> int:
    """Move token cards mis-filed on the ``'main'`` board to ``'token'``.

    One-off repair for precon decks imported BEFORE the V14 ``'token'`` board
    existed (their MTGJSON ``tokens`` cards were manually added to ``'main'``).
    Moves only rows whose printing is a token (``cards.is_token = 1``) from
    ``main`` → ``token``. Idempotent: once moved, a re-run finds nothing on
    ``main`` that is a token and is a no-op. Inventory is untouched (the tokens
    are already there). Returns the number of deck_cards rows moved.

    Guarded against a PK collision (a token already present on BOTH boards for
    the same deck/finish): such rows are left on ``main`` and reported to stderr
    rather than crashing the UPDATE.

    SCHEMA-ADAPTIVE: ``deck_cards`` was version-scoped in V18 (its ``deck_id``
    column became ``deck_version_id``). This runs both as a post-migration repair
    (new shape) AND from the V15 migration hook — which fires BEFORE V18 applies,
    when the table still carries ``deck_id``. We detect the key column via
    ``PRAGMA table_info`` and operate on whichever exists, so the same helper is
    correct across the migration boundary.
    """
    import sys as _sys

    with db.transaction(conn) as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(deck_cards)").fetchall()}
        key = "deck_version_id" if "deck_version_id" in cols else "deck_id"
        candidates = conn.execute(
            f"""
            SELECT dc.{key} AS owner, dc.scryfall_id, dc.finish, dc.count
            FROM deck_cards dc
            JOIN cards c ON c.scryfall_id = dc.scryfall_id
            WHERE dc.board = 'main' AND c.is_token = 1
            """
        ).fetchall()
        moved = 0
        for r in candidates:
            clash = conn.execute(
                f"SELECT 1 FROM deck_cards WHERE {key} = ? AND scryfall_id = ? "
                "AND board = 'token' AND finish = ?",
                (r["owner"], r["scryfall_id"], r["finish"]),
            ).fetchone()
            if clash:
                print(
                    f"warning: {r['scryfall_id']}/{r['finish']} already on 'token' "
                    f"board for {key} {r['owner']}; left the 'main' copy in place",
                    file=_sys.stderr,
                )
                continue
            conn.execute(
                f"UPDATE deck_cards SET board = 'token' WHERE {key} = ? "
                "AND scryfall_id = ? AND board = 'main' AND finish = ?",
                (r["owner"], r["scryfall_id"], r["finish"]),
            )
            moved += 1
    return moved


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


# ---------- versioning engine (SCD-2; V17/V18) ----------
#
# A deck's composition is version-scoped: each deck_versions row is an immutable
# snapshot, and deck_cards hangs off deck_version_id. The `decks.current_version_id`
# pointer names the one live version. These functions maintain the SCD-2
# invariants (exactly one current version; contiguous effective_from/effective_to
# dating) and drive the brew→tuned lifecycle.


def version_list(slug: str) -> list[DeckVersion]:
    """Every version of a deck, oldest first. Raises ``LookupError`` if unknown."""
    with db.connect() as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        rows = conn.execute(
            "SELECT deck_version_id, deck_id, version_number, status, is_current, "
            "effective_from, effective_to, change_reason, legality_report, "
            "suggested_bracket, bracket_detail, created_at "
            "FROM deck_versions WHERE deck_id = ? ORDER BY version_number",
            (deck["deck_id"],),
        ).fetchall()
    return [_version_row_to_dataclass(r) for r in rows]


def version_get(slug: str, version_number: int, *, conn=None) -> DeckVersion | None:
    """One version of a deck by its ``version_number`` (1-based)."""
    with db.transaction(conn) as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        row = conn.execute(
            "SELECT deck_version_id, deck_id, version_number, status, is_current, "
            "effective_from, effective_to, change_reason, legality_report, "
            "suggested_bracket, bracket_detail, created_at "
            "FROM deck_versions WHERE deck_id = ? AND version_number = ?",
            (deck["deck_id"], version_number),
        ).fetchone()
    return _version_row_to_dataclass(row) if row else None


def create_version(
    slug: str,
    *,
    status: str = "brew",
    change_reason: str | None = None,
    copy_from_current: bool = False,
    conn=None,
) -> DeckVersion:
    """Cut a NEW version of a deck and make it current.

    Retires the deck's prior current version (cuts its ``effective_to``), inserts
    a fresh ``deck_versions`` row with the next ``version_number``, points
    ``decks.current_version_id`` at it, and — if ``copy_from_current`` — clones
    the prior current version's ``deck_cards`` into the new version so editing
    starts from the existing list (a working copy). With ``copy_from_current``
    False, the new version starts empty.

    Returns the new :class:`DeckVersion`.
    """
    if status not in _VERSION_STATUSES:
        raise ValueError(f"invalid status {status!r}; expected one of {_VERSION_STATUSES}")
    now = db._utcnow_iso()
    with db.transaction(conn) as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        deck_id = deck["deck_id"]
        prior_version_id = deck["current_version_id"]
        next_num = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 AS n FROM deck_versions WHERE deck_id = ?",
            (deck_id,),
        ).fetchone()["n"]
        new_version_id = _insert_version(
            conn, deck_id, version_number=next_num, status=status,
            change_reason=change_reason, now=now,
        )
        if copy_from_current and prior_version_id is not None:
            conn.execute(
                "INSERT INTO deck_cards (deck_version_id, scryfall_id, board, finish, count) "
                "SELECT ?, scryfall_id, board, finish, count "
                "FROM deck_cards WHERE deck_version_id = ?",
                (new_version_id, prior_version_id),
            )
        _touch_deck(conn, deck_id)
        row = conn.execute(
            "SELECT deck_version_id, deck_id, version_number, status, is_current, "
            "effective_from, effective_to, change_reason, legality_report, "
            "suggested_bracket, bracket_detail, created_at "
            "FROM deck_versions WHERE deck_version_id = ?",
            (new_version_id,),
        ).fetchone()
    return _version_row_to_dataclass(row)


def new_draft_from_current(
    slug: str, *, change_reason: str | None = None, conn=None
) -> DeckVersion:
    """Start a new ``brew`` version seeded with the current version's cards.

    The common "I want to tweak this finalized list" flow: clone the current
    composition into a fresh editable brew (the old version stays as history).
    """
    return create_version(
        slug, status="brew", change_reason=change_reason,
        copy_from_current=True, conn=conn,
    )


def set_status(slug: str, status: str, *, conn=None) -> DeckVersion:
    """Set the current version's ``status`` (``brew``/``tuned``) directly, with
    NO validation side effects (unlike :func:`finalize`). Use to flip a version
    back to ``brew`` for more editing, or to mark ``tuned`` without re-running
    legality/bracket. Returns the updated current :class:`DeckVersion`."""
    if status not in _VERSION_STATUSES:
        raise ValueError(f"invalid status {status!r}; expected one of {_VERSION_STATUSES}")
    with db.transaction(conn) as conn:
        deck_id, version_id = _current_version_id_for_slug(conn, slug)
        conn.execute(
            "UPDATE deck_versions SET status = ? WHERE deck_version_id = ?",
            (status, version_id),
        )
        _touch_deck(conn, deck_id)
        row = conn.execute(
            "SELECT deck_version_id, deck_id, version_number, status, is_current, "
            "effective_from, effective_to, change_reason, legality_report, "
            "suggested_bracket, bracket_detail, created_at "
            "FROM deck_versions WHERE deck_version_id = ?",
            (version_id,),
        ).fetchone()
    return _version_row_to_dataclass(row)


def _materialize_for_checks(conn, version_id: int) -> list[dict]:
    """All cards of a version as legality/bracket-shaped dicts (JSON columns
    decoded to native types). Includes every board — legality.py / brackets.py
    exclude tokens internally."""
    rows = conn.execute(
        """
        SELECT dc.scryfall_id, dc.board, dc.finish, dc.count,
               c.oracle_id, c.name, c.type_line, c.oracle_text,
               c.color_identity, c.keywords, c.legalities, c.game_changer
        FROM deck_cards dc
        JOIN cards c ON c.scryfall_id = dc.scryfall_id
        WHERE dc.deck_version_id = ?
        """,
        (version_id,),
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        out.append({
            "scryfall_id": r["scryfall_id"],
            "oracle_id": r["oracle_id"],
            "name": r["name"],
            "board": r["board"],
            "finish": r["finish"],
            "count": r["count"],
            "type_line": r["type_line"],
            "oracle_text": r["oracle_text"],
            "color_identity": json.loads(r["color_identity"]) if r["color_identity"] else [],
            "keywords": json.loads(r["keywords"]) if r["keywords"] else [],
            "legalities": json.loads(r["legalities"]) if r["legalities"] else None,
            "game_changer": r["game_changer"] or 0,
        })
    return out


def finalize(
    slug: str,
    *,
    change_reason: str | None = None,
    size_override: int | None = None,
    use_spellbook: bool = True,
    conn=None,
) -> dict:
    """Mark the current version ``tuned`` and record legality + bracket metadata.

    WARN-ONLY: finalizing ALWAYS succeeds even if the deck is illegal — the
    legality report (and, for Commander decks, the suggested bracket) is computed
    and stored on the version, and returned for display, but nothing is blocked.
    The user is the authority; this just surfaces what's wrong.

    Runs the deck's ``format`` through :mod:`magic_manager.legality`, and (for
    commander-format decks) :mod:`magic_manager.brackets` — with the Commander
    Spellbook client injected for two-card-combo detection unless
    ``use_spellbook=False`` (or the network is unavailable, which degrades
    gracefully). Results are written to ``deck_versions.legality_report`` /
    ``suggested_bracket`` / ``bracket_detail`` and the status flips to ``tuned``.

    Returns ``{"slug", "version_number", "status", "format", "legality":
    LegalityReport-dict, "bracket": BracketDetail-dict|None}``.
    """
    from . import legality as legality_mod

    with db.transaction(conn) as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        deck_id = deck["deck_id"]
        version_id = _current_version_id(conn, deck_id)
        fmt = deck["format"] or "commander"
        cards = _materialize_for_checks(conn, version_id)

        report = legality_mod.validate(cards, format=fmt, size_override=size_override)
        report_json = report.to_json()

        bracket_json = None
        suggested = None
        if fmt.lower() in legality_mod._COMMANDER_LIKE_FORMATS:
            from . import brackets as brackets_mod
            spellbook = None
            if use_spellbook:
                from . import commander_spellbook as _sb
                spellbook = _sb
            detail = brackets_mod.suggest(cards, spellbook=spellbook)
            bracket_json = detail.to_json()
            suggested = detail.suggested_bracket

        version_row = conn.execute(
            "SELECT version_number FROM deck_versions WHERE deck_version_id = ?",
            (version_id,),
        ).fetchone()
        conn.execute(
            "UPDATE deck_versions SET status = 'tuned', legality_report = ?, "
            "suggested_bracket = ?, bracket_detail = ?, "
            "change_reason = COALESCE(?, change_reason) "
            "WHERE deck_version_id = ?",
            (json.dumps(report_json), suggested,
             json.dumps(bracket_json) if bracket_json is not None else None,
             change_reason, version_id),
        )
        _touch_deck(conn, deck_id)

    return {
        "slug": slug,
        "version_number": version_row["version_number"],
        "status": "tuned",
        "format": fmt,
        "legality": report_json,
        "bracket": bracket_json,
    }


def version_diff(slug: str, version_a: int, version_b: int) -> dict:
    """Diff two versions of a deck by ``version_number``.

    Keyed on ``(scryfall_id, board, finish)``. Returns ``{"added": [...],
    "removed": [...], "changed": [...], "unchanged_count": int}`` where added/
    removed carry ``{scryfall_id, board, finish, count, name}`` and changed
    carries ``{scryfall_id, board, finish, name, count_a, count_b}``. "Added"
    means present in B but not A (and vice-versa for removed).
    """
    with db.connect() as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        deck_id = deck["deck_id"]

        def _load(vnum: int) -> dict[tuple[str, str, str], dict]:
            vrow = conn.execute(
                "SELECT deck_version_id FROM deck_versions "
                "WHERE deck_id = ? AND version_number = ?",
                (deck_id, vnum),
            ).fetchone()
            if vrow is None:
                raise LookupError(f"deck {slug!r} has no version {vnum}")
            rows = conn.execute(
                "SELECT dc.scryfall_id, dc.board, dc.finish, dc.count, c.name "
                "FROM deck_cards dc JOIN cards c ON c.scryfall_id = dc.scryfall_id "
                "WHERE dc.deck_version_id = ?",
                (vrow["deck_version_id"],),
            ).fetchall()
            return {
                (r["scryfall_id"], r["board"], r["finish"]): dict(r)
                for r in rows
            }

        a = _load(version_a)
        b = _load(version_b)

    added: list[dict] = []
    removed: list[dict] = []
    changed: list[dict] = []
    unchanged = 0
    for key, brow in b.items():
        if key not in a:
            added.append({
                "scryfall_id": brow["scryfall_id"], "board": brow["board"],
                "finish": brow["finish"], "count": brow["count"], "name": brow["name"],
            })
        elif a[key]["count"] != brow["count"]:
            changed.append({
                "scryfall_id": brow["scryfall_id"], "board": brow["board"],
                "finish": brow["finish"], "name": brow["name"],
                "count_a": a[key]["count"], "count_b": brow["count"],
            })
        else:
            unchanged += 1
    for key, arow in a.items():
        if key not in b:
            removed.append({
                "scryfall_id": arow["scryfall_id"], "board": arow["board"],
                "finish": arow["finish"], "count": arow["count"], "name": arow["name"],
            })
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged_count": unchanged,
    }


# ---------- deck_cards CRUD ----------

def deck_add_card(
    slug: str,
    scryfall_id: str,
    board: str,
    finish: str,
    count: int,
    *,
    conn=None,
) -> dict:
    """Add ``count`` of a printing to a deck's board+finish slot.

    If a row already exists for ``(deck_id, scryfall_id, board, finish)`` the
    count is summed (insert-or-add semantics). Returns ``{"action":
    "inserted"|"updated", "old_count": int|None, "new_count": int}``.

    Pass ``conn`` to enlist in a caller's open transaction (atomic multi-card
    writes); omit it for a standalone add.
    """
    _validate_board(board)
    _validate_finish(finish)
    if count <= 0:
        raise ValueError(f"count must be > 0, got {count}")

    with db.transaction(conn) as conn:
        deck = _fetch_deck(conn, slug)
        if deck is None:
            raise LookupError(f"deck with slug {slug!r} not found")
        deck_id = deck["deck_id"]
        version_id = _current_version_id(conn, deck_id)
        existing = conn.execute(
            """
            SELECT count FROM deck_cards
            WHERE deck_version_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
            """,
            (version_id, scryfall_id, board, finish),
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
            INSERT INTO deck_cards (deck_version_id, scryfall_id, board, finish, count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(deck_version_id, scryfall_id, board, finish) DO UPDATE SET
                count = ?
            """,
            (version_id, scryfall_id, board, finish, new_count, new_count),
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
        version_id = _current_version_id(conn, deck_id)
        existing = conn.execute(
            """
            SELECT count FROM deck_cards
            WHERE deck_version_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
            """,
            (version_id, scryfall_id, board, finish),
        ).fetchone()
        if existing is None:
            return {"action": "not_found", "old_count": None, "new_count": 0}
        old_count = existing["count"]
        if count is None or old_count - count <= 0:
            conn.execute(
                """
                DELETE FROM deck_cards
                WHERE deck_version_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
                """,
                (version_id, scryfall_id, board, finish),
            )
            _touch_deck(conn, deck_id)
            return {"action": "deleted", "old_count": old_count, "new_count": 0}
        new_count = old_count - count
        conn.execute(
            """
            UPDATE deck_cards SET count = ?
            WHERE deck_version_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
            """,
            (new_count, version_id, scryfall_id, board, finish),
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
        version_id = _current_version_id(conn, deck_id)
        existing = conn.execute(
            """
            SELECT count FROM deck_cards
            WHERE deck_version_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
            """,
            (version_id, scryfall_id, board, finish),
        ).fetchone()
        old_count = existing["count"] if existing else None

        if count == 0:
            if existing is None:
                return {"action": "not_found", "old_count": None, "new_count": 0}
            conn.execute(
                """
                DELETE FROM deck_cards
                WHERE deck_version_id = ? AND scryfall_id = ? AND board = ? AND finish = ?
                """,
                (version_id, scryfall_id, board, finish),
            )
            _touch_deck(conn, deck_id)
            return {"action": "deleted", "old_count": old_count, "new_count": 0}

        action = "updated" if existing else "inserted"
        conn.execute(
            """
            INSERT INTO deck_cards (deck_version_id, scryfall_id, board, finish, count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(deck_version_id, scryfall_id, board, finish) DO UPDATE SET
                count = ?
            """,
            (version_id, scryfall_id, board, finish, count, count),
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
        version_id = _current_version_id(conn, deck_id)

        # Recipe cap: an assignment for a printing can't exceed what the
        # deck's PLAYABLE recipe (deck_cards, summed across boards+finishes for
        # that scryfall_id, EXCLUDING the 'token' board) calls for, minus what's
        # already assigned to this deck for the same printing. This catches
        # "compose the same deck twice" — inventory might still have free copies,
        # but the recipe already has as many pledged as it wants. Tokens are
        # excluded so they're never pledged (matches deck_compose_plan). The
        # recipe is version-scoped (V18): pledges reconcile against the deck's
        # CURRENT version's composition.
        recipe_caps: dict[str, int] = {}
        for r in conn.execute(
            "SELECT scryfall_id, SUM(count) AS total FROM deck_cards "
            "WHERE deck_version_id = ? AND board != 'token' GROUP BY scryfall_id",
            (version_id,),
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
            # A deck-assign event moves deck_assignments, NOT inventory — the
            # owned quantity is unchanged — so it records NO inventory_events;
            # it exists in the dimension for the audit trail (and dedup via the
            # assignment hash as source_sha256).
            ingest_mod.create_event(
                conn, "deck-assign",
                label=f"deck-assigned:{slug}",
                mode="additive",
                source_path=f"deck:{slug}",
                source_sha256=_assignment_hash(writable),
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
            # Unassign also moves only deck_assignments, not inventory — no
            # inventory_events; audit-trail dimension row only.
            ingest_mod.create_event(
                conn, "deck-unassign",
                label=f"deck-unassigned:{slug}",
                mode="additive",
                source_path=f"deck:{slug}",
                source_sha256=_assignment_hash(
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

    # Compose against the PLAYABLE recipe only — tokens ride the deck for
    # record-keeping but are never pledged from inventory (they'd otherwise
    # surface as spurious shortfalls, since token printings aren't tracked as
    # loose singles). deck_assign_batch's recipe_caps applies the same exclusion.
    recipe = deck_show(slug, exclude_boards=("token",))  # already validates the slug

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


def _existing_built_slug_for_file(file_name: str, *, conn=None) -> str | None:
    """The slug of an existing ``built`` deck for this MTGJSON fileName, if any.

    Used by :func:`construct_precon_from_loose` to reuse a recipe on re-run
    instead of minting a ``-2`` clone. Picks the oldest matching row so re-runs
    are deterministic. Returns ``None`` if no built deck references the file.
    """
    with db.transaction(conn) as conn:
        row = conn.execute(
            "SELECT slug FROM decks WHERE source_precon_file_name = ? "
            "AND precon_state = 'built' ORDER BY deck_id LIMIT 1",
            (file_name,),
        ).fetchone()
    return row["slug"] if row else None


def construct_precon_from_loose(
    file_name: str,
    *,
    slug: str | None = None,
    name: str | None = None,
    foil_first: bool = False,
    allow_shortfall: bool = False,
    new_copy: bool = False,
    dry_run: bool = False,
) -> dict:
    """Register an MTGJSON precon as a tracked ``built`` deck and pledge the
    cards the user already owns LOOSE to it — WITHOUT adding those cards to
    inventory (no double-count).

    This composes two existing primitives:
      1. :func:`import_precon` with ``add_inventory=False, precon_state="built"``
         to create the recipe (``deck_cards``) + a built deck row, touching
         nothing in ``inventory`` — the no-double-count guard.
      2. :func:`deck_assign_from_composition` to pledge free inventory to that
         recipe (writes ``deck_assignments`` only; inventory qty preserved).

    Re-run safety: unless ``new_copy=True``, an existing ``built`` deck for the
    same ``file_name`` is reused (no ``-2`` clone). Composing an already-composed
    deck writes 0 new rows (the recipe cap in :func:`deck_assign_batch`).

    Atomicity: recipe-create and compose are SEPARATE transactions. If the recipe
    is created but compose then refuses (shortfalls without ``allow_shortfall``),
    the result is a legitimate built deck with 0 pledged — a re-run reuses it and
    composes. No orphan, no double-count.

    Args:
      file_name: MTGJSON deck fileName (e.g. ``BlueBlack_FIN``).
      slug/name: overrides passed to :func:`import_precon` when creating.
      foil_first: prefer foil for ``'either'`` recipe slots.
      allow_shortfall: pledge whatever inventory covers, leaving the rest as
        shortfalls. Without it, refuse to pledge if ANY row would overflow.
      new_copy: force a fresh deck row even if one exists for this fileName.
      dry_run: create the recipe if needed, then only PREVIEW the pledge
        (no ``deck_assignments`` writes).

    Returns:
      {
        "slug": str, "created_recipe": bool, "reused_existing": bool,
        "recipe_card_qty": int,
        "plan": {"rows", "shortfalls", "either_choices"},
        "assigned_rows": int, "assigned_qty": int,
        "shortfalls": list[dict], "either_choices": list[dict],
        "fully_covered": bool,
      }

    Raises:
      - ``mtgjson_mod.MtgJsonError`` if the deck JSON can't be fetched.
      - ``ValueError`` if the slug can't be derived / conflicts.
      - ``AssignmentOverflow`` if shortfalls exist and ``allow_shortfall`` is
        False (nothing is pledged; the recipe may have just been created).
    """
    existing = None if new_copy else _existing_built_slug_for_file(file_name)
    created_recipe = False
    if existing is not None:
        eff_slug = existing
    else:
        imp = import_precon(
            file_name, slug=slug, name=name,
            add_inventory=False, precon_state="built",
        )
        if not imp["effective_slugs"]:
            # Defensive: built import always makes exactly one row.
            raise ValueError(
                f"import_precon created no deck row for {file_name!r}"
            )
        eff_slug = imp["effective_slugs"][0]
        created_recipe = True

    plan = deck_compose_plan(eff_slug, foil_first=foil_first)
    recipe_card_qty = sum(r["need"] for r in plan["rows"])

    # Net-remaining need: subtract what THIS deck already holds. `free_quantity`
    # (behind plan["rows"][*]["free"]) already excludes this deck's own pledges,
    # so a re-run of a fully-pledged deck must NOT re-count those as work/short.
    # remaining = recipe need − already pledged to this deck; a card is a REAL
    # shortfall only when remaining still exceeds free inventory (not owned).
    assigned_here: dict[tuple[str, str], int] = {}
    for row in deck_assignments_list(eff_slug):
        assigned_here[(row.scryfall_id, row.finish)] = (
            assigned_here.get((row.scryfall_id, row.finish), 0) + row.count
        )

    remaining_rows: list[tuple[str, str, int]] = []
    real_shortfalls: list[dict] = []
    for r in plan["rows"]:
        sid, finish, need, free = r["scryfall_id"], r["finish"], r["need"], r["free"]
        remaining = need - assigned_here.get((sid, finish), 0)
        if remaining <= 0:
            continue  # this deck already holds the full recipe of this slot
        if remaining > free:
            real_shortfalls.append({
                "scryfall_id": sid, "finish": finish,
                "need": remaining, "free": free, "kind": "inventory",
            })
        else:
            remaining_rows.append((sid, finish, remaining))

    fully_covered = not real_shortfalls
    base = {
        "slug": eff_slug,
        "created_recipe": created_recipe,
        "reused_existing": existing is not None,
        "recipe_card_qty": recipe_card_qty,
        "plan": plan,
        "assigned_rows": 0,
        "assigned_qty": 0,
        "shortfalls": real_shortfalls,
        "either_choices": plan["either_choices"],
        "fully_covered": fully_covered,
    }

    if dry_run:
        return base

    if real_shortfalls and not allow_shortfall:
        # Refuse to pledge partial. The recipe (if just created) is a valid
        # built deck with whatever was already pledged; a later run with
        # --allow-shortfall (or after acquiring the cards) reuses it and
        # pledges the rest. Mirrors deck_compose's refuse-unless-explicit.
        raise AssignmentOverflow(real_shortfalls)

    if remaining_rows:
        # Pass only the net-remaining deltas: this exactly equals the recipe
        # headroom (cap − already-pledged) per printing, so deck_assign_batch's
        # recipe cap is never tripped by this deck's own prior pledges. Under
        # allow_shortfall it skips rows free can't cover (the real_shortfalls).
        result = deck_assign_batch(
            eff_slug, remaining_rows, allow_shortfall=allow_shortfall,
        )
        base["assigned_rows"] = result["assigned_rows"]
        base["assigned_qty"] = result["assigned_qty"]
    return base


def precon_recipe_needs(file_name: str, *, include_tokens: bool = False
                        ) -> dict[tuple[str, str], int]:
    """Return a precon's recipe as ``{(scryfall_id, finish): count}``.

    Reads the MTGJSON deck via the canonical ``_BOARD_KEY_TO_NAME`` board-walk.
    By default excludes the ``token`` board (tokens ride a deck for
    record-keeping but aren't tracked as loose singles, mirroring
    :func:`deck_compose_plan`'s exclusion) — this is the recipe the pool true-up
    matches free inventory against. Pass ``include_tokens=True`` to also count
    the token board (the backfill wants tokens, since ``import_precon`` writes
    them to inventory too). Finish is ``'nonfoil'``/``'foil'`` from ``isFoil``.
    The single home for precon board-walk extraction.
    """
    deck_data = mtgjson_mod.deck(file_name)
    needs: dict[tuple[str, str], int] = {}
    for mj_key, board_name in _BOARD_KEY_TO_NAME:
        if board_name == "token" and not include_tokens:
            continue
        for entry in deck_data.get(mj_key, []) or []:
            sid = (entry.get("identifiers") or {}).get("scryfallId")
            if not sid:
                continue
            finish = "foil" if entry.get("isFoil") else "nonfoil"
            needs[(sid, finish)] = needs.get((sid, finish), 0) + int(entry.get("count", 1) or 1)
    return needs


def register_precon_from_loose(
    file_name: str,
    *,
    slug: str | None = None,
    name: str | None = None,
    new_copy: bool = False,
    conn=None,
) -> dict:
    """Register a precon as a tracked ``deconstructed`` deck row from cards the
    user already owns LOOSE — the deconstructed sibling of
    :func:`construct_precon_from_loose`.

    Deconstructed means the recipe is kept as a deck row but its cards stay
    LOOSE (unpledged) — so unlike the built sibling this creates NO
    ``deck_assignments`` and adds NOTHING to ``inventory``
    (``import_precon(add_inventory=False, precon_state="deconstructed")``). It
    is the write primitive the pool true-up uses once a product's full recipe is
    confirmed present in free inventory: it makes the precon COUNT (via
    ``precon_unit_counts``) without double-counting or pledging the loose cards.

    Re-run safety: unless ``new_copy=True``, if a deconstructed deck for this
    fileName already exists this is a no-op that returns the existing slug. When
    a row DOES need creating and the base slug is taken (e.g. a ``built`` copy
    already exists at it), a distinct ``-2``/``-3`` slug is minted — mirroring
    the add-mode engine's ``_build_precon_copies``.

    Pass ``conn`` to run inside a caller's open transaction (the product-coverage
    ``--apply`` uses this so deck-row creation is atomic with its ledger moves).

    Returns ``{"slug": str, "created": bool, "reused_existing": bool}``.
    """
    with db.transaction(conn) as conn:
        if not new_copy:
            row = conn.execute(
                "SELECT slug FROM decks WHERE source_precon_file_name = ? "
                "AND precon_state = 'deconstructed' ORDER BY deck_id LIMIT 1",
                (file_name,),
            ).fetchone()
            if row is not None:
                return {"slug": row["slug"], "created": False, "reused_existing": True}

        # Pick a non-colliding slug: base, else base-2/-3/… (a built copy or an
        # unrelated deck may already hold the base slug).
        base = slug or _slug(name or file_name)
        copy_slug = base
        i = 2
        while deck_get(copy_slug, conn=conn) is not None:
            copy_slug = f"{base}-{i}"
            i += 1

        imp = import_precon(
            file_name, slug=copy_slug, name=name,
            add_inventory=False, precon_state="deconstructed", conn=conn,
        )
    eff = imp["effective_slugs"][0] if imp["effective_slugs"] else copy_slug
    return {"slug": eff, "created": True, "reused_existing": False}


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

# MTGJSON deck JSON has these board keys; map to our ``deck_cards.board``.
# `tokens` (V14) captures the tokens/emblems that ship with a precon — they ride
# the deck on the 'token' board AND flow to inventory (the user collects tokens,
# and precon tokens are kept with the deck). Their setCode (e.g. ttmc) is picked
# up by the same collection loop, so the token set auto-syncs before the FK write.
_BOARD_KEY_TO_NAME = (
    ("commander", "commander"),
    ("mainBoard", "main"),
    ("sideBoard", "side"),
    ("tokens", "token"),
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
    precon_state: str | None = None,
    merge_inventory: bool = False,
    conn=None,
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

    Deck-row + card handling is driven by two knobs:
      - ``deconstruct=True`` adds the cards as LOOSE inventory (never pledged).
        ``deconstruct=False`` (built) pledges nothing here either — the caller
        composes separately — but the cards still go to inventory.
      - ``precon_state`` (V11) controls the deck ROW: ``None`` → create a normal
        ``built`` row UNLESS ``deconstruct`` (the jumpstart "loose packs, no
        row" path). A non-None state (``"built"``/``"deconstructed"``) forces a
        deck row IN THAT STATE — this is how precon tracking records a
        torn-down copy (``"deconstructed"``) as a countable unit.
        ``merge_inventory`` overrides both (no row at all).

    Returns a summary dict with these fields:
      - ``deck_name``       (str) display name used
      - ``effective_slugs`` (list[str]) deck slugs created (0 or 1 entry;
                            empty under a rowless deconstruct or merge_inventory)
      - ``deck_added``      (int) deck_cards rows inserted
      - ``deck_updated``    (int) deck_cards rows updated
      - ``deck_card_qty``   (int) total card-qty written across deck_cards
      - ``inv_added``       (int) inventory rows inserted
      - ``inv_updated``     (int) inventory rows updated
      - ``inv_qty_total``   (int) total card-qty added to inventory
      - ``inv_distinct``    (int) distinct (printing, finish) pairs touched
      - ``copies``          (int) copies parameter (preserved for caller)
      - ``missing_sids``    (list[dict]) entries with no scryfallId, skipped

    Pass ``conn`` to enlist the deck-row + inventory writes in a caller's open
    transaction (borrow-or-open, like ``inventory_add``) — this is what lets the
    product-coverage ``--apply`` register deck rows and move ledger deltas
    ATOMICALLY in one transaction, so a drift-abort rolls back BOTH. When
    ``conn`` is borrowed the sync-before-use step is SKIPPED (the caller is
    responsible for having synced the referenced sets) — syncing opens its own
    connections and must never run inside a borrowed write transaction.

    Raises:
      - ``mtgjson_mod.MtgJsonError`` if the deck JSON cannot be fetched
      - ``ValueError`` if the slug cannot be derived or the slug conflicts
    """
    from . import sets as sets_mod  # local import avoids a module-level cycle

    deck_data = mtgjson_mod.deck(file_name)

    deck_name = name or deck_data.get("name") or file_name
    base_slug = slug or _slug(deck_name)
    if not base_slug:
        raise ValueError(
            f"could not derive slug from name {deck_name!r}; pass slug= explicitly"
        )

    # Collect the entries once (all boards) so we can (a) sync the families the
    # cards belong to BEFORE any write, and (b) walk them inside the atomic
    # block below. Each entry: (sid, count, finish, board_name).
    parsed_entries: list[tuple[str, int, str, str]] = []
    missing_sids: list[dict] = []
    set_codes: set[str] = set()
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
            parsed_entries.append((sid, count, finish, board_name))
            sc = entry.get("setCode")
            if sc:
                set_codes.add(sc.lower())

    # Sync-before-use: the deck's cards must exist in the `cards` table before
    # any deck_cards/inventory FK insert. Precons commonly reference a family
    # that's never been synced (the historical FK-failure bug). We sync here,
    # OUTSIDE the atomic write below, because syncing is a precondition — not
    # part of the deck-creation unit — and mirrors the sync-first pattern in
    # master-list / jumpstart-list / precon-list. SKIP when a conn is borrowed:
    # sync opens its own connections (and hits the network), which must not run
    # inside the caller's open write transaction — the caller pre-syncs instead.
    if set_codes and conn is None:
        sets_mod.sync(sorted(set_codes))

    # V5: one composition per import, regardless of copies. Callers who
    # genuinely want a second composition run import-precon a second time
    # with --slug <other>.
    effective_slugs: list[str] = []
    fmt = format
    if fmt is None:
        fmt = "commander" if deck_data.get("type", "").lower().startswith("commander") else None
    # Hard link to the source set (e.g. 'ncc'): MTGJSON gives it as deck_data['code'].
    src_set = (deck_data.get("code") or "").lower() or None

    deck_added = deck_updated = 0
    deck_card_qty = 0
    inv_aggregate: dict[tuple[str, str], int] = {}
    inv_added = inv_updated = 0
    inv_qty_total = 0

    # Resolve the deck-row state. precon_state=None means "let deconstruct
    # decide": a rowless loose import (jumpstart) if deconstruct else a built
    # row. A caller-supplied state always wins and always makes a row.
    row_state = precon_state if precon_state is not None else ("deconstructed" if deconstruct else "built")
    if row_state not in _PRECON_STATES:
        raise ValueError(f"invalid precon_state {row_state!r}; expected one of {_PRECON_STATES}")

    # ONE transaction spans the collision check, deck creation, every
    # deck_add_card, and every inventory_add. If any FK insert fails, the whole
    # thing rolls back — no orphan deck shell, so a corrected retry works.
    # A deck row is created UNLESS this is a rowless jumpstart deconstruct
    # (deconstruct=True with no explicit precon_state) or --merge-inventory.
    make_deck_row = (not merge_inventory) and (precon_state is not None or not deconstruct)

    with db.transaction(conn) as conn:
        if make_deck_row:
            if deck_get(base_slug, conn=conn) is not None:
                raise ValueError(
                    f"deck slug {base_slug!r} already exists; pass --slug to name a "
                    f"variant, --merge-inventory to skip the deck insert and add "
                    f"only inventory, or delete the existing deck first."
                )
            effective_slugs.append(base_slug)
        elif merge_inventory:
            if deck_get(base_slug, conn=conn) is None:
                raise ValueError(
                    f"--merge-inventory requires an existing deck at slug "
                    f"{base_slug!r}; use plain `import-precon` to create one."
                )

        for s in effective_slugs:
            deck_create(s, deck_name, format=fmt, source_set_code=src_set,
                        source_precon_file_name=file_name,
                        precon_state=row_state, conn=conn)

        for sid, count, finish, board_name in parsed_entries:
            for s in effective_slugs:
                r = deck_add_card(s, sid, board_name, finish, count, conn=conn)
                deck_card_qty += count
                if r["action"] == "inserted":
                    deck_added += 1
                else:
                    deck_updated += 1
            inv_aggregate[(sid, finish)] = inv_aggregate.get((sid, finish), 0) + count * copies

        if add_inventory and inv_aggregate:
            # One `precon` ingest event for this import; every card's inventory
            # add is attributed to it (signed +delta), in this same transaction.
            precon_ingest_id = ingest_mod.create_event(
                conn, "precon",
                label=f"precon:{file_name}",
                source_path=file_name,
                notes=f"import_precon copies={copies} state={row_state}",
            )
            for (sid, finish), qty in inv_aggregate.items():
                r = inv_mod.inventory_add(sid, finish, qty, conn=conn,
                                          ingest_id=precon_ingest_id)
                inv_qty_total += qty
                if r["action"] == "inserted":
                    inv_added += 1
                else:
                    inv_updated += 1
            ingest_mod.finalize_event(conn, precon_ingest_id,
                                      rows_added=inv_added, rows_updated=inv_updated)

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


# ---------- precon unit counts (DERIVED from decks; V10/V11) ----------
#
# Preconstructed products are tracked AS UNITS entirely by the `decks` table:
# each copy is a deck row carrying source_precon_file_name (the MTGJSON
# fileName) and precon_state ('built' | 'deconstructed'). The counts below are
# DERIVED — there is no separate ledger to drift from reality. The V7
# precon_ledger was dropped in V10; precon_state is the V11 widening.

_COUNT_SELECT = (
    "SUM(CASE WHEN precon_state = 'built' THEN 1 ELSE 0 END) AS c, "
    "SUM(CASE WHEN precon_state = 'deconstructed' THEN 1 ELSE 0 END) AS d"
)


def precon_unit_counts_for(file_name: str, *, conn=None) -> tuple[int, int]:
    """Return ``(built, deconstructed)`` for one precon fileName, counted
    live from the ``decks`` table. ``(0, 0)`` if none exist."""
    with db.transaction(conn) as conn:
        row = conn.execute(
            f"SELECT {_COUNT_SELECT} FROM decks WHERE source_precon_file_name = ?",
            (file_name,),
        ).fetchone()
    return (row["c"] or 0, row["d"] or 0)


def precon_unit_counts() -> dict[str, tuple[int, int]]:
    """Whole collection as ``{file_name: (built, deconstructed)}``, derived
    from ``decks`` in one GROUP BY. Used by the `modify` precon checklist to
    prefill every row from the REAL deck collection (no ledger)."""
    with db.connect() as conn:
        rows = conn.execute(
            f"""
            SELECT source_precon_file_name AS fn, {_COUNT_SELECT}
            FROM decks
            WHERE source_precon_file_name IS NOT NULL
            GROUP BY source_precon_file_name
            """
        ).fetchall()
    return {r["fn"]: (r["c"] or 0, r["d"] or 0) for r in rows}

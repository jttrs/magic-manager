"""Provenance ledger — the single DRY seam every inventory write path calls.

The V19 star schema (see ``db.py`` SCHEMA_V19) makes an append-only ledger the
ground truth and demotes ``inventory`` to a rebuildable materialized cache:

- ``ingest_events``   (dimension): ONE row per ingest INSTANCE — a checklist
  ingest, a precon import, an intake session, an ad-hoc add. Carries the
  file-ingest columns the old ``ingest_log`` had (mode/sha/rows_*), which it
  subsumed.
- ``inventory_events`` (fact): append-only SIGNED deltas. The invariant is
  ``inventory.quantity == SUM(inventory_events.delta)`` grouped by
  ``(scryfall_id, finish)``.

Every write path opens an event via :func:`open_ingest_event` (a session — one
event, many deltas) or the low-level :func:`create_event` + :func:`record_delta`
(for CRUD functions already inside a caller's transaction), and appends its
signed deltas IN THE SAME TRANSACTION as the ``inventory`` mutation. That is what
makes the ledger and the cache impossible to drift apart.

This module deliberately mirrors ``db.transaction(conn=None)`` (borrow-or-open):
pass ``conn`` to enlist in a caller's open transaction, omit it for a standalone
event. No write path hand-writes ledger SQL — they all route through here.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from . import db

# The full method vocabulary — mirrors the CHECK constraint on
# ingest_events.method (db.py SCHEMA_V19). Kept here so callers import a name
# rather than a magic string, and a typo fails fast instead of hitting SQLite.
METHODS = frozenset({
    "checklist",
    "precon",
    "intake",
    "adhoc",
    "import-block",
    "deck-assign",
    "deck-unassign",
    "migration-backfill",
    "unattributed-backfill",
})


def _validate_method(method: str) -> None:
    if method not in METHODS:
        raise ValueError(f"unknown ingest method {method!r}; expected one of {sorted(METHODS)}")


# ---------- low-level primitives (enlist in a caller's transaction) ----------


def create_event(
    conn,
    method: str,
    *,
    label: str | None = None,
    source_path: str | None = None,
    archived_path: str | None = None,
    source_sha256: str | None = None,
    mode: str | None = None,
    rows_added: int = 0,
    rows_updated: int = 0,
    rows_zeroed: int = 0,
    status: str = "success",
    error: str | None = None,
    notes: str | None = None,
    at: str | None = None,
) -> int:
    """Insert one ``ingest_events`` row; return its ``ingest_id``.

    Requires an open ``conn`` (this is the primitive; use
    :func:`open_ingest_event` for the borrow-or-open convenience). ``at``
    defaults to now; pass it explicitly when backfilling a historical event.
    """
    _validate_method(method)
    cur = conn.execute(
        """
        INSERT INTO ingest_events
            (at, method, label, source_path, archived_path, source_sha256,
             mode, rows_added, rows_updated, rows_zeroed, status, error, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            at or db._utcnow_iso(), method, label, source_path, archived_path,
            source_sha256, mode, rows_added, rows_updated, rows_zeroed,
            status, error, notes,
        ),
    )
    return cur.lastrowid


def record_delta(
    conn,
    ingest_id: int,
    scryfall_id: str,
    finish: str,
    delta: int,
    *,
    at: str | None = None,
) -> None:
    """Append one signed ``inventory_events`` row bound to ``ingest_id``.

    ``delta`` must be non-zero (the table CHECK enforces this); a no-op change
    should simply not call this. Positive = copies added, negative = removed.
    """
    if delta == 0:
        raise ValueError("record_delta: delta must be non-zero")
    conn.execute(
        """
        INSERT INTO inventory_events (ingest_id, scryfall_id, finish, delta, at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ingest_id, scryfall_id, finish, delta, at or db._utcnow_iso()),
    )


def finalize_event(
    conn,
    ingest_id: int,
    *,
    rows_added: int | None = None,
    rows_updated: int | None = None,
    rows_zeroed: int | None = None,
    status: str | None = None,
    error: str | None = None,
    archived_path: str | None = None,
) -> None:
    """Update the summary columns on an event after its deltas are known.

    Only non-None args are written, so a caller can update just ``status`` on
    failure without clobbering counts. ``archived_path`` is set post-hoc by the
    checklist paths (the file is renamed under processed/ only after a
    successful ingest).
    """
    sets_: list[str] = []
    vals: list = []
    for col, v in (
        ("rows_added", rows_added), ("rows_updated", rows_updated),
        ("rows_zeroed", rows_zeroed), ("status", status), ("error", error),
        ("archived_path", archived_path),
    ):
        if v is not None:
            sets_.append(f"{col} = ?")
            vals.append(v)
    if not sets_:
        return
    vals.append(ingest_id)
    conn.execute(f"UPDATE ingest_events SET {', '.join(sets_)} WHERE ingest_id = ?", vals)


# ---------- the recorder + session context manager ----------


@dataclass
class IngestRecorder:
    """Handle yielded by :func:`open_ingest_event`. Appends deltas to one event
    and tallies add/update counts so the event row can be finalized on exit."""

    ingest_id: int
    conn: object
    rows_added: int = 0      # distinct (sid, finish) pairs newly created (old_qty 0)
    rows_updated: int = 0    # distinct pairs whose existing qty changed
    rows_zeroed: int = 0     # distinct pairs driven to 0
    _touched: set = field(default_factory=set)

    def record(
        self,
        scryfall_id: str,
        finish: str,
        delta: int,
        *,
        old_qty: int | None = None,
        new_qty: int | None = None,
    ) -> None:
        """Append a signed delta and classify it for the summary counts.

        ``old_qty``/``new_qty`` are optional hints so the recorder can tally
        added-vs-updated-vs-zeroed the way the old ingest_log did; if omitted it
        classifies by the sign of ``delta`` alone.
        """
        if delta == 0:
            return
        record_delta(self.conn, self.ingest_id, scryfall_id, finish, delta)
        key = (scryfall_id, finish)
        self._touched.add(key)
        if new_qty == 0:
            self.rows_zeroed += 1
        elif old_qty in (None, 0) and delta > 0:
            self.rows_added += 1
        else:
            self.rows_updated += 1


@contextmanager
def open_ingest_event(
    method: str,
    *,
    label: str | None = None,
    source_path: str | None = None,
    archived_path: str | None = None,
    source_sha256: str | None = None,
    mode: str | None = None,
    notes: str | None = None,
    conn=None,
) -> Iterator[IngestRecorder]:
    """Open an ingest event and yield an :class:`IngestRecorder`.

    Borrow-or-open, exactly like :func:`db.transaction`: pass ``conn`` to enlist
    in the caller's open transaction (the ledger row + inventory mutation commit
    together), or omit it for a standalone event with its own transaction.

    On clean exit the event row's rows_added/updated/zeroed counts are finalized
    from what the recorder tallied. On exception the event is marked
    ``status='failed'`` with the error repr, then the exception re-raises (so the
    surrounding transaction still rolls back if ``conn`` was borrowed and the
    caller lets it propagate).
    """
    _validate_method(method)
    with db.transaction(conn) as c:
        ingest_id = create_event(
            c, method, label=label, source_path=source_path,
            archived_path=archived_path, source_sha256=source_sha256,
            mode=mode, notes=notes,
        )
        rec = IngestRecorder(ingest_id=ingest_id, conn=c)
        try:
            yield rec
        except Exception as e:
            finalize_event(c, ingest_id, status="failed", error=repr(e))
            raise
        if not rec._touched:
            # A no-op event (nothing was recorded — e.g. every card in a batch
            # failed to resolve) is noise; delete the dimension row rather than
            # leave a dangling event. No inventory_events reference it.
            c.execute("DELETE FROM ingest_events WHERE ingest_id = ?", (ingest_id,))
            return
        finalize_event(
            c, ingest_id,
            rows_added=rec.rows_added,
            rows_updated=rec.rows_updated,
            rows_zeroed=rec.rows_zeroed,
        )


# ---------- dedup lookup (replaces db.find_ingest_log_by_hash) ----------


def find_events_by_sha(conn, source_sha256: str) -> list[dict]:
    """Return prior ``ingest_events`` with this source hash, newest first.

    The successor to ``db.find_ingest_log_by_hash`` — the checklist ingest paths
    use it to refuse re-ingesting an identical file without ``--force``.
    """
    rows = conn.execute(
        """
        SELECT ingest_id AS id, at, method, label, mode, source_path,
               archived_path, status, error, rows_added, rows_updated, rows_zeroed
        FROM ingest_events
        WHERE source_sha256 = ?
        ORDER BY ingest_id DESC
        """,
        (source_sha256,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- reconciliation + rebuild (root inventory in the ledger) ----------


def reconcile_inventory_ledger(conn) -> list[dict]:
    """Rows where ``inventory.quantity`` disagrees with ``SUM(delta)``.

    Returns a list of ``{scryfall_id, finish, inventory_qty, ledger_qty}`` for
    every mismatch — an empty list means the cache and the ledger agree. SQLite
    has no FULL OUTER JOIN, so we union two LEFT-JOIN passes (inventory-side and
    ledger-side) to catch drift in either direction.
    """
    rows = conn.execute(
        """
        WITH ledger AS (
            SELECT scryfall_id, finish, SUM(delta) AS qty
            FROM inventory_events
            GROUP BY scryfall_id, finish
        )
        SELECT i.scryfall_id, i.finish,
               i.quantity AS inventory_qty,
               COALESCE(l.qty, 0) AS ledger_qty
        FROM inventory i
        LEFT JOIN ledger l
          ON l.scryfall_id = i.scryfall_id AND l.finish = i.finish
        WHERE i.quantity <> COALESCE(l.qty, 0)
        UNION
        SELECT l.scryfall_id, l.finish,
               COALESCE(i.quantity, 0) AS inventory_qty,
               l.qty AS ledger_qty
        FROM ledger l
        LEFT JOIN inventory i
          ON i.scryfall_id = l.scryfall_id AND i.finish = l.finish
        WHERE COALESCE(i.quantity, 0) <> l.qty
        """
    ).fetchall()
    return [dict(r) for r in rows]


def rebuild_inventory_from_ledger(conn) -> dict:
    """Deterministically recompute ``inventory`` from ``inventory_events``.

    ``inventory.quantity = SUM(delta)`` per ``(scryfall_id, finish)`` where the
    sum is positive; ``acquired_at = MIN(at)`` (the first contribution). Rows with
    a non-positive sum are dropped (a card fully removed). ``notes`` is not
    reconstructable from the ledger and is left NULL.

    Returns ``{"rebuilt_rows": int, "drift_before": int}`` where drift_before is
    how many rows disagreed prior to the rebuild. After a correct ledger this is
    a no-op (drift_before == 0 and the row set is unchanged).
    """
    drift_before = len(reconcile_inventory_ledger(conn))
    conn.execute("DELETE FROM inventory")
    conn.execute(
        """
        INSERT INTO inventory (scryfall_id, finish, quantity, acquired_at, notes)
        SELECT scryfall_id, finish, SUM(delta), MIN(at), NULL
        FROM inventory_events
        GROUP BY scryfall_id, finish
        HAVING SUM(delta) > 0
        """
    )
    n = conn.execute("SELECT COUNT(*) AS n FROM inventory").fetchone()["n"]
    return {"rebuilt_rows": n, "drift_before": drift_before}

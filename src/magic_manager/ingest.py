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
    "collection-import",
    "collection-export",
    "purchase",
    "revert",
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
    reverts_ingest_id: int | None = None,
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
             mode, rows_added, rows_updated, rows_zeroed, status, error, notes,
             reverts_ingest_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            at or db._utcnow_iso(), method, label, source_path, archived_path,
            source_sha256, mode, rows_added, rows_updated, rows_zeroed,
            status, error, notes, reverts_ingest_id,
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
    db.require_cards(conn, (scryfall_id,))
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
    reverts_ingest_id: int | None = None,
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
            mode=mode, notes=notes, reverts_ingest_id=reverts_ingest_id,
        )
        rec = IngestRecorder(ingest_id=ingest_id, conn=c)
        try:
            yield rec
        except Exception as e:
            finalize_event(c, ingest_id, status="failed", error=repr(e))
            raise
        # No-op event → delete the dangling dimension row. "No-op" is judged by
        # whether any inventory_events actually reference this event, NOT by the
        # recorder's tallies: callers may write deltas OUT OF BAND via
        # inventory_add(..., ingest_id=)/record_delta (bypassing rec.record), so
        # the ground truth is the child table. Deleting a parent that still has
        # children would violate the FK (inventory_events.ingest_id) and roll the
        # whole transaction back — the add-card/import crash this guards against.
        has_children = c.execute(
            "SELECT 1 FROM inventory_events WHERE ingest_id = ? LIMIT 1", (ingest_id,)
        ).fetchone() is not None
        if not has_children:
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


# ---------- re-attribution (move provenance between events, net-zero) ----------


def reattribute(
    conn,
    *,
    to_ingest_id: int,
    needs: dict[tuple[str, str], int],
    sources: list[tuple[int, dict[tuple[str, str], int]]],
) -> int:
    """Move provenance for ``needs`` onto ``to_ingest_id``, net-zero, drawing
    from one or more SOURCE events in order and capped to each source's balance.

    This is the single home for the "reclassify where copies came from without
    touching the inventory cache" invariant. For each ``(scryfall_id, finish) ->
    qty`` in ``needs``, it walks ``sources`` (an ordered list of
    ``(source_ingest_id, balance_map)`` where balance_map is the source event's
    remaining per-``(sid, finish)`` copies) and, for each, moves
    ``min(remaining_need, source_balance)`` copies: a ``-take`` delta on the
    source event and a ``+take`` delta on ``to_ingest_id``. The pair cancels, so
    ``inventory.quantity == SUM(delta)`` is unchanged. Each source's balance_map
    is DECREMENTED in place so no source is drawn negative and no copy is moved
    twice across calls that share the same balance maps.

    A card whose need exceeds the total available across all sources is moved as
    far as the balances allow (the rest simply stays where it is). Returns the
    number of copies actually moved.
    """
    moved = 0
    for (sid, finish), qty in needs.items():
        need = qty
        for src_id, bal in sources:
            if need <= 0:
                break
            take = min(need, max(0, bal.get((sid, finish), 0)))
            if take > 0:
                record_delta(conn, src_id, sid, finish, -take)
                record_delta(conn, to_ingest_id, sid, finish, take)
                bal[(sid, finish)] -= take
                need -= take
                moved += take
    return moved


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
    db.require_cards(conn, [r[0] for r in conn.execute(
        "SELECT scryfall_id FROM inventory_events GROUP BY scryfall_id HAVING SUM(delta) > 0")])
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


# ---------- revert one import (V35): a compensating event, never a delete ----------
#
# Reverting appends ONE new ``revert`` event whose deltas are the exact negative
# of the reverted event's net delta per (scryfall_id, finish), pointing back via
# ``reverts_ingest_id`` (unique: an event is reverted at most once). History is
# never rewritten. All-or-nothing: every card the event added must still be held
# by it (not removed or moved since) AND free (not pledged to a built deck), and
# a deck the import created (``decks.created_by_ingest_id``) must be unbuilt —
# it is deleted with the revert. Otherwise nothing is written and the plan says why.

# Label prefix of every web Add cards commit (``addcards.commit``: ``web:<source>[ · label]``).
WEB_LABEL_PREFIX = "web:"


def deck_import_linkable(conn, ingest_id: int) -> bool:
    """An unreverted web deck-import event (Add cards → a deck URL) that no deck is
    linked to yet — the only event a newly saved decklist may be linked to (V35)."""
    return conn.execute(
        """SELECT 1 FROM ingest_events e
           WHERE e.ingest_id = ? AND e.method = 'import-block' AND e.label LIKE ? || 'deck%'
             AND NOT EXISTS (SELECT 1 FROM ingest_events r WHERE r.reverts_ingest_id = e.ingest_id)
             AND NOT EXISTS (SELECT 1 FROM decks d WHERE d.created_by_ingest_id = e.ingest_id)""",
        (ingest_id, WEB_LABEL_PREFIX),
    ).fetchone() is not None


# Methods a revert may undo. Anything else is refused with the way out (_NOT_REVERTIBLE).
REVERTIBLE_METHODS = frozenset({"adhoc", "import-block", "intake", "collection-import", "checklist"})

_NOT_REVERTIBLE = {
    "precon": "Preconstructed products aren't reverted here — delete the deck in Decks "
              "(mm deck delete) and adjust its cards with a checklist.",
    "purchase": "Store orders aren't reverted here — use Undo to roll back an order you just added.",
    "deck-assign": "This built a deck — break the deck down in Decks instead.",
    "deck-unassign": "This broke a deck down — build the deck again in Decks instead.",
    "migration-backfill": "Reconstructed history can't be reverted.",
    "unattributed-backfill": "Reconstructed history can't be reverted.",
    "collection-export": "An export didn't change your collection.",
    "revert": "This is already a revert.",
}
_CHECKLIST_NOT_REVERTIBLE = (
    "Only set checklists that added cards can be reverted — a checklist that set counts "
    "(or a precon / Jumpstart sheet) is changed back with another checklist."
)


class RevertRefused(Exception):
    """``revert_event(dry_run=False)`` on a plan that isn't clean; ``.plan`` says why."""

    def __init__(self, plan: "RevertPlan"):
        super().__init__(plan.refusal or "revert refused")
        self.plan = plan


@dataclass
class RevertLine:
    scryfall_id: str
    finish: str
    change: int                    # the reverted event's net delta (+ added, − removed)
    held: int = 0                  # copies the event still accounts for
    owned: int = 0
    pledged: int = 0
    blocker: str | None = None     # None | 'removed' (not all still from this import) | 'pledged'
    pledged_to: list[str] = field(default_factory=list)   # built decks holding this printing-finish (blocked lines)

    @property
    def remove(self) -> int:
        return max(self.change, 0)

    @property
    def restore(self) -> int:
        return max(-self.change, 0)


@dataclass
class RevertDeck:
    slug: str
    name: str
    built: bool
    pledged: int


@dataclass
class RevertPlan:
    ingest_id: int
    at: str
    method: str
    label: str | None
    lines: list[RevertLine]
    decks: list[RevertDeck]
    refusal_code: str | None = None   # not_revertible | already_reverted | deck_in_use | nothing_to_revert | lines_blocked
    refusal: str | None = None
    reverted_by: int | None = None
    revert_ingest_id: int | None = None   # set once applied

    @property
    def ok(self) -> bool:
        return self.refusal_code is None

    @property
    def copies_removed(self) -> int:
        return sum(ln.remove for ln in self.lines)

    @property
    def copies_restored(self) -> int:
        return sum(ln.restore for ln in self.lines)

    @property
    def blocked(self) -> list[RevertLine]:
        return [ln for ln in self.lines if ln.blocker]


def not_revertible_reason(method: str, mode: str | None, label: str | None, status: str) -> str | None:
    """Why an event can never be reverted (by its kind alone), or None if it may be.
    Cheap — no ledger reads; history uses it to decide which entries offer Revert."""
    if status != "success":
        return "Reconstructed history can't be reverted." if status == "backfill" else "This import failed."
    if method == "checklist":
        return None if mode == "additive" and (label or "").startswith("set:") else _CHECKLIST_NOT_REVERTIBLE
    if method not in REVERTIBLE_METHODS:
        return _NOT_REVERTIBLE.get(method, "This kind of change can't be reverted.")
    return None


def _plan(conn, ingest_id: int) -> RevertPlan:
    from . import provenance

    ev = conn.execute(
        "SELECT ingest_id, at, method, label, mode, status FROM ingest_events WHERE ingest_id = ?",
        (ingest_id,),
    ).fetchone()
    if ev is None:
        raise LookupError(f"no ingest event {ingest_id}")
    plan = RevertPlan(ingest_id, ev["at"], ev["method"], ev["label"], [], [])
    by = conn.execute(
        "SELECT ingest_id FROM ingest_events WHERE reverts_ingest_id = ?", (ingest_id,)
    ).fetchone()
    plan.reverted_by = by[0] if by else None
    for d in conn.execute(
        """SELECT d.slug, d.name, d.precon_state,
                  (SELECT COALESCE(SUM(a.count), 0) FROM deck_assignments a WHERE a.deck_id = d.deck_id)
           FROM decks d WHERE d.created_by_ingest_id = ? ORDER BY d.slug""", (ingest_id,),
    ):
        plan.decks.append(RevertDeck(d[0], d[1], d[2] == "built", d[3]))

    why = not_revertible_reason(ev["method"], ev["mode"], ev["label"], ev["status"])
    if why:
        plan.refusal_code, plan.refusal = "not_revertible", why
        return plan
    if plan.reverted_by is not None:
        plan.refusal_code, plan.refusal = "already_reverted", "This import was already reverted."
        return plan

    net: dict[tuple[str, str], int] = {}
    for sid, fin, delta in conn.execute(
        "SELECT scryfall_id, finish, delta FROM inventory_events WHERE ingest_id = ? ORDER BY event_id",
        (ingest_id,),
    ):
        net[(sid, fin)] = net.get((sid, fin), 0) + delta
    sids = sorted({sid for (sid, _), n in net.items() if n})
    held = provenance._held(conn, sids) if sids else {}
    owned: dict[tuple[str, str], int] = {}
    pledged: dict[tuple[str, str], int] = {}
    decks_by: dict[tuple[str, str], list[str]] = {}
    for i in range(0, len(sids), 500):
        part = sids[i:i + 500]
        ph = ",".join("?" * len(part))
        for sid, fin, q in conn.execute(
            f"SELECT scryfall_id, finish, quantity FROM inventory WHERE scryfall_id IN ({ph})", part,
        ):
            owned[(sid, fin)] = q
        for sid, fin, n, name in conn.execute(
            f"""SELECT a.scryfall_id, a.finish, a.count, d.name FROM deck_assignments a
                JOIN decks d ON d.deck_id = a.deck_id WHERE a.scryfall_id IN ({ph})
                ORDER BY d.name""", part,
        ):
            pledged[(sid, fin)] = pledged.get((sid, fin), 0) + n
            decks_by.setdefault((sid, fin), []).append(name)
    for (sid, fin), change in sorted(net.items()):
        if not change:
            continue
        k = (sid, fin)
        ln = RevertLine(sid, fin, change, max(0, held.get((ingest_id, sid, fin), 0)),
                        owned.get(k, 0), pledged.get(k, 0))
        if change > 0:
            if ln.held < change:
                ln.blocker = "removed"
            elif ln.owned - ln.pledged < change:
                ln.blocker = "pledged"
                ln.pledged_to = decks_by.get(k, [])
        plan.lines.append(ln)

    def refuse(code: str, why: str) -> RevertPlan:
        plan.refusal_code, plan.refusal = code, why
        return plan

    busy = [d for d in plan.decks if d.built or d.pledged]
    if busy:
        return refuse("deck_in_use", f"The deck {busy[0].name} it saved is built — break it down in Decks first.")
    if not plan.lines and not plan.decks:
        return refuse("nothing_to_revert", "This import didn't change your collection.")
    if plan.blocked:
        n = len(plan.blocked)
        return refuse("lines_blocked",
                      f"{n} of its {'card' if n == 1 else 'cards'} can't be taken back out: "
                      "copies were removed since or are in a built deck. Free them first, then revert.")
    return plan


def revert_event(ingest_id: int, *, dry_run: bool = True) -> RevertPlan:
    """Plan (``dry_run``, the default) or apply the revert of one ingest event.

    Applying appends ONE ``revert`` event (label ``revert:<id> · <label>``,
    ``reverts_ingest_id`` = ``ingest_id``) with the negative of every net
    per-printing delta, deletes the unbuilt deck the import created, and proves
    ``inventory == SUM(delta)`` — all in one transaction. Raises ``LookupError``
    for an unknown event and :class:`RevertRefused` when the plan isn't clean
    (nothing is written)."""
    from . import decks as decks_mod
    from . import inventory as inv

    with db.connect() as conn:
        if not dry_run and not conn.in_transaction:
            conn.execute("BEGIN IMMEDIATE")   # plan + write see one state
        plan = _plan(conn, ingest_id)
        if dry_run:
            return plan
        if not plan.ok:
            raise RevertRefused(plan)
        label = f"revert:{ingest_id}" + (f" · {plan.label}" if plan.label else "")
        rid = create_event(conn, "revert", label=label, mode="revert", reverts_ingest_id=ingest_id)
        added = updated = zeroed = 0
        for ln in plan.lines:
            if ln.remove:
                r = inv.inventory_remove(ln.scryfall_id, ln.finish, ln.remove, conn=conn, ingest_id=rid, method="revert")
                zeroed += r["action"] == "deleted"
                updated += r["action"] == "decremented"
            else:
                r = inv.inventory_add(ln.scryfall_id, ln.finish, ln.restore, conn=conn, ingest_id=rid, method="revert")
                added += r["action"] == "inserted"
                updated += r["action"] == "updated"
        finalize_event(conn, rid, rows_added=added, rows_updated=updated, rows_zeroed=zeroed)
        for d in plan.decks:
            decks_mod.deck_delete(d.slug, conn=conn)
        drift = reconcile_inventory_ledger(conn)
        if drift:
            raise RuntimeError(f"revert left the ledger out of balance: {drift[:3]}")
        plan.revert_ingest_id = rid
        return plan

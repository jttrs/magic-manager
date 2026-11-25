"""Store orders → purchases, with what you paid (V34).

The browser companion reads your own order history (Mana Pool, TCGplayer, Card
Kingdom) and hands the app normalized order lines. This module is the one home
for what happens next:

* :func:`save` stores each order as a ``purchases`` row + its ``purchase_lines``
  (deduped by store + order id). Saving never touches inventory — an order can
  sit "read, not yet assigned" for as long as you like.
* :func:`review` lists one order's lines read-only: what you paid, what each is
  worth today and how many copies of the printing you own.
* :func:`add_to_collection` adds EVERY single line with a known printing that
  isn't in your collection yet, in ONE transaction: one ``purchase`` ingest event
  per order, dated at the order date (``inventory.inventory_add`` +deltas). The
  ledger invariant ``inventory == SUM(delta)`` is checked before commit. Sealed
  products and other lines are recorded only, never added. Copies are not tied to
  individual orders: :func:`totals` just compares everything paid to what the
  whole collection is worth today. (``purchase_lines.matched`` is a legacy count
  from the retired per-line matching; it still reads, nothing writes it.)

Prices are stored in cents per line (unit price as the store listed it), plus
the order's shipping / tax / fees / store credit as the store showed them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Literal

from . import db, ingest as ingest_mod, inventory as inventory_mod

STORES: dict[str, str] = {"manapool": "Mana Pool", "tcgplayer": "TCGplayer", "cardkingdom": "Card Kingdom"}

# What has been checked against each store's REAL pages (docs/purchases.md §
# Verification). The owner's rule: nothing unverified reaches users silently —
# the app shows this, and an unverified line kind is recorded but never added.
STORE_VERIFICATION: dict[str, tuple[str, str]] = {
    "manapool": ("verified", "Order list and order pages checked against your real Mana Pool orders."),
    "tcgplayer": ("partial", "The first page of orders is checked against your real TCGplayer history; "
                             "later pages (the page links) are not verified yet. Pick the year on TCGplayer's page."),
    "cardkingdom": ("partial", "Sealed products are checked against a real Card Kingdom invoice. Single cards are "
                               "NOT verified: they are recorded with their price but never added to your collection."),
}
# Line kinds a store may turn into cards. Card Kingdom singles are unverified.
_ALLOWED_KINDS: dict[str, frozenset[str]] = {
    "manapool": frozenset({"single", "sealed", "other"}),
    "tcgplayer": frozenset({"single", "sealed", "other"}),
    "cardkingdom": frozenset({"sealed", "other"}),
}


def line_kind_allowed(store: str, kind: str) -> bool:
    return kind in _ALLOWED_KINDS.get(store, frozenset({"other"}))
LineKind = Literal["single", "sealed", "other"]
Status = Literal["new", "partial", "done", "nothing"]


class PurchaseError(ValueError):
    """An order or a decision that can't be applied (bad counts, unknown line…)."""


class AlreadyApplied(PurchaseError):
    """The order is already fully assigned to your collection."""


# ---------- inputs ----------

@dataclass
class OrderLine:
    name: str
    quantity: int
    finish: str = "nonfoil"                 # nonfoil | foil | etched (etched is stored as foil)
    unit_price: float | None = None         # dollars, as the store listed it
    set_name: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    condition: str | None = None
    scryfall_id: str | None = None
    tcgplayer_product_id: int | None = None
    kind: LineKind = "single"


@dataclass
class Order:
    store: str
    order_id: str
    ordered_at: str                         # ISO date or datetime
    lines: list[OrderLine]
    currency: str = "USD"
    subtotal: float | None = None
    shipping: float | None = None
    tax: float | None = None
    fees: float | None = None
    credit: float | None = None             # store credit / discounts used (positive number)
    total: float | None = None


def _cents(v: float | None) -> int | None:
    return None if v is None else int(round(float(v) * 100))


def _usd(c: int | None) -> float | None:
    return None if c is None else round(c / 100, 2)


def _iso(at: str) -> str:
    s = str(at).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt).isoformat(timespec="seconds")
        except ValueError:
            continue
    raise PurchaseError(f"order date {at!r} is not an ISO date")


def _finish(f: str) -> str:
    f = (f or "nonfoil").lower()
    if f in ("foil", "etched"):
        return "foil"
    if f == "nonfoil":
        return "nonfoil"
    raise PurchaseError(f"unknown finish {f!r}")


# ---------- resolving printings ----------

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _tcgplayer_ids(lines: list[OrderLine]) -> None:
    """TCGplayer lines name a TCGplayer product id: ask Scryfall which printing it
    is (``store_ids.tcgplayer_printings``, cached + upserted)."""
    from . import store_ids
    todo = [ln for ln in lines if ln.kind == "single" and not ln.scryfall_id and ln.tcgplayer_product_id]
    found = store_ids.tcgplayer_printings(ln.tcgplayer_product_id for ln in todo)
    for ln in todo:
        if ln.tcgplayer_product_id in found:
            ln.scryfall_id = found[ln.tcgplayer_product_id]["id"]


def _resolve(lines: list[OrderLine], *, remote: bool = True) -> None:
    """Fill ``scryfall_id`` in place: an id the store gave (fetched + upserted when
    the local catalog lacks it), a TCGplayer product id (via Scryfall), else set
    code + collector number from the local catalog. Lines nothing identifies keep
    ``scryfall_id=None`` (shown, never added)."""
    from . import addcards
    if remote:
        _tcgplayer_ids(lines)
    ids = {ln.scryfall_id.lower() for ln in lines if ln.scryfall_id and _UUID.match(ln.scryfall_id.lower())}
    if remote and ids:
        addcards.ensure_printings(ids)
    with db.connect() as conn:
        local = {r[0] for r in conn.execute(
            f"SELECT scryfall_id FROM cards WHERE scryfall_id IN ({','.join('?' * len(ids))})", list(ids))} if ids else set()
        for ln in lines:
            if ln.kind != "single":
                ln.scryfall_id = None
                continue
            sid = (ln.scryfall_id or "").lower()
            if sid in local:
                ln.scryfall_id = sid
                continue
            ln.scryfall_id = None
            if ln.set_code and ln.collector_number:
                r = conn.execute("SELECT scryfall_id FROM cards WHERE set_code = ? AND collector_number = ?",
                                 (ln.set_code.lower(), str(ln.collector_number))).fetchone()
                if r:
                    ln.scryfall_id = r[0]


# ---------- save ----------

@dataclass
class SaveResult:
    saved: list[int] = field(default_factory=list)       # purchase ids stored (new or re-read)
    skipped: list[str] = field(default_factory=list)     # order ids already assigned to your collection
    unresolved: int = 0                                  # single lines no printing could be found for


def save(orders: Iterable[Order], *, remote: bool = True) -> SaveResult:
    """Store orders. A new order is inserted; an order read before but not yet
    assigned is replaced by the fresh read; an order you've already started
    assigning is left alone (``skipped``) — its lines carry your decisions."""
    orders = list(orders)
    for o in orders:
        if o.store not in STORES:
            raise PurchaseError(f"unknown store {o.store!r}")
        if not str(o.order_id).strip():
            raise PurchaseError("order without an order number")
        for ln in o.lines:
            if not line_kind_allowed(o.store, ln.kind):
                ln.kind = "other"   # an unverified store path never becomes a card
        _resolve(o.lines, remote=remote)
    out = SaveResult()
    now = db._utcnow_iso()
    with db.connect() as conn:
        for o in orders:
            oid = str(o.order_id).strip()
            row = conn.execute("SELECT purchase_id, ingest_id FROM purchases WHERE store = ? AND store_order_id = ?",
                               (o.store, oid)).fetchone()
            vals = (_iso(o.ordered_at), o.currency or "USD", _cents(o.subtotal), _cents(o.shipping), _cents(o.tax),
                    _cents(o.fees), _cents(o.credit), _cents(o.total), now)
            if row and row["ingest_id"] is not None:
                out.skipped.append(oid)
                continue
            if row:
                pid = row["purchase_id"]
                conn.execute("""UPDATE purchases SET ordered_at=?, currency=?, subtotal_cents=?, shipping_cents=?,
                                tax_cents=?, fees_cents=?, credit_cents=?, total_cents=?, read_at=? WHERE purchase_id=?""",
                             (*vals, pid))
                conn.execute("DELETE FROM purchase_lines WHERE purchase_id = ?", (pid,))
            else:
                pid = conn.execute("""INSERT INTO purchases (ordered_at, currency, subtotal_cents, shipping_cents, tax_cents,
                                      fees_cents, credit_cents, total_cents, read_at, store, store_order_id)
                                      VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (*vals, o.store, oid)).lastrowid
            for i, ln in enumerate(o.lines, start=1):
                if ln.quantity < 1:
                    raise PurchaseError(f"order {oid} line {i}: quantity must be at least 1")
                conn.execute("""INSERT INTO purchase_lines (purchase_id, line_no, kind, name, set_name, condition, finish,
                                scryfall_id, quantity, unit_price_cents) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                             (pid, i, ln.kind, ln.name.strip()[:300], ln.set_name, ln.condition, _finish(ln.finish),
                              ln.scryfall_id, int(ln.quantity), _cents(ln.unit_price)))
                if ln.kind == "single" and not ln.scryfall_id:
                    out.unresolved += 1
            out.saved.append(pid)
    return out


# ---------- read side ----------

@dataclass
class PurchaseSummary:
    purchase_id: int
    store: str
    store_name: str
    order_id: str
    ordered_at: str
    read_at: str
    lines: int
    copies: int
    assigned: int            # copies matched + added
    assignable: int          # copies on lines with a known printing
    unresolved: int          # single lines with no printing found
    status: Status
    paid_usd: float          # card prices × quantity (every line)
    worth_usd: float         # resolved singles × quantity at today's local prices
    compared_paid_usd: float  # what those same priced lines cost you (apples to apples with worth)
    gain_usd: float          # worth_usd - compared_paid_usd
    subtotal_usd: float | None = None   # the store's own subtotal (may differ from paid_usd: replacements/refunds)
    shipping_usd: float | None = None
    tax_usd: float | None = None
    fees_usd: float | None = None
    credit_usd: float | None = None
    total_usd: float | None = None
    ingest_id: int | None = None


def _unit_today(prices: dict, sid: str | None, finish: str) -> float | None:
    from .provenance import _unit_usd
    return _unit_usd(prices.get(sid), finish) if sid else None


def _summaries(conn, where: str = "", args: tuple = ()) -> list[PurchaseSummary]:
    from .provenance import _priced
    ps = conn.execute(f"SELECT * FROM purchases {where} ORDER BY ordered_at DESC, purchase_id DESC", args).fetchall()
    if not ps:
        return []
    ids = [p["purchase_id"] for p in ps]
    lines = conn.execute(f"SELECT * FROM purchase_lines WHERE purchase_id IN ({','.join('?' * len(ids))})", ids).fetchall()
    prices, _ = _priced(conn, {ln["scryfall_id"] for ln in lines if ln["scryfall_id"]})
    by: dict[int, list] = {}
    for ln in lines:
        by.setdefault(ln["purchase_id"], []).append(ln)
    out = []
    for p in ps:
        ls = by.get(p["purchase_id"], [])
        copies = sum(ln["quantity"] for ln in ls)
        assigned = sum(ln["matched"] + ln["added"] for ln in ls)
        assignable = sum(ln["quantity"] for ln in ls if ln["scryfall_id"])
        paid = sum((ln["unit_price_cents"] or 0) * ln["quantity"] for ln in ls) / 100
        worth = cmp_paid = 0.0
        for ln in ls:
            today = _unit_today(prices, ln["scryfall_id"], ln["finish"])
            if today is None or ln["unit_price_cents"] is None:
                continue
            worth += today * ln["quantity"]
            cmp_paid += ln["unit_price_cents"] * ln["quantity"] / 100
        status: Status = ("nothing" if not assignable else "done" if assigned >= assignable
                          else "partial" if assigned else "new")
        out.append(PurchaseSummary(
            purchase_id=p["purchase_id"], store=p["store"], store_name=STORES[p["store"]], order_id=p["store_order_id"],
            ordered_at=p["ordered_at"], read_at=p["read_at"], lines=len(ls), copies=copies, assigned=assigned,
            assignable=assignable, unresolved=sum(1 for ln in ls if ln["kind"] == "single" and not ln["scryfall_id"]),
            status=status, paid_usd=round(paid, 2), worth_usd=round(worth, 2), compared_paid_usd=round(cmp_paid, 2),
            gain_usd=round(worth - cmp_paid, 2), subtotal_usd=_usd(p["subtotal_cents"]), shipping_usd=_usd(p["shipping_cents"]), tax_usd=_usd(p["tax_cents"]),
            fees_usd=_usd(p["fees_cents"]), credit_usd=_usd(p["credit_cents"]), total_usd=_usd(p["total_cents"]),
            ingest_id=p["ingest_id"],
        ))
    return out


def catalog(*, conn=None) -> list[PurchaseSummary]:
    """Every stored order, newest first, with paid vs. worth today."""
    if conn is not None:
        return _summaries(conn)
    with db.connect() as c:
        return _summaries(c)


def known_orders(store: str) -> dict[str, Status]:
    """Order ids already read for a store → their status (so the app can mark them)."""
    return {s.order_id: s.status for s in catalog() if s.store == store}


def by_ingest(conn, ingest_ids: Iterable[int]) -> dict[int, PurchaseSummary]:
    ids = list(dict.fromkeys(ingest_ids))
    if not ids:
        return {}
    rows = _summaries(conn, f"WHERE ingest_id IN ({','.join('?' * len(ids))})", tuple(ids))
    return {s.ingest_id: s for s in rows if s.ingest_id is not None}


# ---------- review ----------

@dataclass
class ReviewLine:
    line_no: int
    kind: LineKind
    name: str
    set_name: str | None
    condition: str | None
    finish: str
    scryfall_id: str | None
    quantity: int
    unit_usd: float | None
    today_usd: float | None
    matched: int              # legacy: copies matched to owned cards before matching was retired
    added: int
    remaining: int            # quantity - matched - added (singles with a printing: still to add)
    owned: int                # copies of this printing + finish you own now


@dataclass
class Review:
    purchase: PurchaseSummary
    lines: list[ReviewLine]


def _get(conn, purchase_id: int):
    p = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
    if not p:
        raise LookupError(f"no purchase {purchase_id}")
    return p


def review(purchase_id: int) -> Review:
    """One order's lines with what you paid, today's price and what you own now."""
    from .provenance import _priced
    with db.connect() as conn:
        _get(conn, purchase_id)
        summary = _summaries(conn, "WHERE purchase_id = ?", (purchase_id,))[0]
        lines = conn.execute("SELECT * FROM purchase_lines WHERE purchase_id = ? ORDER BY line_no", (purchase_id,)).fetchall()
        sids = {ln["scryfall_id"] for ln in lines if ln["scryfall_id"]}
        prices, _ = _priced(conn, sids)
        owned = {(r[0], r[1]): r[2] for r in conn.execute(
            f"SELECT scryfall_id, finish, quantity FROM inventory WHERE scryfall_id IN ({','.join('?' * len(sids))})",
            list(sids))} if sids else {}
    out = []
    for ln in lines:
        key = (ln["scryfall_id"], ln["finish"])
        out.append(ReviewLine(
            line_no=ln["line_no"], kind=ln["kind"], name=ln["name"], set_name=ln["set_name"],
            condition=ln["condition"], finish=ln["finish"], scryfall_id=ln["scryfall_id"], quantity=ln["quantity"],
            unit_usd=_usd(ln["unit_price_cents"]), today_usd=_unit_today(prices, ln["scryfall_id"], ln["finish"]),
            matched=ln["matched"], added=ln["added"], remaining=ln["quantity"] - ln["matched"] - ln["added"],
            owned=owned.get(key, 0) if ln["scryfall_id"] else 0,
        ))
    return Review(summary, out)


# ---------- add to collection ----------

@dataclass
class ApplyResult:
    purchase_id: int
    ingest_id: int
    added: int


def add_to_collection(purchase_id: int) -> ApplyResult:
    """Add every single of the order with a known printing that isn't in your
    collection yet (quantity − already added − legacy matched), in one
    transaction. Fully added → :class:`AlreadyApplied`; nothing addable (sealed
    only, or no printing found) → :class:`PurchaseError`. All-or-nothing."""
    with db.connect() as conn:
        p = _get(conn, purchase_id)
        lines = conn.execute("SELECT * FROM purchase_lines WHERE purchase_id = ? ORDER BY line_no",
                             (purchase_id,)).fetchall()
        addable = [ln for ln in lines if ln["kind"] == "single" and ln["scryfall_id"]]
        todo = [(ln, ln["quantity"] - ln["matched"] - ln["added"]) for ln in addable]
        todo = [(ln, n) for ln, n in todo if n > 0]
        if not todo:
            if addable:
                raise AlreadyApplied(f"{STORES[p['store']]} order {p['store_order_id']} is already in your collection")
            raise PurchaseError("this order has no single cards with a known printing to add")
        from .provenance import _held
        sids = {ln["scryfall_id"] for ln, _n in todo}
        held_before = _held(conn, sids)

        ingest_id = p["ingest_id"]
        if ingest_id is None:
            label = f"purchase:{p['store']}:{p['store_order_id']}"
            ingest_id = ingest_mod.create_event(conn, "purchase", label=label, source_path=label, mode="purchase",
                                                at=p["ordered_at"], notes=f"{STORES[p['store']]} order {p['store_order_id']}")
            conn.execute("UPDATE purchases SET ingest_id = ? WHERE purchase_id = ?", (ingest_id, purchase_id))
        db.require_cards(conn, sids)
        given: dict[tuple[str, str], int] = {}
        for ln, n in todo:
            inventory_mod.inventory_add(ln["scryfall_id"], ln["finish"], n, conn=conn, ingest_id=ingest_id)
            conn.execute("UPDATE purchase_lines SET added = added + ? WHERE line_id = ?", (n, ln["line_id"]))
            k = (ln["scryfall_id"], ln["finish"])
            given[k] = given.get(k, 0) + n
        n_rows = conn.execute("SELECT COUNT(*) FROM (SELECT 1 FROM inventory_events WHERE ingest_id = ? "
                              "GROUP BY scryfall_id, finish)", (ingest_id,)).fetchone()[0]
        ingest_mod.finalize_event(conn, ingest_id, rows_added=n_rows)
        drift = ingest_mod.reconcile_inventory_ledger(conn)
        if drift:
            raise RuntimeError(f"ledger drift after adding the order ({len(drift)} rows); rolled back")
        held = _held(conn, sids)
        for (sid, fin), n in given.items():
            if held.get((ingest_id, sid, fin), 0) != held_before.get((ingest_id, sid, fin), 0) + n:
                raise RuntimeError("the order would not hold exactly the copies added to it; rolled back")
    return ApplyResult(purchase_id, ingest_id, sum(n for _ln, n in todo))


# ---------- totals (paid vs. what the collection is worth) ----------

@dataclass
class Totals:
    orders: int
    paid_usd: float            # item prices × quantity, every line of every order
    singles_paid_usd: float
    sealed_paid_usd: float
    other_paid_usd: float
    collection_value_usd: float   # today's value of your WHOLE inventory (local prices)
    collection_unpriced: int      # inventory rows with no USD price (not in the value)
    gain_usd: float               # collection_value_usd - paid_usd


def totals() -> Totals:
    """Everything paid across all orders vs. what the whole collection is worth
    today — a rough return estimate. Copies aren't tied to orders, so this is the
    only honest comparison. The value is :func:`inventory.inventory_value` (the
    same local-first price math as ``mm inventory value``)."""
    paid = {"single": 0, "sealed": 0, "other": 0}
    with db.connect() as conn:
        n = conn.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
        for kind, cents in conn.execute(
                "SELECT kind, SUM(COALESCE(unit_price_cents, 0) * quantity) FROM purchase_lines GROUP BY kind"):
            paid[kind if kind in paid else "other"] += cents or 0
    v = inventory_mod.inventory_value()
    total_paid = round(sum(paid.values()) / 100, 2)
    value = round(v["total"], 2)
    return Totals(orders=n, paid_usd=total_paid, singles_paid_usd=round(paid["single"] / 100, 2),
                  sealed_paid_usd=round(paid["sealed"] / 100, 2), other_paid_usd=round(paid["other"] / 100, 2),
                  collection_value_usd=value, collection_unpriced=len(v["missing_price"]),
                  gain_usd=round(value - total_paid, 2))


def forget(purchase_id: int) -> None:
    """Delete a stored order you haven't assigned anything from (a mistaken read).
    Orders with ledger history are kept — undo is the way back for those."""
    with db.connect() as conn:
        p = _get(conn, purchase_id)
        if p["ingest_id"] is not None:
            raise PurchaseError("this order is already in your collection; use Undo to roll it back")
        conn.execute("DELETE FROM purchase_lines WHERE purchase_id = ?", (purchase_id,))
        conn.execute("DELETE FROM purchases WHERE purchase_id = ?", (purchase_id,))

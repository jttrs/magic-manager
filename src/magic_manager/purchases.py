"""Store orders → purchases, with what you paid (V34).

The browser companion reads your own order history (Mana Pool, TCGplayer, Card
Kingdom) and hands the app normalized order lines. This module is the one home
for what happens next:

* :func:`save` stores each order as a ``purchases`` row + its ``purchase_lines``
  (deduped by store + order id). Saving never touches inventory — an order can
  sit "read, not yet assigned" for as long as you like.
* :func:`review` shows, per line, how many copies you already own that could be
  this purchase (copies whose source is *unknown* or *singles*, not another
  purchase or a product), so you can **match** them, and how many to **add**.
* :func:`apply` writes the decision to the V19 ledger in ONE transaction: one
  ``purchase`` ingest event per order, dated at the order date. Adds are +deltas
  (``inventory.inventory_add``); matches are net-zero re-attribution through
  :func:`ingest.reattribute` (the same seam product true-up uses). The ledger
  invariant ``inventory == SUM(delta)`` is checked before commit.

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
    matched: int
    added: int
    remaining: int            # quantity - matched - added
    owned: int                # copies of this printing + finish you own now
    matchable: int            # owned copies not already from a purchase or a product (can be matched)


@dataclass
class Review:
    purchase: PurchaseSummary
    lines: list[ReviewLine]


def _matchable_sources(conn, sids: Iterable[str]) -> list[tuple[int, dict[tuple[str, str], int]]]:
    """Ordered ``(ingest_id, {(sid, finish): copies})`` sources a purchase may draw
    owned copies from: each event's HELD copies (provenance's LIFO netting, so a
    removed copy is never matched) for events whose source is unknown or singles —
    never another purchase or a product. Unknown buckets first, then singles
    newest first."""
    from .provenance import _classify, _held, _products
    held = _held(conn, sids)
    ev_ids = {iid for (iid, _s, _f), n in held.items() if n > 0}
    if not ev_ids:
        return []
    products = _products(conn)
    meta = {r[0]: r for r in conn.execute(
        f"SELECT ingest_id, method, label, source_path, at FROM ingest_events WHERE ingest_id IN ({','.join('?' * len(ev_ids))})",
        list(ev_ids))}
    ranked = []
    for iid in ev_ids:
        _, method, label, path, at = meta[iid]
        if method in ("purchase", "deck-assign", "deck-unassign"):
            continue
        src = _classify(method, label, path, products)
        if src.kind not in ("unknown", "singles"):
            continue
        ranked.append((0 if src.kind == "unknown" else 1, at or "", iid))
    ranked.sort(key=lambda t: (t[0], "" if t[0] == 0 else _neg(t[1]), t[2]))
    out = []
    for _r, _at, iid in ranked:
        bal = {(s, f): n for (i, s, f), n in held.items() if i == iid and n > 0}
        if bal:
            out.append((iid, bal))
    return out


def _neg(s: str) -> str:
    """Sort key that orders ISO strings newest first in an ascending sort."""
    return "".join(chr(0x10FFFF - ord(ch)) for ch in s)


def _get(conn, purchase_id: int):
    p = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
    if not p:
        raise LookupError(f"no purchase {purchase_id}")
    return p


def review(purchase_id: int) -> Review:
    """One order's lines with what you own now and what could be matched."""
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
        avail: dict[tuple[str, str], int] = {}
        for _iid, bal in _matchable_sources(conn, sids):
            for k, n in bal.items():
                avail[k] = avail.get(k, 0) + n
    out = []
    for ln in lines:
        key = (ln["scryfall_id"], ln["finish"])
        out.append(ReviewLine(
            line_no=ln["line_no"], kind=ln["kind"], name=ln["name"], set_name=ln["set_name"],
            condition=ln["condition"], finish=ln["finish"], scryfall_id=ln["scryfall_id"], quantity=ln["quantity"],
            unit_usd=_usd(ln["unit_price_cents"]), today_usd=_unit_today(prices, ln["scryfall_id"], ln["finish"]),
            matched=ln["matched"], added=ln["added"], remaining=ln["quantity"] - ln["matched"] - ln["added"],
            owned=owned.get(key, 0) if ln["scryfall_id"] else 0,
            matchable=avail.get(key, 0) if ln["scryfall_id"] else 0,
        ))
    return Review(summary, out)


# ---------- apply ----------

@dataclass
class Decision:
    line_no: int
    match: int = 0
    add: int = 0


@dataclass
class ApplyResult:
    purchase_id: int
    ingest_id: int
    matched: int
    added: int


def apply(purchase_id: int, decisions: Iterable[Decision]) -> ApplyResult:
    """Assign order lines to your collection in one transaction.

    ``match`` moves that many owned copies' provenance onto the order (net-zero);
    ``add`` adds new copies. Per line, ``match + add`` may not exceed what's left
    to assign, and ``match`` may not exceed the matchable copies. Re-applying a
    fully assigned order raises :class:`AlreadyApplied`. All-or-nothing."""
    decisions = [d for d in decisions if d.match or d.add]
    if any(d.match < 0 or d.add < 0 for d in decisions):
        raise PurchaseError("counts can't be negative")
    if len({d.line_no for d in decisions}) != len(decisions):
        raise PurchaseError("a line is listed twice")
    with db.connect() as conn:
        p = _get(conn, purchase_id)
        lines = {ln["line_no"]: ln for ln in conn.execute(
            "SELECT * FROM purchase_lines WHERE purchase_id = ?", (purchase_id,))}
        assignable = [ln for ln in lines.values() if ln["scryfall_id"]]
        if assignable and all(ln["matched"] + ln["added"] >= ln["quantity"] for ln in assignable):
            raise AlreadyApplied(f"{STORES[p['store']]} order {p['store_order_id']} is already in your collection")
        if not decisions:
            raise PurchaseError("nothing to assign")
        needs: dict[tuple[str, str], int] = {}
        for d in decisions:
            ln = lines.get(d.line_no)
            if ln is None:
                raise PurchaseError(f"no line {d.line_no} on this order")
            if not ln["scryfall_id"]:
                raise PurchaseError(f"line {d.line_no} ({ln['name']}) has no known printing")
            left = ln["quantity"] - ln["matched"] - ln["added"]
            if d.match + d.add > left:
                raise PurchaseError(f"line {d.line_no} ({ln['name']}): only {left} left to assign")
            if d.match:
                k = (ln["scryfall_id"], ln["finish"])
                needs[k] = needs.get(k, 0) + d.match
        sources = _matchable_sources(conn, {k[0] for k in needs})
        avail: dict[tuple[str, str], int] = {}
        for _iid, bal in sources:
            for k, n in bal.items():
                avail[k] = avail.get(k, 0) + n
        short = [k for k, n in needs.items() if n > avail.get(k, 0)]
        if short:
            raise PurchaseError(f"{len(short)} line(s) ask to match more copies than you own unassigned")

        ingest_id = p["ingest_id"]
        if ingest_id is None:
            label = f"purchase:{p['store']}:{p['store_order_id']}"
            ingest_id = ingest_mod.create_event(conn, "purchase", label=label, source_path=label, mode="purchase",
                                                at=p["ordered_at"], notes=f"{STORES[p['store']]} order {p['store_order_id']}")
            conn.execute("UPDATE purchases SET ingest_id = ? WHERE purchase_id = ?", (ingest_id, purchase_id))
        moved = ingest_mod.reattribute(conn, to_ingest_id=ingest_id, needs=needs, sources=sources) if needs else 0
        if moved != sum(needs.values()):
            raise RuntimeError("could not match every requested copy; nothing was changed")
        added = 0
        for d in decisions:
            ln = lines[d.line_no]
            if d.add:
                inventory_mod.inventory_add(ln["scryfall_id"], ln["finish"], d.add, conn=conn, ingest_id=ingest_id)
                added += d.add
            conn.execute("UPDATE purchase_lines SET matched = matched + ?, added = added + ? WHERE line_id = ?",
                         (d.match, d.add, ln["line_id"]))
        n_rows = conn.execute("SELECT COUNT(*) FROM (SELECT 1 FROM inventory_events WHERE ingest_id = ? "
                              "GROUP BY scryfall_id, finish)", (ingest_id,)).fetchone()[0]
        ingest_mod.finalize_event(conn, ingest_id, rows_added=n_rows)
        drift = ingest_mod.reconcile_inventory_ledger(conn)
        if drift:
            raise RuntimeError(f"ledger drift after applying the order ({len(drift)} rows); rolled back")
    return ApplyResult(purchase_id, ingest_id, moved, added)


def forget(purchase_id: int) -> None:
    """Delete a stored order you haven't assigned anything from (a mistaken read).
    Orders with ledger history are kept — undo is the way back for those."""
    with db.connect() as conn:
        p = _get(conn, purchase_id)
        if p["ingest_id"] is not None:
            raise PurchaseError("this order is already in your collection; use Undo to roll it back")
        conn.execute("DELETE FROM purchase_lines WHERE purchase_id = ?", (purchase_id,))
        conn.execute("DELETE FROM purchases WHERE purchase_id = ?", (purchase_id,))

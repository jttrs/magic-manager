"""purchases: store orders read by the companion → V34 purchases + the ledger."""
from __future__ import annotations

import pytest

from magic_manager import addcards, db, ingest, inventory, provenance, purchases
from magic_manager.purchases import Decision, Order, OrderLine

A = "00000000-0000-0000-0000-00000000000a"
B = "00000000-0000-0000-0000-00000000000b"
C = "00000000-0000-0000-0000-00000000000c"


@pytest.fixture
def cards(seed_cards, make_card, monkeypatch):
    seed_cards([
        make_card(id=A, name="Alpha", set="fin", collector_number="1", prices={"usd": "2.00", "usd_foil": "5.00"}),
        make_card(id=B, name="Beta", set="fin", collector_number="2", prices={"usd": "0.50"}),
        make_card(id=C, name="Gamma", set="tla", collector_number="9", prices={"usd": "1.00"}),
    ])
    monkeypatch.setattr(addcards, "ensure_printings", lambda ids: [])


def _event(method, label=None, status="success"):
    with db.connect() as conn:
        iid = ingest.create_event(conn, method, label=label)
        if status != "success":
            conn.execute("UPDATE ingest_events SET status = ? WHERE ingest_id = ?", (status, iid))
    return iid


def _order(order_id="637477", **kw):
    lines = kw.pop("lines", None) or [
        OrderLine(name="Alpha", quantity=2, unit_price=1.50, scryfall_id=A.upper(), condition="NM"),
        OrderLine(name="Beta", quantity=1, unit_price=0.25, finish="foil", set_code="FIN", collector_number="2"),
        OrderLine(name="Commander Decks Set of 4", quantity=1, unit_price=375.0, kind="sealed"),
        OrderLine(name="Mystery", quantity=1, unit_price=3.0, scryfall_id="not-a-uuid"),
    ]
    return Order(store="manapool", order_id=order_id, ordered_at="2026-09-23T11:07", lines=lines,
                 subtotal=494.28, shipping=2.70, tax=51.93, fees=23.85, credit=28.61, total=544.15, **kw)


def _qty(sid, finish):
    with db.connect() as conn:
        r = conn.execute("SELECT quantity FROM inventory WHERE scryfall_id = ? AND finish = ?", (sid, finish)).fetchone()
    return r[0] if r else 0


def _reconciled():
    with db.connect() as conn:
        return ingest.reconcile_inventory_ledger(conn) == []


def test_save_resolves_printings_and_dedupes(cards):
    r = purchases.save([_order()])
    assert len(r.saved) == 1 and r.unresolved == 1 and r.skipped == []
    (s,) = purchases.catalog()
    assert (s.store_name, s.order_id, s.ordered_at, s.status) == ("Mana Pool", "637477", "2026-09-23T11:07:00", "new")
    assert (s.lines, s.copies, s.assignable, s.unresolved) == (4, 5, 3, 1)
    assert (s.shipping_usd, s.tax_usd, s.fees_usd, s.credit_usd, s.total_usd) == (2.70, 51.93, 23.85, 28.61, 544.15)
    assert s.paid_usd == 3.0 + 0.25 + 375.0 + 3.0
    # Worth compares the same priced lines: 2 Alpha nonfoil @ $2 (Beta foil has no foil price).
    assert (s.worth_usd, s.compared_paid_usd, s.gain_usd) == (4.0, 3.0, 1.0)
    rv = purchases.review(s.purchase_id)
    assert [(ln.scryfall_id, ln.finish) for ln in rv.lines] == [(A, "nonfoil"), (B, "foil"), (None, "nonfoil"), (None, "nonfoil")]
    # Reading it again (not yet assigned) replaces it — still one order.
    purchases.save([_order()])
    assert len(purchases.catalog()) == 1
    assert purchases.known_orders("manapool") == {"637477": "new"}


def test_add_creates_copies_on_one_purchase_event(cards):
    pid = purchases.save([_order()]).saved[0]
    res = purchases.apply(pid, [Decision(1, add=2), Decision(2, add=1)])
    assert (res.matched, res.added) == (0, 3)
    with db.connect() as conn:
        ev = conn.execute("SELECT method, at, label FROM ingest_events WHERE ingest_id = ?", (res.ingest_id,)).fetchone()
    assert tuple(ev) == ("purchase", "2026-09-23T11:07:00", "purchase:manapool:637477")
    assert _qty(A, "nonfoil") == 2
    assert _reconciled()
    (s,) = purchases.catalog()
    assert (s.status, s.assigned, s.ingest_id) == ("done", 3, res.ingest_id)
    # Fully assigned → refused; and re-reading it is skipped, never re-added.
    with pytest.raises(purchases.AlreadyApplied):
        purchases.apply(pid, [Decision(1, add=1)])
    assert purchases.save([_order()]).skipped == ["637477"]
    assert _qty(A, "nonfoil") == 2


def test_match_reattributes_owned_copies_net_zero(cards):
    unknown = _event("unattributed-backfill", "backfill:unattributed", status="backfill")
    inventory.inventory_add(A, "nonfoil", 1, ingest_id=unknown)
    singles = _event("checklist", "set:fin")
    inventory.inventory_add(A, "nonfoil", 2, ingest_id=singles)
    product = _event("precon", "precon:Goblins_FDN")
    inventory.inventory_add(A, "nonfoil", 5, ingest_id=product)     # a product's copies are never matched
    pid = purchases.save([_order()]).saved[0]
    rv = {ln.line_no: ln for ln in purchases.review(pid).lines}
    assert (rv[1].owned, rv[1].matchable, rv[1].remaining) == (8, 3, 2)

    res = purchases.apply(pid, [Decision(1, match=2)])
    assert (res.matched, res.added) == (2, 0)
    assert _qty(A, "nonfoil") == 8      # counts unchanged
    assert _reconciled()
    src = {cs.source.key: cs.copies for cs in provenance.card_sources([A])[A]}
    # The unknown bucket is drawn first, then singles.
    assert src == {"purchase:manapool:637477": 2, "singles": 1, "product:Goblins_FDN": 5}
    assert (purchases.catalog()[0].status) == "partial"

    # Asking to match more than is left unassigned refuses, all-or-nothing.
    with pytest.raises(purchases.PurchaseError):
        purchases.apply(pid, [Decision(2, add=1), Decision(1, match=0, add=1), Decision(4, add=1)])
    assert _qty(B, "foil") == 0


def test_apply_validates(cards):
    pid = purchases.save([_order()]).saved[0]
    for bad in ([Decision(1, add=3)], [Decision(3, add=1)], [Decision(9, add=1)],
                [Decision(1, match=1)], [Decision(1, add=1), Decision(1, add=1)], []):
        with pytest.raises(purchases.PurchaseError):
            purchases.apply(pid, bad)
    with pytest.raises(LookupError):
        purchases.apply(999, [Decision(1, add=1)])
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM ingest_events WHERE method = 'purchase'").fetchone()[0] == 0


def test_history_shows_purchase_with_paid(cards):
    pid = purchases.save([_order()]).saved[0]
    purchases.apply(pid, [Decision(1, add=2)])
    (e,) = [h for h in provenance.history().entries if h.kind == "purchase"]
    assert (e.title, e.purchase_id, e.held, e.value_usd, e.paid_usd) == ("Mana Pool order #637477", pid, 2, 4.0, 3.0)
    entry, lines = provenance.history_event(e.ingest_id)
    assert entry.paid_usd == 3.0 and lines[0].held == 2


def test_rejects_bad_orders(cards):
    with pytest.raises(purchases.PurchaseError):
        purchases.save([_order(order_id=" ")])
    with pytest.raises(purchases.PurchaseError):
        purchases.save([Order(store="ebay", order_id="1", ordered_at="2026-01-01", lines=[])])
    with pytest.raises(purchases.PurchaseError):
        purchases.save([Order(store="manapool", order_id="1", ordered_at="yesterday", lines=[])])


def test_removed_copy_is_not_matched_twice(cards):
    """A removal written before a match must not land on the order later, which
    would make the source look as if it still held the copy (retro review, #133)."""
    unknown = _event("unattributed-backfill", "backfill:unattributed", status="backfill")
    inventory.inventory_add(A, "nonfoil", 3, ingest_id=unknown)
    inventory.inventory_remove(A, "nonfoil", 1)
    alpha = lambda n: [OrderLine(name="Alpha", quantity=n, unit_price=1.0, scryfall_id=A)]  # noqa: E731
    one = purchases.save([_order("1", lines=alpha(2))]).saved[0]
    res = purchases.apply(one, [Decision(1, match=2)])
    two = purchases.save([_order("2", lines=alpha(1))]).saved[0]
    assert purchases.review(two).lines[0].matchable == 0
    with pytest.raises(purchases.PurchaseError):
        purchases.apply(two, [Decision(1, match=1)])
    with db.connect() as conn:
        held = provenance._held(conn, [A])
    assert held[(res.ingest_id, A, "nonfoil")] == 2 and held[(unknown, A, "nonfoil")] == 0
    assert _qty(A, "nonfoil") == 2 and _reconciled()


def test_held_draws_a_removal_from_copies_held_at_that_time(cards):
    first = _event("checklist", "set:fin")
    inventory.inventory_add(A, "nonfoil", 3, ingest_id=first)
    inventory.inventory_remove(A, "nonfoil", 1)
    later = _event("checklist", "set:fin")
    inventory.inventory_add(A, "nonfoil", 2, ingest_id=later)
    with db.connect() as conn:
        held = provenance._held(conn, [A])
    # The removed copy came from the first batch, not one acquired after it.
    assert (held[(first, A, "nonfoil")], held[(later, A, "nonfoil")]) == (2, 2)


def test_held_after_a_reattribution_from_a_raw_balance(cards):
    """Trueup draws raw per-event balances: moving 3 out of a source that holds 2
    (one was removed) leaves the target holding 2 and never touches another event."""
    other = _event("checklist", "set:tla")
    inventory.inventory_add(A, "nonfoil", 1, ingest_id=other)
    src = _event("unattributed-backfill", "backfill:unattributed", status="backfill")
    inventory.inventory_add(A, "nonfoil", 3, ingest_id=src)
    inventory.inventory_remove(A, "nonfoil", 1)
    with db.connect() as conn:
        to = ingest.create_event(conn, "precon", label="trueup:X")
        ingest.reattribute(conn, to_ingest_id=to, needs={(A, "nonfoil"): 3}, sources=[(src, {(A, "nonfoil"): 3})])
        held = provenance._held(conn, [A])
    assert (held[(other, A, "nonfoil")], held[(src, A, "nonfoil")], held[(to, A, "nonfoil")]) == (1, 0, 2)
    assert _reconciled()

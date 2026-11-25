"""purchases: store orders read by the companion → V34 purchases + the ledger."""
from __future__ import annotations

import pytest

from magic_manager import addcards, db, ingest, inventory, provenance, purchases
from magic_manager.purchases import Order, OrderLine

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


def test_add_to_collection_adds_every_single_on_one_purchase_event(cards):
    pid = purchases.save([_order()]).saved[0]
    res = purchases.add_to_collection(pid)
    assert res.added == 3          # 2 Alpha + 1 Beta foil; the sealed line and the unresolved line are not added
    with db.connect() as conn:
        ev = conn.execute("SELECT method, at, label FROM ingest_events WHERE ingest_id = ?", (res.ingest_id,)).fetchone()
    assert tuple(ev) == ("purchase", "2026-09-23T11:07:00", "purchase:manapool:637477")
    assert (_qty(A, "nonfoil"), _qty(B, "foil")) == (2, 1)
    assert _reconciled()
    (s,) = purchases.catalog()
    assert (s.status, s.assigned, s.ingest_id) == ("done", 3, res.ingest_id)
    # Fully added → refused; and re-reading it is skipped, never re-added.
    with pytest.raises(purchases.AlreadyApplied):
        purchases.add_to_collection(pid)
    assert purchases.save([_order()]).skipped == ["637477"]
    assert _qty(A, "nonfoil") == 2


def test_add_to_collection_never_touches_existing_copies(cards):
    inventory.inventory_add(A, "nonfoil", 4, ingest_id=_event("checklist", "set:fin"))
    pid = purchases.save([_order()]).saved[0]
    rv = {ln.line_no: ln for ln in purchases.review(pid).lines}
    assert (rv[1].owned, rv[1].remaining) == (4, 2)
    purchases.add_to_collection(pid)
    assert _qty(A, "nonfoil") == 6 and _reconciled()


def test_legacy_matched_copies_are_not_added_again(cards):
    pid = purchases.save([_order()]).saved[0]
    with db.connect() as conn:
        conn.execute("UPDATE purchase_lines SET matched = 1 WHERE purchase_id = ? AND line_no = 1", (pid,))
    assert purchases.add_to_collection(pid).added == 2    # 1 Alpha left + 1 Beta foil
    assert _qty(A, "nonfoil") == 1


def test_add_to_collection_validates(cards):
    sealed = purchases.save([_order("5", lines=[OrderLine(name="Box", quantity=1, unit_price=9.0, kind="sealed")])]).saved[0]
    with pytest.raises(purchases.PurchaseError):
        purchases.add_to_collection(sealed)
    with pytest.raises(LookupError):
        purchases.add_to_collection(999)
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM ingest_events WHERE method = 'purchase'").fetchone()[0] == 0


def test_totals_compare_paid_to_the_whole_collection(cards):
    assert purchases.totals().orders == 0
    purchases.save([_order()])
    inventory.inventory_add(A, "nonfoil", 5, ingest_id=_event("checklist", "set:fin"))   # not from an order
    t = purchases.totals()
    assert (t.orders, t.paid_usd, t.singles_paid_usd, t.sealed_paid_usd) == (1, 381.25, 6.25, 375.0)
    assert t.other_paid_usd == 0.0
    assert (t.collection_value_usd, t.gain_usd) == (10.0, round(10.0 - 381.25, 2))


def test_history_shows_purchase_with_paid(cards):
    pid = purchases.save([_order()]).saved[0]
    purchases.add_to_collection(pid)
    (e,) = [h for h in provenance.history().entries if h.kind == "purchase"]
    assert (e.title, e.purchase_id, e.held, e.value_usd, e.paid_usd) == ("Mana Pool order #637477", pid, 3, 4.0, 3.25)
    entry, lines = provenance.history_event(e.ingest_id)
    assert entry.paid_usd == 3.25 and lines[0].held == 2


def test_rejects_bad_orders(cards):
    with pytest.raises(purchases.PurchaseError):
        purchases.save([_order(order_id=" ")])
    with pytest.raises(purchases.PurchaseError):
        purchases.save([Order(store="ebay", order_id="1", ordered_at="2026-01-01", lines=[])])
    with pytest.raises(purchases.PurchaseError):
        purchases.save([Order(store="manapool", order_id="1", ordered_at="yesterday", lines=[])])


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


def test_purchase_after_a_reattribution_from_a_raw_balance(cards):
    """The shortfall of a raw-balance re-attribution stays on its target, so a later
    purchase add holds its own copy and the apply guard doesn't roll it back."""
    src = _event("unattributed-backfill", "backfill:unattributed", status="backfill")
    inventory.inventory_add(A, "nonfoil", 3, ingest_id=src)
    inventory.inventory_remove(A, "nonfoil", 1)
    with db.connect() as conn:
        to = ingest.create_event(conn, "precon", label="trueup:X")
        ingest.reattribute(conn, to_ingest_id=to, needs={(A, "nonfoil"): 3}, sources=[(src, {(A, "nonfoil"): 3})])
    pid = purchases.save([_order("9", lines=[OrderLine(name="Alpha", quantity=1, unit_price=1.0, scryfall_id=A)])]).saved[0]
    res = purchases.add_to_collection(pid)
    with db.connect() as conn:
        held = provenance._held(conn, [A])
    assert (held[(to, A, "nonfoil")], held[(res.ingest_id, A, "nonfoil")]) == (2, 1)
    assert _qty(A, "nonfoil") == 3 and _reconciled()

"""provenance: where owned copies came from (V19 ledger) and where they are now."""
from __future__ import annotations

from magic_manager import db, decks, ingest, inventory, provenance

A = "00000000-0000-0000-0000-00000000000a"
B = "00000000-0000-0000-0000-00000000000b"
A2 = "00000000-0000-0000-0000-0000000000a2"   # same oracle as A, other printing
ORACLE_A = "aaaaaaaa-0000-0000-0000-0000000000aa"


def _seed(seed_cards, make_card):
    seed_cards([
        make_card(id=A, oracle_id=ORACLE_A, name="Alpha", set="fin", collector_number="1"),
        make_card(id=A2, oracle_id=ORACLE_A, name="Alpha", set="fin", collector_number="301"),
        make_card(id=B, oracle_id="bbbbbbbb-0000-0000-0000-0000000000bb", name="Beta", set="fin", collector_number="2"),
    ])


def _event(method, label=None, source_path=None, status="success"):
    with db.connect() as conn:
        iid = ingest.create_event(conn, method, label=label, source_path=source_path)
        if status != "success":
            conn.execute("UPDATE ingest_events SET status = ? WHERE ingest_id = ?", (status, iid))
        conn.commit()
    return iid


def test_classify_products_singles_and_unknown():
    products = {"CampComrades_FIN": ("pool", "Camp Comrades")}
    got = lambda *a: provenance._classify(*a, products)  # noqa: E731
    camp = got("precon", "trueup:CampComrades_FIN", None)
    assert (camp.key, camp.kind, camp.label, camp.set_code) == ("product:CampComrades_FIN", "pool", "Camp Comrades", "fin")
    assert got("checklist", "checklist:fin", None).key == "singles"
    assert got("precon", "backfill:precon", None).key == "unknown"
    # A product with no deck row falls back to a prettified fileName.
    mystery = got("precon", "precon:Mystery_XYZ", "Mystery_XYZ")
    assert (mystery.kind, mystery.label, mystery.set_code) == ("deck", "Mystery (XYZ)", "xyz")


def test_reattribution_moves_copies_between_events(seed_cards, make_card):
    _seed(seed_cards, make_card)
    backfill = _event("unattributed-backfill", "backfill:unattributed", status="backfill")
    inventory.inventory_add(A, "nonfoil", 3, ingest_id=backfill)
    product = _event("precon", "trueup:CampComrades_FIN")
    with db.connect() as conn:
        ingest.reattribute(conn, to_ingest_id=product, needs={(A, "nonfoil"): 2},
                           sources=[(backfill, {(A, "nonfoil"): 3})])
        conn.commit()
        held = provenance._held(conn, [A])
    assert (held[(product, A, "nonfoil")], held[(backfill, A, "nonfoil")]) == (2, 1)


def test_a_removal_only_draws_on_copies_acquired_before_it(seed_cards, make_card):
    _seed(seed_cards, make_card)
    inventory.inventory_add(A, "nonfoil", 1, ingest_id=_event("precon", "precon:Goblins_FDN", "Goblins_FDN"))
    inventory.inventory_remove(A, "nonfoil", 1)          # the precon copy leaves…
    inventory.inventory_add(A, "nonfoil", 1)             # …and a single is bought later
    held = {e.title: e.held for e in provenance.history().entries if e.held}
    assert held == {"Added by hand": 1}                  # purchase history agrees


def test_holdings_per_finish_pledges_and_other_printings(seed_cards, make_card):
    _seed(seed_cards, make_card)
    inventory.inventory_add(A, "nonfoil", 3)
    inventory.inventory_add(A, "foil", 1)
    inventory.inventory_add(A2, "nonfoil", 2)
    d = decks.deck_create("atraxa", "Atraxa")
    with db.connect() as conn:
        conn.execute("INSERT INTO deck_assignments (deck_id, scryfall_id, finish, count, assigned_at) "
                     "VALUES (?, ?, 'nonfoil', 2, '2026-01-01')", (d.deck_id, A))
        conn.commit()

    h = provenance.card_holdings(A)
    assert h.owned == {"nonfoil": 3, "foil": 1}
    assert h.pledged == {"nonfoil": 2}
    assert h.free == {"nonfoil": 1, "foil": 1}
    assert [(p.slug, p.finish, p.count) for p in h.decks] == [("atraxa", "nonfoil", 2)]
    assert h.other_printings_owned == 2

    none = provenance.card_holdings(B)
    assert none.owned == {} and none.other_printings_owned == 0


def test_api_holdings_endpoint(seed_cards, make_card, monkeypatch):
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app

    _seed(seed_cards, make_card)
    decks.deck_create("camp", "Camp Comrades", source_precon_file_name="CampComrades_FIN", kind="pool")
    inventory.inventory_add(A, "nonfoil", 2, ingest_id=_event("precon", "trueup:CampComrades_FIN"))
    client = TestClient(create_app(serve_frontend=False))

    r = client.get(f"/api/cards/{A}/holdings")
    assert r.status_code == 200
    body = r.json()
    assert body["owned"] == {"nonfoil": 2}
    assert "sources" not in body and body["other_printings_owned"] == 0

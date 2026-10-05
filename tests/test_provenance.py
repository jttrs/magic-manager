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


def test_sources_classify_products_singles_and_unknown(seed_cards, make_card):
    _seed(seed_cards, make_card)
    decks.deck_create("camp", "Camp Comrades", source_precon_file_name="CampComrades_FIN",
                      precon_state="deconstructed", kind="pool")
    decks.deck_create("goblins", "Goblins", source_precon_file_name="Goblins_FDN", kind="deck")
    inventory.inventory_add(A, "nonfoil", 2, ingest_id=_event("precon", "trueup:CampComrades_FIN"))
    inventory.inventory_add(A, "nonfoil", 1, ingest_id=_event("precon", "precon:Goblins_FDN", "Goblins_FDN"))
    inventory.inventory_add(A, "foil", 1, ingest_id=_event("checklist", "checklist:fin"))
    inventory.inventory_add(A, "nonfoil", 1, ingest_id=_event("precon", "backfill:precon", status="backfill"))
    inventory.inventory_add(B, "nonfoil", 1, ingest_id=_event("precon", "precon:Mystery_XYZ", "Mystery_XYZ"))

    got = provenance.card_sources([A, B])
    a = {(cs.source.key, cs.finish): (cs.source.kind, cs.source.label, cs.copies) for cs in got[A]}
    assert a == {
        ("product:CampComrades_FIN", "nonfoil"): ("pool", "Camp Comrades", 2),
        ("product:Goblins_FDN", "nonfoil"): ("deck", "Goblins", 1),
        ("singles", "foil"): ("singles", "Singles", 1),
        ("unknown", "nonfoil"): ("unknown", "Unknown origin", 1),
    }
    assert got[A][0].source.set_code == "fin"          # largest balance first
    # A product with no deck row falls back to a prettified fileName.
    (b,) = got[B]
    assert (b.source.kind, b.source.label, b.source.set_code) == ("deck", "Mystery (XYZ)", "xyz")


def test_reattribution_moves_copies_between_sources(seed_cards, make_card):
    _seed(seed_cards, make_card)
    backfill = _event("unattributed-backfill", "backfill:unattributed", status="backfill")
    inventory.inventory_add(A, "nonfoil", 3, ingest_id=backfill)
    product = _event("precon", "trueup:CampComrades_FIN")
    with db.connect() as conn:
        ingest.reattribute(conn, to_ingest_id=product, needs={(A, "nonfoil"): 2},
                           sources=[(backfill, {(A, "nonfoil"): 3})])
        conn.commit()
    got = {cs.source.key: cs.copies for cs in provenance.card_sources([A])[A]}
    assert got == {"product:CampComrades_FIN": 2, "unknown": 1}


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
    assert {cs.source.key for cs in h.sources} == {"singles"}   # ad-hoc adds count as singles
    assert h.other_printings_owned == 2

    none = provenance.card_holdings(B)
    assert none.owned == {} and none.sources == [] and none.other_printings_owned == 0


def test_api_collection_sources_and_holdings_endpoint(seed_cards, make_card, monkeypatch):
    from fastapi.testclient import TestClient
    from magic_manager.api import collection as collection_api
    from magic_manager.web.app import create_app

    _seed(seed_cards, make_card)
    decks.deck_create("camp", "Camp Comrades", source_precon_file_name="CampComrades_FIN", kind="pool")
    inventory.inventory_add(A, "nonfoil", 2, ingest_id=_event("precon", "trueup:CampComrades_FIN"))
    client = TestClient(create_app(serve_frontend=False))

    r = client.get(f"/api/cards/{A}/holdings")
    assert r.status_code == 200
    body = r.json()
    assert body["owned"] == {"nonfoil": 2}
    assert body["sources"][0]["source"] == {"key": "product:CampComrades_FIN", "kind": "pool",
                                            "label": "Camp Comrades", "set_code": "fin", "printings": 0}

    # family_view attaches source keys + a per-view catalog (engine stubbed to the seeded cards).
    from magic_manager import collection_view

    class _FC:
        summary = type("S", (), {})()
    fc = _FC()
    fc.summary.__dict__.update(code="fin", name="Final Fantasy", printings=2, owned_printings=1, owned_copies=2,
                               owned_usd=0.0, missing_printings=1, missing_usd=0.0, sets=[])

    def _card(sid, owned):
        return collection_view.CollectionCard(
            scryfall_id=sid, oracle_id=None, name="x", family="fin", set_code="fin", collector_number="1",
            rarity="rare", type_line=None, cmc=None, color_identity=[], released_at=None, finishes=["nonfoil"],
            owned=owned, pledged={}, price_usd=None, price_usd_foil=None, image_uri=None, scryfall_uri=None,
            treatment="", standard_frame=True, is_bulk=False, is_chase=False, is_token=False)
    fc.cards = [_card(A, {"nonfoil": 2}), _card(B, {})]
    monkeypatch.setattr(collection_view, "family_cards", lambda code: fc)
    out = collection_api.family_view(["fin"])
    assert {c.scryfall_id: c.sources for c in out.cards} == {A: ["product:CampComrades_FIN"], B: []}
    assert [(s.key, s.kind, s.printings) for s in out.sources] == [("product:CampComrades_FIN", "pool", 1)]

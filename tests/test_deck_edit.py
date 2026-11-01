"""deck_edit: build / break down, copy, new deck, versioned save with pledge rebalance."""
from __future__ import annotations

import pytest

from magic_manager import db, deck_edit, decks, inventory
from magic_manager.deck_edit import DraftCard

A, B, C = (f"00000000-0000-0000-0000-00000000000{x}" for x in "abc")


@pytest.fixture
def cards(seed_cards, make_card):
    seed_cards([make_card(id=s, oracle_id=f"aaaaaaaa-0000-0000-0000-00000000000{s[-1]}", name=n, collector_number=str(i))
                for i, (s, n) in enumerate([(A, "Alpha"), (B, "Beta"), (C, "Gamma")], 1)])


def _pledged(slug):
    with db.connect() as conn:
        return {(r[0], r[1]): r[2] for r in conn.execute(
            "SELECT a.scryfall_id, a.finish, a.count FROM deck_assignments a JOIN decks d USING(deck_id) WHERE d.slug = ?", (slug,))}


def _state(slug):
    with db.connect() as conn:
        return conn.execute("SELECT precon_state FROM decks WHERE slug = ?", (slug,)).fetchone()[0]


def _cards(slug):
    return sorted((r.scryfall_id, r.board, r.finish, r.count) for r in decks.deck_show(slug))


def test_create_copy_build_and_break_down(cards):
    inventory.inventory_add(A, "nonfoil", 2)
    inventory.inventory_add(B, "foil", 1)
    slug = deck_edit.create_deck("My Brew", commander=A)
    assert slug == "my-brew" and _state(slug) == "deconstructed"
    decks.deck_add_card(slug, B, "main", "either", 1)
    decks.deck_add_card(slug, C, "main", "nonfoil", 1)

    plan = deck_edit.build_plan(slug)
    assert (plan["target"], plan["need"], plan["covered"]) == (slug, 3, 2)
    assert [(s["scryfall_id"], s["qty"]) for s in plan["short"]] == [(C, 1)]
    with pytest.raises(deck_edit.Shortfall):
        deck_edit.build(slug)
    r = deck_edit.build(slug, allow_shortfall=True)
    assert r["sleeved"] == 2 and _state(slug) == "built"
    assert _pledged(slug) == {(A, "nonfoil"): 1, (B, "foil"): 1}      # 'either' fell back to the free foil

    copy = deck_edit.copy_recipe(slug)
    assert copy == "my-brew-copy" and _cards(copy) == _cards(slug) and _pledged(copy) == {}
    assert deck_edit.is_editable(copy)

    out = deck_edit.break_down(slug)
    assert out["pulled"] == 2 and _pledged(slug) == {} and _state(slug) == "deconstructed"
    with pytest.raises(ValueError):
        deck_edit.break_down(slug)


def test_save_cuts_a_version_and_rebalances_a_built_deck(cards):
    inventory.inventory_add(A, "nonfoil", 1)
    inventory.inventory_add(B, "nonfoil", 2)
    inventory.inventory_add(C, "nonfoil", 1)
    slug = deck_edit.create_deck("Tuned")
    decks.deck_add_card(slug, A, "main", "nonfoil", 1)
    decks.deck_add_card(slug, B, "main", "nonfoil", 1)
    deck_edit.build(slug)
    with db.connect() as conn:
        v1 = conn.execute("SELECT current_version_id FROM decks WHERE slug = ?", (slug,)).fetchone()[0]

    draft = [DraftCard(B, "main", "nonfoil", 2), DraftCard(C, "main", "nonfoil", 1), DraftCard(A, "maybe", "nonfoil", 1)]
    pv = deck_edit.preview(slug, draft)
    assert pv["built"]
    assert {(s["scryfall_id"], s["qty"]) for s in pv["swap"]["pull"]} == {(A, 1)}
    assert {(s["scryfall_id"], s["qty"]) for s in pv["swap"]["sleeve"]} == {(B, 1), (C, 1)}
    assert pv["swap"]["short"] == []

    r = deck_edit.save(slug, draft, expected_version_id=v1, name="Tuned v2")
    assert r["version_number"] == 2 and r["pulled"] == 1 and r["sleeved"] == 2
    assert _pledged(slug) == {(B, "nonfoil"): 2, (C, "nonfoil"): 1}
    assert _cards(slug) == sorted([(B, "main", "nonfoil", 2), (C, "main", "nonfoil", 1), (A, "maybe", "nonfoil", 1)])
    assert [v.version_number for v in decks.version_list(slug)] == [1, 2]

    with pytest.raises(deck_edit.StaleDraft):
        deck_edit.save(slug, draft, expected_version_id=v1)


def test_precons_are_read_only(cards):
    decks.deck_create("goblins", "Goblins", source_precon_file_name="Goblins_FDN")
    decks.deck_add_card("goblins", A, "main", "nonfoil", 1)
    with db.connect() as conn:
        vid = conn.execute("SELECT current_version_id FROM decks WHERE slug = 'goblins'").fetchone()[0]
    assert not deck_edit.is_editable("goblins")
    with pytest.raises(deck_edit.ReadOnlyDeck):
        deck_edit.save("goblins", [], expected_version_id=vid)
    copy = deck_edit.copy_recipe("goblins", name="Goblins Remix")
    assert copy == "goblins-remix" and deck_edit.is_editable(copy)


def test_api_routes(cards):
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app

    inventory.inventory_add(A, "nonfoil", 1)
    client = TestClient(create_app(serve_frontend=False))
    r = client.post("/api/decks", json={"name": "Api Deck", "commander": A})
    assert r.status_code == 201 and r.json()["slug"] == "api-deck"
    d = client.get("/api/decks/api-deck").json()
    assert d["editable"] is True and d["version_id"]
    r = client.put("/api/decks/api-deck", json={"cards": [], "expected_version_id": d["version_id"] + 99})
    assert r.status_code == 409
    r = client.post("/api/decks/api-deck/build", json={})
    assert r.status_code == 200 and "1 card pledged" in r.json()["summary"]
    assert client.post("/api/decks/nope/break-down").status_code == 404


def test_imports_are_recipes_and_built_follows_pledges(cards, make_card, monkeypatch):
    from magic_manager import decksource

    payload = {"source": "archidekt", "id": "42", "name": "Imported Brew", "author": "me",
               "cards": [{"qty": 1, "name": "Alpha", "scryfall_id": A, "board": "main", "finish": "nonfoil"}]}
    raw = make_card(id=A, oracle_id="aaaaaaaa-0000-0000-0000-00000000000a", name="Alpha", collector_number="1")
    monkeypatch.setattr(decksource, "_resolve_cards", lambda cs: ({A: raw}, {}, {}, []))
    r = deck_edit.import_payload(payload)
    assert r == {"slug": "imported-brew", "duplicate": False, "created": True, "not_found": 0}
    assert _state("imported-brew") == "deconstructed"                       # a recipe, not built
    again = deck_edit.import_payload(payload)
    assert again["duplicate"] and again["slug"] == "imported-brew"         # no second copy

    # Adding the recipe's cards to the collection does NOT build it.
    out = deck_edit.add_recipe_to_collection("imported-brew")
    assert out["copies"] == 1 and _state("imported-brew") == "deconstructed"
    with db.connect() as conn:
        assert conn.execute("SELECT quantity FROM inventory WHERE scryfall_id = ?", (A,)).fetchone()[0] == 1
    # Pledging marks it built; unpledging everything marks it not built.
    decks.deck_assign_batch("imported-brew", [(A, "nonfoil", 1)])
    assert _state("imported-brew") == "built"
    decks.deck_unassign_batch("imported-brew", "all")
    assert _state("imported-brew") == "deconstructed"


def test_backfill_built_state_only_fixes_unpledged_non_precons(cards):
    inventory.inventory_add(A, "nonfoil", 1)
    decks.deck_create("old-import", "Old import")                         # legacy default: built, nothing pledged
    decks.deck_create("pledged", "Pledged")
    decks.deck_add_card("pledged", A, "main", "nonfoil", 1)
    decks.deck_assign_batch("pledged", [(A, "nonfoil", 1)])
    decks.deck_create("precon", "Precon", source_precon_file_name="X_TST")   # precons untouched
    assert decks.unpledged_built_count() == 1
    decks.deck_create("precon-2", "Precon", source_precon_file_name="X_TST")    # a second built copy, nothing pledged
    decks.deck_create("precon-3", "Precon", source_precon_file_name="X_TST", precon_state="deconstructed")
    assert decks.extra_built_precon_count() == 1
    assert decks.backfill_built_state() == {"corrected": 1, "precon_extras": 1}
    assert (_state("old-import"), _state("pledged"), _state("precon"), _state("precon-2"), _state("precon-3")) == (
        "deconstructed", "built", "built", "deconstructed", "deconstructed")   # one built copy per precon
    assert decks.backfill_built_state() == {"corrected": 0, "precon_extras": 0}   # idempotent


def test_check_reports_legality_and_bracket_floor(cards, monkeypatch):
    slug = deck_edit.create_deck("Checked")
    with db.connect() as conn:
        conn.execute("UPDATE cards SET game_changer = 1, legalities = ? WHERE scryfall_id = ?",
                     ('{"commander": "legal"}', B))
        conn.execute("UPDATE cards SET legalities = ? WHERE scryfall_id IN (?, ?)", ('{"commander": "legal"}', A, C))
        conn.execute("UPDATE cards SET type_line = 'Legendary Creature — Elf' WHERE scryfall_id = ?", (A,))
        conn.commit()
    r = deck_edit.check(slug, [DraftCard(A, "commander", "nonfoil", 1), DraftCard(B, "main", "nonfoil", 1)])
    assert r["format"] == "commander"
    assert r["legality"]["legal"] is False                                 # 2 of 100 cards
    assert r["bracket"]["game_changers"] == ["Beta"] and r["bracket"]["suggested_bracket"] >= 3


def test_backfill_built_state_keeps_the_pledged_precon_copy_built(cards):
    inventory.inventory_add(A, "nonfoil", 1)
    decks.deck_create("precon", "Precon", source_precon_file_name="X_TST")       # lowest id, nothing pledged
    decks.deck_create("precon-2", "Precon", source_precon_file_name="X_TST")     # really assembled
    decks.deck_add_card("precon-2", A, "main", "nonfoil", 1)
    decks.deck_assign_batch("precon-2", [(A, "nonfoil", 1)])
    with db.connect() as conn:
        first = conn.execute("SELECT deck_id FROM decks WHERE slug = 'precon'").fetchone()[0]
    assert decks.built_state_correction_ids() == {first}
    assert decks.backfill_built_state() == {"corrected": 0, "precon_extras": 1}
    assert (_state("precon"), _state("precon-2")) == ("deconstructed", "built")


# ---------- retro-review fixes (PR88-2/3/4, PR89-1/8/9, PR88-7/8) ----------

def _vid(slug):
    with db.connect() as conn:
        return conn.execute("SELECT current_version_id FROM decks WHERE slug = ?", (slug,)).fetchone()[0]


def test_either_slot_splits_across_finishes_and_shares_free():
    free = {(A, "nonfoil"): 2, (A, "foil"): 1}
    assert deck_edit._needs([DraftCard(A, "main", "either", 3)], {}, free) == {(A, "nonfoil"): 2, (A, "foil"): 1}
    # Two 'either' rows of one printing share the free pool (no double count).
    two = [DraftCard(A, "main", "either", 2), DraftCard(A, "side", "either", 1)]
    assert deck_edit._needs(two, {}, free) == {(A, "nonfoil"): 2, (A, "foil"): 1}
    # An exact-finish row later in the list still claims its copies first.
    mixed = [DraftCard(A, "main", "either", 2), DraftCard(A, "side", "nonfoil", 1)]
    assert deck_edit._needs(mixed, {}, free) == {(A, "nonfoil"): 2, (A, "foil"): 1}
    # Excess beyond free lands on nonfoil (short).
    assert deck_edit._needs([DraftCard(A, "main", "either", 5)], {}, free) == {(A, "nonfoil"): 4, (A, "foil"): 1}
    # Already-pledged copies are kept before free ones are taken.
    assert deck_edit._needs([DraftCard(A, "main", "either", 2)], {(A, "foil"): 1}, free) == {(A, "foil"): 1, (A, "nonfoil"): 1}


def test_needs_is_the_shared_resolve_needs_rule():
    """deck_edit._needs delegates to decks.resolve_needs (the rule compose shares):
    a representative split — exact row, 'either' across pledged + free, a token
    keeping its pledge, excess landing on nonfoil — resolves identically."""
    free = {(A, "nonfoil"): 1, (A, "foil"): 2, (B, "nonfoil"): 0, (B, "foil"): 0}
    pledged = {(A, "foil"): 1, (B, "nonfoil"): 1, (C, "foil"): 1}
    cards_ = [DraftCard(A, "main", "either", 3), DraftCard(A, "side", "foil", 1),
              DraftCard(B, "main", "either", 2), DraftCard(C, "token", "either", 1)]
    expect = {(A, "foil"): 3, (A, "nonfoil"): 1, (B, "nonfoil"): 2, (C, "foil"): 1}   # output of the pre-lift _needs
    assert deck_edit._needs(cards_, pledged, free) == expect
    assert decks.resolve_needs(cards_, pledged, free) == expect
    # `order` only changes which finish is tried first / takes the excess.
    assert decks.resolve_needs([DraftCard(B, "main", "either", 2)], {}, free,
                               order=("foil", "nonfoil")) == {(B, "foil"): 2}


def test_build_either_split_has_no_false_shortfall(cards):
    inventory.inventory_add(A, "nonfoil", 2)
    inventory.inventory_add(A, "foil", 1)
    slug = deck_edit.create_deck("Split")
    decks.deck_add_card(slug, A, "main", "either", 3)
    assert deck_edit.build_plan(slug)["short"] == []
    r = deck_edit.build(slug)
    assert r["sleeved"] == 3 and _pledged(slug) == {(A, "nonfoil"): 2, (A, "foil"): 1}
    assert deck_edit.build_target(slug) is None


def test_maybeboard_does_not_keep_a_built_deck_incomplete(cards):
    from magic_manager import deck_view

    inventory.inventory_add(A, "nonfoil", 1)
    slug = deck_edit.create_deck("Maybe")
    decks.deck_add_card(slug, A, "main", "nonfoil", 1)
    decks.deck_add_card(slug, B, "maybe", "nonfoil", 2)
    deck_edit.build(slug)
    assert deck_edit.build_target(slug) is None
    assert deck_edit.build_plan(slug)["target"] is None
    with pytest.raises(ValueError):
        deck_edit.build(slug)
    summary = next(s for s in deck_view._summaries() if s["slug"] == slug)
    assert summary["pledged_pct"] == 100.0


def test_save_keeps_tokens_and_their_pledges(cards, make_card, seed_cards):
    T = "00000000-0000-0000-0000-00000000000f"
    seed_cards([make_card(id=T, oracle_id="aaaaaaaa-0000-0000-0000-00000000000f", name="Soldier", collector_number="9")])
    inventory.inventory_add(A, "nonfoil", 2)
    inventory.inventory_add(T, "nonfoil", 1)
    slug = deck_edit.create_deck("Tokens")
    decks.deck_add_card(slug, A, "main", "nonfoil", 1)
    decks.deck_add_card(slug, T, "token", "nonfoil", 1)
    deck_edit.build(slug)
    # A token pledged by hand (e.g. CLI) must survive a save of the built copy.
    with db.connect() as conn:
        did = conn.execute("SELECT deck_id FROM decks WHERE slug = ?", (slug,)).fetchone()[0]
        conn.execute("INSERT INTO deck_assignments (deck_id, scryfall_id, finish, count, assigned_at) "
                     "VALUES (?, ?, 'nonfoil', 1, 'x')", (did, T))
    draft = [DraftCard(A, "main", "nonfoil", 2)]                    # the editor never sends the token board
    pv = deck_edit.preview(slug, draft)
    assert [c["scryfall_id"] for c in pv["changes"]] == [A] and pv["swap"]["pull"] == []
    deck_edit.save(slug, draft, expected_version_id=_vid(slug))
    assert (T, "token", "nonfoil", 1) in _cards(slug)
    assert _pledged(slug) == {(A, "nonfoil"): 2, (T, "nonfoil"): 1}
    # A rename-only save with no token rows is a no-op for the cards.
    r = deck_edit.save(slug, draft, expected_version_id=_vid(slug), name="Tokens!")
    assert r["version_number"] is None and r["changes"] == []


def test_built_follows_pledges_on_pull_and_empty_build(cards):
    inventory.inventory_add(A, "nonfoil", 1)
    slug = deck_edit.create_deck("Emptied")
    decks.deck_add_card(slug, A, "main", "nonfoil", 1)
    deck_edit.build(slug)
    assert _state(slug) == "built"
    deck_edit.save(slug, [DraftCard(B, "main", "nonfoil", 1)], expected_version_id=_vid(slug))
    assert _pledged(slug) == {} and _state(slug) == "deconstructed"   # every pledge pulled → not built

    # A Build that can pledge nothing refuses even with allow_shortfall.
    other = deck_edit.create_deck("Nothing free")
    decks.deck_add_card(other, C, "main", "nonfoil", 1)
    with pytest.raises(deck_edit.Shortfall):
        deck_edit.build(other, allow_shortfall=True)
    assert _state(other) == "deconstructed"

    # The explicit-rows unassign also flips state when the last copy leaves.
    inventory.inventory_add(B, "nonfoil", 1)
    third = deck_edit.create_deck("Third")
    decks.deck_add_card(third, B, "main", "nonfoil", 1)
    deck_edit.build(third)
    decks.deck_unassign_batch(third, [(B, "nonfoil", 1)])
    assert _state(third) == "deconstructed"


def test_check_without_a_format(cards):
    decks.deck_create("imp", "Imported", precon_state="deconstructed")      # imports record no format
    r = deck_edit.check("imp", [DraftCard(A, "main", "nonfoil", 1)])
    assert r["format"] is None and r["bracket"] is None and r["legality"]["legal"] is True
    assert [v["code"] for v in r["legality"]["violations"]] == ["no_format"]
    r = deck_edit.check("imp", [DraftCard(A, "commander", "nonfoil", 1), DraftCard(B, "main", "nonfoil", 1)])
    assert r["format"] == "commander" and r["bracket"] is not None


def test_unique_slug_and_set_precon_state(cards):
    decks.deck_create("brew", "Brew")
    decks.deck_create("brew-3", "Brew 3")
    with db.connect() as conn:
        assert decks.unique_slug(conn, "brew") == "brew-2"
        assert decks.unique_slug(conn, "fresh") == "fresh"
    decks.set_precon_state("brew", "deconstructed")
    assert _state("brew") == "deconstructed"
    with pytest.raises(ValueError):
        decks.set_precon_state("brew", "melted")
    with pytest.raises(LookupError):
        decks.set_precon_state("nope", "built")


def test_check_and_import_routes(cards, make_card, monkeypatch):
    from fastapi.testclient import TestClient
    from magic_manager import decksource
    from magic_manager.web.app import create_app

    client = TestClient(create_app(serve_frontend=False))
    body = {"cards": [{"scryfall_id": A, "board": "commander", "finish": "nonfoil", "count": 1}]}
    assert client.post("/api/decks/nope/check", json=body).status_code == 404
    slug = deck_edit.create_deck("Routed")
    r = client.post(f"/api/decks/{slug}/check", json=body)
    assert r.status_code == 200 and r.json()["format"] == "commander" and r.json()["bracket"] is not None
    decks.deck_create("std", "Std", format="standard", precon_state="deconstructed")
    r = client.post("/api/decks/std/check", json={"cards": [{"scryfall_id": A, "board": "main", "finish": "nonfoil", "count": 1}]})
    assert r.status_code == 200 and r.json()["format"] == "standard" and r.json()["bracket"] is None
    decks.deck_create("nofmt", "No format", precon_state="deconstructed")
    r = client.post("/api/decks/nofmt/check", json={"cards": [{"scryfall_id": A, "board": "main", "finish": "nonfoil", "count": 1}]})
    assert r.status_code == 200 and r.json()["format"] is None

    raw = make_card(id=A, oracle_id="aaaaaaaa-0000-0000-0000-00000000000a", name="Alpha", collector_number="1")
    monkeypatch.setattr(decksource, "_resolve_cards", lambda cs: ({A: raw}, {}, {}, []))
    deck = {"source": "archidekt", "id": "7", "name": "Via Api", "author": None,
            "cards": [{"qty": 1, "name": "Alpha", "scryfall_id": A, "board": "main", "finish": "nonfoil"}]}
    r = client.post("/api/decks/import", json={"deck": deck})
    assert r.status_code == 200 and r.json() == {"slug": "via-api", "duplicate": False, "summary": "Decklist saved"}
    r = client.post("/api/decks/import", json={"deck": deck})
    assert r.status_code == 200 and r.json() == {"slug": "via-api", "duplicate": True, "summary": "Already in your decks"}
    assert client.post("/api/decks/import", json={"deck": {**deck, "id": "8", "cards": []}}).status_code == 422


def test_pledged_pct_counts_only_playable_pledges(cards):
    from magic_manager import deck_view

    inventory.inventory_add(A, "nonfoil", 1)
    inventory.inventory_add(B, "nonfoil", 3)
    slug = deck_edit.create_deck("Short")
    decks.deck_add_card(slug, A, "main", "nonfoil", 1)
    decks.deck_add_card(slug, C, "main", "nonfoil", 1)        # never free → the deck stays short
    decks.deck_add_card(slug, B, "maybe", "nonfoil", 3)
    decks.deck_assign_batch(slug, [(A, "nonfoil", 1), (B, "nonfoil", 3)])   # compose pledges maybe too
    summary = next(s for s in deck_view._summaries() if s["slug"] == slug)
    assert summary["pledged_pct"] == 50.0                       # 1 of 2 playable, maybe pledges ignored
    assert deck_edit.build_target(slug) == slug


def test_build_plan_flags_unbuildable_and_save_swap_stays_built(cards):
    slug = deck_edit.create_deck("Nothing free")
    decks.deck_add_card(slug, C, "main", "nonfoil", 2)
    plan = deck_edit.build_plan(slug)
    assert plan["buildable"] is False and plan["covered"] == 0

    inventory.inventory_add(A, "nonfoil", 1)
    inventory.inventory_add(B, "nonfoil", 1)
    built = deck_edit.create_deck("Swap all")
    decks.deck_add_card(built, A, "main", "nonfoil", 1)
    assert deck_edit.build_plan(built)["buildable"] is True
    deck_edit.build(built)
    # Every pledge is pulled and a free replacement sleeved in one save → still built.
    deck_edit.save(built, [DraftCard(B, "main", "nonfoil", 1)], expected_version_id=_vid(built))
    assert _pledged(built) == {(B, "nonfoil"): 1} and _state(built) == "built"

"""Foil gap (magic_manager.foil_gap), per-printing floors
(card_floor.printing_floors), and their Market / API surfaces — offline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from magic_manager import card_floor, decks, foil_gap, market, scryfall

ROOT = Path(__file__).resolve().parent.parent
A, A_CHEAP, B = "44444444-0000-0000-0000-000000000001", "44444444-0000-0000-0000-000000000002", "44444444-0000-0000-0000-000000000003"
OA, OB = "cccccccc-0000-0000-0000-000000000001", "cccccccc-0000-0000-0000-000000000002"


# ---------- foil_gap ----------

def test_foil_gap_buckets_in_fixed_precedence():
    both = ["nonfoil", "foil"]
    assert foil_gap.foil_gap(finishes=both, treatment="b|ff", nonfoil=1, foil=2).status == "fancy"
    assert foil_gap.foil_gap(finishes=["foil"], treatment="", nonfoil=None, foil=2).status == "foil_only"
    assert foil_gap.foil_gap(finishes=["nonfoil"], treatment="", nonfoil=1, foil=None).status == "nonfoil_only"
    assert foil_gap.foil_gap(finishes=both, treatment="", nonfoil=0, foil=2).status == "unpriced"
    assert foil_gap.foil_gap(finishes=both, treatment="", nonfoil=None, foil=2).status == "unpriced"
    g = foil_gap.foil_gap(finishes=both, treatment="b", nonfoil=2.0, foil=3.0)
    assert (g.status, g.pct, g.usd) == ("ok", 0.5, 1.0)


def test_foil_gap_keep_bounds_are_inclusive_and_percent():
    g = foil_gap.FoilGap("ok", 0.25, 0.5)
    assert foil_gap.keep(g, max_pct=25) and not foil_gap.keep(g, max_pct=24.9)
    assert foil_gap.keep(g, min_raw=0.5) and not foil_gap.keep(g, max_raw=0.49)
    assert not foil_gap.keep(foil_gap.FoilGap("ok", 1.2, 10), drop_expensive=(100, 10))
    assert foil_gap.keep(foil_gap.FoilGap("ok", 1.2, 9.99), drop_expensive=(100, 10))
    assert not foil_gap.keep(foil_gap.FoilGap("fancy"))


def test_foil_price_diff_script_ranks_through_the_engine(monkeypatch, capsys):
    """The script is a thin driver: same buckets/order/filter as the engine."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import foil_price_diff as script
    cards = [
        {"name": "Big", "set": "aaa", "collector_number": "1", "finishes": ["nonfoil", "foil"],
         "prices": {"usd": "1.00", "usd_foil": "5.00"}},
        {"name": "Small", "set": "aaa", "collector_number": "2", "finishes": ["nonfoil", "foil"],
         "prices": {"usd": "2.00", "usd_foil": "2.20"}},
        {"name": "Surge", "set": "aaa", "collector_number": "3", "finishes": ["nonfoil", "foil"],
         "promo_types": ["surgefoil"], "prices": {"usd": "1.00", "usd_foil": "9.00"}},
    ]
    monkeypatch.setattr(scryfall, "collection", lambda idents: (cards, []))
    monkeypatch.setattr(sys, "argv", ["foil_price_diff.py", "--max-pct", "100"])
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("1 Big (AAA) 1\n1 Small (AAA) 2\n1 Surge (AAA) 3\n"))
    assert script.main() == 0
    out, err = capsys.readouterr()
    assert "Ranked 1 cards" in err and "fancy-foil=1" in err and "filtered=1" in err
    assert "Small" in out and "+10.0%" in out and "Big" not in out


# ---------- printing_floors ----------

@pytest.fixture
def cards(tmp_db, seed_cards, make_card):
    seed_cards([
        make_card(id=A, oracle_id=OA, name="Skullclamp", set="fic", collector_number="1",
                  prices={"usd": "5.00", "usd_foil": "6.00"}),
        make_card(id=A_CHEAP, oracle_id=OA, name="Skullclamp", set="msc", collector_number="9",
                  prices={"usd": "2.00", "usd_foil": "8.00"}),
        make_card(id=B, oracle_id=OB, name="Sol Ring", set="fic", collector_number="2",
                  prices={"usd": "1.00", "usd_foil": None}),
    ])


def test_printing_floors_local_per_finish(cards):
    got = card_floor.printing_floors([A, B, "unknown"])
    assert set(got) == {A, B}
    assert (got[A].nonfoil.usd, got[A].nonfoil.set_code, got[A].nonfoil.scryfall_id) == (2.0, "msc", A_CHEAP)
    assert (got[A].foil.usd, got[A].foil.set_code) == (6.0, "fic")
    assert got[B].foil is None


def test_printing_floors_live_is_opt_in(cards, monkeypatch):
    calls = []

    def fake_search(q, **k):
        calls.append(q)
        return [{"id": "anywhere", "oracle_id": OA, "set": "sld", "collector_number": "7",
                 "prices": {"usd": "0.50", "usd_foil": None}}]
    monkeypatch.setattr(scryfall, "search", fake_search)
    card_floor.printing_floors([A])
    assert calls == []                                  # local by default
    got = card_floor.printing_floors([A], live=True)
    assert len(calls) == 1
    assert (got[A].nonfoil.usd, got[A].nonfoil.set_code, got[A].nonfoil.scryfall_id) == (0.5, "sld", "anywhere")


def test_deck_cost_live_uses_anywhere_floor(cards, monkeypatch):
    decks.deck_create("clamp", "Clamp")
    decks.deck_add_card("clamp", A, "main", "nonfoil", 1)
    monkeypatch.setattr(scryfall, "search", lambda q, **k: [
        {"id": "anywhere", "oracle_id": OA, "set": "sld", "collector_number": "7",
         "prices": {"usd": "0.50", "usd_foil": None}}])
    local = market.deck_cost("clamp", with_sealed=False)
    assert local["live"] is False and local["lines"][0]["floor_set_code"] == "msc"
    live = market.deck_cost("clamp", with_sealed=False, live=True)
    assert live["live"] is True and live["scratch_floor"] == 0.5
    assert live["lines"][0]["floor_scryfall_id"] == "anywhere"


def test_family_card_prices_carries_the_foil_gap(cards, monkeypatch):
    from types import SimpleNamespace as NS
    fc = NS(summary=NS(code="fic", name="FIC"), cards=[NS(
        scryfall_id=A, oracle_id=OA, name="Skullclamp", set_code="fic", collector_number="1",
        rarity="rare", type_line=None, finishes=["nonfoil", "foil"], treatment="", image_uri=None,
        is_chase=False, price_usd=5.0, price_usd_foil=6.0, owned_total=0)])
    monkeypatch.setattr(market.collection_view, "family_cards", lambda code: fc)
    row = market.family_card_prices("fic")["cards"][0]
    assert (row["foil_gap_status"], row["foil_gap_pct"], row["foil_gap_usd"]) == ("ok", 0.2, 1.0)


def test_card_floors_route(cards):
    from fastapi.testclient import TestClient
    from magic_manager.web.app import create_app
    client = TestClient(create_app())
    r = client.post("/api/cards/floors", json={"scryfall_ids": [A]})
    assert r.status_code == 200
    body = r.json()
    assert body["live"] is False
    assert body["floors"][0]["nonfoil"]["set_code"] == "msc"
    assert client.post("/api/cards/floors", json={"scryfall_ids": []}).status_code == 422

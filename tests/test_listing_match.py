"""listing_match + deals.compare — what a store listing is, and what it's worth.

Offline: Scryfall's set list, MTGJSON's products/decks, the Secret Lair drop
list and card lookups are stubbed with a small slice of the real catalog; the
titles are real store titles captured 2026-10-05.
"""
from __future__ import annotations

import pytest

from magic_manager import deals, listing_match as lm, mtgjson, scryfall, sld, valuation

SETS = [
    ("hob", "The Hobbit", "expansion"), ("fin", "Final Fantasy", "expansion"), ("fic", "Final Fantasy Commander", "commander"),
    ("sos", "Secrets of Strixhaven", "expansion"), ("stx", "Strixhaven: School of Mages", "expansion"),
    ("spm", "Marvel's Spider-Man", "expansion"), ("msh", "Marvel Super Heroes", "expansion"),
    ("scd", "Starter Commander Decks", "commander"), ("sld", "Secret Lair Drop", "box"), ("fdn", "Foundations", "core"),
    ("pfdn", "Foundations Promos", "promo"),
]
PRODUCTS = {
    "hob": ["The Hobbit Play Booster Box", "The Hobbit Play Booster Box Case", "The Hobbit Collector Booster Box", "The Hobbit Bundle", "The Hobbit Gift Bundle"],
    "fin": ["Final Fantasy Play Booster Box", "Final Fantasy Collector Booster Box", "Final Fantasy Collector Booster Box Case", "Final Fantasy Starter Kit"],
    "fic": ["Final Fantasy Commander Deck Counter Blitz", "Final Fantasy Commander Deck Counter Blitz Collectors Edition"],
    "sos": ["Secrets of Strixhaven Play Booster Box", "Secrets of Strixhaven Bundle", "Secrets of Strixhaven Commander Deck Lorehold Spirit",
            "Secrets of Strixhaven Commander Deck Prismari Flow"],
    "stx": ["Strixhaven School of Mages Draft Booster Box"],
    "spm": ["Marvels Spider Man Bundle", "Marvels Spider Man Play Booster Box"],
    "msh": ["Marvel Super Heroes Collector Booster Box"],
    "scd": ["Starter Commander Deck First Flight", "Starter Commander Decks Set of 5"],
    "sld": ["Secret Lair Drop God of War Norse", "Secret Lair Drop God of War Norse Foil"],
}
FAMILIES = {"fin": ["fic", "fin"], "fic": ["fic", "fin"]}


@pytest.fixture(autouse=True)
def catalog(monkeypatch, tmp_db, seed_cards, make_card):
    monkeypatch.setattr(scryfall, "all_sets", lambda: [{"code": c, "name": n, "set_type": t, "digital": False} for c, n, t in SETS])
    lm._set_names.cache_clear()
    lm._set_tails.cache_clear()
    monkeypatch.setattr(mtgjson, "sealed_products", lambda code: [{"name": n} for n in PRODUCTS.get(code, [])])
    monkeypatch.setattr(mtgjson, "deck_list", lambda **kw: [{"name": "First Flight", "code": "SCD"}])
    monkeypatch.setattr(lm, "_family", lambda code: FAMILIES.get(code, [code]))
    monkeypatch.setattr(sld, "all_drops", lambda: {n: {"name": n} for n in ("God of War: Norse", "Goblingram", "Uncharted")})
    monkeypatch.setattr(scryfall, "collection", lambda ids: ([], list(ids)))
    seed_cards([
        make_card(id="sos11", oracle_id="o-eager", set="sos", collector_number="11", name="Eager Glyphmage"),
        make_card(id="pfdn11p", oracle_id="o-ex", set="pfdn", collector_number="11p", name="Exemplar of Light", prices={"usd": "21.47", "usd_foil": None}),
        make_card(id="fdn297", oracle_id="o-ex", set="fdn", collector_number="297", name="Exemplar of Light", prices={"usd": "7.06", "usd_foil": None}),
        make_card(id="sld2296", oracle_id="o-melt", set="sld", collector_number="2296", name="Meltdown", prices={"usd": "6.41", "usd_foil": "9.00"}),
    ])
    yield
    lm._set_names.cache_clear()
    lm._set_tails.cache_clear()


@pytest.mark.parametrize("title,expected", [
    ("Magic: The Gathering - The Hobbit Play Booster Box", "The Hobbit Play Booster Box"),
    ("The Hobbit - Play Booster Display", "The Hobbit Play Booster Box"),                     # Display = Box
    ("The Hobbit - Play Booster Display Case", "The Hobbit Play Booster Box Case"),
    ("Magic The Gathering | Secrets of Strixhaven Play Booster Box", "Secrets of Strixhaven Play Booster Box"),  # not stx
    ("Final Fantasy Starter Kit", "Final Fantasy Starter Kit"),                                # fin, not fic
    ("FINAL FANTASY Commander Deck - FINAL FANTASY X Counter Blitz (Collector's Edition)",
     "Final Fantasy Commander Deck Counter Blitz Collectors Edition"),
    ("Magic: The Gathering Universes Beyond: Spider-Man Bundle", "Marvels Spider Man Bundle"),  # set name minus "Marvel's"
    ("Magic the Gathering: Edge of Nothing [PRESALE] Hobbit Gift Bundle - expected release", "The Hobbit Gift Bundle"),  # noise ignored
    ("Magic: The Gathering: Starter Commander - First Flight Commander Deck", "Starter Commander Deck First Flight"),
    ("Secret Lair x God of War: Norse [Non-Foil Edition]", "God of War: Norse"),
])
def test_sealed_and_secret_lair_titles_match(title, expected):
    m = lm.match(title)
    assert m.status == "matched", (m.status, [c.name for c in m.candidates], m.note)
    assert m.match.name == expected


def test_secret_lair_finish_is_kept():
    m = lm.match("Secret Lair Drop - Goblingram [Rainbow Foil Edition]")
    assert (m.kind, m.match.name, m.match.finish) == ("sld", "Goblingram", "foil")
    assert sld.strip_finish_marker(sld.normalize_name("Uncharted [Non-Foil Edition]")) == "uncharted"
    assert sld.strip_finish_marker(sld.normalize_name("Uncharted (Nonfoil)")) == "uncharted"


def test_ambiguous_and_skipped_listings():
    generic = lm.match("Magic: The Gathering | Secrets of Strixhaven - Commander Deck")
    assert generic.status == "ambiguous" and len(generic.candidates) >= 2
    jp = lm.match("Magic: The Gathering Final Fantasy Japanese Collector Booster Box [JPN]")
    assert jp.status == "ambiguous" and "Japanese" in jp.note
    assert lm.match("Pokémon TCG: Terastal Festival Booster Pack").kind == "other_game"
    assert lm.match("Magic the Gathering - Godzilla - Custom Built Commander Deck").status == "skipped"
    assert lm.match("MTG Graded: Lightning, Lone Commando #54 Final Fantasy (2025) Foil Beckett 10").status == "skipped"


def test_singles_match_by_set_and_number_when_the_name_agrees():
    m = lm.match("Meltdown (SLD-2296) - Secret Lair Drop Series Foil")
    assert (m.status, m.match.scryfall_id, m.match.finish, m.match.price) == ("matched", "sld2296", "foil", 9.0)


def test_singles_with_wrong_store_metadata_are_never_silently_picked():
    # SOS #11 is Eager Glyphmage, not Exemplar of Light: offer Exemplar's printings,
    # the one closest to the asking price first.
    m = lm.match("Exemplar of Light (11) (Secrets of Strixhaven)", price=23.99)
    assert m.status == "ambiguous" and "Eager Glyphmage" in m.note
    assert [c.scryfall_id for c in m.candidates] == ["pfdn11p", "fdn297"]


def test_compare_values_at_face_price_and_honors_confirmations(monkeypatch):
    from magic_manager import sealed
    calls = []

    def fake_sealed(set_code, name, **kw):
        calls.append(name)
        return sealed.ProductValuation(label=name, kind="sealed", sealed_market=152.92, intrinsic=154.08)
    monkeypatch.setattr(valuation, "value_sealed_product", fake_sealed)
    row = {"url": "u1", "title": "The Hobbit - Play Booster Display", "price": 149.99, "available": True}
    out = deals.compare(row, cache={})
    assert (out["status"], out["market"], out["contents"], out["delta"], out["pct"]) == ("matched", 152.92, 154.08, -2.93, -1.9)

    # A confirmation wins over the title, and is remembered by URL.
    deals.confirm_match("u1", {"kind": "sealed", "set_code": "hob", "name": "The Hobbit Bundle"})
    confirmed = deals.confirmed_matches(["u1", "u2"])
    assert list(confirmed) == ["u1"]
    out = deals.compare(row, confirmed=confirmed["u1"], cache={})
    assert out["status"] == "confirmed" and calls[-1] == "The Hobbit Bundle"
    deals.confirm_match("u1", None)
    assert deals.confirmed_matches(["u1"]) == {}

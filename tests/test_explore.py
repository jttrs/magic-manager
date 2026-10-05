"""explore: a card as one of the 99 (EDHREC card page) and two cards compared."""
from __future__ import annotations

import json

import pytest

from magic_manager import db, edhrec, explore, inventory

SOL, SIG, CMD, BIRD, VAULT = (f"00000000-0000-0000-0000-00000000000{x}" for x in "12345")
OID = {n: f"aaaaaaaa-0000-0000-0000-00000000000{i}" for i, n in enumerate(["Sol Ring", "Arcane Signet", "Tifa", "Birds", "Mana Vault"], 1)}


def _page(name, commanders, coplayed, similar=(), salt=1.0):
    cv = lambda n, num, pot, **o: {"name": n, "slug": edhrec.slugify(n), "num_decks": num, "potential_decks": pot, **o}  # noqa: E731
    return {
        "header": f"{name} (Card)", "similar": list(similar),
        "panels": {"piechart": {"content": [{"label": "Land", "value": 35}, {"label": "Creature", "value": 26}]}},
        "container": {"json_dict": {
            "card": {"num_decks": 800, "potential_decks": 1000, "salt": salt},
            "cardlists": [
                {"tag": "topcommanders", "cardviews": [cv(n, num, pot) for n, num, pot in commanders]},
                {"tag": "creatures", "cardviews": [cv(n, 5, 10, lift=lift) for n, lift in coplayed]},
            ],
        }},
    }


@pytest.fixture
def seeded(seed_cards, make_card, monkeypatch):
    seed_cards([
        make_card(id=SOL, oracle_id=OID["Sol Ring"], name="Sol Ring", type_line="Artifact", collector_number="1"),
        make_card(id=SIG, oracle_id=OID["Arcane Signet"], name="Arcane Signet", type_line="Artifact", collector_number="2"),
        make_card(id=CMD, oracle_id=OID["Tifa"], name="Tifa", type_line="Legendary Creature — Human Monk", collector_number="3"),
        make_card(id=BIRD, oracle_id=OID["Birds"], name="Birds", type_line="Creature — Bird", collector_number="4"),
        make_card(id=VAULT, oracle_id=OID["Mana Vault"], name="Mana Vault", type_line="Artifact", collector_number="5"),
    ])
    with db.connect() as conn:
        for name, page in {
            "Sol Ring": _page("Sol Ring", [("Tifa", 90, 100)], [("Birds", 1.5)], similar=["Mana Vault"], salt=1.46),
            "Arcane Signet": _page("Arcane Signet", [("Tifa", 40, 100)], [("Birds", 1.1)], salt=0.24),
        }.items():
            conn.execute("INSERT INTO edhrec_pages (page_type, slug, timeframe, json, http_status, fetched_at) VALUES ('card', ?, '', ?, 200, '2026-01-01')",
                         (edhrec.slugify(name), json.dumps(page)))
        conn.commit()
    monkeypatch.setattr(edhrec, "resolve_names_to_oracle",
                        lambda names: {n.casefold(): {"oracle_id": OID.get(n)} for n in names if n in OID})
    inventory.inventory_add(BIRD, "nonfoil", 2)


def test_card_profile_reads_the_cached_page_and_joins_local_facts(seeded):
    p = explore.card_profile("sol ring")                       # case-insensitive, local-first resolve
    assert (p.name, p.commander_eligible, p.num_decks, p.salt) == ("Sol Ring", False, 800, 1.46)
    assert [(c.name, c.share, c.group) for c in p.commanders] == [("Tifa", 90.0, "top")]
    (bird,) = p.coplayed
    assert (bird.name, bird.lift, bird.group, bird.facts.owned, bird.facts.free) == ("Birds", 1.5, "Creatures", 2, 2)
    assert [s.name for s in p.similar] == ["Mana Vault"]
    assert p.deck_mix[0] == {"label": "Land", "value": 35}


def test_compare_cards_pairs_commanders_by_share_and_coplay_by_lift(seeded):
    c = explore.compare_cards("Sol Ring", "Arcane Signet")
    (tifa,) = c.commanders
    assert (tifa.bucket, tifa.a.share, tifa.b.share, tifa.gap) == ("both", 90.0, 40.0, 50.0)
    (birds,) = c.coplayed
    assert birds.bucket == "both" and birds.gap == pytest.approx(0.4)


def test_search_cards_finds_any_card_and_flags_leaders(seeded):
    hits = explore.search_cards("ti")
    assert [(h["name"], h["commander_eligible"]) for h in hits] == [("Tifa", True)]
    assert [h["name"] for h in explore.search_cards("ring")] == ["Sol Ring"]

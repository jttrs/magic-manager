"""Offline tests for the EDHREC integration.

slugify is pure. The sync engines are exercised with the client's page-fetchers
monkeypatched to return canned EDHREC-shaped pages (no bash wrapper / HTTP), and
scryfall.collection stubbed via the shared fake — mirroring the rest of the suite.
"""

from __future__ import annotations

import pytest

from magic_manager import edhrec


# ---------- slugify (pure) ----------

@pytest.mark.parametrize("name, expected", [
    ("Atraxa, Praetors' Voice", "atraxa-praetors-voice"),
    ("Ragavan, Nimble Pilferer", "ragavan-nimble-pilferer"),
    ("Sol Ring", "sol-ring"),
    ("Jace, Vryn's Prodigy // Jace, Telepath Unbound", "jace-vryns-prodigy"),
    ("Tibalt, Cosmic Impostor", "tibalt-cosmic-impostor"),
    ("Kongming, “Sleeping Dragon”", "kongming-sleeping-dragon"),
])
def test_slugify(name, expected):
    assert edhrec.slugify(name) == expected


# ---------- canned EDHREC pages ----------

def _cardview(name, slug, *, num_decks=None, potential_decks=None,
              synergy=None, lift=None, salt=None, rank=None, trend=None):
    cv = {"name": name, "slug": slug, "sanitized": slug}
    if num_decks is not None:
        cv["num_decks"] = num_decks
    if potential_decks is not None:
        cv["potential_decks"] = potential_decks
    if synergy is not None:
        cv["synergy"] = synergy
    if lift is not None:
        cv["lift"] = lift
    if salt is not None:
        cv["salt"] = salt
    if rank is not None:
        cv["rank"] = rank
    if trend is not None:
        cv["trend_zscore"] = trend
    return cv


def _page(cardlists):
    """Wrap {tag: [cardview]} into EDHREC's nested container shape."""
    return {
        "header": "Test Header",
        "container": {"json_dict": {"cardlists": [
            {"tag": tag, "header": tag, "cardviews": cvs}
            for tag, cvs in cardlists.items()
        ]}},
    }


@pytest.fixture
def fake_edhrec(monkeypatch):
    """Stub the four EDHREC page-fetchers with canned pages."""
    state = {"commander": {}, "card": {}, "commanders": {}, "top": {}}

    def configure(*, commander=None, card=None, commanders=None, top=None):
        if commander is not None:
            state["commander"] = commander
        if card is not None:
            state["card"] = card
        if commanders is not None:
            state["commanders"] = commanders
        if top is not None:
            state["top"] = top

    monkeypatch.setattr(edhrec, "commander_page", lambda slug: dict(state["commander"]))
    monkeypatch.setattr(edhrec, "card_page", lambda slug: dict(state["card"]))
    monkeypatch.setattr(edhrec, "commanders_ranking", lambda tf="week": dict(state["commanders"]))
    monkeypatch.setattr(edhrec, "top_ranking", lambda seg="week": dict(state["top"]))
    return configure


# ---------- workflow A: commander -> cards ----------

def test_sync_commander_persists_and_resolves(tmp_db, fake_edhrec, fake_scryfall, seed_cards, make_card):
    from magic_manager import db

    # Local card resolves Swords; Farseek is absent locally -> lazy Scryfall fill.
    seed_cards([make_card(
        id="s1", oracle_id="oracle-swords", name="Swords to Plowshares",
        set="tst", collector_number="1", prices={"usd": "1.42", "usd_foil": "3.00"},
        type_line="Instant", cmc=1.0,
    )])
    fake_scryfall(collection_found=[make_card(
        id="f1", oracle_id="oracle-farseek", name="Farseek",
        set="tst", collector_number="2", prices={"usd": "0.45"},
        type_line="Sorcery", cmc=2.0,
    )])
    fake_edhrec(commander=_page({
        "topcards": [
            _cardview("Swords to Plowshares", "swords-to-plowshares",
                      num_decks=25051, potential_decks=44993, synergy=-0.02),
            _cardview("Farseek", "farseek", num_decks=21040, potential_decks=44993, synergy=0.06),
        ],
    }))

    res = edhrec.sync_commander("Atraxa, Praetors' Voice")
    edhrec.enrich_rows(res.rows)

    assert res.slug == "atraxa-praetors-voice"
    by_name = {r.name: r for r in res.rows}
    swords = by_name["Swords to Plowshares"]
    assert swords.oracle_id == "oracle-swords"
    assert swords.inclusion_pct == pytest.approx(55.68, abs=0.01)
    assert swords.lowest_usd == 1.42
    assert swords.type_line == "Instant"
    # Farseek was filled from Scryfall and upserted, so it enriches too.
    assert by_name["Farseek"].oracle_id == "oracle-farseek"
    assert by_name["Farseek"].lowest_usd == 0.45

    # Persistence: rows landed + a raw page snapshot exists.
    with db.connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM edhrec_commander_cards WHERE commander_slug='atraxa-praetors-voice'"
        ).fetchone()[0]
        assert n == 2
        pages = conn.execute(
            "SELECT COUNT(*) FROM edhrec_pages WHERE page_type='commander' AND slug='atraxa-praetors-voice'"
        ).fetchone()[0]
        assert pages == 1


def test_enrich_rows_decodes_color_identity_to_list(tmp_db, fake_edhrec, fake_scryfall, seed_cards, make_card):
    # F7 regression: cards.color_identity is stored as a json.dumps STRING; after
    # enrich it must be a real list on the row (so the report JSON contract is an
    # array, not a double-encoded string).
    seed_cards([make_card(
        id="c1", oracle_id="oracle-ci", name="Coloredy Card",
        set="tst", collector_number="9", color_identity=["W", "U"],
        prices={"usd": "1.00"}, type_line="Instant", cmc=2.0,
    )])
    fake_scryfall(collection_found=[])
    fake_edhrec(commander=_page({
        "topcards": [_cardview("Coloredy Card", "coloredy-card", num_decks=5, potential_decks=10)],
    }))
    res = edhrec.sync_commander("Atraxa, Praetors' Voice")
    edhrec.enrich_rows(res.rows)
    row = next(r for r in res.rows if r.name == "Coloredy Card")
    assert row.color_identity == ["W", "U"]  # a real list, not '["W","U"]'
    assert isinstance(row.color_identity, list)


def test_sync_commander_idempotent(tmp_db, fake_edhrec, fake_scryfall):
    from magic_manager import db
    fake_scryfall(collection_found=[])
    fake_edhrec(commander=_page({
        "topcards": [_cardview("Sol Ring", "sol-ring", num_decks=100, potential_decks=200)],
    }))
    edhrec.sync_commander("Atraxa, Praetors' Voice")
    edhrec.sync_commander("Atraxa, Praetors' Voice")
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM edhrec_commander_cards").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM edhrec_pages").fetchone()[0] == 1


# ---------- workflow B: card -> commanders ----------

def test_sync_card_commanders(tmp_db, fake_edhrec, fake_scryfall):
    from magic_manager import db
    fake_scryfall(collection_found=[])
    fake_edhrec(card=_page({
        "topcommanders": [
            _cardview("Y'shtola, Night's Blessed", "yshtola-nights-blessed",
                      num_decks=51616, potential_decks=54968),
            _cardview("Edgar Markov", "edgar-markov", num_decks=46936, potential_decks=51141),
        ],
        # a non-commander list on the same page should be ignored by workflow B
        "topcards": [_cardview("Arcane Signet", "arcane-signet", num_decks=1)],
    }))
    res = edhrec.sync_card("Sol Ring")
    assert res.slug == "sol-ring"
    names = {r.name for r in res.rows}
    assert names == {"Y'shtola, Night's Blessed", "Edgar Markov"}  # only commanders
    ysh = next(r for r in res.rows if r.name.startswith("Y'shtola"))
    assert ysh.inclusion_pct == pytest.approx(93.9, abs=0.1)
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM edhrec_card_commanders WHERE card_slug='sol-ring'").fetchone()[0] == 2


# ---------- workflow C: rankings ----------

def test_sync_rankings_salt_derives_rank(tmp_db, fake_edhrec, fake_scryfall):
    fake_scryfall(collection_found=[])
    # salt page: no explicit rank -> derived from position.
    fake_edhrec(top=_page({
        "pastweek": [
            _cardview("Stasis", "stasis", salt=3.06, num_decks=18038),
            _cardview("Winter Orb", "winter-orb", salt=2.96, num_decks=15000),
        ],
    }))
    res = edhrec.sync_rankings("salt")
    assert res.scope == "salt" and res.timeframe == "all"
    assert [r.rank for r in res.rows] == [1, 2]
    assert res.rows[0].salt == 3.06


def test_sync_rankings_commanders_uses_explicit_rank(tmp_db, fake_edhrec, fake_scryfall):
    fake_scryfall(collection_found=[])
    fake_edhrec(commanders=_page({
        "pastweek": [
            _cardview("Jace, Multiverse Architect", "jace-multiverse-architect", num_decks=2382, rank=1),
            _cardview("Y'shtola, Night's Blessed", "yshtola-nights-blessed", num_decks=2025, rank=2),
        ],
    }))
    res = edhrec.sync_rankings("commanders", "week")
    assert [r.rank for r in res.rows] == [1, 2]
    assert res.rows[0].num_decks == 2382


def test_sync_rankings_rejects_bad_scope(tmp_db, fake_edhrec, fake_scryfall):
    fake_scryfall(collection_found=[])
    with pytest.raises(edhrec.EdhrecError):
        edhrec.sync_rankings("nonsense")


# ---------- resolution + price helper ----------

def test_resolve_names_local_first(tmp_db, fake_scryfall, seed_cards, make_card):
    seed_cards([make_card(id="a1", oracle_id="oracle-a", name="Alpha",
                          set="aaa", collector_number="1")])
    # Beta is not local -> filled from Scryfall (distinct set/cn to avoid the
    # cards UNIQUE(set_code, collector_number) constraint).
    fake_scryfall(collection_found=[make_card(id="b1", oracle_id="oracle-b", name="Beta",
                                              set="bbb", collector_number="1")])
    out = edhrec.resolve_names_to_oracle(["Alpha", "Beta", "Alpha"])
    assert out["alpha"]["oracle_id"] == "oracle-a"
    assert out["beta"]["oracle_id"] == "oracle-b"


def test_resolve_names_dfc_front_face(tmp_db, fake_scryfall, seed_cards, make_card):
    # EDHREC gives the FRONT face; Scryfall/our cards store "Front // Back".
    # Local row is the full DFC name — a front-face lookup must still hit it.
    seed_cards([make_card(id="t1", oracle_id="oracle-tergrid",
                          name="Tergrid, God of Fright // Tergrid's Lantern",
                          set="khm", collector_number="110")])
    fake_scryfall(collection_found=[])
    out = edhrec.resolve_names_to_oracle(["Tergrid, God of Fright"])
    assert out["tergrid, god of fright"]["oracle_id"] == "oracle-tergrid"


def test_lowest_price_by_oracle_min_across_printings(tmp_db, seed_cards, make_card):
    from magic_manager import sets
    # Two printings of the same oracle card: cheapest nonfoil wins for price AND
    # supplies the identity/metadata (per the helper's docstring).
    seed_cards([
        make_card(id="p1", oracle_id="oracle-x", name="Reprint Me", set="aaa",
                  collector_number="1", prices={"usd": "9.00", "usd_foil": "20.00"},
                  type_line="Artifact — Expensive", cmc=1.0),
        make_card(id="p2", oracle_id="oracle-x", name="Reprint Me", set="bbb",
                  collector_number="2", prices={"usd": "3.00", "usd_foil": "5.00"},
                  type_line="Artifact — Cheap", cmc=1.0),
    ])
    m = sets.lowest_price_by_oracle(["oracle-x"])
    assert m["oracle-x"]["lowest_usd"] == 3.00       # MIN across printings
    assert m["oracle-x"]["lowest_usd_foil"] == 5.00
    assert m["oracle-x"]["type_line"] == "Artifact — Cheap"  # cheapest-nonfoil printing's metadata
    assert sets.lowest_price_by_oracle([]) == {}

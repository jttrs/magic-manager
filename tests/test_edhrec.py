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
    # Accent fold (NFKD → drop combining marks): EDHREC folds é→e, û→u, etc.
    # Without the fold the accented letter is dropped ("owyn-…") and 403s.
    ("Éowyn, Shieldmaiden", "eowyn-shieldmaiden"),
    ("Sméagol, Helpful Guide", "smeagol-helpful-guide"),
    ("Théoden, King of Rohan", "theoden-king-of-rohan"),
    ("The Balrog, Flame of Udûn", "the-balrog-flame-of-udun"),
])
def test_slugify(name, expected):
    assert edhrec.slugify(name) == expected


# ---------- resolve_oracle_card: SET CN heuristic ----------

def test_resolve_oracle_card_hyphenated_name_not_treated_as_printing(monkeypatch):
    """A two-token name whose second token is numeric ("Spider-Man 2099") must
    NOT be parsed as a "SET CN" printing — the hyphenated first token isn't a
    set code. Regression: it used to fire the collection() path with
    set='spider-man', producing an HTTP 400 that crashed the whole sync."""
    def _boom(*a, **k):
        raise AssertionError("collection() must not be called for a card name")
    monkeypatch.setattr(edhrec.scryfall, "collection", _boom)
    monkeypatch.setattr(edhrec.scryfall, "named",
                        lambda ref: {"name": "Spider-Man 2099", "type_line": "Legendary Creature"})
    name, card = edhrec.resolve_oracle_card("Spider-Man 2099")
    assert name == "Spider-Man 2099"
    assert card is not None


def test_resolve_oracle_card_set_cn_still_resolves(monkeypatch):
    """A genuine "SET CN" printing ("fin 3") still resolves via collection()."""
    monkeypatch.setattr(edhrec.scryfall, "collection",
                        lambda ids: ([{"name": "Adelbert Steiner", "type_line": "Legendary Creature"}], []))
    name, card = edhrec.resolve_oracle_card("fin 3")
    assert name == "Adelbert Steiner"
    assert card is not None


def test_resolve_oracle_card_set_cn_failsoft_to_name(monkeypatch):
    """If the SET CN guess raises (malformed/hiccup), fall through to name
    resolution instead of crashing."""
    def _boom(*a, **k):
        raise edhrec.scryfall.ScryfallError("HTTP 400")
    monkeypatch.setattr(edhrec.scryfall, "collection", _boom)
    monkeypatch.setattr(edhrec.scryfall, "named",
                        lambda ref: {"name": "Kav 2000", "type_line": "Artifact Creature"})
    name, card = edhrec.resolve_oracle_card("Kav 2000")
    assert name == "Kav 2000"
    assert card is not None


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
    """Stub the EDHREC page-fetchers with canned pages.

    ``color``/``tag`` are keyed by slug; ``set_pages`` is keyed by set code (so a
    set-family union can return a distinct page per code)."""
    state = {"commander": {}, "card": {}, "commanders": {}, "top": {},
             "color": {}, "tag": {}, "set_pages": {}}

    def configure(*, commander=None, card=None, commanders=None, top=None,
                  color=None, tag=None, set_pages=None):
        for k, v in (("commander", commander), ("card", card),
                     ("commanders", commanders), ("top", top),
                     ("color", color), ("tag", tag), ("set_pages", set_pages)):
            if v is not None:
                state[k] = v

    monkeypatch.setattr(edhrec, "commander_page", lambda slug: dict(state["commander"]))
    monkeypatch.setattr(edhrec, "card_page", lambda slug: dict(state["card"]))
    monkeypatch.setattr(edhrec, "commanders_ranking", lambda tf="week": dict(state["commanders"]))
    monkeypatch.setattr(edhrec, "top_ranking", lambda seg="week": dict(state["top"]))
    monkeypatch.setattr(edhrec, "color_ranking", lambda slug, tf=None: dict(state["color"]))
    monkeypatch.setattr(edhrec, "tag_ranking", lambda slug: dict(state["tag"]))
    monkeypatch.setattr(edhrec, "set_page", lambda code: dict(state["set_pages"].get(code, {})))
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


# ---------- filtered commander rankings (color / tag / set) ----------

@pytest.mark.parametrize("spec, expected", [
    ("wu", "azorius"), ("r", "mono-red"), ("azorius", "azorius"),
    ("wubrg", "five-color"), ("rgw", "naya"), ("wubr", "yore-tiller"),
    ("c", "colorless"), ("", "colorless"), ("bant", "bant"),
    ("mono-green", "mono-green"),
])
def test_color_filter_slug(spec, expected):
    assert edhrec.color_filter_slug(spec) == expected


def test_color_filter_slug_rejects_garbage():
    with pytest.raises(edhrec.EdhrecError):
        edhrec.color_filter_slug("zzz")


def test_sync_rankings_color(tmp_db, fake_edhrec, fake_scryfall):
    from magic_manager import db
    fake_scryfall(collection_found=[])
    # color pages carry a single '<slug>commanders' list.
    fake_edhrec(color=_page({"mono-redcommanders": [
        _cardview("Krenko, Mob Boss", "krenko-mob-boss", num_decks=885, potential_decks=1000),
        _cardview("Magda, Brazen Outlaw", "magda-brazen-outlaw", num_decks=434, potential_decks=900),
    ]}))
    res = edhrec.sync_rankings("commanders", "week", color="mono-red")
    assert res.scope == "commanders" and res.timeframe == "week"
    assert [r.rank for r in res.rows] == [1, 2]
    assert res.rows[0].name == "Krenko, Mob Boss"
    with db.connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM edhrec_rankings WHERE filter='color:mono-red'"
        ).fetchone()[0]
        assert n == 2


def test_sync_rankings_tag_reads_topcommanders_not_newcommanders(tmp_db, fake_edhrec, fake_scryfall):
    from magic_manager import db
    fake_scryfall(collection_found=[])
    # A tags page's FIRST non-empty list is newcommanders (small); we must read
    # topcommanders. Give them disjoint entries and assert topcommanders wins.
    fake_edhrec(tag=_page({
        "newcommanders": [_cardview("New Guy", "new-guy", num_decks=10, potential_decks=99)],
        "topcommanders": [
            _cardview("Krenko, Mob Boss", "krenko-mob-boss", num_decks=5084, potential_decks=6000),
            _cardview("Zada, Hedron Grinder", "zada-hedron-grinder", num_decks=649, potential_decks=1000),
        ],
    }))
    res = edhrec.sync_rankings("commanders", "week", tag="goblins")
    assert res.timeframe == "all"          # tag pages are all-time only
    names = {r.name for r in res.rows}
    assert "Krenko, Mob Boss" in names     # topcommanders present
    assert "New Guy" in names              # newcommanders merged in
    # dedup + deck-count sort → Krenko first
    assert res.rows[0].name == "Krenko, Mob Boss"
    with db.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM edhrec_rankings WHERE filter='tag:goblins'"
        ).fetchone()[0] == 3


def test_sync_rankings_set_unions_codes(tmp_db, fake_edhrec, fake_scryfall, monkeypatch):
    from magic_manager import db, sets

    class _RS:  # minimal ResolvedSet stand-in
        code = "fin"
        all_codes = ["fin", "fic"]
    monkeypatch.setattr(sets, "resolve", lambda s: _RS())
    fake_scryfall(collection_found=[])
    fake_edhrec(set_pages={
        "fin": _page({"commanders(fin)": [
            _cardview("Y'shtola, Night's Blessed", "yshtola-nights-blessed", num_decks=55144, potential_decks=60000)]}),
        "fic": _page({"commanders(fic)": [
            _cardview("Cloud, Ex-SOLDIER", "cloud-ex-soldier", num_decks=31785, potential_decks=40000)]}),
    })
    res = edhrec.sync_rankings("commanders", "week", set_family="fin")
    assert res.timeframe == ""             # set rankings are timeframe-less
    names = [r.name for r in res.rows]
    assert names == ["Y'shtola, Night's Blessed", "Cloud, Ex-SOLDIER"]  # unioned, deck-sorted
    with db.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM edhrec_rankings WHERE filter='set:fin'"
        ).fetchone()[0] == 2


def test_sync_rankings_filters_mutually_exclusive(tmp_db, fake_edhrec, fake_scryfall):
    fake_scryfall(collection_found=[])
    with pytest.raises(edhrec.EdhrecError):
        edhrec.sync_rankings("commanders", "week", color="r", tag="goblins")


def test_sync_rankings_filter_requires_commander_scope(tmp_db, fake_edhrec, fake_scryfall):
    fake_scryfall(collection_found=[])
    with pytest.raises(edhrec.EdhrecError):
        edhrec.sync_rankings("cards", "week", color="r")


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


# ---------- commander eligibility + dual ingest ----------

@pytest.mark.parametrize("card, expected", [
    ({"type_line": "Legendary Creature — Elf Druid", "oracle_text": ""}, True),
    ({"type_line": "Legendary Planeswalker — Teferi",
      "oracle_text": "Teferi can be your commander."}, True),
    ({"type_line": "Enchantment — Background", "oracle_text": ""}, True),
    ({"type_line": "Instant", "oracle_text": "Draw a card."}, False),
    ({"type_line": "Creature — Human", "oracle_text": ""}, False),   # non-legendary
    ({"type_line": None, "oracle_text": None}, False),               # tolerates None
])
def test_is_commander_eligible(card, expected):
    from magic_manager import legality
    assert legality.is_commander_eligible(card) is expected


def test_sync_both_eligible_ingests_both(tmp_db, fake_edhrec, fake_scryfall, monkeypatch):
    from magic_manager import db
    # Resolver yields an eligible (Legendary Creature) card → both views ingest.
    monkeypatch.setattr(edhrec, "resolve_oracle_card", lambda ref: (
        "Atraxa, Praetors' Voice",
        {"type_line": "Legendary Creature — Phyrexian Angel Horror", "oracle_text": ""},
    ))
    fake_scryfall(collection_found=[])
    fake_edhrec(
        commander=_page({"topcards": [_cardview("Sol Ring", "sol-ring", num_decks=100, potential_decks=200)]}),
        card=_page({"topcommanders": [_cardview("Edgar Markov", "edgar-markov", num_decks=50, potential_decks=60)]}),
    )
    res = edhrec.sync_both("Atraxa, Praetors' Voice")
    assert res.eligible is True
    assert res.commander is not None and len(res.commander.rows) == 1
    assert res.card is not None and len(res.card.rows) == 1
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM edhrec_pages WHERE page_type='commander'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM edhrec_pages WHERE page_type='card'").fetchone()[0] == 1


def test_sync_both_ineligible_skips_commander(tmp_db, fake_edhrec, fake_scryfall, monkeypatch):
    from magic_manager import db
    # Resolver yields an ineligible (Instant) card → commander page NEVER fetched.
    monkeypatch.setattr(edhrec, "resolve_oracle_card", lambda ref: (
        "Sol Ring", {"type_line": "Artifact", "oracle_text": "{T}: Add {C}{C}."},
    ))
    # If sync_both tried the commander page despite ineligibility, this raises.
    monkeypatch.setattr(edhrec, "commander_page",
                        lambda slug: (_ for _ in ()).throw(AssertionError("commander_page must not be called")))
    fake_scryfall(collection_found=[])
    fake_edhrec(card=_page({"topcommanders": [_cardview("Edgar Markov", "edgar-markov", num_decks=50, potential_decks=60)]}))
    res = edhrec.sync_both("Sol Ring")
    assert res.eligible is False
    assert res.commander is None
    assert res.card is not None and len(res.card.rows) == 1
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM edhrec_pages WHERE page_type='commander'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM edhrec_pages WHERE page_type='card'").fetchone()[0] == 1


def test_sync_both_unresolved_ref_still_ingests_card(tmp_db, fake_edhrec, fake_scryfall, monkeypatch):
    # Scryfall can't resolve → card is None → skip commander gate, still try card.
    monkeypatch.setattr(edhrec, "resolve_oracle_card", lambda ref: ("Mystery Card", None))
    monkeypatch.setattr(edhrec, "commander_page",
                        lambda slug: (_ for _ in ()).throw(AssertionError("commander_page must not be called")))
    fake_scryfall(collection_found=[])
    fake_edhrec(card=_page({"topcommanders": [_cardview("Some Commander", "some-commander", num_decks=3, potential_decks=9)]}))
    res = edhrec.sync_both("Mystery Card")
    assert res.eligible is False
    assert res.commander is None
    assert res.card is not None and len(res.card.rows) == 1


# ---------- names_from_selector: token + digital-only exclusion ----------

def test_names_from_selector_excludes_tokens_and_digital(tmp_db, seed_cards, make_card):
    # A set-family selector must drop tokens (no EDHREC page for a Treasure) and
    # digital-only cards — including an Alchemy ORIGINAL that carries only the
    # arena stamp and NO 'A-' name prefix (the case a name-prefix check misses).
    seed_cards([
        make_card(id="c1", oracle_id="o-legend", name="Real Legend", set="tst",
                  collector_number="1", type_line="Legendary Creature — Hero"),
        make_card(id="c2", oracle_id="o-token", name="Treasure", set="tst",
                  collector_number="2", type_line="Token Artifact — Treasure",
                  layout="token"),
        make_card(id="c3", oracle_id="o-alch", name="Herald of Vengeance", set="tst",
                  collector_number="3", type_line="Legendary Creature — Angel",
                  security_stamp="arena"),
        make_card(id="c4", oracle_id="o-reb", name="A-Rebalanced One", set="tst",
                  collector_number="4", type_line="Legendary Creature — Wizard",
                  promo_types=["rebalanced"], security_stamp="arena"),
    ])
    names = edhrec.names_from_selector("set:tst")
    assert names == ["Real Legend"]  # token, Alchemy-original, and A- reprint all dropped


def test_names_from_selector_type_filter(tmp_db, seed_cards, make_card):
    seed_cards([
        make_card(id="c1", oracle_id="o1", name="Legend One", set="tst",
                  collector_number="1", type_line="Legendary Creature — Hero"),
        make_card(id="c2", oracle_id="o2", name="Plain Bolt", set="tst",
                  collector_number="2", type_line="Instant"),
    ])
    assert edhrec.names_from_selector("set:tst", card_type="legendary creature") == ["Legend One"]


# ---------- sync_bulk: per-eligibility resume + bug/transient split ----------

def test_sync_bulk_resume_skips_card_only_when_card_page_cached(tmp_db, fake_edhrec, fake_scryfall, monkeypatch):
    # A card-only (ineligible) card is "done" once its card page is cached — the
    # commander-slug-only key used to re-fetch it every run.
    monkeypatch.setattr(edhrec, "resolve_oracle_card",
                        lambda ref: ("Sol Ring", {"type_line": "Artifact", "oracle_text": ""}))
    fake_scryfall(collection_found=[])
    fake_edhrec(card=_page({"topcommanders": [_cardview("Edgar Markov", "edgar-markov", num_decks=5, potential_decks=9)]}))
    first = edhrec.sync_bulk(["Sol Ring"])
    assert first.ok == 1 and first.card_only == 1 and first.already == 0
    # Second run: card page is cached, card is ineligible → skipped, no re-fetch.
    monkeypatch.setattr(edhrec, "sync_both",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not re-fetch a fully-cached card-only card")))
    second = edhrec.sync_bulk(["Sol Ring"])
    assert second.already == 1 and second.ok == 0


def test_sync_bulk_resume_refetches_eligible_missing_commander_page(tmp_db, fake_edhrec, fake_scryfall, monkeypatch):
    # An ELIGIBLE card with only its card page cached (commander page missing, as
    # after an interrupted run) is NOT skipped — both pages are required.
    monkeypatch.setattr(edhrec, "resolve_oracle_card",
                        lambda ref: ("Atraxa", {"type_line": "Legendary Creature — Angel", "oracle_text": ""}))
    fake_scryfall(collection_found=[])
    # Warm ONLY the card page by faking an ineligible-looking first pass is awkward;
    # instead store a card page directly, then run bulk and assert it fetches the commander page.
    from magic_manager import db
    with db.transaction() as conn:
        edhrec._store_page(conn, page_type="card", slug="atraxa", timeframe="", page={}, at=db._utcnow_iso())
    fake_edhrec(
        commander=_page({"topcards": [_cardview("Sol Ring", "sol-ring", num_decks=10, potential_decks=20)]}),
        card=_page({"topcommanders": [_cardview("Edgar Markov", "edgar-markov", num_decks=5, potential_decks=9)]}),
    )
    res = edhrec.sync_bulk(["Atraxa"])
    assert res.already == 0 and res.ok == 1 and res.eligible == 1


def test_sync_bulk_tags_unexpected_exception_as_bug(tmp_db, fake_scryfall, monkeypatch):
    # A non-network exception (a code/parse bug) must be tagged distinctly, not
    # tallied as flaky-fetch noise — and the loop still continues.
    monkeypatch.setattr(edhrec, "resolve_oracle_card",
                        lambda ref: ("Buggy Card", {"type_line": "Instant", "oracle_text": ""}))
    def _boom(*a, **k):
        raise TypeError("NoneType has no attribute get")
    monkeypatch.setattr(edhrec, "sync_both", _boom)
    tags = []
    res = edhrec.sync_bulk(["Buggy Card"], resume=False,
                           progress=lambda i, t, n, tag: tags.append(tag))
    assert res.failed == 1 and res.ok == 0
    assert tags and tags[0].startswith("BUG: TypeError")
    assert res.failures[0][1].startswith("UNEXPECTED TypeError")


def test_sync_bulk_tags_edhrec_error_as_transient(tmp_db, fake_scryfall, monkeypatch):
    monkeypatch.setattr(edhrec, "resolve_oracle_card",
                        lambda ref: ("Net Card", {"type_line": "Instant", "oracle_text": ""}))
    def _boom(*a, **k):
        raise edhrec.EdhrecError("HTTP 429")
    monkeypatch.setattr(edhrec, "sync_both", _boom)
    tags = []
    res = edhrec.sync_bulk(["Net Card"], resume=False,
                           progress=lambda i, t, n, tag: tags.append(tag))
    assert res.failed == 1
    assert tags and tags[0].startswith("ERROR:") and "BUG" not in tags[0]

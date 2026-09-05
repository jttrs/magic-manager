"""Tests for ev.py — deterministic booster expected-value math.

All math is hand-computed so a regression in the weighting is caught exactly.
Local prices are seeded into a throwaway DB via MAGIC_MANAGER_DB (same pattern
as tests/test_mtgjson_sealed.py::test_v11_backfill).
"""

import pytest

from magic_manager import ev


# ---------- pure-arithmetic tests (no DB) ----------

def test_sheet_ev_basic():
    """Two cards, equal weight, prices $1 and $3 → E[pull] = 0.5·1 + 0.5·3 = $2."""
    sheet = {"foil": False, "totalWeight": 2,
             "cards": {"u1": 1, "u2": 1}}
    up = {"u1": {"usd": 1.0, "usd_foil": 9.0},
          "u2": {"usd": 3.0, "usd_foil": 9.0}}
    se = ev.sheet_ev(sheet, up)
    assert se.ev_per_pull == pytest.approx(2.0)
    assert se.n_cards == 2 and se.n_unpriced == 0
    assert se.priced_weight == 2


def test_sheet_ev_weights_unequal():
    """Weights 3:1, prices $4 and $8 → (3/4)·4 + (1/4)·8 = 3 + 2 = $5."""
    sheet = {"foil": False, "totalWeight": 4, "cards": {"a": 3, "b": 1}}
    up = {"a": {"usd": 4.0, "usd_foil": 0}, "b": {"usd": 8.0, "usd_foil": 0}}
    assert ev.sheet_ev(sheet, up).ev_per_pull == pytest.approx(5.0)


def test_sheet_ev_foil_reads_foil_price():
    """A foil sheet uses usd_foil, not usd."""
    sheet = {"foil": True, "totalWeight": 1, "cards": {"x": 1}}
    up = {"x": {"usd": 1.0, "usd_foil": 10.0}}
    assert ev.sheet_ev(sheet, up).ev_per_pull == pytest.approx(10.0)


def test_sheet_ev_unpriced_stays_in_denominator():
    """An unpriced card contributes 0 to EV but its weight stays in totalWeight,
    so the priced card is NOT renormalized up. 2 cards weight 1/1, one unpriced,
    priced one is $4 → EV = (1/2)·4 = $2 (NOT $4)."""
    sheet = {"foil": False, "totalWeight": 2, "cards": {"p": 1, "np": 1}}
    up = {"p": {"usd": 4.0, "usd_foil": 0}, "np": {"usd": None, "usd_foil": None}}
    se = ev.sheet_ev(sheet, up)
    assert se.ev_per_pull == pytest.approx(2.0)
    assert se.n_unpriced == 1
    assert se.priced_weight == 1


def test_booster_config_ev_sums_counts():
    sheet_evs = {
        "common": ev.SheetEV("common", False, 1, 0.10, 5, 0, 1),
        "rare": ev.SheetEV("rare", False, 1, 2.00, 5, 0, 1),
    }
    config = {"contents": {"common": 10, "rare": 1}, "weight": 1}
    # 10·0.10 + 1·2.00 = 1.00 + 2.00 = 3.00
    assert ev.booster_config_ev(config, sheet_evs) == pytest.approx(3.0)


def test_booster_ev_weighted_mix_of_layouts():
    """Two layouts weighted 3:1 over EVs A=$2 and B=$6 → (3·2 + 1·6)/4 = $3."""
    set_data = {
        "code": "TST",
        "booster": {
            "draft": {
                "boostersTotalWeight": 4,
                "boosters": [
                    {"contents": {"a": 1}, "weight": 3},   # EV = 1·$2 = $2
                    {"contents": {"b": 1}, "weight": 1},   # EV = 1·$6 = $6
                ],
                "sheets": {
                    "a": {"foil": False, "totalWeight": 1, "cards": {"ca": 1}},
                    "b": {"foil": False, "totalWeight": 1, "cards": {"cb": 1}},
                },
            }
        },
    }
    up = {"ca": {"usd": 2.0, "usd_foil": 0}, "cb": {"usd": 6.0, "usd_foil": 0}}
    b = ev.booster_ev(set_data, "draft", uuid_price=up)
    assert b.ev_usd == pytest.approx(3.0)
    assert b.n_configs == 2
    assert b.boosters_total_weight == 4
    assert b.coverage == pytest.approx(1.0)


def test_booster_ev_coverage_pull_weighted():
    """One rare slot (always) priced, one foil slot (rare, 1-in-4) unpriced.
    Coverage should stay HIGH because the unpriced sheet has little pull mass."""
    set_data = {
        "code": "TST",
        "booster": {
            "draft": {
                "boostersTotalWeight": 4,
                "boosters": [
                    {"contents": {"rare": 1}, "weight": 3},
                    {"contents": {"rare": 1, "foil": 1}, "weight": 1},
                ],
                "sheets": {
                    "rare": {"foil": False, "totalWeight": 1, "cards": {"r": 1}},
                    "foil": {"foil": True, "totalWeight": 1, "cards": {"f": 1}},
                },
            }
        },
    }
    up = {"r": {"usd": 1.0, "usd_foil": 0},
          "f": {"usd": None, "usd_foil": None}}  # unpriced foil
    b = ev.booster_ev(set_data, "draft", uuid_price=up)
    # expected pulls: rare = 1.0, foil = 1/4 = 0.25.
    # coverage = (1.0·1 + 0.25·0) / (1.0 + 0.25) = 1.0/1.25 = 0.8
    assert b.coverage == pytest.approx(0.8)
    assert b.n_unpriced == 1


def test_booster_ev_unknown_type_raises():
    set_data = {"code": "TST", "booster": {"draft": {"boosters": [], "sheets": {}}}}
    with pytest.raises(KeyError):
        ev.booster_ev(set_data, "collector")


def test_booster_types_sorted():
    set_data = {"booster": {"play": {}, "collector": {}, "draft": {}}}
    assert ev.booster_types(set_data) == ["collector", "draft", "play"]
    assert ev.booster_types({}) == []


# ---------- DB-backed test: build_uuid_price_map joins local cards ----------

def test_build_uuid_price_map_joins_local_prices(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(tmp_path / "mm.db"))
    from magic_manager import db
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO cards (scryfall_id, name, set_code, collector_number, "
            "rarity, prices_usd, prices_usd_foil) "
            "VALUES ('sid-1', 'Priced Card', 'tst', '1', 'rare', 2.50, 9.00)",
        )
    set_data = {
        "cards": [
            {"uuid": "u-priced", "name": "Priced Card",
             "identifiers": {"scryfallId": "sid-1"}},
            {"uuid": "u-missing", "name": "Unsynced Card",
             "identifiers": {"scryfallId": "sid-2"}},   # no local row
            {"uuid": "u-nosid", "name": "No Scryfall Id",
             "identifiers": {}},                          # no scryfallId
        ]
    }
    up, no_row = ev.build_uuid_price_map(set_data)
    assert up["u-priced"]["usd"] == 2.50
    assert up["u-priced"]["usd_foil"] == 9.00
    assert up["u-missing"]["usd"] is None
    assert "u-missing" in no_row
    assert "u-nosid" in no_row


# ---------- cross-set booster price map (sourceSetCodes) ----------

def _parent_with_cross_set_booster():
    """A parent set 'AAA' whose collector booster has ONE sheet sourced entirely
    from another set 'BBB' (mirrors AFR collector → AFC). sourceSetCodes lists
    both (parent included, as MTGJSON does)."""
    return {
        "code": "AAA",
        "cards": [  # parent has its own card, unrelated to the cross-set sheet
            {"uuid": "u-aaa", "name": "Parent Card", "identifiers": {"scryfallId": "sid-aaa"}},
        ],
        "booster": {
            "collector": {
                "sourceSetCodes": ["AAA", "BBB"],
                "boostersTotalWeight": 1,
                "boosters": [{"contents": {"cross": 1}, "weight": 1}],
                "sheets": {
                    # every card on this sheet lives in BBB, not AAA
                    "cross": {"foil": False, "totalWeight": 1, "cards": {"u-bbb": 1}},
                },
            }
        },
    }


_BBB_FILE = {
    "code": "BBB",
    "cards": [
        {"uuid": "u-bbb", "name": "Other-Set Card", "identifiers": {"scryfallId": "sid-bbb"}},
    ],
}


def test_build_booster_uuid_price_map_merges_source_sets(tmp_path, monkeypatch):
    """A uuid living only in a referenced set file is priced once that set's
    cards are seeded locally + its set file is resolvable."""
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(tmp_path / "mm.db"))
    from magic_manager import db, mtgjson
    with db.connect() as conn:
        conn.execute("INSERT INTO cards (scryfall_id, name, set_code, collector_number, "
                     "rarity, prices_usd, prices_usd_foil) "
                     "VALUES ('sid-bbb', 'Other-Set Card', 'bbb', '1', 'rare', 5.0, 12.0)")
    monkeypatch.setattr(mtgjson, "set_file", lambda code: _BBB_FILE)  # only BBB is fetched

    up, no_row = ev.build_booster_uuid_price_map(_parent_with_cross_set_booster(), "collector")
    assert up["u-bbb"]["usd"] == 5.0        # cross-set card resolved + priced
    assert "u-bbb" not in no_row


def test_booster_ev_cross_set_coverage_full(tmp_path, monkeypatch):
    """The regression proof for the AFR bug: a booster whose sheet is sourced
    from another set prices to 100% coverage once that set is local."""
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(tmp_path / "mm.db"))
    from magic_manager import db, mtgjson
    with db.connect() as conn:
        conn.execute("INSERT INTO cards (scryfall_id, name, set_code, collector_number, "
                     "rarity, prices_usd, prices_usd_foil) "
                     "VALUES ('sid-bbb', 'Other-Set Card', 'bbb', '1', 'rare', 5.0, 12.0)")
    monkeypatch.setattr(mtgjson, "set_file", lambda code: _BBB_FILE)

    b = ev.booster_ev(_parent_with_cross_set_booster(), "collector")  # no uuid_price
    assert b.ev_usd == pytest.approx(5.0)
    assert b.n_unpriced == 0
    assert b.coverage == pytest.approx(1.0)


def test_booster_ev_cross_set_unpriced_before_sync(tmp_path, monkeypatch):
    """Same booster but the referenced set is NOT seeded locally → the sheet is
    unpriced, coverage < 1, no crash (matches the pre-fix 93.3% state)."""
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(tmp_path / "mm.db"))
    from magic_manager import db, mtgjson
    with db.connect():
        pass  # empty cards table — BBB not synced
    monkeypatch.setattr(mtgjson, "set_file", lambda code: _BBB_FILE)

    b = ev.booster_ev(_parent_with_cross_set_booster(), "collector")
    assert b.ev_usd == pytest.approx(0.0)
    assert b.n_unpriced == 1
    assert b.coverage == pytest.approx(0.0)


def test_build_booster_uuid_price_map_no_source_codes_falls_back(tmp_path, monkeypatch):
    """A booster with no sourceSetCodes behaves exactly like build_uuid_price_map
    (parent-only) — zero regression for older sets."""
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(tmp_path / "mm.db"))
    from magic_manager import db
    with db.connect() as conn:
        conn.execute("INSERT INTO cards (scryfall_id, name, set_code, collector_number, "
                     "rarity, prices_usd, prices_usd_foil) "
                     "VALUES ('sid-aaa', 'Parent Card', 'aaa', '1', 'rare', 1.0, 2.0)")
    set_data = {
        "code": "AAA",
        "cards": [{"uuid": "u-aaa", "name": "Parent Card",
                   "identifiers": {"scryfallId": "sid-aaa"}}],
        "booster": {"draft": {"boosters": [], "sheets": {}}},  # no sourceSetCodes
    }
    got, _ = ev.build_booster_uuid_price_map(set_data, "draft")
    want, _ = ev.build_uuid_price_map(set_data)
    assert got == want
    assert got["u-aaa"]["usd"] == 1.0


def test_build_booster_uuid_price_map_dedupes_parent(tmp_path, monkeypatch):
    """sourceSetCodes listing the parent (and dupes) must NOT re-fetch the parent
    via set_file — the parent's cards come from the passed set_data."""
    monkeypatch.setenv("MAGIC_MANAGER_DB", str(tmp_path / "mm.db"))
    from magic_manager import db, mtgjson
    with db.connect():
        pass
    fetched = []
    monkeypatch.setattr(mtgjson, "set_file",
                        lambda code: fetched.append(code.lower()) or _BBB_FILE)
    set_data = _parent_with_cross_set_booster()
    set_data["booster"]["collector"]["sourceSetCodes"] = ["AAA", "aaa", "BBB"]

    ev.build_booster_uuid_price_map(set_data, "collector")
    assert "aaa" not in fetched          # parent never re-fetched
    assert fetched.count("bbb") == 1     # referenced set fetched exactly once


# ---------- sealed.referenced_set_codes discovery ----------

def test_referenced_set_codes_includes_booster_source_sets(monkeypatch):
    """A pack node whose booster sourceSetCodes name another set surfaces that
    set even though no node carries it as set_code."""
    from magic_manager import mtgjson, sealed
    monkeypatch.setattr(mtgjson, "set_file", lambda code: {
        "booster": {"collector": {"sourceSetCodes": ["AAA", "BBB"]}}
    })
    pack = sealed.ProductNode(
        name="AAA collector booster", set_code="aaa", kind="pack",
        ev_detail=ev.BoosterEV(booster_type="collector", ev_usd=0.0,
                               boosters_total_weight=1, n_configs=1),
    )
    root = sealed.ProductNode(name="Box", set_code="aaa", kind="sealed", children=[pack])
    codes = sealed.referenced_set_codes(root)
    assert "aaa" in codes and "bbb" in codes

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

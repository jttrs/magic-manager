"""Pool true-up — match loose cards to products, report conflicts, and
re-attribute the ledger on apply.

Offline: stubs mtgjson.deck_list + mtgjson.deck, seeds inventory + an
unattributed-backfill ledger event, then drives scripts/trueup_pools.py's core.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _load():
    path = ROOT / "scripts" / "trueup_pools.py"
    spec = importlib.util.spec_from_file_location("trueup_pools", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _seed_unattributed(conn, deltas):
    """Create an unattributed-backfill event + inventory rows == its deltas, so
    inventory == SUM(ledger) holds and the bucket looks like a fresh backfill."""
    from magic_manager import ingest
    uid = ingest.create_event(conn, "unattributed-backfill",
                              label="backfill:unattributed", status="backfill")
    for sid, fin, qty in deltas:
        ingest.record_delta(conn, uid, sid, fin, qty)
        conn.execute(
            "INSERT INTO inventory (scryfall_id, finish, quantity, acquired_at) "
            "VALUES (?, ?, ?, '2021-01-01T00:00:00+00:00')", (sid, fin, qty))
    return uid


@pytest.fixture
def stub_products(monkeypatch):
    """Stub mtgjson.deck_list (per set) + mtgjson.deck (per fileName)."""
    from magic_manager import mtgjson
    state = {"decklist": {}, "decks": {}}  # set_code -> [entries]; fileName -> deck

    def configure(*, decklist=None, decks=None):
        if decklist is not None:
            state["decklist"] = decklist
        if decks is not None:
            state["decks"] = decks

    monkeypatch.setattr(mtgjson, "deck_list",
                        lambda *, set_code=None: list(state["decklist"].get((set_code or "").lower(), [])))
    monkeypatch.setattr(mtgjson, "deck", lambda fn: dict(state["decks"].get(fn, {})))
    # default_precon_state is called by import_precon-adjacent paths; keep simple.
    return configure


def _deck(name, code, dtype, cards):
    """cards: list of (scryfallId, count, isFoil, setCode) → MTGJSON mainBoard."""
    return {
        "name": name, "code": code, "type": dtype,
        "mainBoard": [{"count": c, "isFoil": f, "setCode": sc,
                       "identifiers": {"scryfallId": sid}} for sid, c, f, sc in cards],
        "commander": [], "sideBoard": [], "tokens": [],
    }


# ---------- full-coverage claim ----------

def test_full_coverage_claim_and_reattribute(tmp_db, seed_cards, make_card, stub_products, fake_scryfall):
    from magic_manager import db, ingest, decks
    fake_scryfall()  # sync() is a no-op; cards already seeded

    a = "aaaa0000-0000-0000-0000-000000000001"
    b = "aaaa0000-0000-0000-0000-000000000002"
    seed_cards([
        make_card(id=a, set="tla", collector_number="62", name="Scene A"),
        make_card(id=b, set="tle", collector_number="63", name="Scene B"),
    ])
    with db.connect() as conn:
        uid = _seed_unattributed(conn, [(a, "nonfoil", 1), (b, "nonfoil", 1)])

    stub_products(
        decklist={"tla": [{"fileName": "SceneBox_TLA", "name": "The Scene Box",
                           "code": "TLA", "type": "Box Set"}]},
        decks={"SceneBox_TLA": _deck("The Scene Box", "TLA", "Box Set",
                                     [(a, 1, False, "tla"), (b, 1, False, "tle")])},
    )

    tp = _load()
    # dry-run: lists ready, writes nothing
    tp.run(mode="from-unattributed", target=None, apply=False, picks=set(),
           sld_threshold=0.9, json_out=True)
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) c FROM decks WHERE source_precon_file_name='SceneBox_TLA'").fetchone()["c"] == 0

    # apply: registers deconstructed deck + re-attributes both copies
    tp.run(mode="from-unattributed", target=None, apply=True, picks=set(),
           sld_threshold=0.9, json_out=True)
    with db.connect() as conn:
        built, decon = decks.precon_unit_counts_for("SceneBox_TLA", conn=conn)
        assert (built, decon) == (0, 1)
        # ledger still reconciles (net-zero re-attribution)
        assert ingest.reconcile_inventory_ledger(conn) == []
        # unattributed bucket drained for these cards
        uatt = conn.execute(
            "SELECT COALESCE(SUM(ie.delta),0) s FROM inventory_events ie "
            "JOIN ingest_events ev ON ev.ingest_id=ie.ingest_id "
            "WHERE ev.method='unattributed-backfill'").fetchone()["s"]
        assert uatt == 0
        # a precon trueup event now holds them
        pre = conn.execute(
            "SELECT COALESCE(SUM(ie.delta),0) s FROM inventory_events ie "
            "JOIN ingest_events ev ON ev.ingest_id=ie.ingest_id "
            "WHERE ev.method='precon' AND ev.label LIKE 'trueup:%'").fetchone()["s"]
        assert pre == 2
        # inventory quantities untouched (no double count)
        assert conn.execute("SELECT quantity FROM inventory WHERE scryfall_id=?", (a,)).fetchone()["quantity"] == 1


# ---------- priority allocation: shared card goes to higher-priority product ----------

def test_priority_resolves_land_pack_vs_jumpstart(tmp_db, seed_cards, make_card,
                                                  stub_products, fake_scryfall):
    """A Bundle Land Pack (low tier) loses a shared basic to a Jumpstart (high
    tier) automatically — no --pick needed. The land pack drops to NOT COVERED."""
    from magic_manager import db
    fake_scryfall()

    shared = "bbbb0000-0000-0000-0000-000000000001"
    seed_cards([make_card(id=shared, set="tla", collector_number="1", name="Island")])
    with db.connect() as conn:
        _seed_unattributed(conn, [(shared, "nonfoil", 1)])  # only ONE copy

    stub_products(
        decklist={"tla": [
            {"fileName": "LandPack_TLA", "name": "Land Pack", "code": "TLA", "type": "Bundle Land Pack"},
            {"fileName": "Jumpstart_TLA", "name": "A Jumpstart", "code": "TLA", "type": "Jumpstart"},
        ]},
        decks={
            "LandPack_TLA": _deck("Land Pack", "TLA", "Bundle Land Pack", [(shared, 1, False, "tla")]),
            "Jumpstart_TLA": _deck("A Jumpstart", "TLA", "Jumpstart", [(shared, 1, False, "tla")]),
        },
    )

    tp = _load()
    tp.run(mode="from-unattributed", target=None, apply=True, picks=set(),
           sld_threshold=0.9, json_out=True)
    with db.connect() as conn:
        # Jumpstart (tier 80) won the Island; Land Pack (tier 10) lost.
        assert conn.execute("SELECT COUNT(*) c FROM decks WHERE source_precon_file_name='Jumpstart_TLA'").fetchone()["c"] == 1
        assert conn.execute("SELECT COUNT(*) c FROM decks WHERE source_precon_file_name='LandPack_TLA'").fetchone()["c"] == 0


def test_pick_overrides_priority(tmp_db, seed_cards, make_card, stub_products, fake_scryfall):
    """--pick forces a product to win the shared card even against a
    higher-priority competitor (the user knows they opened it)."""
    from magic_manager import db
    fake_scryfall()

    shared = "bbbb0000-0000-0000-0000-000000000002"
    seed_cards([make_card(id=shared, set="tla", collector_number="2", name="Island2")])
    with db.connect() as conn:
        _seed_unattributed(conn, [(shared, "nonfoil", 1)])

    stub_products(
        decklist={"tla": [
            {"fileName": "LandPack_TLA", "name": "Land Pack", "code": "TLA", "type": "Bundle Land Pack"},
            {"fileName": "Jumpstart_TLA", "name": "A Jumpstart", "code": "TLA", "type": "Jumpstart"},
        ]},
        decks={
            "LandPack_TLA": _deck("Land Pack", "TLA", "Bundle Land Pack", [(shared, 1, False, "tla")]),
            "Jumpstart_TLA": _deck("A Jumpstart", "TLA", "Jumpstart", [(shared, 1, False, "tla")]),
        },
    )

    tp = _load()
    # Pick the land pack — it should win despite lower tier.
    tp.run(mode="from-unattributed", target=None, apply=True, picks={"LandPack_TLA"},
           sld_threshold=0.9, json_out=True)
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) c FROM decks WHERE source_precon_file_name='LandPack_TLA'").fetchone()["c"] == 1
        assert conn.execute("SELECT COUNT(*) c FROM decks WHERE source_precon_file_name='Jumpstart_TLA'").fetchone()["c"] == 0


def test_version_tiebreak_prefers_lower(tmp_db, seed_cards, make_card, stub_products, fake_scryfall):
    """Same-tier version variants: '(1)' wins the shared card over '(2)'."""
    from magic_manager import db
    fake_scryfall()

    shared = "bbbb0000-0000-0000-0000-000000000003"
    seed_cards([make_card(id=shared, set="tle", collector_number="3", name="SharedJS")])
    with db.connect() as conn:
        _seed_unattributed(conn, [(shared, "nonfoil", 1)])

    stub_products(
        decklist={"tle": [
            {"fileName": "Gliding2_TLE", "name": "Gliding (2)", "code": "TLE", "type": "Jumpstart"},
            {"fileName": "Gliding1_TLE", "name": "Gliding (1)", "code": "TLE", "type": "Jumpstart"},
        ]},
        decks={
            "Gliding1_TLE": _deck("Gliding (1)", "TLE", "Jumpstart", [(shared, 1, False, "tle")]),
            "Gliding2_TLE": _deck("Gliding (2)", "TLE", "Jumpstart", [(shared, 1, False, "tle")]),
        },
    )

    tp = _load()
    tp.run(mode="from-unattributed", target=None, apply=True, picks=set(),
           sld_threshold=0.9, json_out=True)
    with db.connect() as conn:
        # (1) wins the shared card despite (2) appearing first in the decklist.
        assert conn.execute("SELECT COUNT(*) c FROM decks WHERE source_precon_file_name='Gliding1_TLE'").fetchone()["c"] == 1
        assert conn.execute("SELECT COUNT(*) c FROM decks WHERE source_precon_file_name='Gliding2_TLE'").fetchone()["c"] == 0


# ---------- no double-count: a pledged card isn't claimable ----------

def test_card_attributed_elsewhere_not_claimable(tmp_db, seed_cards, make_card,
                                                 stub_products, fake_scryfall):
    """A card whose unattributed balance is 0 (already attributed to a precon —
    e.g. an owned starter kit's card) can't back a new product. This is the LTR
    'Mountain' scenario: owned but not available in the unattributed pool."""
    from magic_manager import db, ingest
    fake_scryfall()

    x = "cccc0000-0000-0000-0000-000000000001"
    seed_cards([make_card(id=x, set="ltr", collector_number="269", name="Mountain")])

    # Own 1 copy, fully attributed to a precon (an owned starter kit) → the
    # unattributed balance for it is 0.
    with db.connect() as conn:
        ev = ingest.create_event(conn, "precon", label="precon:GondorGreenWhite_LTR")
        ingest.record_delta(conn, ev, x, "nonfoil", 1)
        conn.execute("INSERT INTO inventory (scryfall_id, finish, quantity, acquired_at) "
                     "VALUES (?, 'nonfoil', 1, '2021-01-01T00:00:00+00:00')", (x,))
        # A (real but empty) unattributed event must exist for the run.
        ingest.create_event(conn, "unattributed-backfill",
                            label="backfill:unattributed", status="backfill")
        assert ingest.reconcile_inventory_ledger(conn) == []

    # A jumpstart deck needing that Mountain — but its balance is 0.
    stub_products(
        decklist={"ltr": [{"fileName": "Marauders1_LTR", "name": "Marauders 1",
                           "code": "LTR", "type": "Jumpstart"}]},
        decks={"Marauders1_LTR": _deck("Marauders 1", "LTR", "Jumpstart",
                                       [(x, 1, False, "ltr")])},
    )
    tp = _load()
    tp.run(mode="all", target=None, apply=True, picks=set(),
           sld_threshold=0.9, json_out=True)
    with db.connect() as conn:
        # Not claimed — the Mountain is already spoken for.
        assert conn.execute(
            "SELECT COUNT(*) c FROM decks WHERE source_precon_file_name='Marauders1_LTR'"
        ).fetchone()["c"] == 0
        assert ingest.reconcile_inventory_ledger(conn) == []


# ---------- coverage requires the recipe to fit the UNATTRIBUTED balance ----------

def test_recipe_exceeding_unattributed_balance_not_covered(tmp_db, seed_cards, make_card,
                                                           stub_products, fake_scryfall):
    """A product is coverable only if its FULL recipe fits the unattributed
    balance. Owning 3 copies of a card but with only 2 unattributed (1 already
    on a checklist) does NOT cover a product needing 3 — the 1 checklist copy is
    already spoken for, so it can't back this product too."""
    from magic_manager import db, ingest, decks
    fake_scryfall()

    z = "dddd0000-0000-0000-0000-000000000001"
    seed_cards([make_card(id=z, set="tla", collector_number="9", name="Split Prov")])

    # Own 3 copies: 1 attributed to a checklist event, 2 to unattributed.
    with db.connect() as conn:
        chk = ingest.create_event(conn, "checklist", label="set:tla", mode="additive")
        ingest.record_delta(conn, chk, z, "nonfoil", 1)
        uid = ingest.create_event(conn, "unattributed-backfill",
                                  label="backfill:unattributed", status="backfill")
        ingest.record_delta(conn, uid, z, "nonfoil", 2)
        conn.execute("INSERT INTO inventory (scryfall_id, finish, quantity, acquired_at) "
                     "VALUES (?, 'nonfoil', 3, '2021-01-01T00:00:00+00:00')", (z,))
        assert ingest.reconcile_inventory_ledger(conn) == []  # 3 == 1 + 2

    # A product needing 3 of z — but only 2 are unattributed.
    stub_products(
        decklist={"tla": [{"fileName": "SplitBox_TLA", "name": "Split Box",
                           "code": "TLA", "type": "Box Set"}]},
        decks={"SplitBox_TLA": _deck("Split Box", "TLA", "Box Set", [(z, 3, False, "tla")])},
    )

    tp = _load()
    tp.run(mode="from-unattributed", target=None, apply=True, picks=set(),
           sld_threshold=0.9, json_out=True)

    with db.connect() as conn:
        # NOT covered/claimed — recipe (3) exceeds unattributed balance (2).
        assert decks.precon_unit_counts_for("SplitBox_TLA", conn=conn) == (0, 0)
        assert ingest.reconcile_inventory_ledger(conn) == []
        # Balances untouched.
        uatt = conn.execute(
            "SELECT COALESCE(SUM(ie.delta),0) s FROM inventory_events ie "
            "JOIN ingest_events ev ON ev.ingest_id=ie.ingest_id "
            "WHERE ev.method='unattributed-backfill' AND ie.scryfall_id=?", (z,)).fetchone()["s"]
        assert uatt == 2


# ---------- SLD: complete vs partial by CN ownership ----------

def test_sld_complete_vs_partial(tmp_db, seed_cards, make_card, monkeypatch):
    from magic_manager import db, sld

    # Drop has 2 CNs; own both = complete. A second drop: own 1 of 2 = 50% (< 0.9).
    d1 = ["sld-0001", "sld-0002"]
    d2 = ["sld-1001", "sld-1002"]
    seed_cards([
        make_card(id=d1[0], set="sld", collector_number="1", name="D1a"),
        make_card(id=d1[1], set="sld", collector_number="2", name="D1b"),
        make_card(id=d2[0], set="sld", collector_number="1001", name="D2a"),
        make_card(id=d2[1], set="sld", collector_number="1002", name="D2b"),
    ])
    with db.connect() as conn:
        # Own both of drop 1; only one of drop 2.
        for sid in (d1[0], d1[1], d2[0]):
            conn.execute("INSERT INTO inventory (scryfall_id, finish, quantity, acquired_at) "
                         "VALUES (?, 'nonfoil', 1, '2021-01-01T00:00:00+00:00')", (sid,))

    monkeypatch.setattr(sld, "all_drops", lambda: {
        "Drop One": {"file_names": ["DropOne_SLD"]},
        "Drop Two": {"file_names": ["DropTwo_SLD"]},
    })
    monkeypatch.setattr(sld, "collect_drop_ids",
                        lambda fns: d1 if fns == ["DropOne_SLD"] else d2)

    tp = _load()
    with db.connect() as conn:
        complete, partial = tp._sld_status(conn, 0.9)
    names_c = {c["name"] for c in complete}
    names_p = {p["name"] for p in partial}
    assert "Drop One" in names_c
    assert "Drop Two" not in names_c and "Drop Two" not in names_p  # 50% < 0.9 threshold

    with db.connect() as conn:
        complete2, partial2 = tp._sld_status(conn, 0.5)  # lower threshold surfaces it
    assert "Drop Two" in {p["name"] for p in partial2}


def test_sld_complete_drop_registered_on_apply(tmp_db, seed_cards, make_card,
                                               stub_products, fake_scryfall, monkeypatch):
    """A complete SLD drop flows through the same apply path: registers a
    deconstructed deck row + re-attributes its copies from unattributed."""
    from magic_manager import db, ingest, decks, sld

    fake_scryfall()
    s1 = "eeee0000-0000-0000-0000-000000000001"
    s2 = "eeee0000-0000-0000-0000-000000000002"
    seed_cards([
        make_card(id=s1, set="sld", collector_number="9001", name="Drop Card 1"),
        make_card(id=s2, set="sld", collector_number="9002", name="Drop Card 2"),
    ])
    with db.connect() as conn:
        _seed_unattributed(conn, [(s1, "nonfoil", 1), (s2, "nonfoil", 1)])

    # SLD drop of 2 cards, both owned → complete.
    monkeypatch.setattr(sld, "all_drops", lambda: {
        "My Drop": {"file_names": ["MyDrop_SLD"]},
    })
    monkeypatch.setattr(sld, "collect_drop_ids", lambda fns: [s1, s2])
    # The drop's fileName recipe (via mtgjson.deck) — both cards, nonfoil.
    stub_products(
        decklist={"sld": []},  # deck_list(sld) filtered to Secret Lair Drop → none here
        decks={"MyDrop_SLD": _deck("My Drop", "SLD", "Secret Lair Drop",
                                   [(s1, 1, False, "sld"), (s2, 1, False, "sld")])},
    )

    tp = _load()
    tp.run(mode="from-unattributed", target=None, apply=True, picks=set(),
           sld_threshold=0.9, json_out=True)

    with db.connect() as conn:
        assert decks.precon_unit_counts_for("MyDrop_SLD", conn=conn) == (0, 1)
        assert ingest.reconcile_inventory_ledger(conn) == []
        uatt = conn.execute(
            "SELECT COALESCE(SUM(ie.delta),0) s FROM inventory_events ie "
            "JOIN ingest_events ev ON ev.ingest_id=ie.ingest_id "
            "WHERE ev.method='unattributed-backfill'").fetchone()["s"]
        assert uatt == 0


def test_sld_drop_not_double_registered_across_editions(tmp_db, seed_cards, make_card,
                                                        stub_products, fake_scryfall, monkeypatch):
    """A drop with base + Foil-Edition siblings referencing the SAME printings
    must register ONCE, not once per edition (no double-count)."""
    from magic_manager import db, ingest, decks, sld

    fake_scryfall()
    s = "ffff0000-0000-0000-0000-000000000001"
    seed_cards([make_card(id=s, set="sld", collector_number="7777", name="Shared Drop Card")])
    with db.connect() as conn:
        _seed_unattributed(conn, [(s, "nonfoil", 1)])

    monkeypatch.setattr(sld, "all_drops", lambda: {
        "Twin Drop": {"file_names": ["TwinDrop_SLD", "TwinDropFoilEdition_SLD"]},
    })
    monkeypatch.setattr(sld, "collect_drop_ids", lambda fns: [s])
    # BOTH editions' recipes reference the same nonfoil printing.
    stub_products(
        decklist={"sld": []},
        decks={
            "TwinDrop_SLD": _deck("Twin Drop", "SLD", "Secret Lair Drop", [(s, 1, False, "sld")]),
            "TwinDropFoilEdition_SLD": _deck("Twin Drop", "SLD", "Secret Lair Drop", [(s, 1, False, "sld")]),
        },
    )

    tp = _load()
    tp.run(mode="from-unattributed", target=None, apply=True, picks=set(),
           sld_threshold=0.9, json_out=True)

    with db.connect() as conn:
        # Registered exactly ONE deck row (the chosen edition), not two.
        n = conn.execute(
            "SELECT COUNT(*) c FROM decks WHERE source_precon_file_name IN "
            "('TwinDrop_SLD','TwinDropFoilEdition_SLD')").fetchone()["c"]
        assert n == 1
        assert ingest.reconcile_inventory_ledger(conn) == []

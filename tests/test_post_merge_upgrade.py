"""scripts/post_merge_upgrade.py — the exact precon_state proof around the built backfill."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from magic_manager import db, decks, inventory, scryfall_art, scryfall_tags, sets

ROOT = Path(__file__).resolve().parent.parent
A = "00000000-0000-0000-0000-00000000000a"


@pytest.fixture
def pmu():
    spec = importlib.util.spec_from_file_location("post_merge_upgrade", ROOT / "scripts" / "post_merge_upgrade.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_built_state_problems_allows_only_predicted_built_to_deconstructed(pmu):
    ok = pmu._built_state_problems({1: "built", 2: "built", 3: "deconstructed"}, {1},
                                   {1: "deconstructed", 2: "built", 3: "deconstructed"}, [], 0)
    assert ok == []
    unpredicted = pmu._built_state_problems({1: "built", 2: "built"}, {1}, {1: "built", 2: "deconstructed"}, [], 0)
    assert unpredicted == ["deck 2: built → deconstructed (not an allowed correction)"]
    wrong_way = pmu._built_state_problems({1: "deconstructed"}, {1}, {1: "built"}, [], 0)
    assert wrong_way == ["deck 1: deconstructed → built (not an allowed correction)"]
    assert pmu._built_state_problems({}, set(), {}, [7], 0) == ["deck 7: deconstructed but holds pledged cards"]
    assert pmu._built_state_problems({}, set(), {}, [], 2) == ["2 deck(s) still violate 'built follows pledges'"]


@pytest.fixture
def upgrade_db(tmp_db, seed_cards, make_card, monkeypatch):
    """A DB needing the built backfill, with the network backfill steps stubbed."""
    seed_cards([make_card(id=A, name="Alpha")])
    inventory.inventory_add(A, "nonfoil", 1)
    decks.deck_create("old-import", "Old import")                                 # unpledged built → corrected
    decks.deck_create("precon", "Precon", source_precon_file_name="X_TST")        # unpledged extra copy → corrected
    decks.deck_create("precon-2", "Precon", source_precon_file_name="X_TST")      # pledged → stays built
    decks.deck_add_card("precon-2", A, "main", "nonfoil", 1)
    decks.deck_assign_batch("precon-2", [(A, "nonfoil", 1)])
    monkeypatch.setattr(sets, "backfill_released_at", lambda: 0)
    monkeypatch.setattr(scryfall_tags, "sync_kinds", lambda: "stubbed")
    monkeypatch.setattr(decks, "unclassified_precon_count", lambda **k: 0)
    monkeypatch.setattr(scryfall_art, "backfill_illustration_ids", lambda: 0)
    return tmp_db


def _states():
    with db.connect() as conn:
        return dict(conn.execute("SELECT slug, precon_state FROM decks"))


def test_run_passes_when_backfill_flips_only_predicted_decks(pmu, upgrade_db, capsys):
    assert pmu.run(upgrade_db) == 0
    assert _states() == {"old-import": "deconstructed", "precon": "deconstructed", "precon-2": "built"}
    assert "2 deck(s) built → not built" in capsys.readouterr().out


def test_run_fails_when_a_pledged_deck_is_flipped(pmu, upgrade_db, monkeypatch, capsys):
    real = decks.backfill_built_state

    def wrong(**k):
        out = real(**k)
        with db.connect() as conn:
            conn.execute("UPDATE decks SET precon_state = 'deconstructed' WHERE slug = 'precon-2'")
        return out
    monkeypatch.setattr(decks, "backfill_built_state", wrong)
    assert pmu.run(upgrade_db) == 1
    out = capsys.readouterr().out
    assert "built → deconstructed (not an allowed correction)" in out and "holds pledged cards" in out


def test_run_fails_when_a_deck_is_flipped_to_built(pmu, upgrade_db, monkeypatch):
    decks.deck_create("loose", "Loose", source_precon_file_name="Y_TST", precon_state="deconstructed")

    def flips_to_built():  # an unrelated backfill step that wrongly rebuilds a loose copy
        with db.connect() as conn:
            return conn.execute("UPDATE decks SET precon_state = 'built' WHERE slug = 'loose'").rowcount
    monkeypatch.setattr(scryfall_art, "backfill_illustration_ids", flips_to_built)
    assert pmu.run(upgrade_db) == 1

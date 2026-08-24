"""Tests for magic_manager.missing.missing_printings — the shared missing-set
union. Offline: seeded tmp DB + faked all_sets. Uses 'tla' (configured with an
empty dupe-foil set) so the preferred filter runs without extra config."""

from __future__ import annotations

import pytest


@pytest.fixture
def tla_family(monkeypatch):
    """Make sets.resolve('tla') work offline as a single-code family."""
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets",
                        lambda: [{"code": "tla", "parent_set_code": None,
                                  "name": "Avatar", "set_type": "expansion"}])


def test_missing_excludes_owned_printings(tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing, db
    seed_cards([
        make_card(id="m1", set="tla", collector_number="5", rarity="rare", name="Unowned Rare"),
        make_card(id="m2", set="tla", collector_number="6", rarity="rare", name="Owned Rare"),
    ])
    with db.connect() as conn:
        conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) "
                     "VALUES ('m2','nonfoil',1,'2025-01-01')")
    rows = missing.missing_printings("tla")
    sids = {r.scryfall_id for r in rows}
    assert "m1" in sids          # unowned rare is missing
    assert "m2" not in sids      # owned rare is not


def test_missing_printing_level_any_finish_owned(tmp_db, tla_family, seed_cards, make_card):
    """Owning ANY finish of a printing removes it from missing (printing-level)."""
    from magic_manager import missing, db
    seed_cards([make_card(id="p1", set="tla", collector_number="7", rarity="mythic",
                          finishes=["nonfoil", "foil"], name="Dual Finish")])
    with db.connect() as conn:
        # own only the foil
        conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) "
                     "VALUES ('p1','foil',1,'2025-01-01')")
    rows = missing.missing_printings("tla")
    assert "p1" not in {r.scryfall_id for r in rows}


def test_missing_empty_when_all_owned(tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing, db
    seed_cards([make_card(id="o1", set="tla", collector_number="8", rarity="rare")])
    with db.connect() as conn:
        conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) "
                     "VALUES ('o1','nonfoil',1,'2025-01-01')")
    assert missing.missing_printings("tla") == []


def test_sub_selectors_shape(tmp_db, tla_family):
    """sub_selectors returns 4 (slug, selector) pairs; the repr-building code in
    cli relies on indices 0-2 being the rare/mythic/uncommon-chase subs."""
    from magic_manager import missing
    subs = missing.sub_selectors("tla")
    assert len(subs) == 4
    slugs = [s for s, _ in subs]
    assert slugs[:3] == ["rare-regular", "mythic-regular", "uncommon-chase"]


def test_arena_stamped_alchemy_originals_excluded(tmp_db, tla_family, seed_cards, make_card):
    """Alchemy-ORIGINAL cards carry no rebalanced/alchemy promo_type — only
    security_stamp='arena'. They must still be filtered from missing-set
    (regression: they leaked into SNC because the projection dropped the stamp)."""
    from magic_manager import missing
    seed_cards([
        make_card(id="phys", set="tla", collector_number="5", rarity="rare",
                  name="Physical Rare"),                       # normal → missing
        make_card(id="arena1", set="tla", collector_number="6", rarity="rare",
                  name="Digital Rare", promo_types=[], security_stamp="arena"),  # digital → excluded
    ])
    rows = missing.missing_printings("tla")
    sids = {r.scryfall_id for r in rows}
    assert "phys" in sids
    assert "arena1" not in sids, "arena-stamped Alchemy original leaked into missing-set"

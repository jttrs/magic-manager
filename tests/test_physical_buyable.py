"""Tests for magic_manager.missing.physical_buyable — the flat-list buy-list
gate that producers (jumpstart-buildable, etc.) run so none of them leak
tokens / digital-only / family-unobtainable / meld-back prints.

Offline: seeded tmp DB + faked all_sets ('tla', configured with an empty
dupe-foil set so the preferred filter runs — matching test_missing_printings.py).
"""

from __future__ import annotations

import pytest


@pytest.fixture
def tla_family(monkeypatch):
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets",
                        lambda: [{"code": "tla", "parent_set_code": None,
                                  "name": "Avatar", "set_type": "expansion"}])


def _rows_for(ids):
    """Materialize a flat MaterializedRow list for the given seeded scryfall_ids,
    in `cards`-table order, nonfoil."""
    from magic_manager import db, selectors as sel
    with db.connect() as conn:
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT {sel._CARD_COLS} FROM cards c WHERE c.scryfall_id IN ({placeholders})",
            list(ids),
        ).fetchall()
    return [sel.MaterializedRow(scryfall_id=r["scryfall_id"], quantity=1,
                                finish="nonfoil", card=sel._card_dict(r))
            for r in rows]


def test_physical_buyable_drops_tokens_and_digital(tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing
    seed_cards([
        make_card(id="real", set="tla", collector_number="5", rarity="rare", name="Real Rare"),
        make_card(id="tok", set="tla", collector_number="20", rarity="rare",
                  name="Angel Token", layout="token"),
        make_card(id="arena", set="tla", collector_number="6", rarity="rare",
                  name="Digital Rare", promo_types=[], security_stamp="arena"),
    ])
    rows = _rows_for(["real", "tok", "arena"])
    kept = {r.scryfall_id for r in missing.physical_buyable(rows, "tla")}
    assert kept == {"real"}


def test_physical_buyable_drops_meld_backs(tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing
    # A meld back: every family printing of this name has a 'b'-suffix CN.
    seed_cards([
        make_card(id="front", set="tla", collector_number="99", rarity="rare", name="Front Half"),
        make_card(id="back", set="tla", collector_number="99b", rarity="rare", name="Merged Back"),
    ])
    rows = _rows_for(["front", "back"])
    kept = {r.scryfall_id for r in missing.physical_buyable(rows, "tla")}
    assert "front" in kept
    assert "back" not in kept, "meld-back face leaked past physical_buyable"


def test_physical_buyable_toggles_are_independent(tmp_db, tla_family, seed_cards, make_card):
    from magic_manager import missing
    seed_cards([
        make_card(id="real", set="tla", collector_number="5", rarity="rare", name="Real Rare"),
        make_card(id="tok", set="tla", collector_number="20", rarity="rare",
                  name="Angel Token", layout="token"),
    ])
    rows = _rows_for(["real", "tok"])
    # drop_tokens=False keeps the token; the rest of the gate still runs.
    kept = {r.scryfall_id for r in missing.physical_buyable(rows, "tla", drop_tokens=False)}
    assert kept == {"real", "tok"}


def test_physical_buyable_single_digital_flag(tmp_db, tla_family, seed_cards, make_card):
    """drop_digital alone drops the digital print but NOT the token (the two
    digital/unobtainable guards are now independent — F3 removed the dead
    'both-flags' elif, so a single-flag call takes a defined path)."""
    from magic_manager import missing
    seed_cards([
        make_card(id="real", set="tla", collector_number="5", rarity="rare", name="Real Rare"),
        make_card(id="arena", set="tla", collector_number="6", rarity="rare",
                  name="Digital Rare", promo_types=[], security_stamp="arena"),
        make_card(id="tok", set="tla", collector_number="20", rarity="rare",
                  name="Angel Token", layout="token"),
    ])
    rows = _rows_for(["real", "arena", "tok"])
    kept = {r.scryfall_id for r in missing.physical_buyable(
        rows, "tla", drop_digital=True, drop_family_unobtainable=False,
        drop_datestamped_siblings=False, drop_meld_backs=False, drop_tokens=False)}
    assert kept == {"real", "tok"}  # only the digital print dropped


def test_physical_buyable_no_filter_is_identity(tmp_db, tla_family, seed_cards, make_card):
    """All toggles off ⇒ returns rows untouched (the --no-filter escape hatch)."""
    from magic_manager import missing
    seed_cards([
        make_card(id="tok", set="tla", collector_number="20", rarity="rare",
                  name="Angel Token", layout="token"),
    ])
    rows = _rows_for(["tok"])
    kept = missing.physical_buyable(
        rows, "tla", drop_tokens=False, drop_digital=False,
        drop_family_unobtainable=False, drop_datestamped_siblings=False,
        drop_meld_backs=False,
    )
    assert [r.scryfall_id for r in kept] == ["tok"]

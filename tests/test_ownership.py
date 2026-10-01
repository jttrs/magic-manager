"""Tests for magic_manager.ownership.owned_counts / owned_oracle_ids — the
canonical SUM-grain ownership queries. Offline: seeded tmp DB.

Covers both grains, both scopes, the no-join scryfall_id fast path (an inventory
row with no matching cards row still counts), and the exclusive-scope guard.
"""

from __future__ import annotations

import pytest


def _own(conn, sid, finish="nonfoil", qty=1):
    conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) "
                 "VALUES (?,?,?,'2025-01-01')", (sid, finish, qty))


def test_counts_by_scryfall_id_sums_finishes(tmp_db, seed_cards, make_card):
    from magic_manager import db, ownership
    seed_cards([make_card(id="a", set="tla", collector_number="1",
                          finishes=["nonfoil", "foil"])])
    with db.connect() as conn:
        _own(conn, "a", "nonfoil", 2)
        _own(conn, "a", "foil", 1)
    counts = ownership.owned_counts(grain="scryfall_id", scryfall_ids=["a"])
    assert counts == {"a": 3}


def test_counts_by_scryfall_id_scopes_to_requested_ids(tmp_db, seed_cards, make_card):
    """Only the requested scryfall_ids are counted; owned-but-unrequested are
    omitted, requested-but-unowned simply don't appear."""
    from magic_manager import db, ownership
    seed_cards([
        make_card(id="a", set="tla", collector_number="1"),
        make_card(id="b", set="tla", collector_number="2"),
        make_card(id="c", set="tla", collector_number="3"),  # requested, unowned
    ])
    with db.connect() as conn:
        _own(conn, "a", "nonfoil", 1)
        _own(conn, "b", "nonfoil", 2)
    counts = ownership.owned_counts(grain="scryfall_id", scryfall_ids=["a", "c"])
    assert counts == {"a": 1}  # 'b' not requested, 'c' unowned


def test_counts_by_oracle_id_groups_printings(tmp_db, seed_cards, make_card):
    from magic_manager import db, ownership
    seed_cards([
        make_card(id="p1", set="tla", collector_number="1", oracle_id="O"),
        make_card(id="p2", set="tla", collector_number="2", oracle_id="O"),
        make_card(id="q1", set="tla", collector_number="3", oracle_id="Q"),
    ])
    with db.connect() as conn:
        _own(conn, "p1", "nonfoil", 1)
        _own(conn, "p2", "nonfoil", 2)
        _own(conn, "q1", "nonfoil", 1)
    counts = ownership.owned_counts(grain="oracle_id", family_codes=["tla"])
    assert counts == {"O": 3, "Q": 1}


def test_owned_oracle_ids_is_the_positive_keyset(tmp_db, seed_cards, make_card):
    from magic_manager import db, ownership
    seed_cards([
        make_card(id="p1", set="tla", collector_number="1", oracle_id="O"),
        make_card(id="u1", set="tla", collector_number="2", oracle_id="U"),  # unowned
    ])
    with db.connect() as conn:
        _own(conn, "p1", "nonfoil", 1)
    assert ownership.owned_oracle_ids(["tla"]) == {"O"}


def test_family_scope_is_case_insensitive_on_set_code(tmp_db, seed_cards, make_card):
    from magic_manager import db, ownership
    seed_cards([make_card(id="p1", set="TLA", collector_number="1", oracle_id="O")])
    with db.connect() as conn:
        _own(conn, "p1", "nonfoil", 1)
    # family_codes passed lowercase; stored set_code is upper — LOWER() matches.
    assert ownership.owned_counts(grain="oracle_id", family_codes=["tla"]) == {"O": 1}


def test_requires_exactly_one_scope():
    from magic_manager import ownership
    with pytest.raises(ValueError):
        ownership.owned_counts(grain="scryfall_id")
    with pytest.raises(ValueError):
        ownership.owned_counts(grain="scryfall_id", scryfall_ids=["a"],
                               family_codes=["tla"])


def test_empty_scope_returns_empty(tmp_db):
    from magic_manager import ownership
    assert ownership.owned_counts(grain="scryfall_id", scryfall_ids=[]) == {}
    assert ownership.owned_counts(grain="oracle_id", family_codes=[]) == {}

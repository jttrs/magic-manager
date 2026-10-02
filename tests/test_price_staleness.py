"""Tests for the price-freshness fix: fetch-time stamps + staleness helpers.

Offline via conftest's tmp_db / make_card / fake_scryfall. The core behaviors:
  - upsert stamps prices_updated_at with the FETCH time, not released_at,
  - sets.stale_set_codes flags present-but-outdated sets (not missing ones),
  - sets.plan_sync splits missing vs stale,
  - sets.ensure_priced syncs missing always + stale only when refresh_stale.
"""

from __future__ import annotations

import pytest


def test_upsert_stamps_fetch_time_not_release(tmp_db, make_card):
    """prices_updated_at defaults to ~now (a fetch stamp), NOT the card's
    released_at (the old, staleness-blind proxy)."""
    from magic_manager import db
    card = make_card(id="s1", set="tst", collector_number="1",
                     released_at="2019-01-01")  # old release; must NOT become the price date
    with db.connect() as conn:
        db.upsert_card(conn, card)
        row = conn.execute(
            "SELECT prices_updated_at FROM cards WHERE scryfall_id='s1'").fetchone()
    stamp = row["prices_updated_at"][:4]
    assert stamp != "2019"  # not the release year
    # a real ISO date/time was stamped (current year, whatever the test runs in)
    assert row["prices_updated_at"] >= "2025-01-01"


def test_upsert_explicit_priced_at(tmp_db, make_card):
    from magic_manager import db
    with db.connect() as conn:
        db.upsert_card(conn, make_card(id="s2"), priced_at="2026-03-04T00:00:00")
        row = conn.execute(
            "SELECT prices_updated_at FROM cards WHERE scryfall_id='s2'").fetchone()
    assert row["prices_updated_at"] == "2026-03-04T00:00:00"


def test_upsert_cards_shares_one_stamp(tmp_db, make_card):
    """A batch shares a single fetch stamp."""
    from magic_manager import db
    cards = [make_card(id=f"b{i}", set="tst", collector_number=str(i)) for i in range(3)]
    with db.connect() as conn:
        db.upsert_cards(conn, cards, priced_at="2026-05-05T00:00:00")
        stamps = {r["prices_updated_at"] for r in
                  conn.execute("SELECT prices_updated_at FROM cards")}
    assert stamps == {"2026-05-05T00:00:00"}


def _seed(conn, sid, set_code, cn, priced_at):
    conn.execute(
        "INSERT INTO cards (scryfall_id, name, set_code, collector_number, rarity, "
        "prices_usd, prices_usd_foil, prices_updated_at) "
        "VALUES (?, 'C', ?, ?, 'rare', 1.0, 2.0, ?)",
        (sid, set_code, cn, priced_at),
    )


def test_stale_set_codes_flags_only_outdated(tmp_db):
    from magic_manager import db, sets
    with db.connect() as conn:
        _seed(conn, "f1", "fresh", "1", "2026-09-01")   # 4 days before today
        _seed(conn, "o1", "oldy", "1", "2026-06-01")    # months old
    stale = sets.stale_set_codes(["fresh", "oldy", "missing"], today="2026-09-05")
    assert "oldy" in stale
    assert "fresh" not in stale       # within 7 days
    assert "missing" not in stale     # no rows → that's unsynced, not stale


def test_stale_boundary_exactly_7_days(tmp_db):
    from magic_manager import db, sets
    with db.connect() as conn:
        _seed(conn, "e1", "edge", "1", "2026-08-29")   # exactly 7 days before
    # cutoff = today - 7 = 2026-08-29; strictly-less-than means 08-29 is NOT stale
    assert sets.stale_set_codes(["edge"], today="2026-09-05") == []
    # one day older IS stale
    with db.connect() as conn:
        conn.execute("UPDATE cards SET prices_updated_at='2026-08-28' WHERE scryfall_id='e1'")
    assert sets.stale_set_codes(["edge"], today="2026-09-05") == ["edge"]


def test_plan_sync_splits_missing_and_stale(tmp_db):
    from magic_manager import db, sets
    with db.connect() as conn:
        _seed(conn, "s1", "staleset", "1", "2020-01-01")
        _seed(conn, "f1", "freshset", "1", "2026-09-04")
    plan = sets.plan_sync(["staleset", "freshset", "missingset"], today="2026-09-05")
    assert plan["missing"] == ["missingset"]
    assert plan["stale"] == ["staleset"]  # freshset excluded, missingset not double-counted


def test_ensure_priced_syncs_missing_and_stale(tmp_db, monkeypatch):
    """refresh_stale=True (the explicit --refresh opt-in) syncs BOTH missing and
    stale; refresh_stale=False (the local-first DEFAULT) syncs only missing and
    reports stale for the caller to warn."""
    from magic_manager import db, sets
    with db.connect() as conn:
        _seed(conn, "s1", "staleset", "1", "2020-01-01")
    synced_calls = []
    monkeypatch.setattr(sets, "sync", lambda codes: synced_calls.append(sorted(codes)) or 0)

    # refresh_stale=True → syncs missing ∪ stale
    sets.ensure_priced(["staleset", "missingset"], refresh_stale=True, today="2026-09-05")
    assert synced_calls and set(synced_calls[0]) == {"staleset", "missingset"}

    # refresh_stale=False (default) → syncs only missing; stale left alone
    synced_calls.clear()
    plan = sets.ensure_priced(["staleset", "missingset"], refresh_stale=False,
                              today="2026-09-05")
    assert synced_calls == [["missingset"]]
    assert plan["stale"] == ["staleset"]


def test_priced_map_reads_local_without_network_when_fresh(tmp_db, make_card, monkeypatch):
    """priced_map(refresh=False) is local-first: it never calls sets.sync for a
    set whose newest price is within the freshness window."""
    from magic_manager import db, sets
    with db.connect() as conn:
        db.upsert_card(conn, make_card(id="f1", set="freshset", collector_number="1"),
                       priced_at="2026-09-04T00:00:00")

    sync_calls = []
    monkeypatch.setattr(sets, "sync", lambda codes: sync_calls.append(sorted(codes)) or 0)

    result = sets.priced_map(["f1"], refresh=False, today="2026-09-05")
    assert sync_calls == []
    assert result["f1"]["usd"] == 1.00
    assert result["f1"]["usd_foil"] == 2.00
    assert result["f1"]["prices_updated_at"] == "2026-09-04T00:00:00"


def test_priced_map_warns_on_stale_without_refresh(tmp_db, make_card, monkeypatch):
    """Stale sets trigger the warn callback with their codes when refresh=False,
    and sync is NOT called — local-first means stale is reported, not fetched."""
    from magic_manager import db, sets
    with db.connect() as conn:
        db.upsert_card(conn, make_card(id="s1", set="staleset", collector_number="1"),
                       priced_at="2020-01-01T00:00:00")

    sync_calls = []
    monkeypatch.setattr(sets, "sync", lambda codes: sync_calls.append(sorted(codes)) or 0)
    warned = []

    result = sets.priced_map(["s1"], refresh=False, today="2026-09-05", warn=warned.append)
    assert sync_calls == []
    assert warned == [["staleset"]]
    # local price is still returned as-is
    assert result["s1"]["usd"] == 1.00


def test_priced_map_refresh_true_syncs_stale(tmp_db, make_card, monkeypatch):
    """refresh=True re-syncs stale sets (and does not warn)."""
    from magic_manager import db, sets
    with db.connect() as conn:
        db.upsert_card(conn, make_card(id="s1", set="staleset", collector_number="1"),
                       priced_at="2020-01-01T00:00:00")

    sync_calls = []
    monkeypatch.setattr(sets, "sync", lambda codes: sync_calls.append(sorted(codes)) or 0)
    warned = []

    sets.priced_map(["s1"], refresh=True, today="2026-09-05", warn=warned.append)
    assert sync_calls == [["staleset"]]
    assert warned == []

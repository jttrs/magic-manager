"""Tests for sets.sync's per-batch-commit resilience.

sync() commits each ~60-code Scryfall batch in its OWN transaction, so a
transient failure on a later batch does NOT discard the batches that already
succeeded — it raises SyncBatchError instead, and the completed batches stay
persisted (a re-run only redoes the tail). Offline via a stateful monkeypatch
of scryfall.search (the built-in fake_scryfall returns one canned list for every
query, so it can't distinguish batch 1 from batch 2 — we need per-call control).
"""

from __future__ import annotations

import pytest


def _codes(n: int) -> list[str]:
    """n distinct set codes → forces ceil(n/60) batches in sync()."""
    return [f"s{i:03d}" for i in range(n)]


def test_sync_partial_progress_survives_batch_failure(tmp_db, make_card, monkeypatch):
    """Batch 1 commits; batch 2 raises → SyncBatchError, but batch-1 cards PERSIST.

    Pre-fix (one transaction around all batches) this count would be 0.
    """
    from magic_manager import sets, scryfall, db

    calls = {"n": 0}

    def fake_search(query, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            # Batch 1: yield two cards that get upserted + committed.
            yield make_card(id="b1c1", set="s000", collector_number="1")
            yield make_card(id="b1c2", set="s000", collector_number="2")
        else:
            # Batch 2: transient Scryfall failure mid-run.
            raise scryfall.ScryfallError("simulated transient 503")

    monkeypatch.setattr(scryfall, "search", fake_search)

    codes = _codes(120)  # 2 batches of 60
    with pytest.raises(sets.SyncBatchError) as ei:
        sets.sync(codes)

    err = ei.value
    assert err.batch_index == 2 and err.batch_count == 2
    assert err.cards_done == 2                       # batch-1 cards were counted
    assert err.failed_codes == codes[60:120]         # the aborted batch
    assert isinstance(err.__cause__, scryfall.ScryfallError)

    # The crux: batch-1 cards are DURABLE despite batch-2's failure.
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 2
        assert conn.execute(
            "SELECT COUNT(*) FROM cards WHERE scryfall_id IN ('b1c1','b1c2')"
        ).fetchone()[0] == 2


def test_sync_all_success_reports_progress_per_batch(tmp_db, make_card, monkeypatch):
    """All batches succeed → full count returned, no error, progress called once
    per batch with a monotonic running total."""
    from magic_manager import sets, scryfall, db

    calls = {"n": 0}

    def fake_search(query, **kwargs):
        calls["n"] += 1
        # One card per batch (id keyed by batch so both persist distinctly).
        yield make_card(id=f"c{calls['n']}", set="s000",
                        collector_number=str(calls["n"]))

    monkeypatch.setattr(scryfall, "search", fake_search)

    seen: list[tuple[int, int, int]] = []
    n = sets.sync(_codes(120), progress=lambda bi, bc, done: seen.append((bi, bc, done)))

    assert n == 2                                    # one card per batch × 2 batches
    assert seen == [(1, 2, 1), (2, 2, 2)]            # per-batch, running total
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 2


def test_sync_single_batch_no_progress_callback_still_works(tmp_db, make_card, monkeypatch):
    """The progress kwarg is additive/optional — omitting it (every existing
    caller) still works, and a single-batch (<60 codes) run is unaffected."""
    from magic_manager import sets, scryfall, db

    monkeypatch.setattr(scryfall, "search",
                        lambda *a, **k: iter([make_card(id="x", set="ncc", collector_number="1")]))
    n = sets.sync(["ncc"])
    assert n == 1
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM cards WHERE scryfall_id='x'").fetchone()[0] == 1

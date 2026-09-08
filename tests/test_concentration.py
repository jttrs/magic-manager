"""Tests for the missing-$ scarcity-tier concentration flag (missing.concentration
/ is_concentrated). Pure functions — no DB, no network; rows are built by hand
and prices injected via a dict-backed price_fn.

The flag is ADVISORY (a review prompt), so these assert the math + the trigger
boundary, NOT any exclude/keep decision.
"""

from __future__ import annotations

from magic_manager import missing
from magic_manager.selectors import MaterializedRow


def _row(sid, finish="nonfoil", name="C", st="tst", cn="1"):
    return MaterializedRow(scryfall_id=sid, quantity=1, finish=finish,
                           card={"name": name, "set": st, "collector_number": cn})


def _price_fn(prices):
    return lambda sid, finish: prices.get((sid, finish), 0.0)


def test_concentration_math():
    """Exact top5_share / over_100_share on a hand-built distribution."""
    rows = [_row(f"s{i}", cn=str(i)) for i in range(6)]
    prices = {("s0", "nonfoil"): 900.0, ("s1", "nonfoil"): 100.0,
              ("s2", "nonfoil"): 10.0, ("s3", "nonfoil"): 10.0,
              ("s4", "nonfoil"): 10.0, ("s5", "nonfoil"): 10.0}
    c = missing.concentration(rows, _price_fn(prices))
    assert c["total_usd"] == 1040.0
    assert c["n"] == 6
    # top5 = 900+100+10+10+10 = 1030 / 1040
    assert abs(c["top5_share"] - 1030.0 / 1040.0) < 1e-9
    # only s0 is strictly > 100 → 900/1040
    assert c["n_over_100"] == 1
    assert abs(c["over_100_share"] - 900.0 / 1040.0) < 1e-9
    assert c["top_prints"][0][0] == "C" and c["top_prints"][0][4] == 900.0


def test_unpriced_rows_ignored():
    rows = [_row("a"), _row("b")]
    c = missing.concentration(rows, _price_fn({("a", "nonfoil"): 5.0}))  # b unpriced
    assert c["n"] == 1 and c["total_usd"] == 5.0


def test_empty_is_safe():
    c = missing.concentration([], _price_fn({}))
    assert c["total_usd"] == 0.0 and c["top_prints"] == []
    assert missing.is_concentrated(c) is False


def test_is_concentrated_fires_on_spm_like():
    """Few huge + many small, big total → fires (over_100_share high)."""
    rows = [_row("chase", finish="foil")] + [_row(f"s{i}", cn=str(i)) for i in range(40)]
    prices = {("chase", "foil"): 1800.0}
    prices.update({(f"s{i}", "nonfoil"): 3.0 for i in range(40)})
    c = missing.concentration(rows, _price_fn(prices))
    assert c["total_usd"] >= missing.CONCENTRATION_MIN_USD
    assert missing.is_concentrated(c) is True


def test_is_concentrated_quiet_on_flat():
    """Many similar low-value prints → not flagged even if total is modest."""
    rows = [_row(f"s{i}", cn=str(i)) for i in range(200)]
    prices = {(f"s{i}", "nonfoil"): 4.0 for i in range(200)}  # $800 total, flat
    c = missing.concentration(rows, _price_fn(prices))
    assert c["total_usd"] == 800.0            # above MIN_USD…
    assert c["over_100_share"] == 0.0          # …but no high-value concentration
    assert c["top5_share"] < missing.CONCENTRATION_TOP5_SHARE
    assert missing.is_concentrated(c) is False


def test_is_concentrated_quiet_below_min_usd():
    """A concentrated shape under the $ floor isn't worth flagging."""
    rows = [_row("big", finish="foil"), _row("s1")]
    prices = {("big", "foil"): 300.0, ("s1", "nonfoil"): 5.0}  # $305 total < 750 floor
    c = missing.concentration(rows, _price_fn(prices))
    assert c["over_100_share"] > 0.9           # very concentrated…
    assert missing.is_concentrated(c) is False  # …but below MIN_USD

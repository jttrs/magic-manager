"""Thin wrapper over manapool.sh 'sealed' + a sealed-product MarketProvider.

Mana Pool prices SEALED products by an EXACT MTGJSON-uuid join — the same
``node_meta["uuid"]`` every ``sealed.ProductNode`` carries (``sealed._market_meta``).
No fuzzy matching, unlike eBay (title search) or tcgapi (set-name search); it's
the most robust join of any market provider here, and it reuses the already-
sanctioned ``manapool.sh`` wrapper + ``manapool-guard.sh`` hook (no new
wrapper/guard/settings).

Prices are in CENTS. The deterministic market price prefers ``price_market``
(Mana Pool's market price, populated on liquid products) and falls back to
``low_price`` (the lowest available ask / floor). ``recent_sales`` is REAL
settled-transaction data (timestamps + cents) — a genuine sold-comp signal
(which eBay's Browse API can't provide) — but the set of recent sales drifts per
fetch, so its median is surfaced as an ADVISORY annotation (``full()``), never in
the deterministic market column (``price()``). This mirrors ``ebay.py``'s
``price``/``full`` split.

Auth: ``manapool.sh`` reads ``MANAPOOL_EMAIL`` + ``MANAPOOL_ACCESS_TOKEN`` from
``.env`` and exits 2 when either is missing; that surfaces here as
``ManapoolUnconfigured`` so ``sealed._build_providers`` drops the provider with a
stderr note. Memoized per uuid; the wrapper's 24h cache keeps a whole tree cheap.
"""

from __future__ import annotations

import json
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path

WRAPPER = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "manapool-search" / "manapool.sh"
)

# A well-formed but non-existent uuid → the API returns a clean {"data":[]}. Used
# to probe credential configuration without hitting a real product. (A non-uuid
# string like "__probe__" would 400 as an invalid format, so use a valid shape.)
_PROBE_UUID = "00000000-0000-0000-0000-000000000000"


class ManapoolError(RuntimeError):
    """Raised when the wrapper exits non-zero (other than the no-creds exit 2)."""


class ManapoolUnconfigured(ManapoolError):
    """Raised (wrapper exit 2) when MANAPOOL_EMAIL/ACCESS_TOKEN are absent — a
    soft, expected condition that drops the provider."""


def _run(args: list[str]) -> dict:
    if not WRAPPER.exists():
        raise ManapoolError(f"wrapper missing: {WRAPPER}")
    res = subprocess.run(
        [str(WRAPPER), *args], text=True, capture_output=True, check=False,
    )
    if res.returncode == 2:   # manapool.sh's missing-creds exit (lines 45-48)
        raise ManapoolUnconfigured(res.stderr.strip() or "MANAPOOL_* not set")
    if res.returncode != 0:
        raise ManapoolError(
            f"manapool.sh {' '.join(args)} exited {res.returncode}: "
            f"{res.stderr.strip() or res.stdout.strip()}"
        )
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise ManapoolError(f"non-JSON response from manapool.sh {args}: {e}") from e


def _usd(cents) -> float | None:
    """Cents → dollars, or None for 0/absent (mirrors manapool_common's convention)."""
    return round(cents / 100.0, 2) if isinstance(cents, (int, float)) and cents else None


@dataclass
class ManapoolSealed:
    """A Mana Pool sealed-product price snapshot for one product."""
    market: float | None       # price_market>0 else low_price, in $ (the deterministic figure)
    low: float | None          # low_price floor, in $
    n_available: int
    recent_sales_median: float | None   # median of recent_sales prices, $ (ADVISORY)
    n_sales: int
    as_of: str = ""

    def as_display(self) -> str:
        parts: list[str] = []
        if self.market is not None:
            parts.append(f"${self.market:.2f} market")
        if self.low is not None and self.low != self.market:
            parts.append(f"${self.low:.2f} floor")
        if self.recent_sales_median is not None:
            parts.append(f"sold-median ${self.recent_sales_median:.2f} (n={self.n_sales})")
        parts.append(f"{self.n_available} available")
        return " / ".join(parts) if parts else "(no Mana Pool data)"


def _parse(row: dict) -> ManapoolSealed:
    """Build a :class:`ManapoolSealed` from one /products/sealed data row."""
    market_c = row.get("price_market") or 0
    low_c = row.get("low_price") or 0
    chosen_c = market_c if market_c > 0 else low_c
    sales = row.get("recent_sales") or []
    sale_prices = [s["price"] for s in sales
                   if isinstance(s.get("price"), (int, float))]
    med = round(statistics.median(sale_prices) / 100.0, 2) if sale_prices else None
    return ManapoolSealed(
        market=_usd(chosen_c),
        low=_usd(low_c),
        n_available=int(row.get("available_quantity") or 0),
        recent_sales_median=med,
        n_sales=len(sale_prices),
    )


class ManapoolMarketProvider:
    """A ``sealed.MarketProvider`` backed by Mana Pool, joined by MTGJSON uuid.

    ``price(node_meta)`` returns the deterministic market $ (``price_market>0``
    else ``low_price``); ``full(node_meta)`` returns the structured
    :class:`ManapoolSealed` incl. the advisory recent-sales median. Raises
    ``ManapoolUnconfigured`` at construction if creds are absent so the assembler
    drops it. Memoizes per uuid."""

    name = "manapool"

    def __init__(self):
        # Eager config probe: any manapool.sh call exits 2 without creds. A
        # well-formed non-existent uuid returns a clean {"data":[]}, so only the
        # creds exit trips this (matches tcgapi/ebay eager-probe pattern).
        try:
            _run(["sealed", _PROBE_UUID])
        except ManapoolUnconfigured:
            raise
        except ManapoolError:
            pass   # network/other issues degrade per-call, not at construction
        self._cache: dict[str, ManapoolSealed | None] = {}

    def _lookup(self, uuid: str) -> ManapoolSealed | None:
        if uuid not in self._cache:
            try:
                data = _run(["sealed", uuid]).get("data") or []
            except ManapoolError:
                self._cache[uuid] = None
            else:
                self._cache[uuid] = _parse(data[0]) if data else None
        return self._cache[uuid]

    def full(self, node_meta: dict) -> ManapoolSealed | None:
        uuid = node_meta.get("uuid")
        return self._lookup(uuid) if uuid else None

    def price(self, node_meta: dict) -> float | None:
        snap = self.full(node_meta)
        return snap.market if snap else None

"""Thin wrapper over ebay.sh + an ADVISORY market provider.

eBay comps are ADVISORY ONLY: they vary per fetch, so they NEVER enter the
deterministic artifact rows — ``sealed_value.py`` puts the value in a separate
``ebay_advisory_usd`` field/line, clearly labeled. The Browse API returns ACTIVE
listings (a listed-price ceiling), not sold comps (those need eBay's restricted
Marketplace Insights API).

Auth: eBay app tokens expire ~2h, so ``ebay.sh`` MINTS one on demand from
``EBAY_CLIENT_ID`` + ``EBAY_CLIENT_SECRET`` (developer.ebay.com App ID / Cert ID)
and caches it; a pre-minted ``EBAY_OAUTH_TOKEN`` is honored as an override. With
none of these in ``.env`` the wrapper exits 7 and the provider degrades to
``None``.

The provider searches by product NAME (eBay has no TCGplayer-product-id key) and
returns a robust central estimate (median of active-listing prices) as the
advisory figure. Because active listings ≠ sold comps, treat the number as a
rough ceiling, not a settlement price.
"""

from __future__ import annotations

import json
import statistics
import subprocess
from pathlib import Path

WRAPPER = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "sealed-value" / "ebay.sh"
)


class EbayError(RuntimeError):
    pass


class EbayUnconfigured(EbayError):
    """Raised (exit 7) when eBay credentials are absent — a soft condition."""


def _run(args: list[str]) -> dict:
    if not WRAPPER.exists():
        raise EbayError(f"wrapper missing: {WRAPPER}")
    res = subprocess.run(
        [str(WRAPPER), *args], text=True, capture_output=True, check=False,
    )
    if res.returncode == 7:
        raise EbayUnconfigured(res.stderr.strip() or "eBay credentials not set")
    if res.returncode != 0:
        raise EbayError(
            f"ebay.sh {' '.join(args)} exited {res.returncode}: "
            f"{res.stderr.strip() or res.stdout.strip()}"
        )
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise EbayError(f"non-JSON response from ebay.sh {args}: {e}") from e


def _median_listing_price(body: dict) -> float | None:
    """Median price across an eBay Browse ``itemSummaries`` response, or None.

    Defensive against schema drift: each summary's price is at
    ``price.value`` (a string). Median resists the sky-high 'lot of 100' and
    the lowball 'empty wrapper' outliers active listings are full of."""
    items = body.get("itemSummaries") or []
    prices: list[float] = []
    for it in items:
        pv = ((it.get("price") or {}).get("value"))
        try:
            if pv is not None:
                prices.append(float(pv))
        except (TypeError, ValueError):
            continue
    if not prices:
        return None
    return round(statistics.median(prices), 2)


def advisory_price(product_name: str) -> float | None:
    """Advisory central price for a product name via active eBay listings."""
    try:
        body = _run(["search", product_name])
    except EbayUnconfigured:
        return None
    return _median_listing_price(body)


class EbayAdvisoryProvider:
    """Advisory-only ``sealed.MarketProvider``. Memoizes per product name.

    Raises ``EbayUnconfigured`` at construction if credentials are absent so the
    caller can drop it."""

    name = "ebay-advisory"

    def __init__(self):
        res = subprocess.run(
            [str(WRAPPER), "raw", "/__probe__"], text=True,
            capture_output=True, check=False,
        )
        if res.returncode == 7:
            raise EbayUnconfigured(res.stderr.strip() or "eBay credentials not set")
        self._cache: dict[str, float | None] = {}

    def price(self, node_meta: dict) -> float | None:
        name = node_meta.get("name")
        if not name:
            return None
        if name not in self._cache:
            self._cache[name] = advisory_price(name)
        return self._cache[name]

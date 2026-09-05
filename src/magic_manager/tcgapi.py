"""Thin wrapper over tcgapi.sh (TCG API / tcgapi.dev) + a MarketProvider.

A SECONDARY market source to :mod:`tcgcsv` — independent TCGplayer price data
behind an ``X-API-Key`` (free tier 100 req/day). Useful for the
``--market compare`` cross-check. Requires ``TCGAPI_KEY`` in the repo ``.env``;
without it the wrapper exits 7 and the provider degrades to ``None`` (so a
compare run silently drops this column rather than crashing).

**Search-keyed, but matched by id.** tcgapi.dev has no lookup-by-productId
endpoint — it is search-only (``/v1/search?q=<query>&game=magic``, container
``data``, paginated via ``meta.has_more``/``page``). BUT each result row carries
``tcgplayer_id`` — the same ``tcgplayerProductId`` MTGJSON gives each product. So
the provider searches by the **set name** (tcgapi names products
``<set> - <product>``, e.g. "Magic 2015 (M15) - Booster Box", so a product-name
search misses; a set-name search surfaces all the set's products in one call)
and matches back by ``tcgplayer_id`` — an EXACT id join, as robust as tcgcsv's.
A no-id-match degrades to ``None``. Confirmed live 2026-09-04: response fields
``id, name, tcgplayer_id, product_type ('Sealed Products'/'Cards'), market_price,
low_price, median_price, total_listings``; M15 Booster Box → $375.83 (matches
tcgcsv exactly).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

WRAPPER = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "sealed-value" / "tcgapi.sh"
)


class TcgapiError(RuntimeError):
    """Raised when the wrapper exits non-zero (other than the no-key exit 7)."""


class TcgapiUnconfigured(TcgapiError):
    """Raised (exit 7) when TCGAPI_KEY is absent — a soft, expected condition."""


def _run(args: list[str]) -> dict:
    if not WRAPPER.exists():
        raise TcgapiError(f"wrapper missing: {WRAPPER}")
    res = subprocess.run(
        [str(WRAPPER), *args], text=True, capture_output=True, check=False,
    )
    if res.returncode == 7:
        raise TcgapiUnconfigured(res.stderr.strip() or "TCGAPI_KEY not set")
    if res.returncode != 0:
        raise TcgapiError(
            f"tcgapi.sh {' '.join(args)} exited {res.returncode}: "
            f"{res.stderr.strip() or res.stdout.strip()}"
        )
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise TcgapiError(f"non-JSON response from tcgapi.sh {args}: {e}") from e


_MAX_PAGES = 10  # runaway guard; a set's product list is well under 500 rows


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _result_price(row: dict) -> float | None:
    """Market price from one search-result row (market → median → low)."""
    for key in ("market_price", "median_price", "low_price"):
        v = _num(row.get(key))
        if v is not None:
            return v
    return None


def set_prices_by_id(set_name: str) -> dict[int, float]:
    """``{tcgplayer_id: market_price}`` for every priced product tcgapi returns
    for a set-name search, following pagination.

    Searching the SET name (not a product name) surfaces all of a set's products
    in one query family, because tcgapi names them ``<set> - <product>``. Rows
    carry ``tcgplayer_id`` (== MTGJSON's ``tcgplayerProductId``), so the caller
    matches by id — an exact join. Returns ``{}`` when unconfigured/empty."""
    out: dict[int, float] = {}
    page = 1
    while page <= _MAX_PAGES:
        try:
            body = _run(["raw", _search_path(set_name, page)])
        except TcgapiUnconfigured:
            return {}
        rows = body.get("data") if isinstance(body, dict) else None
        if not isinstance(rows, list):
            break
        for r in rows:
            tid = r.get("tcgplayer_id")
            price = _result_price(r)
            if tid is not None and price is not None and int(tid) not in out:
                out[int(tid)] = price
        meta = (body.get("meta") or {}) if isinstance(body, dict) else {}
        if not meta.get("has_more"):
            break
        page += 1
    return out


def _search_path(query: str, page: int) -> str:
    from urllib.parse import quote
    q = quote(query, safe="")
    return f"/v1/search?q={q}&game=magic&page={page}"


class TcgapiMarketProvider:
    """A ``sealed.MarketProvider`` backed by TCG API, matched by ``tcgplayer_id``.

    Raises ``TcgapiUnconfigured`` at construction time if the key is absent, so
    callers can choose to skip it; the ``sealed_value.py`` assembler catches that
    and drops the provider. Memoizes each set's ``{id: price}`` table so a whole
    tree costs one search per referenced set."""

    name = "tcgapi"

    def __init__(self):
        # Probe configuration eagerly so an unconfigured provider is dropped
        # rather than returning None for every node with no explanation.
        res = subprocess.run(
            [str(WRAPPER), "raw", "/__probe__"], text=True,
            capture_output=True, check=False,
        )
        if res.returncode == 7:
            raise TcgapiUnconfigured(res.stderr.strip() or "TCGAPI_KEY not set")
        self._by_set: dict[str, dict[int, float]] = {}

    def price(self, node_meta: dict) -> float | None:
        set_name = node_meta.get("set_name")
        pid = node_meta.get("tcgplayer_product_id")
        if not set_name or not pid:
            return None
        if set_name not in self._by_set:
            self._by_set[set_name] = set_prices_by_id(set_name)
        return self._by_set[set_name].get(int(pid))

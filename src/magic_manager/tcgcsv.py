"""Thin Python wrapper over the project's tcgcsv.sh script + a MarketProvider.

tcgcsv.com is a free, no-auth mirror of TCGplayer's public price + product data,
keyed by TCGplayer's categoryId (Magic = 1) and groupId (== MTGJSON's
``tcgplayerGroupId``). We use it for SEALED product market prices, which
MTGJSON's own price feed does not carry. Every request goes through tcgcsv.sh
(24h cache, paced); a PreToolUse hook blocks direct ``curl tcgcsv.com``.

The ``TcgcsvMarketProvider`` satisfies ``sealed.MarketProvider``: given a node's
``{tcgplayer_group_id, tcgplayer_product_id}`` it returns the sealed product's
market price (``marketPrice``, falling back to ``midPrice``). It memoizes each
group's price table so a whole tree costs one request per referenced group.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

MAGIC_CATEGORY_ID = 1

WRAPPER = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "sealed-value" / "tcgcsv.sh"
)


class TcgcsvError(RuntimeError):
    """Raised when the wrapper exits non-zero or returns non-JSON."""


def _run(args: list[str]) -> dict:
    if not WRAPPER.exists():
        raise TcgcsvError(f"wrapper missing: {WRAPPER}")
    res = subprocess.run(
        [str(WRAPPER), *args], text=True, capture_output=True, check=False,
    )
    if res.returncode != 0:
        raise TcgcsvError(
            f"tcgcsv.sh {' '.join(args)} exited {res.returncode}: "
            f"{res.stderr.strip() or res.stdout.strip()}"
        )
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise TcgcsvError(f"non-JSON response from tcgcsv.sh {args}: {e}") from e


def prices(group_id: int, *, category_id: int = MAGIC_CATEGORY_ID) -> dict[int, dict]:
    """Return ``{productId: price_row}`` for a TCGplayer group.

    A product can have multiple subtypes (Normal / Foil); sealed products are
    ``Normal``, so we keep the ``Normal`` row when present, else the first row.
    Each price_row carries ``lowPrice/midPrice/highPrice/marketPrice/…``."""
    body = _run(["prices", str(group_id), str(category_id)])
    out: dict[int, dict] = {}
    for row in body.get("results") or []:
        pid = row.get("productId")
        if pid is None:
            continue
        # Prefer the Normal subtype (sealed products); don't clobber it with Foil.
        if pid not in out or row.get("subTypeName") == "Normal":
            out[int(pid)] = row
    return out


class TcgcsvMarketProvider:
    """A ``sealed.MarketProvider`` backed by tcgcsv.com. Memoizes per group."""

    name = "tcgcsv"

    def __init__(self, *, category_id: int = MAGIC_CATEGORY_ID):
        self.category_id = category_id
        self._cache: dict[int, dict[int, dict]] = {}

    def _group_prices(self, group_id: int) -> dict[int, dict]:
        if group_id not in self._cache:
            self._cache[group_id] = prices(group_id, category_id=self.category_id)
        return self._cache[group_id]

    def price(self, node_meta: dict) -> float | None:
        group = node_meta.get("tcgplayer_group_id")
        pid = node_meta.get("tcgplayer_product_id")
        if not group or not pid:
            return None
        try:
            row = self._group_prices(int(group)).get(int(pid))
        except TcgcsvError:
            return None
        if not row:
            return None
        val = row.get("marketPrice") or row.get("midPrice")
        return float(val) if val is not None else None

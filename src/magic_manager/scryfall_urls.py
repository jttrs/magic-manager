"""Shared Scryfall search-URL chunking — the single home for turning a list of
printings into browser-safe (≤20-term) Scryfall URLs. Both `mm query missing-set`
and `mm query url --mode prints` and `mm query card-diff` route through here so
the 20-condition web-UI cap is enforced in exactly one place.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

CHUNK_DEFAULT = 20  # Scryfall web UI caps OR'd queries at 20 nested conditions.


@dataclass
class UrlChunk:
    index: int        # 1-based
    n: int            # printings in this chunk
    price_lo: float | None
    price_hi: float | None
    url: str


def printing_url_chunks(
    printings: list[tuple[str, str]],
    *,
    chunk_size: int = CHUNK_DEFAULT,
    prices: list[float | None] | None = None,
) -> list[UrlChunk]:
    """Chunk `printings` (a list of `(set_code, collector_number)` pairs, in the
    DESIRED ORDER — caller pre-sorts, e.g. cheapest-first) into browser-safe
    Scryfall search URLs.

    `prices` is an optional parallel list of per-printing `float | None` (same
    order/length as `printings`) used to compute the price band (first/last
    printing in each chunk) — `None` when the caller has no price data.

    Builds `(set:CODE cn:"CN") or …` terms joined by `" or "`, then
    `unique=prints&order=usd&dir=asc` so Scryfall returns each printing as a
    separate result, cheapest-first.
    """
    chunks: list[UrlChunk] = []
    n = len(printings)
    for start in range(0, n, chunk_size):
        chunk = printings[start:start + chunk_size]
        idx = start // chunk_size + 1
        terms = " or ".join(f'(set:{s} cn:"{cn}")' for s, cn in chunk)
        url = f"https://scryfall.com/search?q={quote_plus(terms)}&unique=prints&order=usd&dir=asc"
        if prices is not None:
            price_chunk = prices[start:start + chunk_size]
            price_lo = price_chunk[0] if price_chunk else None
            price_hi = price_chunk[-1] if price_chunk else None
        else:
            price_lo = price_hi = None
        chunks.append(UrlChunk(index=idx, n=len(chunk), price_lo=price_lo, price_hi=price_hi, url=url))
    return chunks


def dedupe_printings(rows) -> list[tuple[str, str]]:
    """Collapse MaterializedRows to ordered unique `(set, cn)` pairs, skipping
    rows with an empty set or collector_number. Preserves first-seen order."""
    seen: set[tuple[str, str]] = set()
    printings: list[tuple[str, str]] = []
    for r in rows:
        setc = r.card.get("set") or ""
        cn = r.card.get("collector_number") or ""
        if not setc or not cn:
            continue
        key = (setc, cn)
        if key in seen:
            continue
        seen.add(key)
        printings.append(key)
    return printings

"""Shared Scryfall search-URL chunking — the single home for turning a list of
printings into browser-safe (≤20-term) Scryfall URLs. `mm query missing-set`
and `mm query card-diff` share both the chunking (`printing_url_chunks`) and
the markdown-table rendering (`render_chunk_table`) of the resulting chunks.
`mm query url --mode prints` uses a different plain-text format and does not
route through the shared renderer.
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


def render_chunk_table(chunks: list[UrlChunk]) -> list[str]:
    """Render `chunks` as markdown table lines: a header row, a separator
    row, and one row per chunk (`| # | Printings | Price band | URL |`,
    prices em-dash `—` when `None`, band as `lo → hi`, URL cell as
    `[chunk N](url)`). Returns the lines for the caller to `typer.echo`
    individually (or join); does not emit a leading/trailing blank line."""
    lines = ["| # | Printings | Price band | URL |", "|---:|---:|---|---|"]
    for uc in chunks:
        cs = f"${uc.price_lo:.2f}" if uc.price_lo is not None else "—"
        ms = f"${uc.price_hi:.2f}" if uc.price_hi is not None else "—"
        lines.append(f"| {uc.index} | {uc.n} | {cs} → {ms} | [chunk {uc.index}]({uc.url}) |")
    return lines


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

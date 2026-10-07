"""Secret Lair in Market: the recent drops, each priced sealed vs the cards inside.

Thin composition (no new valuation math): drop discovery is :mod:`sld`
(``recent_drops`` — base + Foil Edition merged into one logical drop), the
sealed product per edition is :func:`valuation.sld_sealed_product`, and every
figure comes from :func:`market.product_cost` (``kind='sld'``, memoized 30 min):
the TCGplayer-market sealed price, the cards inside — the drop's cards plus its
bonus card (or bonus-pack EV) — at their exact printings and at each card's
cheapest printing. Consumed by ``api.market`` (the web Market → Secret Lair
subject) and ``scripts/secret_lair_value.py`` (the markdown table).
"""
from __future__ import annotations

from typing import Callable

from . import market, sld, valuation

EDITIONS = ("nonfoil", "foil")


def tcgplayer_url(product: dict | None) -> str | None:
    """The TCGplayer product page of an MTGJSON sealed product (its direct
    product id, not MTGJSON's redirect link) — the store link a watched drop
    tracks."""
    pid = ((product or {}).get("identifiers") or {}).get("tcgplayerProductId")
    return f"https://www.tcgplayer.com/product/{pid}" if pid else None


def _edition(drop: dict, edition: str) -> dict | None:
    """One edition of a drop: whether MTGJSON lists it, its sealed product + TCGplayer page."""
    has_deck = any(fn.endswith("FoilEdition_SLD") == (edition == "foil") for fn in drop["file_names"] if fn)
    product = valuation.sld_sealed_product(drop["name"], edition, strict=True)
    if not has_deck and product is None:
        return None
    return {"finish": edition, "sealed_name": product.get("name") if product else None,
            "tcgplayer_url": tcgplayer_url(product)}


def recent(limit: int = 30) -> dict:
    """The ``limit`` most recent drops (newest first), each with the editions it
    ships in. Instant-ish (MTGJSON files are cached); values are per drop via
    :func:`value`. Returns ``{"total", "drops": [{name, release_date, editions}]}``."""
    chosen, total = sld.recent_drops(max(1, limit))
    drops = []
    for d in chosen:
        eds = [e for e in (_edition(d, ed) for ed in EDITIONS) if e is not None]
        drops.append({"name": d["name"], "release_date": d.get("release_date"), "editions": eds})
    return {"total": total, "drops": drops}


def value(name: str, finish: str | None = None) -> dict:
    """One drop edition's worth — :func:`market.product_cost` for ``kind='sld'``."""
    return market.product_cost("sld", "sld", name, finish or "nonfoil")


def gap(cost: dict, basis: str = "exact") -> dict | None:
    """Sealed price vs the cards inside (``basis`` = ``exact`` | ``floor``):
    ``{"usd": sealed − cards, "pct": that as % of cards}`` — negative ⇒ the
    sealed drop costs less than its cards. None when either side is unpriced."""
    cards, sealed = cost.get(basis), cost.get("market")
    if not cards or sealed is None:
        return None
    usd = round(sealed - cards, 2)
    return {"usd": usd, "pct": round(usd / cards * 100, 1)}


def survey(limit: int = 30, finish: str = "nonfoil", *,
           progress: Callable[[int, int, str], None] | None = None) -> list[dict]:
    """Value the recent drops at one edition: each row is the drop (name, release)
    plus :func:`value` — or ``error`` when it can't be valued. Drops without that
    edition are skipped."""
    drops = [d for d in recent(limit)["drops"] if any(e["finish"] == finish for e in d["editions"])]
    rows = []
    for i, d in enumerate(drops, 1):
        if progress:
            progress(i, len(drops), d["name"])
        try:
            rows.append({**d, "finish": finish, "cost": value(d["name"], finish), "error": None})
        except Exception as e:  # noqa: BLE001 — one bad drop never sinks the table
            rows.append({**d, "finish": finish, "cost": None, "error": str(e)})
    return rows

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

The provider searches by product NAME (eBay has no TCGplayer-product-id key in
MTGJSON), then FILTERS the keyword-search noise before aggregating — a plain
median over eBay's fuzzy results is misleading (a "Magic 2015 Booster Box"
search returns Modern Masters 2015, Fate Reforged, Origins, single packs, and
empty wrappers). We keep only New/Factory-Sealed listings whose title overlaps
the query tokens strongly AND (when the product name carries a set-code/year
token like ``m15``/``2015``) contains one of those discriminator tokens, then
take an interquartile-trimmed median. If too few listings survive the filter we
return ``None`` — an honest "can't confidently price" rather than a noisy guess.

Because active listings ≠ sold comps AND the match is title-heuristic (eBay
gives us no product-id join), treat the number as a ROUGH ceiling, not a
settlement price. This is why eBay is advisory-only and never deterministic.
"""

from __future__ import annotations

import json
import re
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Generic words that carry no product identity — dropped from query tokens so
# matching keys on the distinguishing terms (set name/code + product type).
_STOPWORDS = frozenset({
    "the", "a", "an", "of", "for", "and", "mtg", "magic", "gathering", "tcg",
    "card", "cards", "game", "trading", "english", "sealed", "factory", "new",
    "set",
})
# Product-type tokens: a matching listing must share at least one, so a
# "Booster Box" query never matches a loose "Booster Pack" or a "Bundle".
_TYPE_TOKENS = frozenset({
    "box", "booster", "bundle", "pack", "deck", "case", "collector", "draft",
    "play", "kit", "fat", "gift", "tin", "blister",
})
# Minimum surviving listings to trust a median (else return None).
_MIN_MATCHES = 3
# Title substrings that mark a listing as NOT the sealed SKU we want — empty
# collectible boxes, loose single/multi packs sold under a box-ish search, and
# lot/quantity phrasing. Matched case-insensitively on the raw title.
_NEGATIVE_MARKERS = (
    "empty", "read ", "promo booster", "6-card", "6 card",
    "x 3", "x3 ", "10x", "9x", "5x", "3x", "2x", "packs promo", "per pack",
    "from booster box", "from box", "single pack", "1x ", "pack case",
    "booster box pack", "box pack",
)
# Non-English editions trade well below the English box; exclude so the advisory
# prices the English SKU (the one MTGJSON/TCGplayer track). Matched on the title.
_LANGUAGE_MARKERS = (
    "japanese", "chinese", "korean", "french", "german", "italian",
    "portuguese", "russian", "spanish", "t-chinese", "j-", "jpn",
)

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


def _tokens(text: str) -> set[str]:
    """Lowercased alphanumeric tokens of ``text``, minus generic stopwords.
    A 4-digit year (2015) and short set codes (m15) survive as discriminators."""
    raw = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {t for t in raw if t not in _STOPWORDS and len(t) >= 2}


def _discriminators(query_tokens: set[str]) -> set[str]:
    """The subset of query tokens that pin a SPECIFIC set: a 4-digit year or a
    set-code-shaped token (letters+digits like ``m15``, or 3-letter codes).
    A matching listing must contain at least one, so "Magic 2015 Booster Box"
    won't collapse onto "Modern Masters 2015" (shares 2015) — both carry 2015,
    so we also require the non-type, non-year tokens to overlap (see _matches)."""
    out = set()
    for t in query_tokens:
        if re.fullmatch(r"\d{4}", t):        # a year, e.g. 2015
            out.add(t)
        elif re.fullmatch(r"[a-z]+\d+|\d+[a-z]+", t):  # set-code-shaped, e.g. m15
            out.add(t)
    return out


def _matches(title: str, query_tokens: set[str], type_tokens: set[str],
             discriminators: set[str]) -> bool:
    """True if a listing title plausibly IS the queried product.

    Requires: (1) ALL product-TYPE tokens present (a "booster box" query needs
    both 'booster' AND 'box', so single-pack listings are excluded), (2) if the
    query has discriminators (year/set-code), the title carries one, (3) strong
    overlap of the remaining identity tokens (set name words), and (4) no
    negative marker (empty box, promo/6-card packs, lot quantities)."""
    low = title.lower()
    if any(m in low for m in _NEGATIVE_MARKERS):
        return False
    if any(m in low for m in _LANGUAGE_MARKERS):   # non-English edition
        return False
    tt = _tokens(title)
    if type_tokens and not type_tokens.issubset(tt):
        return False
    if discriminators and not (discriminators & tt):
        return False
    # identity tokens = query minus type/discriminator (the SET-NAME words, e.g.
    # 'core'/'set' for M15, 'modern'/'masters' for MM2). Require FULL overlap so
    # a shared year (2015) can't collapse "Core Set 2015" onto "Modern Masters
    # 2015" — the identity words must all be present.
    identity = query_tokens - type_tokens - discriminators
    if identity:
        overlap = len(identity & tt) / len(identity)
        if overlap < 1.0:
            return False
    return True


def _trimmed(prices: list[float]) -> list[float]:
    """The interquartile core: sorted prices with the bottom/top 25% dropped
    (needs ≥4 to trim; else unchanged). Kills residual '10x lot' / 'empty box' /
    keyword-bait outliers so both the median AND the reported range reflect the
    confident cluster, not the noise."""
    ps = sorted(prices)
    if len(ps) >= 4:
        lo, hi = len(ps) // 4, len(ps) - len(ps) // 4
        ps = ps[lo:hi] or ps
    return ps


def _trimmed_median(prices: list[float]) -> float | None:
    """Median of the interquartile core (see :func:`_trimmed`)."""
    ps = _trimmed(prices)
    return round(statistics.median(ps), 2) if ps else None


def _is_sealed_condition(cond: str) -> bool:
    """New / Factory Sealed. The default for sealed product."""
    c = cond.lower()
    return "new" in c or "sealed" in c


def _is_inspection_condition(cond: str) -> bool:
    """Like-new / Near Mint 'opened only for inspection' — allowed opt-in."""
    c = cond.lower()
    return any(t in c for t in ("like new", "near mint", "open box", "excellent"))


@dataclass
class Candidate:
    """One matched eBay listing, reviewable (URL + image) to confirm identity."""
    title: str
    price: float
    condition: str
    item_url: str | None
    image_url: str | None
    buying_options: tuple[str, ...]


@dataclass
class EbayAdvisory:
    """Structured advisory result — a price WITH its confidence/context, never a
    bare float (eBay has no product-id join, so the number is heuristic)."""
    price: float | None          # interquartile-trimmed median of matched, or None
    n_matched: int               # listings that passed the title/condition filter
    n_total: int                 # listings eBay returned for the query
    low: float | None            # min matched price
    high: float | None           # max matched price
    conditions: dict             # {condition_string: count} across matches
    confidence: str              # "none" | "low" | "medium" | "high"
    candidates: list             # list[Candidate], sorted by price, for review
    note: str = ""               # human caveat (e.g. active-listings-not-sold)

    def as_display(self) -> str:
        """One-line advisory for chat/stdout: price + range + confidence + n."""
        if self.price is None:
            return f"(no confident eBay match — {self.n_matched}/{self.n_total} listings passed the filter)"
        rng = ""
        if self.low is not None and self.high is not None:
            rng = f"  range ${self.low:.0f}–${self.high:.0f}"
        return (f"${self.price:.2f}{rng}  [{self.confidence} confidence, "
                f"n={self.n_matched} active BIN listings; {self.note}]")


def _confidence(n_matched: int, low: float | None, high: float | None,
                price: float | None) -> str:
    """Confidence label from sample size + price spread. A wide spread relative
    to the median (noisy match set) knocks confidence down even with many hits."""
    if price is None or n_matched == 0:
        return "none"
    spread = (high - low) / price if (low is not None and high is not None and price) else 99
    if n_matched >= 6 and spread <= 1.0:
        return "high"
    if n_matched >= 4 and spread <= 2.0:
        return "medium"
    return "low"


def _collect_candidates(body: dict, product_name: str, *,
                        allow_inspection: bool = False) -> list:
    """Matched listings as :class:`Candidate`s (buy-it-now, condition-filtered,
    title-matched). Sorted by price ascending."""
    items = body.get("itemSummaries") or []
    qtok = _tokens(product_name)
    ttok = qtok & _TYPE_TOKENS
    disc = _discriminators(qtok)
    cands: list[Candidate] = []
    for it in items:
        cond = it.get("condition") or ""
        ok_cond = _is_sealed_condition(cond) or (allow_inspection and _is_inspection_condition(cond))
        if not ok_cond:
            continue
        opts = tuple(it.get("buyingOptions") or ())
        if "AUCTION" in opts and "FIXED_PRICE" not in opts:  # skip pure auctions
            continue
        if not _matches(it.get("title", ""), qtok, ttok, disc):
            continue
        pv = (it.get("price") or {}).get("value")
        try:
            price = float(pv) if pv is not None else None
        except (TypeError, ValueError):
            price = None
        if price is None:
            continue
        cands.append(Candidate(
            title=it.get("title", ""), price=price, condition=cond,
            item_url=it.get("itemWebUrl"),
            image_url=(it.get("image") or {}).get("imageUrl"),
            buying_options=opts,
        ))
    cands.sort(key=lambda c: c.price)
    return cands


def advisory(product_name: str, *, allow_inspection: bool = False) -> EbayAdvisory:
    """Full structured eBay advisory for a product name.

    Buy-it-now, sealed (or opt-in inspection), title-matched. The price is an
    interquartile-trimmed median with confidence + range + reviewable candidate
    listings. NOTE: Browse exposes ACTIVE listings only — eBay's settled/sold
    prices need the restricted Marketplace Insights API — so this is a listed-
    price signal, not a sold comp."""
    try:
        body = _run(["search", product_name])   # wrapper defaults to fixed-price
    except EbayUnconfigured:
        return EbayAdvisory(None, 0, 0, None, None, {}, "none", [],
                            note="eBay not configured")
    cands = _collect_candidates(body, product_name, allow_inspection=allow_inspection)
    n_total = len(body.get("itemSummaries") or [])
    prices = [c.price for c in cands]
    conditions: dict = {}
    for c in cands:
        conditions[c.condition] = conditions.get(c.condition, 0) + 1
    price = _trimmed_median(prices) if len(prices) >= _MIN_MATCHES else None
    # Range over the trimmed core (not raw min/max) so one keyword-bait listing
    # can't make the range look alarming while the median stays accurate.
    core = _trimmed(prices)
    low = min(core) if core else None
    high = max(core) if core else None
    return EbayAdvisory(
        price=price, n_matched=len(cands), n_total=n_total, low=low, high=high,
        conditions=conditions, confidence=_confidence(len(cands), low, high, price),
        candidates=cands,
        note="active listings, not sold comps",
    )


def advisory_price(product_name: str) -> float | None:
    """Back-compat scalar: the advisory's trimmed-median price (or None)."""
    return advisory(product_name).price


class EbayAdvisoryProvider:
    """Advisory-only ``sealed.MarketProvider``. Memoizes per product name.

    ``price()`` returns the scalar median for the market seam; ``full()`` returns
    the structured :class:`EbayAdvisory` (confidence/range/candidates) for the
    report. Raises ``EbayUnconfigured`` at construction if credentials are absent
    so the caller can drop it."""

    name = "ebay-advisory"

    def __init__(self, *, allow_inspection: bool = False):
        res = subprocess.run(
            [str(WRAPPER), "raw", "/__probe__"], text=True,
            capture_output=True, check=False,
        )
        if res.returncode == 7:
            raise EbayUnconfigured(res.stderr.strip() or "eBay credentials not set")
        self.allow_inspection = allow_inspection
        self._cache: dict[str, EbayAdvisory] = {}

    def full(self, node_meta: dict) -> EbayAdvisory | None:
        name = node_meta.get("name")
        if not name:
            return None
        if name not in self._cache:
            self._cache[name] = advisory(name, allow_inspection=self.allow_inspection)
        return self._cache[name]

    def price(self, node_meta: dict) -> float | None:
        adv = self.full(node_meta)
        return adv.price if adv else None

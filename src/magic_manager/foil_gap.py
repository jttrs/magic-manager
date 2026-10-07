"""Foil vs nonfoil price gap of one printing — the single home for the math
``scripts/foil_price_diff.py`` and the web Market → Cards view share.

"Foil" means the plain foil finish: a printing whose treatment carries the
``ff`` keyword (surgefoil, etched, textured, rainbowfoil, …) is a separate
premium product, not a finish choice, so its gap is not computed.

Each printing lands in exactly one bucket, in fixed precedence:
``fancy`` > ``foil_only`` > ``nonfoil_only`` > ``unpriced`` > ``ok``. Only
``ok`` carries a gap: ``pct = (foil − nonfoil) / nonfoil`` (a fraction; negative
when the foil is cheaper) and ``usd = foil − nonfoil``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

Status = Literal["ok", "fancy", "foil_only", "nonfoil_only", "unpriced"]
STATUSES: tuple[Status, ...] = ("fancy", "foil_only", "nonfoil_only", "unpriced", "ok")


@dataclass(frozen=True)
class FoilGap:
    status: Status
    pct: float | None = None
    usd: float | None = None


def is_fancy(treatment: str | None) -> bool:
    """True when a ``treatments.compute_treatment`` string carries ``ff``."""
    return "ff" in (treatment or "").split("|")


def foil_gap(*, finishes: Iterable[str], treatment: str | None,
             nonfoil: float | None, foil: float | None) -> FoilGap:
    """Bucket a printing and, when both plain finishes are priced, its gap."""
    fins = list(finishes or [])
    if is_fancy(treatment):
        return FoilGap("fancy")
    if fins == ["foil"]:
        return FoilGap("foil_only")
    if "foil" not in fins:
        return FoilGap("nonfoil_only")
    if nonfoil is None or foil is None or nonfoil == 0:
        return FoilGap("unpriced")
    return FoilGap("ok", (foil - nonfoil) / nonfoil, foil - nonfoil)


def keep(gap: FoilGap, *, min_pct: float | None = None, max_pct: float | None = None,
         min_raw: float | None = None, max_raw: float | None = None,
         drop_expensive: tuple[float, float] | None = None) -> bool:
    """Inclusive bound filter on an ``ok`` gap. Percent bounds are in PERCENT
    (``max_pct=25`` keeps foils up to 25% over nonfoil); raw bounds in USD.
    ``drop_expensive=(PCT, RAW)`` drops a row only when BOTH pct > PCT and
    usd ≥ RAW. A gap that isn't ``ok`` never passes."""
    if gap.status != "ok" or gap.pct is None or gap.usd is None:
        return False
    pct = gap.pct * 100
    if min_pct is not None and pct < min_pct:
        return False
    if max_pct is not None and pct > max_pct:
        return False
    if min_raw is not None and gap.usd < min_raw:
        return False
    if max_raw is not None and gap.usd > max_raw:
        return False
    if drop_expensive is not None and pct > drop_expensive[0] and gap.usd >= drop_expensive[1]:
        return False
    return True


def sort_key(gap: FoilGap) -> float:
    """Ascending-by-percent key, rounded so penny flips don't reorder rows."""
    return round(gap.pct, 4) if gap.pct is not None else float("inf")

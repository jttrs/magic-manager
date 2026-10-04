"""Card-diff (missing-set) surface of the typed API.

Wraps :mod:`magic_manager.card_diff` (the three missing pools) and
:mod:`magic_manager.card_diff_tiles` (pool rows → deduped exact-printing tiles
with buy-list lines). The JSON contract mirrors the compare view's shape —
sections + cards with pool tags — so one frontend component set renders both.
"""
from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field

from .. import card_diff, card_diff_tiles, family_status

PoolKey = Literal["printing", "functional", "variant-chase"]
ChaseMode = Literal["exclude", "include", "only"]


class PoolSummary(BaseModel):
    count: int
    usd: float


class FamilyOut(BaseModel):
    code: str
    name: str
    owned_prints: int
    owned_qty: int
    owned_usd: float
    pools: dict[str, PoolSummary]


class CardDiffTile(BaseModel):
    key: str = Field(description="Stable per-family tile id (exact printing).")
    family: str
    pools: list[PoolKey]
    name: str
    set_code: str | None
    collector_number: str | None
    rarity: str | None
    finish: str | None
    usd: float | None
    image_uri: str | None
    scryfall_url: str | None
    manapool_line: str = ""
    tcgplayer_line: str = ""


class CardDiffOut(BaseModel):
    families: list[FamilyOut]
    cards: list[CardDiffTile]
    skipped: list[str] = Field(default_factory=list, description="Codes that didn't resolve to a configured family.")


class FamilyOption(BaseModel):
    code: str
    name: str


_FAMILIES_TTL_S = 120.0
_families_cache: tuple[float, list[FamilyOption]] | None = None


def families(*, max_age_s: float = _FAMILIES_TTL_S) -> list[FamilyOption]:
    """Families the collection touches (owned or registered), for the picker.

    Resolving every owned set code to its family parent costs seconds, and the
    answer only changes when inventory gains a new set, so it is memoized for a
    couple of minutes (``max_age_s=0`` forces a recompute)."""
    global _families_cache
    now = time.monotonic()
    if _families_cache and now - _families_cache[0] < max_age_s:
        return list(_families_cache[1])
    parents = family_status._owned_family_parents()
    result = sorted(
        (FamilyOption(code=c, name=n) for c, n in parents.items()
         if c not in family_status.NON_FAMILY_SETS),
        key=lambda f: f.name,
    )
    _families_cache = (now, result)
    return list(result)


def diff(codes: list[str], *, pools: list[PoolKey] | None = None,
         chase: ChaseMode = "exclude") -> CardDiffOut:
    """The three missing pools for the given families as exact-printing tiles.
    Local-first prices (no network refresh from the web read path)."""
    pools = list(pools or card_diff_tiles.POOL_CHOICES)
    skipped: list[str] = []
    diffs = card_diff.multi_family_diff(codes, chase=chase, on_skip=skipped.append)
    tiles = card_diff_tiles.build_tiles(diffs, pools)
    return CardDiffOut(
        families=[
            FamilyOut(
                code=fd.code, name=fd.name, owned_prints=fd.owned_prints,
                owned_qty=fd.owned_qty, owned_usd=fd.owned_usd,
                pools={
                    p: PoolSummary(count=pool.count, usd=pool.usd)
                    for p in pools
                    for pool in [getattr(fd, p.replace("-", "_"))]
                },
            )
            for fd in diffs
        ],
        cards=[
            CardDiffTile(
                key="|".join(str(x) for x in t["sid_key"]),
                family=t["family"], pools=sorted(t["pools"]), name=t["name"],
                set_code=t["set"], collector_number=t["cn"], rarity=t["rarity"],
                finish=t["finish"], usd=t["usd"], image_uri=t["image_uri"],
                scryfall_url=t["scryfall_url"],
                manapool_line=t.get("data_attrs", {}).get("mp", ""),
                tcgplayer_line=t.get("data_attrs", {}).get("tcg", ""),
            )
            for t in tiles
        ],
        skipped=skipped,
    )

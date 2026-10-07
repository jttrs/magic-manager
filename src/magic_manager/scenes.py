"""Scene / poster completion for a set family.

A *scene* is a curated run of collector numbers whose art tiles into one
picture (LTR's borderless scene runs, its 5-panel posters). Scryfall doesn't
tag membership, so the runs live in ``config/families.toml`` ``[[scenes.<anchor>]]``
(``selectors.FAMILY_SCENES``; ``kind`` = ``scene`` | ``poster``, default scene).

This engine joins those runs to the Collection universe
(``collection_view.family_cards`` — same printings, ownership and local prices,
no second query) and reports, per scene and per finish, how many printings you
own and what the missing ones cost. Collectors assemble a scene in ONE finish
(mismatched panels look wrong side by side), so completion is per finish:
``owned`` counts printings held in THAT finish, ``missing_usd`` sums the unowned
ones at that finish's price. ``owned_printings`` is the any-finish tally.

Prices are the local ``cards`` prices by default (what the Collection view
shows); ``live_prices`` re-prices a scene's printings from Scryfall for the
``scripts/scene_table.py`` report.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import collection_view, scryfall, selectors as sel_mod

FINISHES = ("nonfoil", "foil")


@dataclass
class SceneFinish:
    finish: str
    printings: int = 0          # scene printings that exist in this finish
    owned: int = 0              # … of those, held in this finish
    missing_usd: float = 0.0    # Σ price of the unowned ones in this finish
    unpriced: int = 0           # unowned ones with no price in this finish
    missing_ids: list[str] = field(default_factory=list)


@dataclass
class SceneProgress:
    key: str                    # "<set>:<cn_lo>-<cn_hi>" — unique across families
    family: str
    rank: int                   # config order within the family
    name: str
    artist: str | None
    kind: str                   # scene | poster
    set_code: str
    cn_lo: int
    cn_hi: int
    card_ids: list[str] = field(default_factory=list)   # collector-number order
    owned_printings: int = 0    # printings held in any finish
    finishes: dict[str, SceneFinish] = field(default_factory=dict)

    @property
    def printings(self) -> int:
        return len(self.card_ids)


def scene_key(sc: dict) -> str:
    return f"{str(sc['set']).lower()}:{int(sc['cn_lo'])}-{int(sc['cn_hi'])}"


def configured(family: str) -> list[dict]:
    """The family's scene config, in config order (empty when none)."""
    return list(sel_mod.FAMILY_SCENES.get(family.lower(), []))


def scene_of(scenes: list[dict], set_code: str, collector_number: str) -> dict | None:
    """The scene a printing belongs to: same set, a plain-numeric collector
    number inside ``[cn_lo, cn_hi]`` (variant suffixes like ``731z`` never match)."""
    if not collector_number.isdigit():
        return None
    cn = int(collector_number)
    sc_set = set_code.lower()
    for sc in scenes:
        if str(sc["set"]).lower() == sc_set and int(sc["cn_lo"]) <= cn <= int(sc["cn_hi"]):
            return sc
    return None


def _price(card: collection_view.CollectionCard, finish: str,
           prices: dict[str, tuple[float | None, float | None]] | None) -> float | None:
    if prices is not None and card.scryfall_id in prices:
        nf, f = prices[card.scryfall_id]
        return f if finish == "foil" else nf
    return card.price_usd_foil if finish == "foil" else card.price_usd


def progress(fc: collection_view.FamilyCollection,
             prices: dict[str, tuple[float | None, float | None]] | None = None) -> list[SceneProgress]:
    """Per-scene, per-finish completion over a family's Collection universe.
    ``prices`` (scryfall_id → (usd, usd_foil)) overrides the local prices."""
    family = fc.summary.code
    cfg = configured(family)
    out = [
        SceneProgress(
            key=scene_key(sc), family=family, rank=i, name=str(sc["name"]),
            artist=sc.get("artist") or None, kind=str(sc.get("kind") or "scene"),
            set_code=str(sc["set"]).lower(), cn_lo=int(sc["cn_lo"]), cn_hi=int(sc["cn_hi"]),
            finishes={f: SceneFinish(finish=f) for f in FINISHES},
        )
        for i, sc in enumerate(cfg)
    ]
    by_key = {s.key: s for s in out}
    members = sorted(
        ((sc, c) for c in fc.cards if (sc := scene_of(cfg, c.set_code, c.collector_number))),
        key=lambda p: (int(p[1].collector_number), p[1].scryfall_id),
    )
    for sc, c in members:
        s = by_key[scene_key(sc)]
        s.card_ids.append(c.scryfall_id)
        if c.owned_total:
            s.owned_printings += 1
        for fin in c.finishes:
            sf = s.finishes[fin]
            sf.printings += 1
            if c.owned.get(fin, 0) > 0:
                sf.owned += 1
                continue
            sf.missing_ids.append(c.scryfall_id)
            p = _price(c, fin, prices)
            if p is None:
                sf.unpriced += 1
            else:
                sf.missing_usd += p
    for s in out:
        for sf in s.finishes.values():
            sf.missing_usd = round(sf.missing_usd, 2)
    return out


def scene_card_keys(fc: collection_view.FamilyCollection) -> dict[str, str]:
    """scryfall_id → scene key for every scene printing in the family."""
    cfg = configured(fc.summary.code)
    return {
        c.scryfall_id: scene_key(sc)
        for c in fc.cards if (sc := scene_of(cfg, c.set_code, c.collector_number))
    }


def live_prices(scryfall_ids: list[str]) -> dict[str, tuple[float | None, float | None]]:
    """Current Scryfall prices for printings (batched, rate-limited, 24h cache)."""
    def num(v) -> float | None:
        try:
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    found, _ = scryfall.collection({"id": sid} for sid in dict.fromkeys(scryfall_ids))
    return {
        c["id"]: (num((c.get("prices") or {}).get("usd")), num((c.get("prices") or {}).get("usd_foil")))
        for c in found
    }


def family_scenes(code: str) -> tuple[collection_view.FamilyCollection, list[SceneProgress]]:
    """``family_cards(code)`` plus its scene progress at local prices (re-price
    with ``progress(fc, live_prices(...))``). Raises ``LookupError`` for an
    unknown code."""
    fc = collection_view.family_cards(code)
    return fc, progress(fc)

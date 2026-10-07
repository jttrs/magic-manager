"""Card surfer surface of the typed API: random cards for an endless feed.

Adapts :mod:`magic_manager.surf` (the engine).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import surf


class SurfFiltersIn(BaseModel):
    art: list[str] = Field(default_factory=list, description="Art tag slugs (any of).")
    families: list[str] = Field(default_factory=list, description="Set family anchors (any of).")
    colors: str = Field("", description="Colour identity letters WUBRG, or C for colourless.")
    color_match: Literal["exact", "within"] = "exact"
    flavor: Literal["any", "has", "none"] = "any"
    types: list[str] = Field(default_factory=list, description="Card types (any of).")
    legendary: Literal["any", "only", "not"] = "any"
    rarity: list[str] = Field(default_factory=list)
    artist: str = ""
    treatments: list[str] = Field(default_factory=list, description="Treatment keys (any of), see /api/surf/options.")


class SurfDrawIn(BaseModel):
    filters: SurfFiltersIn = Field(default_factory=SurfFiltersIn)
    source: Literal["scryfall", "owned"] = "scryfall"
    n: int = Field(4, ge=1, le=surf.MAX_DRAW)
    seed: int = Field(0, description="Your cards: shuffle seed (one per feed).")
    offset: int = Field(0, ge=0, description="Your cards: position in the shuffled list.")
    with_total: bool = Field(False, description="All of Magic: also count the matching printings (first page).")


class SurfFaceOut(BaseModel):
    name: str
    type_line: str | None = None
    oracle_text: str | None = None
    flavor_text: str | None = None
    artist: str | None = None
    image: str | None = None


class SurfTagOut(BaseModel):
    slug: str
    label: str


class SurfPricesOut(BaseModel):
    nonfoil: float | None = None
    foil: float | None = None


class SurfCardOut(BaseModel):
    scryfall_id: str
    oracle_id: str | None = None
    name: str
    type_line: str | None = None
    oracle_text: str | None = None
    flavor_text: str | None = None
    artist: str | None = None
    set_code: str
    set_name: str | None = None
    collector_number: str | None = None
    rarity: str | None = None
    released_at: str | None = None
    image: str | None = None
    faces: list[SurfFaceOut] = Field(description="A double-faced card's faces (empty for one face).")
    scryfall_uri: str | None = None
    color_identity: list[str]
    prices: SurfPricesOut
    owned: int = Field(description="Copies of this printing you own.")
    owned_any: int = Field(description="Copies you own across every printing.")
    art_tags: list[SurfTagOut] = Field(description="The artwork's art tags (local tag cache).")


class SurfDrawOut(BaseModel):
    source: Literal["scryfall", "owned"]
    query: str = Field(description="The Scryfall search the filters compile to.")
    cards: list[SurfCardOut]
    total: int | None = Field(None, description="Printings that match (when asked / your cards).")
    next_offset: int | None = None
    exhausted: bool = Field(description="No more cards to draw (nothing matches, or every one of yours was shown).")


class SurfOptionOut(BaseModel):
    value: str
    label: str


class SurfFamilyOut(BaseModel):
    value: str
    label: str
    year: str | None = None


class SurfOptionsOut(BaseModel):
    families: list[SurfFamilyOut] = Field(description="Top-level paper sets, newest first.")
    treatments: list[SurfOptionOut]
    types: list[SurfOptionOut]
    rarities: list[SurfOptionOut]


def _filters(f: SurfFiltersIn) -> surf.Filters:
    return surf.Filters(
        art=tuple(f.art), families=tuple(f.families), colors=f.colors, color_match=f.color_match,
        flavor=f.flavor, types=tuple(t.lower() for t in f.types), legendary=f.legendary,
        rarity=tuple(r.lower() for r in f.rarity), artist=f.artist, treatments=tuple(f.treatments),
    )


def draw(body: SurfDrawIn) -> SurfDrawOut:
    d = surf.draw(_filters(body.filters), source=body.source, n=body.n, seed=body.seed,
                  offset=body.offset, with_total=body.with_total)
    return SurfDrawOut(source=d.source, query=d.query, cards=[SurfCardOut.model_validate(c) for c in d.cards],
                       total=d.total, next_offset=d.next_offset, exhausted=d.exhausted)


def options() -> SurfOptionsOut:
    return SurfOptionsOut.model_validate(surf.options())

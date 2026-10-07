"""Art surface of the typed API: on-theme art printing swaps for the deck
editor — Scryfall Tagger art tags, and for each card in a draft the printings
whose artwork carries the chosen tag.

Adapts :mod:`magic_manager.art_swap` (the engine).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import art_swap
from .decks import DraftCardIn
from .ingest import PrintingOut


class ArtTagOut(BaseModel):
    id: str
    label: str
    slug: str
    illustrations: int = Field(description="Artworks tagged with it directly (child tags add more).")


class ArtTagsOut(BaseModel):
    synced: bool = Field(description="False until the Scryfall tag cache is loaded (job `scryfall.sync_tags`).")
    tags: list[ArtTagOut]


class ArtSwapsIn(BaseModel):
    tag: str = Field(min_length=1, description="Art tag id, slug or label.")
    cards: list[DraftCardIn]


class ArtSwapRowOut(BaseModel):
    scryfall_id: str = Field(description="The printing the draft uses now.")
    status: Literal["on_theme", "swap", "none"]
    pick: str | None = Field(description="Best on-theme printing: yours with the most free copies, else the cheapest.")
    candidates: list[str] = Field(description="Every on-theme printing of the card, best first.")


class ArtTagRefOut(BaseModel):
    id: str
    label: str


class ArtSwapsOut(BaseModel):
    tag: ArtTagRefOut
    rows: list[ArtSwapRowOut]
    printings: dict[str, PrintingOut]
    matched: dict[str, list[str]] = Field(description="Per on-theme printing, the tags (incl. child tags) that matched.")
    free_by_finish: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Per printing you own, free copies per finish (`nonfoil`/`foil`); `printings[sid].free` is the finish-agnostic total.")


class ArtLookupOut(BaseModel):
    searched: int = Field(description="Cards asked about.")
    added: int = Field(description="On-theme printings new to the local catalog.")


def tags(q: str, limit: int = 20) -> ArtTagsOut:
    return ArtTagsOut.model_validate(art_swap.search_tags(q, limit))


def _sids(body: ArtSwapsIn) -> list[str]:
    return [c.scryfall_id for c in body.cards if c.count > 0]


def swaps(body: ArtSwapsIn) -> ArtSwapsOut:
    return ArtSwapsOut.model_validate(art_swap.swaps(body.tag, _sids(body)))


def lookup(body: ArtSwapsIn) -> ArtLookupOut:
    return ArtLookupOut.model_validate(art_swap.lookup_scryfall(body.tag, _sids(body)))

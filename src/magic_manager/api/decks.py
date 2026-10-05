"""Decks surface of the typed API: every tracked deck (recipe) with its source and
ownership, and one deck's cards with exact printings + owned / pledged / free.

Adapts :mod:`magic_manager.deck_view` (the engine). Card printings reuse the
add-cards ``PrintingOut`` so a deck's cards drop straight into the add-cards
review step ("add this deck / these cards to my collection").
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import deck_view
from .ingest import PrintingOut


class DeckSummaryOut(BaseModel):
    slug: str
    name: str
    format: str | None
    deck_type: str = Field(description="What kind of deck: the game format (Commander, Standard, Pauper, Jumpstart…), else the precon product family (Starter / intro, Secret Lair, Land pack…).")
    state: Literal["built", "deconstructed"]
    origin: Literal["precon", "import", "custom"] = Field(description="precon = MTGJSON product; import = deck-builder URL; custom = hand-built.")
    source: str | None = Field(description="Deck builder for imports (moxfield, archidekt…); precon product type for precons.")
    author: str | None
    set_code: str | None
    set_name: str | None
    released: str | None = Field(description="Product release date (precons) or set release date; ISO.")
    cards: int = Field(description="Card count excluding tokens.")
    value_usd: float = Field(description="Sum of non-token cards at their finish's price.")
    pledged_pct: float = Field(description="Share of non-token card copies currently pledged to this deck (0–100).")
    image_uri: str | None = Field(description="Representative art: the commander, else the priciest card.")


class DeckCardOut(BaseModel):
    printing: PrintingOut
    board: Literal["main", "side", "commander", "companion", "maybe", "token"]
    finish: Literal["nonfoil", "foil", "either"]
    count: int
    type_line: str | None
    cmc: float | None
    color_identity: list[str]
    pledged_here: int = Field(description="Copies of this printing pledged to THIS deck (any finish).")
    free: int = Field(description="Copies you own that no deck has pledged (any finish).")


class DeckDetailOut(BaseModel):
    deck: DeckSummaryOut
    cards: list[DeckCardOut]


def summaries() -> list[DeckSummaryOut]:
    return [DeckSummaryOut(**d) for d in deck_view.deck_summaries()]


def detail(slug: str) -> DeckDetailOut:
    d = deck_view.deck_detail(slug)
    return DeckDetailOut(deck=DeckSummaryOut(**d["deck"]), cards=[DeckCardOut(**c) for c in d["cards"]])

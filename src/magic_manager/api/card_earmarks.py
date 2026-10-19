"""Earmarked cards in the typed API: singles you're interested in (to collect, or a
deck idea), the list of them, and the ones that fit a deck being edited.

Adapts :mod:`magic_manager.card_earmarks` (the engine). Printings reuse Add
cards' ``PrintingOut`` so an earmarked card renders and adds like any other.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import card_earmarks
from ..deck_edit import DraftCard
from .decks import DraftCardIn
from .ingest import PrintingOut


class CardEarmarkOut(BaseModel):
    oracle_id: str
    name: str
    scryfall_id: str | None = Field(description="The preferred printing, when one was chosen.")
    finish: Literal["nonfoil", "foil"] | None
    reason: Literal["collect", "deck"] | None
    deck_slug: str | None = Field(description="The deck this card is earmarked for.")
    deck_name: str | None
    note: str | None
    earmarked_at: str
    updated_at: str


class EarmarkEntryOut(BaseModel):
    earmark: CardEarmarkOut
    printing: PrintingOut | None = Field(description="The preferred printing, else your copy with the most free, else the first standard printing.")
    owned: int = Field(description="Copies owned across every printing of the card.")
    free: int = Field(description="Owned copies no built deck has pledged, across printings.")


class DeckEarmarkOut(EarmarkEntryOut):
    in_deck: bool = Field(description="The card is already in the draft (any board).")
    reasons: list[str] = Field(description="Why it can't go in this deck, plain words ([] = it can).")


class DeckEarmarksOut(BaseModel):
    format: str | None = Field(description="The format filtered on (None = the deck has no format: nothing filtered).")
    commander_colors: list[str] | None = Field(description="The commander's colour identity (None = no commander yet, or not a commander format).")
    for_deck: list[DeckEarmarkOut] = Field(description="Earmarked for this deck — always listed.")
    legal: list[DeckEarmarkOut]
    hidden: list[DeckEarmarkOut] = Field(description="Earmarks that don't fit this deck, each with its reasons.")


class CardEarmarkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    card: str = Field(min_length=1, max_length=200, description="Any printing's scryfall_id, or the card's name.")
    printing: str | None = Field(None, max_length=64, description="Preferred printing (scryfall_id of the same card).")
    finish: Literal["nonfoil", "foil"] | None = None
    reason: Literal["collect", "deck"] | None = None
    deck: str | None = Field(None, max_length=200, description="Slug of the deck it's earmarked for.")
    note: str | None = Field(None, max_length=500)


class DeckEarmarksIn(BaseModel):
    cards: list[DraftCardIn]


def listing(reason: str | None = None, deck: str | None = None) -> list[EarmarkEntryOut]:
    return [EarmarkEntryOut.model_validate(e) for e in card_earmarks.entries(card_earmarks.listing(reason=reason, deck=deck))]


def save(body: CardEarmarkIn) -> CardEarmarkOut:
    e = card_earmarks.save(body.card, printing=body.printing, finish=body.finish, reason=body.reason,
                           deck=body.deck, note=body.note)
    return CardEarmarkOut.model_validate(e.to_json())


def remove(oracle_id: str) -> bool:
    return card_earmarks.remove(oracle_id)


def for_deck(slug: str, body: DeckEarmarksIn) -> DeckEarmarksOut:
    draft = [DraftCard(c.scryfall_id, c.board, c.finish, c.count) for c in body.cards]
    return DeckEarmarksOut.model_validate(card_earmarks.for_deck(slug, draft))

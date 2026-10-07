"""Combos surface of the typed API: Commander Spellbook combos a deck contains /
is one card away from, and the combos one card is part of — each piece joined
to what you own and its cheapest price.

Adapts :mod:`magic_manager.combos` (the engine). Card facts reuse Explore's
``FactsOut`` so a combo piece renders like any other Explore card.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .. import addcards, combos
from .decks import DraftCardIn
from .explore import FactsOut, _facts
from .ingest import PrintingOut


class PieceOut(BaseModel):
    name: str
    oracle_id: str | None
    in_deck: bool = Field(description="The deck already runs this card (deck combos only).")
    facts: FactsOut = Field(description="Owned / free copies across printings, cheapest price, display printing.")
    image_uri: str | None = Field(description="Spellbook's art crop, for cards not in the local catalog.")
    printing: PrintingOut | None = Field(None, description="The printing to add: your copy with the most free, else the first standard printing.")


class ComboOut(BaseModel):
    id: str
    url: str = Field(description="The combo's page on Commander Spellbook.")
    pieces: list[PieceOut]
    produces: list[str] = Field(description="What it does (e.g. 'Infinite colorless mana').")
    requires: list[str] = Field(description="Extra pieces described, not named (any card that fits).")
    description: str = Field(description="Steps, one per line.")
    prerequisites: str
    mana_needed: str
    popularity: int | None = Field(description="Decks on EDHREC running every piece.")
    identity: str
    missing: PieceOut | None = Field(None, description="One-card-away combos: the card to add.")


class MissingCardOut(BaseModel):
    piece: PieceOut
    combos: list[str] = Field(description="Ids of the near-miss combos this card completes, most popular first.")
    popularity: int


class DeckCombosOut(BaseModel):
    available: bool = Field(description="False when Commander Spellbook couldn't be reached; see `error`.")
    error: str | None = None
    identity: str | None = None
    included: list[ComboOut]
    almost: list[ComboOut] = Field(description="Combos one card away, in the deck's colours.")
    missing_cards: list[MissingCardOut] = Field(description="The near-misses rolled up per missing card, most combos first.")
    off_color: int = Field(description="Near-misses that would need another colour (not listed).")


class DraftCombosIn(BaseModel):
    cards: list[DraftCardIn]


class CardCombosOut(BaseModel):
    available: bool
    name: str
    error: str | None = None
    combos: list[ComboOut]


Printings = dict[str, PrintingOut]


def _printings(cs: list[combos.Combo]) -> Printings:
    return addcards.printings_for_ids({p.printing_id for c in cs for p in c.pieces if p.printing_id})


def _piece(p: combos.Piece, pr: Printings) -> PieceOut:
    return PieceOut(name=p.name, oracle_id=p.oracle_id, in_deck=p.in_deck, facts=_facts(p.facts),
                    image_uri=p.image_uri, printing=pr.get(p.printing_id or ""))


def _combo(c: combos.Combo, pr: Printings) -> ComboOut:
    return ComboOut(
        id=c.id, url=c.url, pieces=[_piece(p, pr) for p in c.pieces], produces=c.produces, requires=c.requires,
        description=c.description, prerequisites=c.prerequisites, mana_needed=c.mana_needed,
        popularity=c.popularity, identity=c.identity, missing=_piece(c.missing, pr) if c.missing else None,
    )


def _deck_out(r: combos.DeckCombos) -> DeckCombosOut:
    pr = _printings([*r.included, *r.almost])
    return DeckCombosOut(
        available=r.available, error=r.error, identity=r.identity,
        included=[_combo(c, pr) for c in r.included], almost=[_combo(c, pr) for c in r.almost],
        missing_cards=[MissingCardOut(piece=_piece(m.piece, pr), combos=m.combos, popularity=m.popularity) for m in r.missing_cards],
        off_color=r.off_color,
    )


def deck(slug: str) -> DeckCombosOut:
    return _deck_out(combos.deck_combos(slug))


def draft(body: DraftCombosIn) -> DeckCombosOut:
    return _deck_out(combos.combos_for_rows((c.scryfall_id, c.board, c.count) for c in body.cards))


def card(name: str, *, limit: int = 30) -> CardCombosOut:
    r = combos.card_combos(name, limit=limit)
    pr = _printings(r.combos)
    return CardCombosOut(available=r.available, name=r.name, error=r.error, combos=[_combo(c, pr) for c in r.combos])

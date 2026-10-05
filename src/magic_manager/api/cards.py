"""Card surface of the typed API: one printing's holdings for the card inspector.

Adapts :func:`magic_manager.provenance.card_holdings` — owned / pledged / free per
finish, the built decks holding pledged copies, where the copies came from, and
copies owned in other printings of the same card.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import provenance
from .collection import SourceOut

Finish = Literal["nonfoil", "foil"]


class DeckPledgeOut(BaseModel):
    slug: str
    name: str
    finish: Finish
    count: int


class CardSourceOut(BaseModel):
    source: SourceOut
    finish: Finish
    copies: int = Field(description="Copies acquired from this source (history: may exceed what is owned today).")
    acquisitions: int = Field(1, description="Separate ingests from this source (e.g. 2 = two purchases of the same product).")


class HoldingsOut(BaseModel):
    scryfall_id: str
    owned: dict[str, int] = Field(description="finish -> owned copies")
    pledged: dict[str, int] = Field(description="finish -> copies pledged to built decks")
    free: dict[str, int] = Field(description="finish -> owned copies no deck has pledged")
    decks: list[DeckPledgeOut]
    sources: list[CardSourceOut]
    other_printings_owned: int = Field(description="Copies of the same card owned in other printings (all finishes).")


def holdings(scryfall_id: str) -> HoldingsOut:
    h = provenance.card_holdings(scryfall_id)
    return HoldingsOut(
        scryfall_id=h.scryfall_id, owned=h.owned, pledged=h.pledged, free=h.free,
        decks=[DeckPledgeOut(**vars(d)) for d in h.decks],
        sources=[CardSourceOut(source=SourceOut(key=cs.source.key, kind=cs.source.kind, label=cs.source.label,
                                                set_code=cs.source.set_code),
                               finish=cs.finish, copies=cs.copies, acquisitions=cs.acquisitions) for cs in h.sources],
        other_printings_owned=h.other_printings_owned,
    )

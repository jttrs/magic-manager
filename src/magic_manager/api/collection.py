"""Collection surface of the typed API: whole set families with ownership.

Adapts :mod:`magic_manager.collection_view` (the engine) — every computation
lives there. ``families()`` powers the picker; ``family_view()`` returns every
catalogued printing of the requested families with owned/pledged counts and the
classification flags the UI layers on (bulk / chase / standard frame).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import collection_view, family_status, gallery

BuyTarget = Literal["manapool", "tcgplayer", "cardkingdom", "moxfield", "plain"]


class FamilyOption(BaseModel):
    code: str
    name: str


class SetRefOut(BaseModel):
    code: str
    name: str


class FamilySummaryOut(BaseModel):
    code: str
    name: str
    printings: int
    owned_printings: int
    owned_copies: int
    owned_usd: float
    missing_printings: int
    missing_usd: float
    sets: list[SetRefOut] = Field(default_factory=list, description="Member sets with printings, oldest first.")


class CollectionCardOut(BaseModel):
    scryfall_id: str
    oracle_id: str | None
    name: str
    family: str
    set_code: str
    collector_number: str
    rarity: str
    type_line: str | None
    cmc: float | None
    color_identity: list[str]
    released_at: str | None
    finishes: list[str]
    owned: dict[str, int] = Field(description="finish -> owned copies")
    pledged: dict[str, int] = Field(description="finish -> copies pledged to built decks")
    price_usd: float | None
    price_usd_foil: float | None
    image_uri: str | None
    scryfall_url: str | None
    treatment: str = Field(description="Treatment codes (b, fa, shw, ext, sm, ff; '|'-joined); '' = plain")
    standard_frame: bool
    is_bulk: bool
    is_chase: bool


class CollectionOut(BaseModel):
    families: list[FamilySummaryOut]
    cards: list[CollectionCardOut]
    skipped: list[str] = Field(default_factory=list, description="Codes that didn't resolve to a family.")


class BuyItem(BaseModel):
    scryfall_id: str
    finish: Literal["nonfoil", "foil"]
    qty: int = Field(1, ge=1)


class BuyListIn(BaseModel):
    target: BuyTarget
    items: list[BuyItem]


class BuyListOut(BaseModel):
    text: str
    lines: int


def families() -> list[FamilyOption]:
    """Families the collection touches (owned or registered), for the picker."""
    parents = family_status._owned_family_parents()
    return sorted(
        (FamilyOption(code=c, name=n) for c, n in parents.items()
         if c not in family_status.NON_FAMILY_SETS),
        key=lambda f: f.name,
    )


def family_view(codes: list[str]) -> CollectionOut:
    summaries: list[FamilySummaryOut] = []
    cards: list[CollectionCardOut] = []
    skipped: list[str] = []
    seen: set[str] = set()
    for code in codes:
        try:
            fc = collection_view.family_cards(code)
        except LookupError:
            skipped.append(code)
            continue
        if fc.summary.code in seen:   # two member codes of one family
            continue
        seen.add(fc.summary.code)
        summaries.append(FamilySummaryOut(**vars(fc.summary)))
        cards.extend(
            CollectionCardOut(
                **{k: v for k, v in vars(c).items() if k not in ("scryfall_uri", "is_token")},
                scryfall_url=gallery.scryfall_card_url(c.set_code, c.collector_number),
            )
            for c in fc.cards
        )
    return CollectionOut(families=summaries, cards=cards, skipped=skipped)


def buy_list(req: BuyListIn) -> BuyListOut:
    text = collection_view.buy_lines([(i.scryfall_id, i.finish, i.qty) for i in req.items], req.target)
    return BuyListOut(text=text, lines=len([ln for ln in text.splitlines() if ln.strip()]))

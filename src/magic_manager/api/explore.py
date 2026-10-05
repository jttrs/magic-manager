"""Explore surface of the typed API: one card (or two) as a card in the 99.

Adapts :mod:`magic_manager.explore` (the engine). The commander role is served by
:func:`magic_manager.api.edhrec.compare` with ``b`` optional.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, Field

from .. import explore, gallery
from .edhrec import OracleTagOut


class CardOptionOut(BaseModel):
    name: str
    oracle_id: str | None
    type_line: str | None
    color_identity: list[str]
    image_uri: str | None
    cached: bool = Field(description="EDHREC card page already cached locally.")
    commander_eligible: bool


class FactsOut(BaseModel):
    oracle_id: str | None = None
    type_line: str | None = None
    cmc: float | None = None
    color_identity: list[str] = Field(default_factory=list)
    lowest_usd: float | None = None
    scryfall_id: str | None = None
    image_uri: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    scryfall_url: str | None = None
    owned: int = 0
    free: int = 0


class EntryOut(BaseModel):
    name: str
    slug: str
    facts: FactsOut
    num_decks: int | None = None
    potential_decks: int | None = None
    share: float | None = Field(None, description="% of the potential decks that run it.")
    lift: float | None = Field(None, description="Co-play: how many times more often than chance.")
    group: str | None = Field(None, description="Co-play type group, or 'top'/'new' for commanders.")


class CardProfileOut(BaseModel):
    name: str
    slug: str
    facts: FactsOut
    commander_eligible: bool
    num_decks: int | None
    potential_decks: int | None
    salt: float | None
    functions: list[str]
    tags: list[OracleTagOut]
    commanders: list[EntryOut]
    coplayed: list[EntryOut]
    similar: list[EntryOut]
    deck_mix: list[dict]


class PairedOut(BaseModel):
    name: str
    slug: str
    facts: FactsOut
    bucket: Literal["a_only", "both", "b_only"]
    a: EntryOut | None
    b: EntryOut | None
    gap: float | None


class CardExploreOut(BaseModel):
    a: CardProfileOut
    b: CardProfileOut | None = None
    commanders: list[PairedOut] = Field(default_factory=list, description="Comparison only: by share.")
    coplayed: list[PairedOut] = Field(default_factory=list, description="Comparison only: by lift.")
    tags: dict[str, list[OracleTagOut]] = Field(default_factory=dict, description="Comparison only: a_only / both / b_only.")


def _facts(f: explore.Facts) -> FactsOut:
    return FactsOut(**asdict(f), scryfall_url=gallery.scryfall_card_url(f.set_code, f.collector_number) if f.set_code else None)


def _entry(e: explore.Entry) -> EntryOut:
    d = asdict(e)
    d["facts"] = _facts(e.facts)
    return EntryOut(**d)


def _profile(p: explore.CardProfile) -> CardProfileOut:
    return CardProfileOut(
        name=p.name, slug=p.slug, facts=_facts(p.facts), commander_eligible=p.commander_eligible,
        num_decks=p.num_decks, potential_decks=p.potential_decks, salt=p.salt,
        functions=p.functions, tags=[OracleTagOut(**t) for t in p.tags],
        commanders=[_entry(e) for e in p.commanders], coplayed=[_entry(e) for e in p.coplayed],
        similar=[_entry(e) for e in p.similar], deck_mix=p.deck_mix,
    )


def _paired(p: explore.Paired) -> PairedOut:
    return PairedOut(name=p.name, slug=p.slug, facts=_facts(p.facts), bucket=p.bucket,
                     a=_entry(p.a) if p.a else None, b=_entry(p.b) if p.b else None, gap=p.gap)


def search(q: str, *, limit: int = 20) -> list[CardOptionOut]:
    return [CardOptionOut(**c) for c in explore.search_cards(q, limit=limit)]


def card(a: str, b: str | None = None) -> CardExploreOut:
    if not b:
        return CardExploreOut(a=_profile(explore.card_profile(a)))
    c = explore.compare_cards(a, b)
    return CardExploreOut(
        a=_profile(c.a), b=_profile(c.b),
        commanders=[_paired(p) for p in c.commanders], coplayed=[_paired(p) for p in c.coplayed],
        tags={k: [OracleTagOut(**t) for t in v] for k, v in c.tags.items()},
    )

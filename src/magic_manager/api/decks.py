"""Decks surface of the typed API: every playable deck recipe (card pools such as
land packs, scene boxes and most Secret Lair drops are excluded) with its source and
ownership, and one deck's cards with exact printings + owned / pledged / free.

Adapts :mod:`magic_manager.deck_view` (the engine). Card printings reuse the
add-cards ``PrintingOut`` so a deck's cards drop straight into the add-cards
review step ("add this deck / these cards to my collection").
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import addcards, deck_edit, deck_view
from .ingest import PrintingOut


class DeckSummaryOut(BaseModel):
    slug: str
    name: str
    format: str | None
    deck_type: str = Field(description="What kind of deck: the game format (Commander, Standard, Pauper, Jumpstart…), else the precon product family (Starter / intro, Secret Lair, Land pack…).")
    state: Literal["built", "deconstructed"] = Field(description="'built' when at least one copy is built, else 'deconstructed'.")
    built: int = Field(description="Copies of this recipe kept assembled (cards pledged).")
    slugs: list[str] = Field(description="Every deck row that is a copy of this recipe; `slug` is the representative (a built copy first).")
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
    version_id: int = Field(description="Current version; pass back as expected_version_id when saving.")
    editable: bool = Field(description="False for precons (read-only recipes): copy the deck to edit it.")


class SwapLineOut(BaseModel):
    printing: PrintingOut
    finish: Literal["nonfoil", "foil"]
    qty: int


class SwapOut(BaseModel):
    pull: list[SwapLineOut] = Field(description="Copies to take out of the built deck (they return to the free pool).")
    sleeve: list[SwapLineOut] = Field(description="Free copies to put into the built deck (pledged).")
    short: list[SwapLineOut] = Field(description="Copies the deck needs that you don't have free.")


class BuildPlanOut(BaseModel):
    target: str | None = Field(description="The copy a build would assemble; null when every copy is built.")
    need: int
    covered: int = Field(description="Copies of `need` you have free.")
    short: list[SwapLineOut]


class BuildIn(BaseModel):
    allow_shortfall: bool = Field(False, description="Pledge what's free even if some cards are missing.")


class ActionOut(BaseModel):
    slug: str
    summary: str


class NewDeckIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    format: str = "commander"
    commander: str | None = Field(None, description="scryfall_id of the commander to seed.")


class CopyIn(BaseModel):
    name: str | None = Field(None, max_length=120)


class DraftCardIn(BaseModel):
    scryfall_id: str
    board: Literal["main", "side", "commander", "companion", "maybe", "token"]
    finish: Literal["nonfoil", "foil", "either"]
    count: int = Field(ge=0, le=999)


class DraftIn(BaseModel):
    cards: list[DraftCardIn]


class SaveIn(DraftIn):
    expected_version_id: int
    name: str | None = Field(None, max_length=120)


class ChangeOut(BaseModel):
    printing: PrintingOut
    board: str
    finish: str
    before: int
    after: int


class PreviewOut(BaseModel):
    built: bool
    changes: list[ChangeOut]
    swap: SwapOut | None = Field(description="Physical swap list; only for a built deck.")


class SaveOut(PreviewOut):
    version_number: int | None = Field(description="New version number; null when nothing changed.")
    pulled: int
    sleeved: int


class SuggestionOut(BaseModel):
    printing: PrintingOut
    inclusion_pct: float | None
    synergy: float | None
    tags: list[str]
    owned: int = Field(description="Copies owned across every printing of the card.")
    free: int = Field(description="Owned copies no built deck has pledged, across printings.")


class SuggestionsOut(BaseModel):
    commander: str
    cards: list[SuggestionOut]


def summaries() -> list[DeckSummaryOut]:
    return [DeckSummaryOut(**d) for d in deck_view.deck_summaries()]


def detail(slug: str) -> DeckDetailOut:
    d = deck_view.deck_detail(slug)
    return DeckDetailOut(deck=DeckSummaryOut(**d["deck"]), cards=[DeckCardOut(**c) for c in d["cards"]],
                         version_id=d["version_id"], editable=d["editable"])


def _n(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _lines(rows: list[dict]) -> list[SwapLineOut]:
    pr = addcards.printings_for_ids(r["scryfall_id"] for r in rows)
    return [SwapLineOut(printing=pr[r["scryfall_id"]], finish=r["finish"], qty=r["qty"])
            for r in rows if r["scryfall_id"] in pr]


def _swap(sw: dict | None) -> SwapOut | None:
    return None if sw is None else SwapOut(pull=_lines(sw["pull"]), sleeve=_lines(sw["sleeve"]), short=_lines(sw["short"]))


def _draft(cards: list[DraftCardIn]) -> list[deck_edit.DraftCard]:
    return [deck_edit.DraftCard(c.scryfall_id, c.board, c.finish, c.count) for c in cards]


def build_plan(slug: str) -> BuildPlanOut:
    p = deck_edit.build_plan(slug)
    return BuildPlanOut(target=p["target"], need=p["need"], covered=p["covered"], short=_lines(p["short"]))


def build(slug: str, body: BuildIn) -> ActionOut:
    r = deck_edit.build(slug, allow_shortfall=body.allow_shortfall)
    short = sum(s["qty"] for s in r["short"])
    return ActionOut(slug=r["slug"], summary=f"Built — {_n(r['sleeved'], 'card')} pledged" + (f", {short} still missing" if short else ""))


def break_down(slug: str) -> ActionOut:
    r = deck_edit.break_down(slug)
    return ActionOut(slug=r["slug"], summary=f"Broken down — {_n(r['pulled'], 'card')} back in your collection")


def create(body: NewDeckIn) -> ActionOut:
    slug = deck_edit.create_deck(body.name, format=body.format, commander=body.commander)
    return ActionOut(slug=slug, summary=f"Created {body.name}")


def copy(slug: str, body: CopyIn) -> ActionOut:
    new = deck_edit.copy_recipe(slug, name=body.name)
    return ActionOut(slug=new, summary="Copied — edit your copy freely")


def _changes(rows: list[dict]) -> list[ChangeOut]:
    pr = addcards.printings_for_ids(r["scryfall_id"] for r in rows)
    return [ChangeOut(printing=pr[r["scryfall_id"]], board=r["board"], finish=r["finish"], before=r["before"], after=r["after"])
            for r in rows if r["scryfall_id"] in pr]


def preview(slug: str, body: DraftIn) -> PreviewOut:
    p = deck_edit.preview(slug, _draft(body.cards))
    return PreviewOut(built=p["built"], changes=_changes(p["changes"]), swap=_swap(p["swap"]))


def save(slug: str, body: SaveIn) -> SaveOut:
    r = deck_edit.save(slug, _draft(body.cards), expected_version_id=body.expected_version_id, name=body.name)
    return SaveOut(built=r["built"], changes=_changes(r["changes"]), swap=_swap(r["swap"]),
                   version_number=r["version_number"], pulled=r["pulled"], sleeved=r["sleeved"])


def suggestions(commander: str) -> SuggestionsOut:
    r = deck_edit.suggestions(commander)
    return SuggestionsOut(commander=r["commander"], cards=[SuggestionOut(**c) for c in r["cards"]])

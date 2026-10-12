"""Jumpstart surface of the typed API (Decks → the Buy strip for one Jumpstart set).

Adapts :mod:`magic_manager.jumpstart`: a set's pack versions with the totals of
the two shopping lists, and the lists themselves. The packs are listed and
opened as deck recipes (``api.decks`` recipes); a set's card lists are read by
the ``decks.read_recipes`` job.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import addcards, jumpstart, scryfall

Target = Literal["manapool", "tcgplayer", "cardkingdom"]


class JumpstartPackOut(BaseModel):
    file_name: str
    name: str
    theme: str
    version: int | None
    color: str = Field(description="WUBRG letters of the pack's cards; 'C' = colorless.")
    card_count: int
    usd_total: float | None = Field(description="Cards at their shipped finish plus the front card.")
    top_card: str | None
    top_card_usd: float | None
    front_card: str | None
    top_card_image: str | None = None
    built: int
    deconstructed: int
    deck_slug: str | None = Field(None, description="A deck row for this version you own (built first).")
    have: int = Field(description="Pack cards your free copies cover (each pack on its own).")
    short: int = Field(description="Pack cards you have no free copy for.")
    status: Literal["build", "close", "far"]


class JumpstartShopOut(BaseModel):
    cards: int
    copies: int
    usd: float


class JumpstartOut(BaseModel):
    code: str
    name: str
    ready: bool = Field(description="False = deck files not read yet; run the jumpstart.read job.")
    close_short: int = Field(jumpstart.CLOSE_SHORT, description="A pack this many cards short or fewer is 'close'.")
    packs: list[JumpstartPackOut] = Field(default_factory=list)
    themes: int = 0
    buildable: JumpstartShopOut | None = Field(None, description="Cards to make every theme buildable (one built copy of each + other versions' extras).")
    whole: JumpstartShopOut | None = Field(None, description="Every pack version you don't own, full contents.")
    whole_packs: int = 0


class JumpstartBuyIn(BaseModel):
    shop: jumpstart.Shop
    target: Target


class JumpstartBuyOut(BaseModel):
    text: str
    lines: int


def _set_names() -> dict[str, dict]:
    try:
        return {s["code"].lower(): s for s in scryfall.all_sets() if s.get("code")}
    except Exception:  # noqa: BLE001 — names are cosmetic; codes still work offline
        return {}


def _name(code: str, names: dict[str, dict]) -> str:
    return (names.get(code) or {}).get("name") or code.upper()


def _pack(p: jumpstart.Pack, images: dict[str, str | None]) -> JumpstartPackOut:
    return JumpstartPackOut(file_name=p.file_name, name=p.name, theme=p.theme, version=p.version, color=p.color,
                            card_count=p.card_count, usd_total=p.usd_total, top_card=p.top_card,
                            top_card_usd=p.top_card_usd, top_card_image=images.get(p.top_card_id or ""),
                            front_card=p.front_card, built=p.built, deconstructed=p.deconstructed,
                            deck_slug=p.deck_slug, have=p.have, short=p.short, status=p.status)


def _images(packs: list[jumpstart.Pack]) -> dict[str, str | None]:
    pr = addcards.printings_for_ids(p.top_card_id for p in packs if p.top_card_id)
    return {sid: x.get("image_uri") for sid, x in pr.items()}


def _check(code: str) -> str:
    code = code.lower()
    if not jumpstart.variants(code):
        raise LookupError(f"{code.upper()} has no Jumpstart packs")
    return code


def view(code: str) -> JumpstartOut:
    code = _check(code)
    name = _name(code, _set_names())
    if not jumpstart.is_ready(code):
        return JumpstartOut(code=code, name=name, ready=False)
    packs = jumpstart.set_packs(code)
    images = _images(packs)
    b = jumpstart.buildable_missing(code)
    w = jumpstart.missing_packs(code)
    return JumpstartOut(
        code=code, name=name, ready=True, packs=[_pack(p, images) for p in packs],
        themes=len({p.theme for p in packs}),
        buildable=JumpstartShopOut(cards=len(b.rows), copies=b.copies, usd=b.usd),
        whole=JumpstartShopOut(cards=len(w.rows), copies=w.copies, usd=w.usd), whole_packs=len(w.packs),
    )


def buy_list(code: str, req: JumpstartBuyIn) -> JumpstartBuyOut:
    text, lines = jumpstart.buy_text(_check(code), req.shop, req.target)
    return JumpstartBuyOut(text=text, lines=lines)

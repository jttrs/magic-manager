"""Jumpstart surface of the typed API (Decks → the Buy strip for one Jumpstart set).

Adapts :mod:`magic_manager.jumpstart`: the totals of a set's two shopping lists,
and the lists themselves. The packs are listed and
opened as deck recipes (``api.decks`` recipes); a set's card lists are read by
the ``decks.read_recipes`` job.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .. import jumpstart, scryfall

Target = Literal["manapool", "tcgplayer", "cardkingdom"]


class JumpstartShopOut(BaseModel):
    cards: int
    copies: int
    usd: float


class JumpstartOut(BaseModel):
    code: str
    name: str
    ready: bool = Field(description="False = the set's pack card lists aren't read yet; run the decks.read_recipes job with {set: <code>}.")
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
    b = jumpstart.buildable_missing(code)
    w = jumpstart.missing_packs(code)
    return JumpstartOut(
        code=code, name=name, ready=True,
        buildable=JumpstartShopOut(cards=len(b.rows), copies=b.copies, usd=b.usd),
        whole=JumpstartShopOut(cards=len(w.rows), copies=w.copies, usd=w.usd), whole_packs=len(w.packs),
    )


def buy_list(code: str, req: JumpstartBuyIn) -> JumpstartBuyOut:
    text, lines = jumpstart.buy_text(_check(code), req.shop, req.target)
    return JumpstartBuyOut(text=text, lines=lines)

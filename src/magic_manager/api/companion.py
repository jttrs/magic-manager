"""Browser companion surface of the typed API (internal — ``companion`` feature flag).

Thin adapters: the browser companion (``extension/``) or the cart bookmarklet
reads in the user's OWN browser and the app posts only the normalized lines here;
each route hands them to an existing engine seam — ``cart.audit``,
``deals.supplied_tabs``, ``decksource.payload_from_moxfield`` →
``addcards.deck_lines_from_payload``. Inputs are strict (unknown fields are
refused, sizes capped) so nothing beyond card lines can ride along.
Threat model: ``docs/browser-companion-security.md``.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .. import addcards, cart, companion, deals, decksource, features
from .cart import CartAuditOut
from .deals import OpenTabsOut
from .ingest import ResolveOut

_UUID = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


class CompanionFailure(ValueError):
    """A catalogued companion error (``extension/errors.json``)."""

    def __init__(self, code: str, **detail):
        self.body = companion.error(code, **detail)
        super().__init__(self.body["message"])


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- setup ----------

class CompanionOut(BaseModel):
    version: str = Field(description="The extension version in this app's repo — older installs should update.")
    zip_url: str
    bookmarklet_url: str
    errors: dict[str, dict] = Field(description="Every companion error code → {message, fix}.")


def info() -> CompanionOut:
    """Unflagged: the error catalog also serves the cart bookmarklet paste."""
    return CompanionOut(version=companion.version(), zip_url="/api/companion/extension.zip",
                        bookmarklet_url="/api/companion/bookmarklet",
                        errors={k: {"message": v["message"], "fix": v.get("fix")} for k, v in companion.error_catalog().items()})


class BookmarkletOut(BaseModel):
    href: str
    version: str


def bookmarklet() -> BookmarkletOut:
    features.require("cart_check")
    return BookmarkletOut(href=companion.bookmarklet_href(), version=companion.version())


def extension_zip() -> bytes:
    features.require("companion")
    return companion.build_zip()


# ---------- cart ----------

class CartLineIn(_Strict):
    scryfall_id: str | None = Field(None, pattern=_UUID)
    name: str | None = Field(None, max_length=300)
    set_name: str | None = Field(None, max_length=200)
    finish: Literal["nonfoil", "foil", "etched"] = "nonfoil"
    condition: str | None = Field(None, max_length=8)
    treatments: list[str] = Field(default_factory=list, max_length=10)
    quantity: int = Field(ge=1, le=999)
    price: float | None = Field(None, ge=0, le=1_000_000)

    @field_validator("treatments")
    @classmethod
    def _short(cls, v: list[str]) -> list[str]:
        return [t[:40] for t in v]


class CartLinesIn(_Strict):
    items: list[CartLineIn] = Field(max_length=2000)
    source: Literal["extension", "bookmarklet"]
    family: str | None = Field(None, max_length=10, description="Set family to check gaps against; imputed when the cart sits in one.")


def check_lines(req: CartLinesIn) -> CartAuditOut:
    """Audit cart lines read in the user's browser. No Mana Pool account is used."""
    features.require("cart_check")
    if not req.items:
        raise CompanionFailure("cart.no_lines")
    items = [i.model_dump() for i in req.items]
    return CartAuditOut(**cart.audit(items, anchor=req.family))


# ---------- deals ----------

class TabIn(_Strict):
    url: str = Field(max_length=2000, pattern=r"^https?://")
    title: str = Field("", max_length=500)
    window: int = Field(1, ge=1, le=1000)


class TabsIn(_Strict):
    tabs: list[TabIn] = Field(max_length=500)


def tabs(req: TabsIn) -> OpenTabsOut:
    """The user's open store tabs (read by the companion) sorted like a local read."""
    features.require("deals")
    return OpenTabsOut(**deals.supplied_tabs([t.model_dump() for t in req.tabs]))


# ---------- moxfield ----------

class MoxCardIn(_Strict):
    scryfall_id: str | None = Field(None, max_length=40)
    set: str | None = Field(None, max_length=10)
    cn: str | None = Field(None, max_length=12)
    name: str | None = Field(None, max_length=200)
    finish: str | None = Field(None, max_length=20)


class MoxEntryIn(_Strict):
    quantity: int = Field(ge=1, le=999)
    isFoil: bool = False
    finish: str | None = Field(None, max_length=20)
    card: MoxCardIn


class MoxBoardIn(_Strict):
    cards: dict[str, MoxEntryIn] = Field(max_length=1000)


class MoxUserIn(_Strict):
    userName: str | None = Field(None, max_length=100)


class MoxDeckIn(_Strict):
    publicId: str = Field(pattern=r"^[A-Za-z0-9_-]{4,64}$")
    name: str | None = Field(None, max_length=200)
    createdByUser: MoxUserIn = MoxUserIn()
    boards: dict[str, MoxBoardIn] = Field(max_length=20)

    @field_validator("boards")
    @classmethod
    def _board_names(cls, v: dict) -> dict:
        if any(not re.fullmatch(r"[A-Za-z0-9_ -]{1,40}", k) for k in v):
            raise ValueError("unexpected board name")
        return v


class DeckFromBrowserIn(_Strict):
    source: Literal["moxfield"]
    deck: MoxDeckIn


def deck_lines(req: DeckFromBrowserIn) -> ResolveOut:
    """A deck the companion read in the user's browser → review lines (same
    shape as the server-side deck fetch)."""
    features.require("companion")
    data = req.deck.model_dump()
    payload = decksource.payload_from_moxfield(data, req.deck.publicId)
    if not payload["cards"]:
        raise CompanionFailure("deck.empty")
    return ResolveOut(**addcards.deck_lines_from_payload(payload))

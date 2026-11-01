"""Cart surface of the typed API: audit a cart against your collection.

Internal-only and local-only — every route checks the ``cart_check`` feature
flag, and the cart is read with YOUR Mana Pool login from the shell environment
or the gitignored repo-root ``.env`` (``MANAPOOL_EMAIL`` / ``MANAPOOL_PASSWORD``;
check with ``mm secret status``) via ``scripts/manapool_cart.py`` — the one sanctioned home of the
login code; its session token stays in memory there. Hosted, a cart is read in
the user's own browser and only its lines reach the server (Phase 3 decision H13). Never ask users for
these credentials (real money); a cart-page bookmarklet was considered and parked.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from typing import Literal

from pydantic import BaseModel, Field

from .. import cart, features, owner_machine, secrets

_CART_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "manapool_cart.py"
_ACCOUNT_KEYS = secrets.PERSONAL


class FeaturesOut(BaseModel):
    flags: dict[str, bool] = Field(description="Every flag's value for you (hosted: with your admin-set overrides).")
    owner_paths: dict[str, bool] = Field(default_factory=dict, description="Paths that run on the owner's machine or logins (owner_machine.PATHS) → may you use them here. All true locally; admins only when hosted, whatever the flags say.")
    mode: Literal["local", "hosted"] = Field("local", description="hosted = sign-in required (MM_MODE=hosted); local = no login.")


class CartSetupOut(BaseModel):
    account: bool = Field(description="Your Mana Pool login (MANAPOOL_EMAIL + MANAPOOL_PASSWORD) is in this computer's .env or environment, so the cart can be read directly.")


class CartIn(BaseModel):
    family: str | None = Field(None, max_length=10, description="Set family to check gaps against; imputed when the cart sits in one.")


class CartCardOut(BaseModel):
    scryfall_id: str | None = None
    name: str
    set: str
    num: str
    fin: str


class DupeOut(CartCardOut):
    fin: str = ""
    nf_qty: int
    fo_qty: int
    nf_price: float | None
    fo_price: float | None
    cheaper: float | None
    note: str


class OwnedOut(CartCardOut):
    owned_qty: int
    your: float
    condition: str | None = Field(None, description="The cart line's condition (NM, LP… or Card Kingdom's NM/EX/VG/G), when the store shows one.")
    language: str | None = None


class MissingOut(CartCardOut):
    market: float | None


class OverpayOut(CartCardOut):
    qty: int
    your: float | None
    market: float | None
    over: float | None = None
    pct: float | None = None
    condition: str | None = None
    language: str | None = None


class UnidentifiedOut(BaseModel):
    name: str | None
    set: str | None
    num: str | None


class NotCardOut(BaseModel):
    name: str | None
    kind: str = Field(description="sealed | other — not a card, so not checked.")
    qty: int
    price: float | None


class CartAuditOut(BaseModel):
    lines: int
    copies: int
    total: float
    unidentified: list[UnidentifiedOut]
    not_cards: list[NotCardOut] = []
    not_compared: int = Field(0, description="Played or non-English lines left out of Over market (market prices are Near Mint English).")
    family: str | None
    families: list[str]
    dupes: list[DupeOut]
    owned: list[OwnedOut]
    missing: list[MissingOut]
    overpay: list[OverpayOut]


def flags() -> FeaturesOut:
    from ..analytics import consent
    return FeaturesOut(flags=features.flags(), owner_paths=owner_machine.access(), mode=consent.mode())


def _cart_script():
    owner_machine.require("manapool.server_login")  # the server's .env login: admins only when hosted
    spec = importlib.util.spec_from_file_location("manapool_cart", _CART_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def setup() -> CartSetupOut:
    features.require("cart_check")
    owner_machine.require("manapool.server_login")
    env = _cart_script()._load_env()
    return CartSetupOut(account=all(env.get(k) for k in _ACCOUNT_KEYS))


def check(req: CartIn) -> CartAuditOut:
    features.require("cart_check")
    owner_machine.require("manapool.server_login")
    mod = _cart_script()
    items = mod.fetch_headless(mod._load_env())
    if items is None:
        raise cart.CartFormatError("Couldn’t read your cart with your Mana Pool login — check it with `uv run mm secret status`.")
    if not items:
        raise cart.CartFormatError("Your Mana Pool cart is empty.")
    return CartAuditOut(**cart.audit(cart.parse(items), anchor=req.family))

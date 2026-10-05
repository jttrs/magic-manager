"""Cart surface of the typed API: audit a Mana Pool cart against your collection.

Internal-only — every route checks the ``cart_check`` feature flag. The cart
arrives either as the safe bookmarklet's paste (set + number lines, matched
locally, no Mana Pool credentials) or, on a machine with ``MANAPOOL_*`` in
``.env``, straight from the account via ``scripts/manapool_cart.py`` (the one
sanctioned home of the login code; its session token stays in memory there).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from pydantic import BaseModel, Field

from .. import cart, features

_CART_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "manapool_cart.py"
_ACCOUNT_KEYS = ("MANAPOOL_EMAIL", "MANAPOOL_PASSWORD", "MANAPOOL_ACCESS_TOKEN")


class FeaturesOut(BaseModel):
    flags: dict[str, bool]


class CartSetupOut(BaseModel):
    account: bool = Field(description="MANAPOOL_EMAIL, _PASSWORD and _ACCESS_TOKEN are configured, so the cart can be read directly.")


class CartIn(BaseModel):
    cart: str | None = Field(None, max_length=2_000_000, description="The bookmarklet's pasted JSON.")
    use_account: bool = Field(False, description="Read the cart with the configured Mana Pool account instead.")
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


class MissingOut(CartCardOut):
    market: float | None


class OverpayOut(CartCardOut):
    qty: int
    your: float | None
    market: float | None
    over: float | None = None
    pct: float | None = None


class UnidentifiedOut(BaseModel):
    name: str | None
    set: str | None
    num: str | None


class CartAuditOut(BaseModel):
    lines: int
    copies: int
    total: float
    unidentified: list[UnidentifiedOut]
    family: str | None
    families: list[str]
    dupes: list[DupeOut]
    owned: list[OwnedOut]
    missing: list[MissingOut]
    overpay: list[OverpayOut]


def flags() -> FeaturesOut:
    return FeaturesOut(flags=features.flags())


def _cart_script():
    spec = importlib.util.spec_from_file_location("manapool_cart", _CART_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def setup() -> CartSetupOut:
    features.require("cart_check")
    env = _cart_script()._load_env()
    return CartSetupOut(account=all(env.get(k) for k in _ACCOUNT_KEYS))


def check(req: CartIn) -> CartAuditOut:
    features.require("cart_check")
    if req.use_account:
        mod = _cart_script()
        items = mod.fetch_headless(mod._load_env())
        if items is None:
            raise cart.CartFormatError("Couldn’t read the cart with your Mana Pool account — check MANAPOOL_* in .env, or paste from the bookmarklet.")
    elif req.cart:
        items = cart.parse(req.cart)
    else:
        raise cart.CartFormatError("Paste the cart the bookmarklet copied.")
    if not items:
        raise cart.CartFormatError("Your Mana Pool cart is empty.")
    return CartAuditOut(**cart.audit(items, anchor=req.family))

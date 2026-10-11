"""Purchases surface of the typed API (internal — ``purchases`` feature flag).

Thin adapters over :mod:`magic_manager.purchases`: the browser companion reads
your order history in your own browser and the app posts the normalized orders
here (strict models — unknown fields are refused, sizes capped, so nothing but
order lines can ride along); the review/apply routes drive the engine.
Threat model: ``docs/browser-companion-security.md``; design: ``docs/purchases.md``.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import addcards, features, purchases
from .companion import CompanionFailure
from .ingest import PrintingOut

_UUID = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
Store = Literal["manapool", "tcgplayer", "cardkingdom"]
Verification = Literal["verified", "partial", "unverified"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- stores ----------

class StoreOut(BaseModel):
    key: Store
    name: str
    verification: Verification = Field(description="How much of this store's reading has been checked against its real pages.")
    note: str = Field(description="What is and isn't verified, in plain words.")
    needs_permission: bool = Field(description="True when the companion's optional 'Order history' switch must be on.")


def stores() -> list[StoreOut]:
    features.require("purchases")
    return [StoreOut(key=k, name=purchases.STORES[k], verification=v, note=n, needs_permission=k != "manapool")
            for k, (v, n) in purchases.STORE_VERIFICATION.items()]


# ---------- companion → save ----------

class OrderLineIn(_Strict):
    kind: Literal["single", "sealed", "other"] = "single"
    name: str | None = Field(None, max_length=300)
    set_name: str | None = Field(None, max_length=200)
    set_code: str | None = Field(None, max_length=12, pattern=r"^[a-z0-9]+$")
    collector_number: str | None = Field(None, max_length=16)
    scryfall_id: str | None = Field(None, pattern=_UUID)
    tcgplayer_product_id: int | None = Field(None, ge=1, le=100_000_000)
    finish: Literal["nonfoil", "foil", "etched"] = "nonfoil"
    condition: str | None = Field(None, max_length=24)
    rarity: str | None = Field(None, max_length=4)
    treatments: list[str] = Field(default_factory=list, max_length=10)
    detail: str | None = Field(None, max_length=120)
    quantity: int = Field(ge=1, le=9999)
    price: float | None = Field(None, ge=0, le=1_000_000)


class OrderIn(_Strict):
    order_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    ordered_at: str = Field(max_length=32, pattern=r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?Z?)?$")
    ordered_on: str | None = Field(None, max_length=10)
    lines: list[OrderLineIn] = Field(max_length=2000)
    subtotal: float | None = Field(None, ge=0, le=10_000_000)
    shipping: float | None = Field(None, ge=0, le=1_000_000)
    tax: float | None = Field(None, ge=0, le=1_000_000)
    fees: float | None = Field(None, ge=0, le=1_000_000)
    credit: float | None = Field(None, ge=0, le=1_000_000)
    total: float | None = Field(None, ge=0, le=10_000_000)


class OrdersIn(_Strict):
    store: Store
    orders: list[OrderIn] = Field(max_length=100)
    warnings: list[dict] = Field(default_factory=list, max_length=500)


class SaveOut(BaseModel):
    saved: int
    skipped: list[str] = Field(description="Order numbers already assigned to your collection (left untouched).")
    unresolved: int = Field(description="Single-card lines no exact printing was found for (recorded, never added).")
    purchase_ids: list[int]


def save(req: OrdersIn) -> SaveOut:
    features.require("purchases")
    if not req.orders:
        raise CompanionFailure("orders.no_lines")
    orders = [purchases.Order(
        store=req.store, order_id=o.order_id, ordered_at=o.ordered_at.rstrip("Z"),
        subtotal=o.subtotal, shipping=o.shipping, tax=o.tax, fees=o.fees, credit=o.credit, total=o.total,
        lines=[purchases.OrderLine(
            name=(ln.name or ln.detail or "Unnamed line"), quantity=ln.quantity, finish=ln.finish, unit_price=ln.price,
            set_name=ln.set_name, set_code=ln.set_code, collector_number=ln.collector_number,
            condition=ln.condition, scryfall_id=ln.scryfall_id, tcgplayer_product_id=ln.tcgplayer_product_id,
            kind=ln.kind,
        ) for ln in o.lines],
    ) for o in req.orders]
    r = purchases.save(orders)
    return SaveOut(saved=len(r.saved), skipped=r.skipped, unresolved=r.unresolved, purchase_ids=r.saved)


# ---------- read side ----------

class PurchaseOut(BaseModel):
    purchase_id: int
    store: Store
    store_name: str
    order_id: str
    ordered_at: str
    read_at: str
    lines: int
    copies: int
    assigned: int = Field(description="Copies matched to cards you owned or added new.")
    assignable: int = Field(description="Copies on lines with a known printing.")
    unresolved: int
    status: Literal["new", "partial", "done", "nothing"]
    paid_usd: float = Field(description="Item prices × quantity, every line.")
    worth_usd: float = Field(description="Lines with a price today, at today's local prices.")
    compared_paid_usd: float = Field(description="What those same lines cost you.")
    gain_usd: float
    subtotal_usd: float | None = Field(None, description="The store's own item subtotal. When it differs from paid_usd, the "
                                                         "store's line list includes replacements or refunds the companion can't price exactly.")
    shipping_usd: float | None = None
    tax_usd: float | None = None
    fees_usd: float | None = None
    credit_usd: float | None = None
    total_usd: float | None = None
    ingest_id: int | None = None


class PurchasesOut(BaseModel):
    purchases: list[PurchaseOut]
    paid_usd: float
    compared_paid_usd: float
    worth_usd: float
    gain_usd: float


def catalog() -> PurchasesOut:
    features.require("purchases")
    ps = [PurchaseOut(**vars(p)) for p in purchases.catalog()]
    cmp_paid = round(sum(p.compared_paid_usd for p in ps), 2)
    worth = round(sum(p.worth_usd for p in ps), 2)
    return PurchasesOut(purchases=ps, paid_usd=round(sum(p.paid_usd for p in ps), 2), compared_paid_usd=cmp_paid,
                        worth_usd=worth, gain_usd=round(worth - cmp_paid, 2))


class ReviewLineOut(BaseModel):
    line_no: int
    kind: Literal["single", "sealed", "other"]
    name: str
    set_name: str | None
    condition: str | None
    finish: Literal["nonfoil", "foil"]
    printing: PrintingOut | None
    quantity: int
    unit_usd: float | None
    today_usd: float | None
    matched: int
    added: int
    remaining: int
    owned: int
    matchable: int = Field(description="Owned copies whose source is unknown or singles — they can be matched to this order.")


class ReviewOut(BaseModel):
    purchase: PurchaseOut
    lines: list[ReviewLineOut]


def review(purchase_id: int) -> ReviewOut:
    features.require("purchases")
    rv = purchases.review(purchase_id)
    printings = addcards.printings_for_ids(ln.scryfall_id for ln in rv.lines if ln.scryfall_id)
    return ReviewOut(purchase=PurchaseOut(**vars(rv.purchase)), lines=[
        ReviewLineOut(**{k: v for k, v in vars(ln).items() if k != "scryfall_id"},
                      printing=PrintingOut(**printings[ln.scryfall_id]) if ln.scryfall_id in printings else None)
        for ln in rv.lines
    ])


class DecisionIn(_Strict):
    line_no: int = Field(ge=1)
    match: int = Field(0, ge=0, le=9999)
    add: int = Field(0, ge=0, le=9999)


class ApplyIn(_Strict):
    lines: list[DecisionIn] = Field(max_length=2000)


class ApplyOut(BaseModel):
    purchase_id: int
    ingest_id: int
    matched: int
    added: int


def apply(purchase_id: int, req: ApplyIn) -> ApplyOut:
    features.require("purchases")
    r = purchases.apply(purchase_id, [purchases.Decision(d.line_no, d.match, d.add) for d in req.lines])
    return ApplyOut(**vars(r))


def forget(purchase_id: int) -> None:
    features.require("purchases")
    purchases.forget(purchase_id)

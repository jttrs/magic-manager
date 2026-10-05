"""Market surface of the typed API: what sealed product, cards and decks cost.

Adapts :mod:`magic_manager.market` (the engine). Valuing a family's sealed
products is a job (first valuation of a set fetches prices; progress per product).
"""
from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel, Field

from .. import market
from .jobs import Artifact, JobResult, JobSpec, ProgressEvent, ProgressFn, register


class ProductOut(BaseModel):
    set_code: str
    name: str
    category: str | None = None
    subtype: str | None = None
    release_date: str | None = None
    tcgplayer_url: str | None = None


class FamilyProductsOut(BaseModel):
    code: str
    name: str
    products: list[ProductOut]


class ProductValueOut(BaseModel):
    set_code: str
    name: str
    sealed_market: float | None = Field(None, description="The sealed product's own market price.")
    market_source: str | None = None
    contents_value: float | None = Field(None, description="What's inside: fixed cards + booster EV.")
    exact_singles: float | None = Field(None, description="Σ the product's exact card printings.")
    floor_singles: float | None = Field(None, description="Σ the cheapest printing of each card anywhere.")
    booster_only: bool = False
    coverage: float | None = None
    unpriced_cards: int = Field(0, description="Fixed cards with no price at their exact printing (contents value undercounts).")
    total_cards: int = 0
    notes: list[str] = Field(default_factory=list)
    error: str | None = None


class TreeNodeOut(BaseModel):
    name: str
    kind: str
    count: int
    market: float | None
    contents_value: float | None
    contents_kind: str
    children: list["TreeNodeOut"] = Field(default_factory=list)


class CardPriceOut(BaseModel):
    scryfall_id: str
    oracle_id: str | None
    name: str
    set_code: str
    collector_number: str
    rarity: str
    type_line: str | None
    finishes: list[str]
    treatment: str
    image_uri: str | None
    is_chase: bool
    price_usd: float | None
    price_usd_foil: float | None
    floor_usd: float | None = Field(None, description="Cheapest nonfoil printing of this card anywhere.")
    floor_set_code: str | None = None
    floor_collector_number: str | None = None
    owned: int


class FamilyCardsOut(BaseModel):
    code: str
    name: str
    cards: list[CardPriceOut]


class DeckLineOut(BaseModel):
    scryfall_id: str
    finish: str
    name: str
    set_code: str
    collector_number: str
    need: int
    free: int
    buy: int
    unit_usd: float | None
    floor_usd: float | None
    floor_set_code: str | None = None
    floor_collector_number: str | None = None
    floor_scryfall_id: str = Field(description="The cheapest printing (this one when unpriced elsewhere).")


class DeckCostOut(BaseModel):
    slug: str
    sealed_product: str | None = Field(None, description="The sealed product this precon ships in.")
    sealed: float | None
    scratch: float | None = Field(None, description="Every card new, exact printings.")
    with_collection: float | None = Field(None, description="Your free cards first, buy the rest (exact).")
    scratch_floor: float
    with_collection_floor: float
    coverage: float
    unpriced: int
    total_need: int
    lines: list[DeckLineOut]


def family_products(code: str) -> FamilyProductsOut:
    return FamilyProductsOut(**market.family_products(code))


def value_product(set_code: str, name: str) -> ProductValueOut:
    return ProductValueOut(**market.value_products([(set_code, name)])[0])


def product_tree(set_code: str, name: str) -> TreeNodeOut:
    return TreeNodeOut(**asdict(market.product_tree(set_code, name)))


def family_cards(code: str) -> FamilyCardsOut:
    return FamilyCardsOut(**market.family_card_prices(code))


def deck_cost(slug: str) -> DeckCostOut:
    return DeckCostOut(**market.deck_cost(slug))


class ValueFamilyInput(BaseModel):
    code: str = Field(min_length=2, max_length=10, description="Any set code in the family.")


def _run_value_family(inp: ValueFamilyInput, progress: ProgressFn) -> JobResult:
    fam = market.family_products(inp.code)
    items = [(p["set_code"], p["name"]) for p in fam["products"]]
    progress(ProgressEvent(0, len(items), f"Valuing {len(items)} products…"))
    rows = market.value_products(
        items, progress=lambda i, n, name: progress(ProgressEvent(i - 1, n, name)))
    progress(ProgressEvent(len(items), len(items), "Done"))
    out = [ProductValueOut(**r).model_dump() for r in rows]
    failed = sum(1 for r in out if r["error"])
    return JobResult(
        summary=f"{fam['name']} · {len(out) - failed} products valued" + (f" · {failed} failed" if failed else ""),
        artifacts=[Artifact(kind="json", label="values", data=out)],
    )


VALUE_FAMILY = register(JobSpec(
    name="market.value_family",
    title="Value sealed products",
    description="Price every sealed product in a set family: sealed market vs what's inside.",
    input_model=ValueFamilyInput,
    run=_run_value_family,
))

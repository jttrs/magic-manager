"""Market: what sealed product, cards and decks cost — for the web Market view.

Thin composition over the existing engines (no new valuation math):

* a set family's sealed products → :func:`valuation.value_sealed_product` (the
  4-column valuation: sealed market · exact singles · floor singles · contents
  value incl. booster EV) and :func:`sealed.build_product_tree` for drill-down;
* a family's cards → every printing's exact price (``collection_view``) next to
  its functional floor (``sets.lowest_price_by_oracle``: cheapest printing
  anywhere) and what you own;
* a deck recipe's cost → ``construct`` (expand → net against loose → summarize)
  plus the floor alternative per line and, for precons, the sealed product price.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Callable

from . import collection_view, construct, db, family_status, mtgjson, sealed, sets, valuation


# ---------- sealed products ----------

def family_codes(code: str) -> tuple[str, str, list[str]]:
    """(anchor, name, member set codes) for any member code of a family."""
    parent, name, related = family_status.resolve_family(code)
    return parent, name, sorted(family_status._family_code_set(parent, related))


def family_products(code: str) -> dict:
    """Every sealed product (MTGJSON ``sealedProduct``) across a family's sets."""
    parent, name, codes = family_codes(code)
    out = []
    for c in codes:
        try:
            products = mtgjson.sealed_products(c)
        except Exception:  # noqa: BLE001 — a member set without an MTGJSON file has no products
            continue
        for p in products:
            out.append({
                "set_code": c, "name": p.get("name") or "", "category": p.get("category"),
                "subtype": p.get("subtype"), "release_date": p.get("releaseDate"),
                "tcgplayer_url": (p.get("purchaseUrls") or {}).get("tcgplayer"),
            })
    out.sort(key=lambda p: (p["category"] or "", p["name"]))
    return {"code": parent, "name": name, "products": out}


def value_products(items: list[tuple[str, str]], *,
                   progress: Callable[[int, int, str], None] | None = None) -> list[dict]:
    """Value each ``(set_code, product name)`` — failures become error rows."""
    floors: dict = {}
    rows = []
    for i, (set_code, name) in enumerate(items, 1):
        if progress:
            progress(i, len(items), name)
        try:
            v = valuation.value_sealed_product(set_code, name, floors_cache=floors)
            rows.append({
                "set_code": set_code, "name": name, "sealed_market": v.sealed_market,
                "market_source": v.sealed_market_source, "contents_value": v.intrinsic,
                "exact_singles": v.exact_singles, "floor_singles": v.floor_singles,
                "booster_only": v.booster_only, "coverage": round(v.coverage, 3),
                "unpriced_cards": v.unpriced_cards, "total_cards": v.total_cards,
                "notes": [*v.diagnostics, *([v.note] if v.note else [])], "error": None,
            })
        except Exception as e:  # noqa: BLE001 — one bad product never sinks the batch
            rows.append({"set_code": set_code, "name": name, "error": str(e)})
    return rows


@dataclass
class TreeNode:
    name: str
    kind: str
    count: int
    market: float | None
    contents_value: float | None
    contents_kind: str
    children: list["TreeNode"] = field(default_factory=list)


def _node(n: sealed.ProductNode) -> TreeNode:
    return TreeNode(name=n.name, kind=n.kind, count=n.count, market=n.market_usd,
                    contents_value=sealed.aggregate(n).intrinsic, contents_kind=n.intrinsic_kind,
                    children=[_node(c) for c in n.children])


def product_tree(set_code: str, name: str) -> TreeNode:
    """One product's contents, recursively, each node with market + contents value."""
    tree, _ = valuation.priced_tree(set_code, sealed.identify_product(set_code, name))
    return _node(tree)


# ---------- cards: exact printing vs functional floor ----------

def family_card_prices(code: str) -> dict:
    """Every printing in the family at its exact price, beside the card's
    functional floor (cheapest printing anywhere) and your copies."""
    fc = collection_view.family_cards(code)
    floors = sets.lowest_price_by_oracle({c.oracle_id for c in fc.cards if c.oracle_id})
    cards = []
    for c in fc.cards:
        f = floors.get(c.oracle_id or "") or {}
        cards.append({
            "scryfall_id": c.scryfall_id, "oracle_id": c.oracle_id, "name": c.name,
            "set_code": c.set_code, "collector_number": c.collector_number, "rarity": c.rarity,
            "type_line": c.type_line, "finishes": c.finishes, "treatment": c.treatment,
            "image_uri": c.image_uri, "is_chase": c.is_chase,
            "price_usd": c.price_usd, "price_usd_foil": c.price_usd_foil,
            "floor_usd": f.get("lowest_usd"), "floor_set_code": f.get("set_code"),
            "floor_collector_number": f.get("collector_number"),
            "owned": c.owned_total,
        })
    return {"code": fc.summary.code, "name": fc.summary.name, "cards": cards}


# ---------- deck recipe cost ----------

def _precon_product(slug: str) -> tuple[str, str] | None:
    """The sealed product that ships this precon (set code, product name), if any."""
    with db.connect() as conn:
        row = conn.execute("SELECT name, source_precon_file_name FROM decks WHERE slug = ?", (slug,)).fetchone()
    if not row or not row["source_precon_file_name"]:
        return None
    code = row["source_precon_file_name"].rpartition("_")[2].lower()
    try:
        products = mtgjson.sealed_products(code)
    except Exception:  # noqa: BLE001
        return None
    for p in products:
        for d in (p.get("contents") or {}).get("deck") or []:
            if (d.get("name") or "").casefold() == (row["name"] or "").casefold():
                return code, p.get("name") or ""
    return None


def card_lines(rows: list[construct.NetRow]) -> tuple[list[dict], float, float]:
    """Each netted card at its exact printing and at its cheapest printing (the
    functional floor, from local prices — capped at the exact price, since that
    printing is one of the card's printings). Returns ``(lines, Σ floor·need,
    Σ floor·buy)``. Shared by deck cost and product cost."""
    with db.connect() as conn:
        oids = {r[0]: r[1] for r in conn.execute(
            f"SELECT scryfall_id, oracle_id FROM cards WHERE scryfall_id IN ({','.join('?' * len(rows)) or 'NULL'})",
            [r.scryfall_id for r in rows])}
    floors = sets.lowest_price_by_oracle(set(v for v in oids.values() if v))
    lines = []
    need_floor = buy_floor = 0.0
    for r in rows:
        f = floors.get(oids.get(r.scryfall_id) or "") or {}
        floor = f.get("lowest_usd")
        cheaper_elsewhere = floor is not None and (r.unit_usd is None or floor < r.unit_usd)
        if not cheaper_elsewhere:
            floor = r.unit_usd if r.unit_usd is not None else floor
            f = {}
        if floor is not None:
            need_floor += floor * r.need_qty
            buy_floor += floor * r.buy_qty
        lines.append({
            "scryfall_id": r.scryfall_id, "finish": r.finish, "name": r.name,
            "set_code": r.set_code, "collector_number": r.collector_number,
            "need": r.need_qty, "free": r.loose_qty, "buy": r.buy_qty,
            "unit_usd": r.unit_usd, "floor_usd": floor,
            "floor_set_code": f.get("set_code"), "floor_collector_number": f.get("collector_number"),
            "floor_scryfall_id": f.get("scryfall_id") or r.scryfall_id,
        })
    return lines, round(need_floor, 2), round(buy_floor, 2)


_COST_TTL = 30 * 60
_cost_memo: dict[tuple, tuple[float, dict]] = {}


def product_cost(kind: str, set_code: str, name: str, finish: str | None = None) -> dict:
    """What a sealed product or Secret Lair drop is worth, every way: its own
    market price; what's inside at exact printings and at each card's cheapest
    printing, split into KNOWN cards and random-booster EV; and every known card
    as a line (exact + floor + your free copies). Memoized 30 min per product —
    market prices don't move faster, and valuing is slow."""
    key = (kind, set_code.lower(), name, finish)
    hit = _cost_memo.get(key)
    if hit and time.monotonic() - hit[0] < _COST_TTL:
        return hit[1]
    out = _sld_cost(name, finish) if kind == "sld" else _sealed_cost(set_code, name)
    _cost_memo[key] = (time.monotonic(), out)
    return out


def _cost_totals(rows: list[construct.NetRow], ev: float | None) -> dict:
    lines, floor_cards, _ = card_lines(rows)
    priced = [ln for ln in lines if ln["unit_usd"] is not None]
    known_exact = round(sum(ln["unit_usd"] * ln["need"] for ln in priced), 2) if priced else None
    known_floor = floor_cards if lines else None
    plus = lambda v: None if v is None and ev is None else round((v or 0.0) + (ev or 0.0), 2)  # noqa: E731
    total = sum(ln["need"] for ln in lines)
    return {"known_exact": known_exact, "known_floor": known_floor, "booster_ev": ev,
            "exact": plus(known_exact), "floor": plus(known_floor),
            "total_cards": total, "unpriced": total - sum(ln["need"] for ln in priced), "lines": lines}


# Valuation diagnostics the cost ledger already shows as numbers (booster EV, unpriced count).
_LEDGER_NOTE = re.compile(r"random-booster EV \(cols 3/4\)|have no price at their exact printing")


def _sealed_cost(set_code: str, name: str) -> dict:
    product = sealed.identify_product(set_code, name)
    v = valuation.value_sealed_product(set_code, product.get("name"), floors=False)
    rows = construct.net_against_loose(v.card_needs)
    return {"kind": "sealed", "set_code": set_code.lower(), "name": product.get("name") or name,
            "finish": None, "category": product.get("category"), "subtype": product.get("subtype"),
            "release_date": product.get("releaseDate"), "market": v.sealed_market,
            "market_source": v.sealed_market_source, "contents": v.intrinsic, "booster_only": v.booster_only,
            "notes": [d for d in v.diagnostics if not _LEDGER_NOTE.search(d)], **_cost_totals(rows, v.booster_ev)}


def _sld_cost(name: str, finish: str | None) -> dict:
    from . import sld
    drop = sld.identify_drop(name)
    ids = drop.get("ids") or sld.collect_drop_ids(drop["file_names"])
    notes = []
    fin = "foil" if finish == "foil" else "nonfoil"
    exp = construct.expand_printings(ids, finish=fin, label=drop["name"], set_code="sld")
    if fin == "foil" and not any(n.unit_usd is not None for n in exp.needs):
        exp = construct.expand_printings(ids, finish="nonfoil", label=drop["name"], set_code="sld")
        notes.append("foil edition, but these cards are only priced nonfoil — cards use nonfoil prices")
    market, source = valuation.sld_sealed_market(drop["name"], "foil" if finish == "foil" else "auto")
    totals = _cost_totals(construct.net_against_loose(exp.needs), None)
    return {"kind": "sld", "set_code": "sld", "name": drop["name"], "finish": finish,
            "category": "secret_lair", "subtype": None, "release_date": drop.get("release_date"),
            "market": market, "market_source": source, "contents": totals["exact"], "booster_only": False,
            "notes": notes, **totals}


def deck_cost(slug: str, *, with_sealed: bool = True) -> dict:
    """Three ways to get a deck: sealed (precons), everything new, or your free
    cards first — each line at its exact printing and at the functional floor."""
    exp = construct.expand_slug(slug)
    rows = construct.net_against_loose(exp.needs)
    sealed_market = sealed_name = None
    prod = _precon_product(slug) if with_sealed else None
    if prod:
        try:
            v = valuation.value_sealed_product(prod[0], prod[1], floors=False)
            sealed_market, sealed_name = v.sealed_market, v.label
        except Exception:  # noqa: BLE001 — sealed price is optional
            pass
    summary = construct.summarize(rows, sealed_market)
    lines, scratch_floor, with_collection_floor = card_lines(rows)
    lines.sort(key=lambda ln: -((ln["floor_usd"] or 0) * ln["buy"]))
    return {
        "slug": slug, "sealed_product": sealed_name, "sealed": sealed_market,
        "scratch": summary["scratch"], "with_collection": summary["with_collection"],
        "scratch_floor": scratch_floor, "with_collection_floor": with_collection_floor,
        "coverage": round(summary["coverage"], 3), "unpriced": summary["n_unpriced"],
        "total_need": summary["total_need"], "lines": lines,
    }

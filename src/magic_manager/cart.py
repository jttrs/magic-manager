"""Mana Pool cart audit — the DRY engine behind the cart tools.

A cart is a list of line dicts; any of these identify the printing (tried in
order, the first that resolves wins):

  ``scryfall_id``                 direct.
  ``set`` + ``number``            the safe bookmarklet's shape (it reads only the
                                  rendered cart page) → the local ``cards`` table.
  ``card_id`` (MTGJSON uuid)      the headless / legacy bookmarklet shape → Mana
                                  Pool's catalog via ``manapool.sh`` (needs
                                  ``MANAPOOL_*`` credentials; skipped without).

plus ``quantity``, ``price_cents`` (or ``price`` in dollars), and a finish
(``finish_id`` FO/NF/ET or ``finish`` foil/nonfoil/etched), optional
``condition_id``.

Four atomic checks share ONE mapping pass:

  dupes    printings bought more than once (×N one finish, or foil + nonfoil).
  owned    cart lines whose exact printing + finish you already own.
  missing  family gaps (``missing.missing_printings``) not in the cart.
  overpay  lines priced over market (local prices by default; live Scryfall
           for the CLI, which has always been live).

Drivers: ``scripts/manapool_cart_check.py`` / ``manapool_price_check.py`` (CLI)
and ``api.cart`` (web, behind the ``cart_check`` feature flag).
"""
from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from typing import Callable

from . import db, manapool, missing as missing_mod, sets as sets_mod
from .util import cn_sort_key

# Mana Pool finish_id -> is_foil. FO=foil, NF/FN=nonfoil, ET=etched (foil-like).
FINISH_FOIL = {"FO": True, "NF": False, "FN": False, "ET": True}

# A line is flagged as overpaid when it clears BOTH gates: ≥ pct over market AND
# more than this many dollars over (kills "+19% = 4 cents" noise).
OVER_MARKET_USD_MIN = 1.00


class CartFormatError(ValueError):
    """The pasted text isn't a cart."""


@dataclass
class CartLine:
    card_id: str | None            # MTGJSON uuid (when the source carried one)
    price_cents: int | None
    finish_id: str | None
    condition_id: str | None
    quantity: int
    scryfall_id: str | None        # None when the line couldn't be identified
    name: str | None
    set_code: str | None           # upper-cased
    number: str | None
    foil: bool
    prod: dict | None              # Mana Pool product row (only via the catalog path)


# ---------- parsing ----------

def parse(data) -> list[dict]:
    """A cart from pasted JSON text or an already-parsed value: a raw array or
    an ``{"items": [...]}`` envelope."""
    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise CartFormatError("That isn't cart data — paste what the bookmarklet copied.") from e
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise CartFormatError("That isn't cart data — paste what the bookmarklet copied.")
    return items


def _is_foil(c: dict) -> bool:
    if c.get("finish_id") in FINISH_FOIL:
        return FINISH_FOIL[c["finish_id"]]
    return str(c.get("finish") or "").lower() in ("foil", "etched")


def _price_cents(c: dict) -> int | None:
    if isinstance(c.get("price_cents"), (int, float)):
        return int(c["price_cents"])
    if isinstance(c.get("price"), (int, float)):
        return round(c["price"] * 100)
    return None


# ---------- mapping ----------

def single_product(uuid: str) -> dict | None:
    """One Mana Pool catalog row for an MTGJSON uuid (scryfall_id + variants).
    Raises ``manapool.ManapoolUnconfigured`` without credentials."""
    data = manapool._run(["raw", "GET", "/products/singles",
                          "mtgjson_uuids=" + urllib.parse.quote(uuid)]).get("data", [])
    return data[0] if data else None


def _local_cards(*, ids: set[str], set_numbers: set[tuple[str, str]]) -> tuple[dict, dict]:
    by_id: dict[str, dict] = {}
    by_sn: dict[tuple[str, str], dict] = {}
    with db.connect() as conn:
        if ids:
            q = ",".join("?" * len(ids))
            for r in conn.execute(f"SELECT scryfall_id, name, set_code, collector_number FROM cards WHERE scryfall_id IN ({q})", list(ids)):
                by_id[r["scryfall_id"]] = dict(r)
        for s, n in set_numbers:
            r = conn.execute("SELECT scryfall_id, name, set_code, collector_number FROM cards WHERE set_code = ? AND collector_number = ?", (s, n)).fetchone()
            if r:
                by_sn[(s, n)] = dict(r)
    return by_id, by_sn


def _fill_ids(ids: set[str]) -> dict[str, dict]:
    """Printings the cart names by scryfall_id that aren't in the local catalog
    yet (an unsynced set) — fetched once from Scryfall and upserted, so a cart
    read in the browser identifies every exact printing."""
    from . import scryfall
    try:
        found, _ = scryfall.collection([{"id": s} for s in sorted(ids)])
    except Exception:  # noqa: BLE001 — offline: those lines stay unidentified, named
        return {}
    with db.connect() as conn:
        db.upsert_cards(conn, found)
    return {c["id"]: {"scryfall_id": c["id"], "name": c.get("name"), "set_code": c.get("set"),
                      "collector_number": c.get("collector_number")} for c in found}


def map_cart(cart: list[dict], *, remote: bool = True,
             product_fn: Callable[[str], dict | None] | None = None) -> list[CartLine]:
    """Identify every cart line once (see module doc for the order). The Mana
    Pool catalog is consulted only for lines nothing local identified, once per
    uuid, and not at all after it reports missing credentials. Cart order kept."""
    product_fn = product_fn or single_product
    ids = {c["scryfall_id"] for c in cart if c.get("scryfall_id")}
    sns = {(str(c["set"]).lower(), str(c["number"])) for c in cart if c.get("set") and c.get("number")}
    by_id, by_sn = _local_cards(ids=ids, set_numbers=sns)
    if remote and ids - by_id.keys():
        by_id.update(_fill_ids(ids - by_id.keys()))

    prod_by_uuid: dict[str, dict | None] = {}
    configured = remote
    out: list[CartLine] = []
    for c in cart:
        local = by_id.get(c.get("scryfall_id") or "") or by_sn.get((str(c.get("set") or "").lower(), str(c.get("number") or "")))
        prod = None
        uuid = c.get("card_id")
        if not local and uuid and configured:
            if uuid not in prod_by_uuid:
                try:
                    prod_by_uuid[uuid] = product_fn(uuid)
                except manapool.ManapoolUnconfigured:
                    configured = False
                    prod_by_uuid[uuid] = None
                except manapool.ManapoolError:
                    prod_by_uuid[uuid] = None
            prod = prod_by_uuid.get(uuid)
        sid = (local or {}).get("scryfall_id") or (prod or {}).get("scryfall_id")
        number = (local or {}).get("collector_number") or ((prod or {}).get("number"))
        out.append(CartLine(
            card_id=uuid, price_cents=_price_cents(c), finish_id=c.get("finish_id"),
            condition_id=c.get("condition_id"), quantity=int(c.get("quantity") or 1),
            scryfall_id=sid,
            name=(local or {}).get("name") or (prod or {}).get("name") or c.get("name"),
            set_code=((local or {}).get("set_code") or (prod or {}).get("set_code") or c.get("set") or "").upper() or None,
            number=str(number) if number is not None else (str(c["number"]) if c.get("number") else None),
            foil=_is_foil(c), prod=prod,
        ))
    return out


# ---------- pricing ----------

def _usd(cents) -> float | None:
    return round(cents / 100.0, 2) if isinstance(cents, (int, float)) else None


def _variant_low(prod: dict, foil: bool, condition: str) -> int | None:
    """Mana Pool's lowest ask (cents) for the finish+condition, falling back to
    the finish's cheapest across conditions, then the top-level nm field."""
    want_fin = {"FO"} if foil else {"NF", "FN"}
    cands = [v for v in prod.get("variants", []) if v.get("finish_id") in want_fin and v.get("low_price")]
    if not cands:
        return prod.get("price_cents_nm_foil") if foil else prod.get("price_cents_nm")
    exact = [v for v in cands if v.get("condition_id") == condition]
    return min(v["low_price"] for v in (exact or cands))


def live_prices(scryfall_ids: list[str]) -> dict[str, dict]:
    """Live Scryfall prices (the CLI's historical basis)."""
    from . import scryfall
    found, _ = scryfall.collection([{"id": s} for s in scryfall_ids]) if scryfall_ids else ([], [])
    return {c["id"]: c.get("prices") or {} for c in found}


def local_prices(scryfall_ids: list[str]) -> dict[str, dict]:
    """Local market prices from the synced ``cards`` table (Scryfall's keys)."""
    if not scryfall_ids:
        return {}
    with db.connect() as conn:
        q = ",".join("?" * len(scryfall_ids))
        return {
            r[0]: {"usd": r[1], "usd_foil": r[2]}
            for r in conn.execute(f"SELECT scryfall_id, prices_usd, prices_usd_foil FROM cards WHERE scryfall_id IN ({q})", scryfall_ids)
        }


def overpay_rows(mapped: list[CartLine], prices_fn: Callable[[list[str]], dict] = live_prices) -> dict:
    """Each identified line's price vs market: ``{"rows": [...] (by -pct),
    "no_market": [...], "unmapped": n}``. Flagging is the caller's threshold."""
    prices = prices_fn(sorted({m.scryfall_id for m in mapped if m.scryfall_id}))
    rows: list[dict] = []
    no_market: list[dict] = []
    unmapped = 0
    for m in mapped:
        if not m.scryfall_id:
            unmapped += 1
            continue
        your = _usd(m.price_cents)
        val = (prices.get(m.scryfall_id) or {}).get("usd_foil" if m.foil else "usd")
        market = float(val) if val not in (None, "") else None
        rec = {
            "scryfall_id": m.scryfall_id, "name": m.name or "?", "set": m.set_code or "",
            "num": m.number or "", "fin": "foil" if m.foil else "nonfoil", "qty": m.quantity,
            "your": your, "market": market,
            "mp_cheap": _usd(_variant_low(m.prod, m.foil, m.condition_id or "NM")) if m.prod else None,
        }
        if market is None or your is None:
            no_market.append(rec)
            continue
        rec["over"] = your - market
        rec["pct"] = (rec["over"] / market * 100) if market else 0.0
        rows.append(rec)
    rows.sort(key=lambda r: (-r["pct"], r["name"], r["set"], r["num"]))
    return {"rows": rows, "no_market": no_market, "unmapped": unmapped}


def is_flagged(row: dict, over_market_pct: float) -> bool:
    """Overpaid: ≥ ``over_market_pct`` over market AND > $OVER_MARKET_USD_MIN."""
    return row.get("pct", 0) >= over_market_pct and row.get("over", 0) > OVER_MARKET_USD_MIN


# ---------- the checks ----------

def _row_market(foil: bool, card: dict) -> float | None:
    val = card.get("prices_usd_foil") if foil else card.get("prices_usd")
    return float(val) if val not in (None, "") else None


def check_owned(mapped: list[CartLine], family_codes: set[str] | None) -> tuple[list[dict], int]:
    """Cart lines whose exact (printing, finish) you already own. Returns (rows,
    skipped) — lines outside ``family_codes`` are skipped when it's given."""
    candidates: list[CartLine] = []
    skipped = 0
    for m in mapped:
        if not m.scryfall_id:
            continue
        if family_codes is not None and (m.set_code or "").lower() not in family_codes:
            skipped += 1
            continue
        candidates.append(m)
    if not candidates:
        return [], skipped
    sids = list({m.scryfall_id for m in candidates})
    with db.connect() as conn:
        owned = {
            (r["scryfall_id"], r["finish"]): r["quantity"]
            for r in conn.execute(f"SELECT scryfall_id, finish, quantity FROM inventory WHERE scryfall_id IN ({','.join('?' * len(sids))})", sids)
        }
    rows = []
    for m in candidates:
        fin = "foil" if m.foil else "nonfoil"
        qty = owned.get((m.scryfall_id, fin), 0)
        if qty > 0:
            rows.append({"scryfall_id": m.scryfall_id, "name": m.name or "?", "set": m.set_code or "",
                         "num": m.number or "", "fin": fin, "owned_qty": qty, "your": (m.price_cents or 0) / 100.0})
    rows.sort(key=lambda r: (r["set"], cn_sort_key(r["num"]), r["fin"]))
    return rows, skipped


def check_missing(anchor: str, mapped: list[CartLine], treatment_class: str = "preferred") -> list[dict]:
    """Family gaps not in the cart. Printing-level (finish ignored): a foil in
    the cart fills that printing's gap, matching ``missing_printings``."""
    in_cart = {m.scryfall_id for m in mapped if m.scryfall_id}
    rows = []
    for r in missing_mod.missing_printings(anchor, treatment_class):
        if r.scryfall_id in in_cart:
            continue
        rows.append({"scryfall_id": r.scryfall_id, "name": r.card.get("name") or "?",
                     "set": r.card.get("set") or "", "num": r.card.get("collector_number") or "",
                     "fin": r.finish, "market": _row_market(r.finish == "foil", r.card)})
    rows.sort(key=lambda r: (r["set"], cn_sort_key(r["num"]), r["fin"]))
    return rows


def check_overpay(mapped: list[CartLine], family_codes: set[str] | None,
                  prices_fn: Callable[[list[str]], dict] = live_prices) -> tuple[dict, int]:
    """Overpay buckets over (optionally family-scoped) lines; (buckets, skipped)."""
    skipped = 0
    if family_codes is not None:
        scoped = []
        for m in mapped:
            if m.set_code and m.set_code.lower() not in family_codes:
                skipped += 1
                continue
            scoped.append(m)
        mapped = scoped
    return overpay_rows(mapped, prices_fn), skipped


def check_dupes(mapped: list[CartLine]) -> list[dict]:
    """Printings bought more than once: ×N of one finish (hard), or both foil and
    nonfoil of the same art (soft — usually you want only the cheaper)."""
    groups: dict[str, dict] = {}
    for m in mapped:
        if not m.scryfall_id:
            continue
        g = groups.setdefault(m.scryfall_id, {
            "scryfall_id": m.scryfall_id, "name": m.name or "?", "set": m.set_code or "", "num": m.number or "",
            "nf_qty": 0, "fo_qty": 0, "nf_price": None, "fo_price": None,
        })
        price = m.price_cents / 100 if m.price_cents is not None else None
        k = "fo" if m.foil else "nf"
        g[f"{k}_qty"] += m.quantity or 1
        if price is not None and (g[f"{k}_price"] is None or price < g[f"{k}_price"]):
            g[f"{k}_price"] = price
    rows = []
    for g in groups.values():
        hard = g["nf_qty"] >= 2 or g["fo_qty"] >= 2
        soft = g["nf_qty"] >= 1 and g["fo_qty"] >= 1
        if not (hard or soft):
            continue
        notes = []
        if g["nf_qty"] >= 2:
            notes.append(f"×{g['nf_qty']} nonfoil")
        if g["fo_qty"] >= 2:
            notes.append(f"×{g['fo_qty']} foil")
        if soft:
            notes.append("foil+nonfoil")
        prices = [p for p in (g["nf_price"], g["fo_price"]) if p is not None]
        rows.append({**g, "cheaper": min(prices) if (soft and prices) else None, "note": ", ".join(notes)})
    rows.sort(key=lambda r: (r["set"], cn_sort_key(r["num"])))
    return rows


def _family_root(resolved) -> str:
    """The root code of a resolved family (``resolve(x).code`` just echoes x)."""
    codes = {s["code"].lower() for s in resolved.related}
    for s in resolved.related:
        parent = (s.get("parent_set_code") or "").lower()
        if not parent or parent not in codes:
            return s["code"].lower()
    return resolved.code.lower()


def infer_set_anchors(mapped: list[CartLine]) -> list[str]:
    """Distinct family roots of the cart's identified printings."""
    roots: set[str] = set()
    for c in {m.set_code.lower() for m in mapped if m.set_code and m.scryfall_id}:
        try:
            roots.add(_family_root(sets_mod.resolve(c)))
        except LookupError:
            pass
    return sorted(roots)


def family_codes(anchor: str) -> set[str]:
    return {c.lower() for c in sets_mod.resolve(anchor).all_codes}


def audit(cart: list[dict], *, anchor: str | None = None, over_market_pct: float = 10.0,
          remote: bool = True, prices_fn: Callable[[list[str]], dict] = local_prices) -> dict:
    """Every check in one pass, for the web: the family is ``anchor`` or, when
    the cart sits in exactly one family, imputed from it."""
    mapped = map_cart(cart, remote=remote)
    anchors = infer_set_anchors(mapped)
    family = anchor or (anchors[0] if len(anchors) == 1 else None)
    owned, _ = check_owned(mapped, None)
    over, _ = check_overpay(mapped, None, prices_fn)
    return {
        "lines": len(mapped),
        "copies": sum(m.quantity for m in mapped),
        "total": round(sum((m.price_cents or 0) * m.quantity for m in mapped) / 100, 2),
        "unidentified": [{"name": m.name, "set": m.set_code, "num": m.number} for m in mapped if not m.scryfall_id],
        "family": family,
        "families": anchors,
        "dupes": check_dupes(mapped),
        "owned": owned,
        "missing": check_missing(family, mapped) if family else [],
        "overpay": [r for r in over["rows"] if is_flagged(r, over_market_pct)],
        "no_market": over["no_market"],
    }

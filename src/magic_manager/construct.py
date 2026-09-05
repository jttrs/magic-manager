"""Value the cost to *construct* a decklist or sealed product from singles.

Three questions, one card list:

  1. **sealed** — what the sealed product costs to buy (only meaningful for a
     sealed-product input; a bare decklist is not a purchasable SKU).
  2. **scratch** — buy every card as a net-new single: ``Σ need·unit_usd``.
  3. **with-collection** — use my LOOSE (unpledged) copies first, buy net-new
     only for the shortfall: ``Σ max(0, need − loose)·unit_usd``.

This module is the composite behind the ``construct-value`` skill. It reuses the
existing primitives rather than re-implementing valuation:

  - **sealed market price** — :func:`sealed.build_product_tree` +
    :func:`sealed.aggregate` (``market_whole``); the full recursion, cycle guard
    and cross-set pack resolution already live there.
  - **sub-product resolution** — :func:`sealed._resolve_subproduct` (a
    Case → 12 Kits → 2 decks each resolves correctly).
  - **decks → cards** — :func:`mtgjson.deck` for MTGJSON precons,
    :func:`decks.deck_show` for a local slug, :func:`parsers.parse_text` +
    :func:`parsers.resolve` for a pasted block.
  - **pricing + card identity** — :func:`sets.card_price_map` (the single
    source of truth shared with ``_rollup_deck_prices``), after syncing the
    referenced sets via :func:`sets.unsynced_set_codes` / :func:`sets.sync`.
  - **loose inventory** — :func:`inventory.free_quantity`
    (``inventory.quantity − Σ deck_assignments.count``).

RANDOM booster packs (``contents.pack``) cannot be constructed from singles, so
they are EXCLUDED from the card table and recorded in ``packs_skipped`` with a
diagnostic — their booster EV is still available from the ``sealed-value`` skill.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from . import inventory, mtgjson, parsers, sealed, sets

_MAX_DEPTH = 6  # mirrors sealed._MAX_DEPTH — Case → Kit → deck is the deepest real nesting


# ---------- data ----------

@dataclass
class CardNeed:
    """One (printing, finish) requirement contributed by a source, priced."""
    scryfall_id: str
    finish: str                 # 'nonfoil' | 'foil'
    qty: int
    source: str                 # deck / product label the need came from
    name: str
    set_code: str
    collector_number: str
    unit_usd: float | None      # local Scryfall price at this finish; None = unpriced


@dataclass
class NetRow:
    """A (printing, finish) after netting the aggregated need vs loose inventory."""
    scryfall_id: str
    finish: str
    name: str
    set_code: str
    collector_number: str
    need_qty: int
    loose_qty: int
    buy_qty: int
    unit_usd: float | None

    @property
    def scratch_usd(self) -> float | None:
        return None if self.unit_usd is None else round(self.unit_usd * self.need_qty, 2)

    @property
    def buy_usd(self) -> float | None:
        return None if self.unit_usd is None else round(self.unit_usd * self.buy_qty, 2)


@dataclass
class Expansion:
    """The result of expanding a source into priced card needs."""
    needs: list[CardNeed] = field(default_factory=list)
    packs_skipped: list[str] = field(default_factory=list)
    sealed_market: float | None = None
    label: str = ""
    diagnostics: list[str] = field(default_factory=list)


# ---------- raw need collection (pre-pricing) ----------

# A raw need is a dict: {scryfall_id, finish, count, source,
#                        fb_name, fb_set, fb_cn}  (fb_* = fallback identity).

def _norm_finish(finish: str | None, *, is_foil: bool = False) -> str:
    """Collapse to the two physical finishes. A local recipe's ``'either'`` and
    any unknown value map to ``'nonfoil'`` — the conservative, cheaper basis,
    matching ``decks.DeckCardRow.unit_price``."""
    if finish == "foil" or is_foil:
        return "foil"
    return "nonfoil"


def _needs_from_deck_json(deck_data: dict, source: str) -> list[dict]:
    """Flatten an MTGJSON deck file (commander/main/side) into raw needs."""
    out: list[dict] = []
    for board in ("commander", "mainBoard", "sideBoard"):
        for e in deck_data.get(board) or []:
            sid = (e.get("identifiers") or {}).get("scryfallId")
            if not sid:
                continue
            out.append({
                "scryfall_id": sid,
                "finish": _norm_finish(None, is_foil=bool(e.get("isFoil"))),
                "count": int(e.get("count", 1) or 1),
                "source": source,
                "fb_name": e.get("name"),
                "fb_set": (e.get("setCode") or "").lower(),
                "fb_cn": e.get("number"),
            })
    return out


def _needs_from_card_refs(card_refs: list[dict], source: str) -> list[dict]:
    """Flatten explicit ``contents.card`` refs (promos/singles) into raw needs."""
    out: list[dict] = []
    for ref in card_refs:
        sid = (ref.get("identifiers") or {}).get("scryfallId")
        if not sid:
            continue
        out.append({
            "scryfall_id": sid,
            "finish": _norm_finish(None, is_foil=bool(ref.get("foil"))),
            "count": int(ref.get("count", 1) or 1),
            "source": source,
            "fb_name": ref.get("name"),
            "fb_set": (ref.get("set") or "").lower(),
            "fb_cn": ref.get("number"),
        })
    return out


def _walk_product_contents(
    set_code: str, product: dict, source_prefix: str,
    *, raw: list[dict], packs: list[str], diags: list[str],
    depth: int = 0, seen: set[str] | None = None,
) -> None:
    """Recurse a sealed product's contents, appending deterministic needs to
    ``raw`` and random-pack labels to ``packs``. Delegates sub-product resolution
    to :func:`sealed._resolve_subproduct` so cross-set nesting and name/uuid
    matching stay in one place."""
    seen = set() if seen is None else seen
    uuid = product.get("uuid")
    if uuid and uuid in seen:
        return
    if uuid:
        seen = seen | {uuid}
    if depth >= _MAX_DEPTH:
        diags.append(f"max recursion depth {_MAX_DEPTH} reached under {source_prefix}")
        return

    contents = product.get("contents") or {}

    # sealed sub-products (Case → Kits, Bundle → sub-boxes) — recurse.
    for ref in contents.get("sealed") or []:
        sub_product, sub_set = sealed._resolve_subproduct(ref, set_code)
        cnt = int(ref.get("count", 1) or 1)
        if sub_product is None:
            diags.append(f"unresolved sub-product {ref.get('name')!r} — skipped")
            continue
        # Multiplicity flattens into per-card counts: expand cnt copies.
        for _ in range(cnt):
            _walk_product_contents(
                sub_set, sub_product, source_prefix,
                raw=raw, packs=packs, diags=diags, depth=depth + 1, seen=seen,
            )

    # random boosters — cannot be built from singles; record + skip.
    for pref in contents.get("pack") or []:
        pset = (pref.get("set") or set_code).upper()
        packs.append(f"{pset} {pref.get('code')} booster")

    # precon decks — resolve fileName then flatten card-by-card.
    for dref in contents.get("deck") or []:
        dset = dref.get("set") or set_code
        name = (dref.get("name") or "").lower()
        fname = None
        for entry in mtgjson.deck_list(set_code=dset):
            if (entry.get("name") or "").lower() == name:
                fname = entry["fileName"]
                break
        if fname is None:
            diags.append(f"deck {dref.get('name')!r} unresolved — skipped")
            continue
        raw.extend(_needs_from_deck_json(mtgjson.deck(fname), dref.get("name") or fname))

    # explicit singles / promos.
    raw.extend(_needs_from_card_refs(contents.get("card") or [], f"{product.get('name')} inserts"))

    # variable contents — a physical product yields one random config; not
    # itemizable deterministically. Note it rather than guess.
    if contents.get("variable"):
        diags.append(f"{product.get('name')} has variable contents — not itemized in the card table")


# ---------- pricing ----------

def _price_raw_needs(raw: list[dict]) -> list[CardNeed]:
    """Sync referenced sets, then resolve every raw need to a priced
    :class:`CardNeed` via the shared :func:`sets.card_price_map`. Card identity
    (name/set/cn) prefers the local ``cards`` row; falls back to the source's own
    fields when a printing isn't in the local table (then ``unit_usd`` is None)."""
    if not raw:
        return []
    # Sync sets referenced by the needs so local prices resolve.
    codes = {r["fb_set"] for r in raw if r.get("fb_set")}
    unsynced = sets.unsynced_set_codes(codes)
    if unsynced:
        try:
            sets.sync(unsynced)
        except Exception as e:  # noqa: BLE001 — a sync failure just under-reports
            import sys
            print(f"  ! sync failed: {e} (prices may under-report)", file=sys.stderr)

    price_map = sets.card_price_map(r["scryfall_id"] for r in raw)
    needs: list[CardNeed] = []
    for r in raw:
        sid, finish = r["scryfall_id"], r["finish"]
        meta = price_map.get(sid)
        if meta:
            name = meta["name"]
            set_code = meta["set_code"]
            cn = meta["collector_number"]
            price = meta["prices_usd_foil"] if finish == "foil" else meta["prices_usd"]
            unit = float(price) if price is not None else None
        else:
            name = r.get("fb_name") or "(unknown)"
            set_code = (r.get("fb_set") or "").upper()
            cn = r.get("fb_cn") or "?"
            unit = None
        needs.append(CardNeed(
            scryfall_id=sid, finish=finish, qty=r["count"], source=r["source"],
            name=name, set_code=set_code, collector_number=cn, unit_usd=unit,
        ))
    return needs


# ---------- source expansion (public) ----------

def expand_sealed(set_code: str, product_substr: str | None,
                  *, market: str = "null") -> Expansion:
    """Expand a sealed product into priced card needs + its sealed market price.

    Random boosters are recorded in ``packs_skipped``; deterministic contents
    (decks, explicit cards) feed ``needs``. ``sealed_market`` is the whole
    product's external price from the chosen provider (``None`` if unpriced/manual).
    """
    product = sealed.identify_product(set_code, product_substr)  # raises LookupError
    exp = Expansion(label=product.get("name") or set_code.upper())

    # Deterministic card needs (delegates sub-product/deck resolution).
    raw: list[dict] = []
    _walk_product_contents(
        set_code, product, exp.label,
        raw=raw, packs=exp.packs_skipped, diags=exp.diagnostics,
    )
    exp.needs = _price_raw_needs(raw)

    # Sealed market price — reuse the sealed valuation engine's whole-product price.
    provider = sealed.make_market_provider(market)
    tree = sealed.build_product_tree(set_code, product, market_provider=provider)
    exp.sealed_market = sealed.aggregate(tree).market_whole
    if exp.packs_skipped:
        exp.diagnostics.append(
            f"{len(exp.packs_skipped)} random booster(s) excluded from the buildable "
            f"card table (cannot construct a random pack from singles): "
            + ", ".join(exp.packs_skipped)
        )
    return exp


def expand_deck_file(file_name: str) -> Expansion:
    """Expand an MTGJSON precon deck fileName (e.g. ``AncientArsenal_ACR``)."""
    deck_data = mtgjson.deck(file_name)
    if not deck_data:
        raise LookupError(f"no MTGJSON deck file {file_name!r}")
    label = deck_data.get("name") or file_name
    raw = _needs_from_deck_json(deck_data, label)
    return Expansion(needs=_price_raw_needs(raw), label=label)


def expand_slug(slug: str) -> Expansion:
    """Expand a local deck by slug, using its stored ``deck_cards`` recipe."""
    from . import decks
    rows = decks.deck_show(slug)  # raises LookupError if unknown
    if not rows:
        raise LookupError(f"deck {slug!r} has no cards")
    raw = [{
        "scryfall_id": r.scryfall_id,
        "finish": _norm_finish(r.finish),
        "count": r.count,
        "source": slug,
        "fb_name": r.name,
        "fb_set": (r.set_code or "").lower(),
        "fb_cn": r.collector_number,
    } for r in rows]
    return Expansion(needs=_price_raw_needs(raw), label=slug)


def expand_decklist_text(text: str, *, label: str = "decklist") -> Expansion:
    """Expand a pasted Moxfield-style block (``1 Sol Ring (LTR) 123``).

    Reuses :func:`parsers.parse_text` + :func:`parsers.resolve` to turn names
    into scryfall_ids, then prices via the shared local price map."""
    parsed = parsers.resolve(parsers.parse_text(text))
    exp = Expansion(label=label)
    for w in parsed.warnings:
        exp.diagnostics.append(w)
    raw: list[dict] = []
    for e in parsed.entries:
        card = e.card
        if not card or not card.get("id"):
            exp.diagnostics.append(f"unresolved: {e.raw.strip()}")
            continue
        raw.append({
            "scryfall_id": card["id"],
            "finish": _norm_finish(None, is_foil=bool(e.foil)),
            "count": e.qty,
            "source": label,
            "fb_name": card.get("name"),
            "fb_set": (card.get("set") or "").lower(),
            "fb_cn": card.get("collector_number"),
        })
    exp.needs = _price_raw_needs(raw)
    return exp


# ---------- netting + summary (public) ----------

def net_against_loose(needs: list[CardNeed]) -> list[NetRow]:
    """Aggregate needs by ``(scryfall_id, finish)`` FIRST, then subtract loose
    (unpledged) inventory ONCE per key.

    Aggregating before netting is the fix for the cross-source double-spend bug:
    if two decks each need a card, summing the need and subtracting the loose
    count once is correct, whereas netting each deck independently would let the
    same loose copies cancel both decks' needs. ``buy_qty = max(0, need − loose)``.
    Rows sort by unit value desc, then name.
    """
    agg: dict[tuple[str, str], dict] = {}
    for n in needs:
        key = (n.scryfall_id, n.finish)
        row = agg.get(key)
        if row is None:
            agg[key] = {
                "name": n.name, "set_code": n.set_code,
                "collector_number": n.collector_number,
                "need": n.qty, "unit_usd": n.unit_usd,
            }
        else:
            row["need"] += n.qty

    out: list[NetRow] = []
    with inventory.db.connect() as conn:
        for (sid, finish), row in agg.items():
            loose = inventory.free_quantity(sid, finish, conn=conn)
            need = row["need"]
            out.append(NetRow(
                scryfall_id=sid, finish=finish, name=row["name"],
                set_code=row["set_code"], collector_number=row["collector_number"],
                need_qty=need, loose_qty=loose, buy_qty=max(0, need - loose),
                unit_usd=row["unit_usd"],
            ))
    out.sort(key=lambda r: (-(r.unit_usd if r.unit_usd is not None else -1), r.name))
    return out


def summarize(rows: list[NetRow], sealed_market: float | None) -> dict:
    """Fold netted rows into the three headline totals + coverage.

    ``scratch`` = Σ need·unit (buy everything new); ``with_collection`` =
    Σ buy·unit (use loose copies first). ``coverage`` is the priced fraction of
    total need (an unpriced printing drags both scratch and with_collection down)."""
    scratch = 0.0
    with_collection = 0.0
    total_need = 0
    priced_need = 0
    n_unpriced = 0
    for r in rows:
        total_need += r.need_qty
        if r.unit_usd is None:
            n_unpriced += r.need_qty
            continue
        priced_need += r.need_qty
        scratch += r.unit_usd * r.need_qty
        with_collection += r.unit_usd * r.buy_qty
    return {
        "sealed": sealed_market,
        "scratch": round(scratch, 2) if scratch else (0.0 if rows else None),
        "with_collection": round(with_collection, 2) if with_collection else (0.0 if rows else None),
        "coverage": (priced_need / total_need) if total_need else 1.0,
        "n_unpriced": n_unpriced,
        "total_need": total_need,
    }

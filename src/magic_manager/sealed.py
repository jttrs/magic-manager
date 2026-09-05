"""Identify a sealed MTG product and value its card contents, recursively.

This is the composite engine behind the ``sealed-value`` skill. It walks a
MTGJSON ``sealedProduct`` and produces a tree of :class:`ProductNode`, each
carrying two INDEPENDENT valuations:

  - **intrinsic** — the value of the cards inside, computed deterministically:
      * ``pack``  → expected value of a random booster (``ev.booster_ev``),
        keyed by the pack's ``contents.pack[].code`` (draft/set/play/collector…).
      * ``deck``  → the precon deck's summed singles (``sets._rollup_deck_prices``).
      * ``cards`` → explicit singles/promos summed (``singles_value``).
      * ``variable`` → weighted-average over the alternative configs (flagged as
        an approximation — the physical product yields exactly one config).
      * ``sealed`` → a CONTAINER: its intrinsic is Σ child.intrinsic·count.
  - **market** — an external per-unit price from a pluggable
    :class:`MarketProvider` (TCGplayer/eBay/…); ``None`` when no provider is
    wired, in which case the caller surfaces the ``purchaseUrls.tcgplayer`` link
    and marks the cell manual.

The recursion is the point: a Booster Box's ``contents.sealed`` lists 36 Booster
Packs (``count: 36``), each of which is itself a sealed product whose
``contents.pack`` selects a booster type. A Deck Builder's Toolkit can even nest
packs from OTHER sets (Theros/Born of the Gods), so sub-products are resolved
against the REFERENCED set's file, not the parent's. Aggregation reports both
the container's own market price (value the WHOLE) and the sum of its
components' market prices (value the PARTS) — the user's "recursively value the
whole and the components" requirement.

``contents.other`` (dice, playmats, guides, storage boxes) is intentionally
ignored — we value cards and pack contents only.

Reuse: ``mtgjson.sealed_products`` / ``set_file`` / ``deck`` /
``sealed_product_deck_refs`` for data; ``sets._rollup_deck_prices`` (a private
function called directly — documented dependency) for deck valuation;
``ev.booster_ev`` for pack EV.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from . import ev, mtgjson

_MAX_DEPTH = 6  # sealed→pack is the deepest real nesting; this is a runaway guard


# ---------- the tree node ----------

@dataclass
class ProductNode:
    name: str
    set_code: str
    kind: str                              # sealed|pack|deck|cards|variable
    category: str | None = None
    subtype: str | None = None
    count: int = 1                         # multiplicity within the parent
    tcgplayer_product_id: int | None = None
    tcgplayer_group_id: int | None = None
    purchase_url: str | None = None
    market_usd: float | None = None        # per-unit external price
    intrinsic_usd: float | None = None     # per-unit intrinsic value
    intrinsic_kind: str = ""               # ev|deck|singles|variable|sum-of-children
    ev_detail: "ev.BoosterEV | None" = None  # for pack nodes (auditable sheets)
    ebay_advisory_usd: float | None = None  # advisory only, NON-deterministic
    children: list["ProductNode"] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)


@dataclass
class Totals:
    market_whole: float | None       # the node's OWN external price (value the whole)
    market_sum_of_parts: float | None  # Σ child.market·count (value the parts)
    intrinsic: float | None          # Σ child.intrinsic·count (or the leaf's own)
    coverage: float                  # min pack-EV coverage across the tree (worst case)
    diagnostics: list[str]


# ---------- market provider seam ----------

@runtime_checkable
class MarketProvider(Protocol):
    name: str
    def price(self, node_meta: dict) -> float | None: ...


class NullMarketProvider:
    """The offline default: never returns a market price, forcing the report to
    show ``(manual)`` and surface the TCGplayer link. Fully deterministic."""
    name = "null"
    def price(self, node_meta: dict) -> float | None:  # noqa: D401
        return None


class ChainMarketProvider:
    """Try providers in order; the first non-``None`` price wins. Records which
    provider answered in ``last_source`` (per call) for the compare/report."""
    def __init__(self, providers: list[MarketProvider]):
        self.providers = providers
        self.name = "chain(" + ",".join(p.name for p in providers) + ")"
        self.last_source: str | None = None

    def price(self, node_meta: dict) -> float | None:
        for p in self.providers:
            v = p.price(node_meta)
            if v is not None:
                self.last_source = p.name
                return v
        self.last_source = None
        return None


class CompareMarketProvider:
    """Queries EVERY sub-provider per node and records each price, so the report
    can show them side-by-side. ``price()`` returns the first non-None (so the
    tree's primary market column is still populated); ``seen[key]`` holds the
    per-provider breakdown for the compare table."""

    name = "compare"

    def __init__(self, providers: list[MarketProvider]):
        self.providers = providers
        # key -> {provider_name: price|None}; key is (tcgplayer_product_id or name)
        self.seen: dict = {}

    def price(self, node_meta: dict) -> float | None:
        key = node_meta.get("tcgplayer_product_id") or node_meta.get("name")
        row = {p.name: p.price(node_meta) for p in self.providers}
        if key is not None:
            self.seen[key] = {"name": node_meta.get("name"), **row}
        first = next((v for v in row.values() if v is not None), None)
        return first


def _build_providers(names: list[str]) -> list[MarketProvider]:
    """Instantiate the named providers, skipping any that are unconfigured.

    Providers are opt-in and imported lazily so the default offline path needs
    no external clients. An unconfigured provider (missing key/credentials)
    degrades to a stderr note and is dropped, not raised."""
    import sys

    providers: list[MarketProvider] = []
    for n in names:
        try:
            if n == "tcgcsv":
                from . import tcgcsv
                providers.append(tcgcsv.TcgcsvMarketProvider())
            elif n == "tcgapi":
                from . import tcgapi
                providers.append(tcgapi.TcgapiMarketProvider())
        except Exception as e:  # noqa: BLE001 — unconfigured provider degrades to manual
            print(f"  ! market provider {n!r} unavailable: {e}", file=sys.stderr)
    return providers


def make_market_provider(mode: str) -> MarketProvider:
    """Resolve a ``--market`` choice (``null|tcgcsv|tcgapi|chain|compare``) to a
    :class:`MarketProvider`. Shared by the ``sealed-value`` and ``construct-value``
    CLIs so the provider-chain assembly lives in exactly one place."""
    if mode == "null":
        return NullMarketProvider()
    if mode == "compare":
        providers = _build_providers(["tcgcsv", "tcgapi"])
        return CompareMarketProvider(providers) if providers else NullMarketProvider()
    names = ["tcgcsv", "tcgapi"] if mode == "chain" else [mode]
    providers = _build_providers(names)
    if not providers:
        return NullMarketProvider()
    if len(providers) == 1:
        return providers[0]
    return ChainMarketProvider(providers)


# ---------- product identification ----------

def identify_product(set_code: str, product_name_substr: str | None) -> dict:
    """Resolve one ``sealedProduct`` dict in ``set_code``.

    With ``product_name_substr=None`` and exactly one product, returns it; else
    raises ``LookupError`` listing the available names. With a substring: exact
    (case-insensitive) match wins, else a unique substring match; ambiguous or
    absent raises ``LookupError`` with the candidate list."""
    products = mtgjson.sealed_products(set_code)
    if not products:
        raise LookupError(f"no sealedProduct data for set {set_code.upper()!r}")
    if product_name_substr is None:
        if len(products) == 1:
            return products[0]
        names = ", ".join(sorted(p.get("name", "?") for p in products))
        raise LookupError(
            f"{len(products)} products in {set_code.upper()}; name a substring. "
            f"Available: {names}"
        )
    want = product_name_substr.strip().lower()
    exact = [p for p in products if (p.get("name") or "").lower() == want]
    if exact:
        return exact[0]
    subs = [p for p in products if want in (p.get("name") or "").lower()]
    if len(subs) == 1:
        return subs[0]
    names = ", ".join(sorted(p.get("name", "?") for p in products))
    if not subs:
        raise LookupError(
            f"no product matching {product_name_substr!r} in {set_code.upper()}; "
            f"available: {names}"
        )
    raise LookupError(
        f"{len(subs)} products match {product_name_substr!r} in "
        f"{set_code.upper()}; be more specific: "
        + ", ".join(sorted(p.get("name", "?") for p in subs))
    )


def _resolve_subproduct(ref: dict, parent_set: str) -> tuple[dict | None, str]:
    """Resolve a ``contents.sealed`` ref ``{name,count,set,uuid}`` to its own
    sealedProduct dict, in its referenced set (which may differ from the parent
    — e.g. a Toolkit nesting Theros packs). Match by uuid first, then name.
    Returns ``(product_or_None, resolved_set_code)``."""
    ref_set = (ref.get("set") or parent_set)
    uuid = ref.get("uuid")
    name = (ref.get("name") or "").lower()
    products = mtgjson.sealed_products(ref_set)
    if uuid:
        for p in products:
            if p.get("uuid") == uuid:
                return p, ref_set
    for p in products:
        if (p.get("name") or "").lower() == name:
            return p, ref_set
    return None, ref_set


# ---------- leaf valuations ----------

def singles_value(card_refs: list[dict], set_code: str) -> tuple[float | None, int, int]:
    """Value explicit ``contents.card`` entries. Each ref carries
    ``identifiers.scryfallId`` (or a uuid we map via the set file's cards).
    Foil-aware on ``ref['foil']``. Returns ``(usd_total, n_priced, n_unpriced)``;
    ``usd_total`` is ``None`` when nothing priced."""
    if not card_refs:
        return None, 0, 0
    set_data = mtgjson.set_file(set_code)
    uuid_price, _ = ev.build_uuid_price_map(set_data)
    # also index by scryfall_id for refs that carry it directly
    by_sid = {m["scryfall_id"]: m for m in uuid_price.values() if m.get("scryfall_id")}
    total = 0.0
    n_priced = n_unpriced = 0
    for ref in card_refs:
        foil = bool(ref.get("foil"))
        count = int(ref.get("count", 1) or 1)
        meta = None
        uuid = ref.get("uuid")
        sid = (ref.get("identifiers") or {}).get("scryfallId")
        if uuid and uuid in uuid_price:
            meta = uuid_price[uuid]
        elif sid and sid in by_sid:
            meta = by_sid[sid]
        price = None
        if meta:
            price = meta.get("usd_foil") if foil else meta.get("usd")
        if price is None:
            n_unpriced += count
            continue
        total += float(price) * count
        n_priced += count
    return (round(total, 2) if total else None), n_priced, n_unpriced


def value_variable(variable_groups: list[dict], set_code: str) -> tuple[float | None, list[str]]:
    """Value ``contents.variable`` as a WEIGHTED AVERAGE over its configs.

    Each group is ``{configs: [{deck|card|sealed: [...],
    variable_config: [{chance, weight}]}]}``. The physical product yields exactly
    ONE config at random; we report the weighted mean as the expected value and
    flag it as an approximation. Only ``deck`` and ``card`` configs are valued
    here (nested ``sealed`` inside a variable config is rare and left as a
    diagnostic). Returns ``(usd_or_None, diagnostics)``."""
    diagnostics: list[str] = []
    grand = 0.0
    any_priced = False
    for group in variable_groups:
        configs = group.get("configs") or []
        weighted_sum = 0.0
        total_weight = 0
        for cfg in configs:
            w = sum(int(vc.get("weight", 1)) for vc in (cfg.get("variable_config") or [{}]))
            total_weight += w
            cfg_val = 0.0
            deck_refs = cfg.get("deck") or []
            for dref in deck_refs:
                val = _deck_ref_value(dref, set_code)
                if val is not None:
                    cfg_val += val
                    any_priced = True
            card_refs = cfg.get("card") or []
            if card_refs:
                cv, _, _ = singles_value(card_refs, set_code)
                if cv:
                    cfg_val += cv
                    any_priced = True
            if cfg.get("sealed"):
                diagnostics.append("variable config nests sealed packs — not valued")
            weighted_sum += w * cfg_val
        if total_weight:
            grand += weighted_sum / total_weight
    if any_priced:
        diagnostics.append("variable contents valued as a weighted average (approximation)")
        return round(grand, 2), diagnostics
    return None, diagnostics


def _deck_ref_value(deck_ref: dict, parent_set: str) -> float | None:
    """Value one ``{name, set}`` deck ref via its DeckList fileName and
    ``sets._rollup_deck_prices``. Returns ``None`` if unresolved/unpriced."""
    from . import sets as sets_mod  # local import: sets imports heavy deps
    ref_set = deck_ref.get("set") or parent_set
    name = (deck_ref.get("name") or "").lower()
    for entry in mtgjson.deck_list(set_code=ref_set):
        if (entry.get("name") or "").lower() == name:
            deck_data = mtgjson.deck(entry["fileName"])
            _, usd_total, _, _, _ = sets_mod._rollup_deck_prices(deck_data)
            return usd_total
    return None


# ---------- the recursive walk ----------

def _market_meta(product: dict, set_data: dict) -> dict:
    """Extract the identifiers a MarketProvider needs from a product dict.

    ``set_name`` is the MTGJSON set display name (e.g. "Magic 2015") — tcgapi is
    search-keyed and names products ``<set> - <product>``, so its provider
    searches by set name then matches back by ``tcgplayer_product_id``."""
    ids = product.get("identifiers") or {}
    tpid = ids.get("tcgplayerProductId")
    return {
        "name": product.get("name"),
        "set_name": set_data.get("name"),
        "tcgplayer_product_id": int(tpid) if tpid else None,
        "tcgplayer_group_id": set_data.get("tcgplayerGroupId"),
        "uuid": product.get("uuid"),
    }


def build_product_tree(
    set_code: str,
    product: dict,
    set_data: dict | None = None,
    *,
    market_provider: MarketProvider | None = None,
    ebay_provider: MarketProvider | None = None,
    _depth: int = 0,
    _seen: set[str] | None = None,
    _count: int = 1,
) -> ProductNode:
    """Build the recursive value tree for one sealed ``product``.

    ``set_data`` is the parent set file (fetched if omitted). ``market_provider``
    attaches per-node market prices (defaults to :class:`NullMarketProvider`).
    ``ebay_provider`` (optional) populates the advisory-only ``ebay_advisory_usd``.
    ``_depth``/``_seen``/``_count`` are recursion bookkeeping."""
    if set_data is None:
        set_data = mtgjson.set_file(set_code)
    if market_provider is None:
        market_provider = NullMarketProvider()
    if _seen is None:
        _seen = set()

    purchase = (product.get("purchaseUrls") or {}).get("tcgplayer")
    meta = _market_meta(product, set_data)
    node = ProductNode(
        name=product.get("name") or "(unnamed)",
        set_code=set_code,
        kind="sealed",
        category=product.get("category"),
        subtype=product.get("subtype"),
        count=_count,
        tcgplayer_product_id=meta["tcgplayer_product_id"],
        tcgplayer_group_id=meta["tcgplayer_group_id"],
        purchase_url=purchase,
        market_usd=market_provider.price(meta),
    )
    if ebay_provider is not None:
        node.ebay_advisory_usd = ebay_provider.price(meta)

    uuid = product.get("uuid")
    if uuid and uuid in _seen:
        node.diagnostics.append("cycle detected — sub-product already visited")
        return node
    if uuid:
        _seen = _seen | {uuid}
    if _depth >= _MAX_DEPTH:
        node.diagnostics.append(f"max recursion depth {_MAX_DEPTH} reached")
        return node

    contents = product.get("contents") or {}

    # --- contents.sealed: recurse into sub-products (Box → 36 Packs, etc.) ---
    for ref in contents.get("sealed") or []:
        sub_product, sub_set = _resolve_subproduct(ref, set_code)
        cnt = int(ref.get("count", 1) or 1)
        if sub_product is None:
            node.diagnostics.append(
                f"unresolved sub-product {ref.get('name')!r} "
                f"(set {sub_set.upper()}) — skipped")
            continue
        sub_data = set_data if sub_set.lower() == set_code.lower() else None
        child = build_product_tree(
            sub_set, sub_product, sub_data,
            market_provider=market_provider, ebay_provider=ebay_provider,
            _depth=_depth + 1, _seen=_seen, _count=cnt,
        )
        node.children.append(child)

    # --- contents.pack: a random booster → EV, keyed by pack.code ---
    for pref in contents.get("pack") or []:
        code = pref.get("code")
        pack_set = pref.get("set") or set_code
        pack_data = set_data if pack_set.lower() == set_code.lower() else mtgjson.set_file(pack_set)
        child = ProductNode(
            name=f"{pack_set.upper()} {code} booster",
            set_code=pack_set, kind="pack", count=1,
        )
        try:
            b = ev.booster_ev(pack_data, code)
            child.intrinsic_usd = round(b.ev_usd, 2)
            child.intrinsic_kind = "ev"
            child.ev_detail = b
            if b.coverage < 0.999:
                child.diagnostics.append(
                    f"EV coverage {b.coverage:.1%} ({b.n_unpriced} unpriced cards)")
        except KeyError as e:
            child.diagnostics.append(str(e))
        node.children.append(child)

    # --- contents.deck: precon decks → summed singles ---
    for dref in contents.get("deck") or []:
        dset = dref.get("set") or set_code
        child = ProductNode(name=dref.get("name") or "(deck)",
                            set_code=dset, kind="deck", count=1)
        val = _deck_ref_value(dref, set_code)
        if val is None:
            child.diagnostics.append("deck unresolved or unpriced")
        else:
            child.intrinsic_usd = val
            child.intrinsic_kind = "deck"
        node.children.append(child)

    # --- contents.card: explicit singles/promos ---
    card_refs = contents.get("card") or []
    if card_refs:
        val, n_priced, n_unpriced = singles_value(card_refs, set_code)
        child = ProductNode(name=f"{len(card_refs)} card(s)", set_code=set_code,
                            kind="cards", count=1, intrinsic_usd=val,
                            intrinsic_kind="singles")
        if n_unpriced:
            child.diagnostics.append(f"{n_unpriced} card(s) unpriced")
        node.children.append(child)

    # --- contents.variable: weighted-average alternatives ---
    var_groups = contents.get("variable") or []
    if var_groups:
        val, diags = value_variable(var_groups, set_code)
        child = ProductNode(name="variable contents", set_code=set_code,
                            kind="variable", count=1, intrinsic_usd=val,
                            intrinsic_kind="variable", diagnostics=diags)
        node.children.append(child)

    # A container's own intrinsic is the sum of its children (× their counts).
    if node.children:
        child_sum = 0.0
        any_val = False
        for c in node.children:
            iv = _node_intrinsic(c)
            if iv is not None:
                child_sum += iv * c.count
                any_val = True
        if any_val:
            node.intrinsic_usd = round(child_sum, 2)
            node.intrinsic_kind = "sum-of-children"
    return node


def _node_intrinsic(node: ProductNode) -> float | None:
    """A node's per-unit intrinsic value: its own if a leaf, else the recursive
    sum already stored on it (build sets it bottom-up)."""
    return node.intrinsic_usd


# ---------- aggregation ----------

def aggregate(node: ProductNode) -> Totals:
    """Fold a built tree into headline totals.

    ``market_whole`` is the node's OWN external price (value the whole product);
    ``market_sum_of_parts`` sums the immediate children's market prices × count
    (value the components) — both surfaced so the user sees box-vs-packs.
    ``intrinsic`` is the node's recursive intrinsic. ``coverage`` is the WORST
    (minimum) pack-EV coverage anywhere in the tree, so a single poorly-priced
    booster type is visible at the top."""
    parts = None
    if node.children:
        s = 0.0
        any_m = False
        for c in node.children:
            if c.market_usd is not None:
                s += c.market_usd * c.count
                any_m = True
        parts = round(s, 2) if any_m else None

    coverages: list[float] = []
    diags: list[str] = []

    def _walk(n: ProductNode, prefix: str = "") -> None:
        label = f"{prefix}{n.name}"
        if n.ev_detail is not None:
            coverages.append(n.ev_detail.coverage)
        for d in n.diagnostics:
            diags.append(f"{label}: {d}")
        for c in n.children:
            _walk(c, prefix=f"{label} → ")

    _walk(node)
    coverage = min(coverages) if coverages else 1.0
    return Totals(
        market_whole=node.market_usd,
        market_sum_of_parts=parts,
        intrinsic=node.intrinsic_usd,
        coverage=coverage,
        diagnostics=diags,
    )


def referenced_set_codes(node: ProductNode) -> set[str]:
    """Every set code whose cards need pricing to value this tree, lowercased.

    Walks the tree collecting each node's own ``set_code``, AND — for every
    ``pack`` node — the booster's ``sourceSetCodes`` (the sets its sheets pull
    from). A pack node's ``set_code`` is only the pack's own set; a booster can
    seed cards from OTHER sets (AFR collector → AFC, AFR set → PLST), and those
    live in the MTGJSON booster config, never as a node field — so a plain
    tree-walk can't surface them. Callers feed this to ``sets.unsynced_set_codes``
    → ``sets.sync`` so cross-set booster cards are local before EV is computed.
    This is the shared discovery path for the sealed-value + review-earmarks
    scripts (keeps the sourceSetCodes logic in one place)."""
    codes: set[str] = set()

    def _walk(n: ProductNode) -> None:
        if n.set_code:
            codes.add(n.set_code.lower())
        if n.kind == "pack" and n.ev_detail is not None:
            booster = ((mtgjson.set_file(n.set_code).get("booster") or {})
                       .get(n.ev_detail.booster_type) or {})
            for c in booster.get("sourceSetCodes") or []:
                if c:
                    codes.add(c.lower())
        for c in n.children:
            _walk(c)

    _walk(node)
    return codes

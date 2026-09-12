"""Unified 4-column valuation across the sealed-value tools.

Cross-engine glue that produces ONE :class:`sealed.ProductValuation` per product,
whether it's a sealed product (booster box / commander display / intro pack / …)
or a Secret Lair drop. The single/batch/recent-N renderers all consume this so
the four columns mean the same thing everywhere:

  1. listing        — the store's asking price (provenance; passed in)
  2. sealed_market  — the product's own wider-secondary-market price (providers)
  3. exact_singles  — Σ market of the product's EXACT card printings
  4. floor_singles  — Σ cheapest printing of each card anywhere (by oracle_id)

Kept in a dedicated module (not in the engine modules) so ``sealed`` / ``construct``
/ ``sld`` stay single-purpose and there's no import cycle — this module imports
all three; none of them import it.

Two capabilities this module adds on top of the engines:
- **Sealed-product FLOOR (col4):** the sealed/construct path has no cheapest-
  anywhere floor. We reuse the generic ``sld.card_floors`` over the product's
  exact-printing cards' oracle_ids (fetched from the local ``cards`` table, whose
  ``oracle_id`` column is indexed — not by bloating ``construct.CardNeed``).
- **SLD SEALED-MARKET (col2):** Secret Lair drops resolve to real MTGJSON
  ``sealedProduct`` entries (base + foil editions, with tcgplayerProductId/uuid),
  so they CAN be priced through the same market-provider seam — ``sld_sealed_market``.
"""

from __future__ import annotations

from . import construct, db, mtgjson, sealed, sets, sld


# ---------- shared floor helpers (sealed-product col4) ----------

def _oracle_ids_for(scryfall_ids: list[str]) -> dict[str, str]:
    """Map ``scryfall_id -> oracle_id`` from the local cards table (indexed).

    The floor lookup keys on oracle_id (all printings of a card), but
    ``construct.CardNeed`` only carries scryfall_id. Rather than bloat CardNeed,
    resolve oracle_ids here in one query over the needs' scryfall_ids."""
    ids = [s for s in dict.fromkeys(scryfall_ids) if s]
    if not ids:
        return {}
    with db.connect() as conn:
        placeholders = ",".join("?" for _ in ids)
        return {
            r["scryfall_id"]: r["oracle_id"]
            for r in conn.execute(
                f"SELECT scryfall_id, oracle_id FROM cards "
                f"WHERE scryfall_id IN ({placeholders})",
                ids,
            ).fetchall()
            if r["oracle_id"]
        }


def _floor_sum(needs, *, floors_cache: dict) -> tuple[float | None, int, int]:
    """Σ cheapest-anywhere floor over a list of ``construct.CardNeed``.

    For each need, use the finish-appropriate floor (``min_usd`` / ``min_usd_foil``)
    from the cheapest printing of that card anywhere, ×qty. Floors are fetched in
    ONE batched pass (``sld.card_floors_many`` — chunked OR-search, not one call
    per card) and memoized in ``floors_cache`` across the run. Returns
    ``(total_or_None, n_priced, n_unpriced)``; total is None when nothing priced."""
    oid_by_sid = _oracle_ids_for([n.scryfall_id for n in needs])
    # Batch-fetch any oracle_ids not already cached (one query per ~60 ids).
    missing = [o for o in dict.fromkeys(oid_by_sid.values()) if o not in floors_cache]
    if missing:
        floors_cache.update(sld.card_floors_many(missing))
    total = 0.0
    n_priced = n_unpriced = 0
    for n in needs:
        oid = oid_by_sid.get(n.scryfall_id)
        if oid is None:
            n_unpriced += n.qty
            continue
        nf_floor, foil_floor = floors_cache.get(oid, (None, None))
        floor = foil_floor if n.finish == "foil" else nf_floor
        if floor is None:
            n_unpriced += n.qty
            continue
        total += floor * n.qty
        n_priced += n.qty
    return (round(total, 2) if n_priced else None), n_priced, n_unpriced


# ---------- sealed-product producer ----------

def value_sealed_product(
    set_code: str, product_substr: str | None, *,
    listing: float | None = None, market: str = "chain",
    refresh_stale: bool = True, floors: bool = True,
    floors_cache: dict | None = None,
) -> sealed.ProductValuation:
    """The 4-column valuation of one sealed product.

    col2 = the product's own market price (``sealed.aggregate(...).market_whole``
    via the chosen provider); col3 = Σ exact-printing singles at local market
    (``construct.expand_sealed`` → ``net_against_loose``); col4 = Σ cheapest-
    anywhere floor (reusing ``sld.card_floors``). A pure random-booster product
    (no fixed singles) sets ``booster_only=True`` and reports the tree's EV as
    both col3/col4 (labeled), since there are no printings to sum.

    Raises ``LookupError`` if the product can't be identified."""
    if floors_cache is None:
        floors_cache = {}
    product = sealed.identify_product(set_code, product_substr)  # LookupError → caller

    # col2: build with a null provider to discover referenced sets, ensure prices,
    # then rebuild with the real provider (mirrors scripts/sealed_value.py).
    provider = sealed.make_market_provider(market)
    scout = sealed.build_product_tree(set_code, product)
    try:
        sets.ensure_priced(sealed.referenced_set_codes(scout),
                           refresh_stale=refresh_stale, log=None)
    except Exception:  # noqa: BLE001 — pricing degrades, never fatal
        pass
    tree = sealed.build_product_tree(set_code, product, market_provider=provider)
    totals = sealed.aggregate(tree)
    source = getattr(provider, "last_source", None) or getattr(provider, "name", None)

    # col3/col4: expand to exact-printing needs (local prices), sum + floor them.
    exp = construct.expand_sealed(set_code, product_substr, market="null",
                                  refresh_stale=False)
    rows = construct.net_against_loose(exp.needs)
    priced = [r for r in rows if r.unit_usd is not None]

    diagnostics = list(totals.diagnostics)
    booster_only = not exp.needs and bool(exp.packs_skipped)
    if booster_only:
        # No fixed singles to sum — the value is the random-booster EV (from the
        # tree's intrinsic). Report it as both col3/col4 with a labeling note.
        ev_val = totals.intrinsic
        return sealed.ProductValuation(
            label=tree.name, kind="sealed", listing=listing,
            sealed_market=totals.market_whole, sealed_market_source=source,
            exact_singles=ev_val, floor_singles=ev_val,
            coverage=totals.coverage, booster_only=True,
            diagnostics=diagnostics,
            note="random-booster product — cols 3/4 are the booster EV, not a fixed-singles sum",
        )

    exact = round(sum(r.unit_usd * r.need_qty for r in priced), 2) if priced else None
    floor_total = None
    if floors:
        floor_total, _fp, _fu = _floor_sum(exp.needs, floors_cache=floors_cache)
    if exp.packs_skipped:
        diagnostics.append(
            f"{len(exp.packs_skipped)} random booster(s) excluded from the "
            f"singles/floor sums (EV only): {', '.join(exp.packs_skipped)}")
    return sealed.ProductValuation(
        label=tree.name, kind="sealed", listing=listing,
        sealed_market=totals.market_whole, sealed_market_source=source,
        exact_singles=exact, floor_singles=floor_total,
        coverage=totals.coverage, diagnostics=diagnostics,
    )


# ---------- SLD col2: drop → sealedProduct market price ----------

def sld_sealed_market(drop_name: str, edition: str = "auto",
                      *, market: str = "chain") -> tuple[float | None, str | None]:
    """Price a Secret Lair drop's SEALED product on the wider market.

    Secret Lair drops DO have MTGJSON ``sealedProduct`` entries (base + foil
    editions, carrying tcgplayerProductId/uuid), so they price through the same
    provider seam as any sealed product. Matches ``sealed_products("sld")`` names
    to ``drop_name`` (stripping the ``"Secret Lair Drop "`` prefix + ``" Foil
    Edition"`` suffix), picks base vs foil per ``edition`` ("foil" → foil product,
    else base), and prices via ``sealed._market_meta`` + the provider chain.
    Returns ``(price_or_None, source_or_None)`` — None when no sealedProduct
    matches (older drops predate the entries) or nothing prices it."""
    try:
        products = mtgjson.sealed_products("sld")
        set_data = mtgjson.set_file("sld")
    except Exception:  # noqa: BLE001
        return None, None

    import re

    def _norm(s: str) -> str:
        # Punctuation-insensitive: the drop name ("Far Out, Man") and the sealed
        # product name ("Far Out Man") differ only in punctuation/spacing.
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    want = _norm(sld.strip_foil_edition(drop_name))

    def _canon(p: dict) -> str:
        n = p.get("name") or ""
        # MTGJSON SLD sealed names look like "Secret Lair Drop <Name>[ Foil]".
        n = n[len("Secret Lair Drop "):] if n.lower().startswith("secret lair drop ") else n
        return _norm(sld.strip_foil_edition(n))

    def _is_foil(p: dict) -> bool:
        return "foil" in (p.get("name") or "").lower()

    matches = [p for p in products if _canon(p) == want]
    if not matches:
        return None, None
    want_foil = edition == "foil"
    # Prefer the edition that matches; fall back to the other if only one exists.
    picked = next((p for p in matches if _is_foil(p) == want_foil), matches[0])

    provider = sealed.make_market_provider(market)
    meta = sealed._market_meta(picked, set_data)
    price = provider.price(meta)
    source = getattr(provider, "last_source", None) or getattr(provider, "name", None)
    return price, (source if price is not None else None)


# ---------- SLD producer ----------

def value_sld_drop(
    drop_or_substr, *, listing: float | None = None, market: str = "chain",
    edition: str = "auto", floors: bool = True,
    _card_by_id: dict | None = None, _floors_cache: dict | None = None,
) -> sealed.ProductValuation:
    """The 4-column valuation of one Secret Lair drop.

    ``drop_or_substr`` is either a resolved drop dict (from ``sld.recent_drops``)
    or a name substring (resolved via ``sld.identify_drop``). ``edition`` ("foil"
    / else) selects which finish cols 3/4 (and the col2 sealed product) reflect —
    a foil-edition tab uses the drop's foil own-printing/floor totals and prices
    the foil sealed product. Raises ``LookupError`` if the drop can't be resolved."""
    drop = drop_or_substr if isinstance(drop_or_substr, dict) \
        else sld.identify_drop(drop_or_substr)
    v = sld.value_drop(drop, floors=floors, _card_by_id=_card_by_id,
                       _floors_cache=_floors_cache)
    foil = edition == "foil"
    exact = v.foil_total if foil else v.nonfoil_total
    floor = v.foil_floor_total if foil else v.nf_floor_total
    sealed_mkt, source = sld_sealed_market(v.name, edition, market=market)
    diagnostics = []
    if sealed_mkt is None:
        diagnostics.append("no matching Secret Lair sealedProduct on the market "
                           "(older drop, or not stocked) — sealed-market blank")
    return sealed.ProductValuation(
        label=v.name, kind="sld", listing=listing,
        sealed_market=sealed_mkt, sealed_market_source=source,
        exact_singles=round(exact, 2) if exact else None,
        floor_singles=round(floor, 2) if floor else None,
        finish="foil" if foil else "nonfoil",
        diagnostics=diagnostics,
        note="live Scryfall singles; sealed-market via tcgcsv/manapool by product id",
    )

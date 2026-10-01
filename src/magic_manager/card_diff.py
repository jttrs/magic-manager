"""Per-family "diff vs collection" engine — the three missing-card pools.

Three pools, per family (``code`` = any member or anchor code, normalized to
the family parent via ``family_status.resolve_family``):

1. **printing** — ``missing.missing_printings``: every art/frame variant not
   owned (printing-level).
2. **functional** — ``missing.functional_missing``: mechanically-unique cards
   (by oracle_id) owned in ZERO printings.
3. **variant-chase** — ``missing.variant_chase_printings``: printing-missing
   rows whose oracle_id the user already owns elsewhere in the family (the
   borderless/alt-art/fancy-foil chase for a card you already have).

Pure logic over the DRY shared seams (``family_status`` for family resolution/
owned-summary/live-price, ``missing`` for the three pools) — no printing, no
file I/O. ``cli.query_card_diff_cmd`` is the only renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import family_status, missing as missing_mod, selectors as sel_mod


@dataclass
class CardDiffPool:
    name: str              # "printing" | "functional" | "variant-chase"
    count: int
    usd: float
    rows: list = field(default_factory=list)   # MaterializedRows (printing/variant-chase) OR FunctionalMissingCards (functional)


@dataclass
class FamilyDiff:
    code: str
    name: str
    owned_prints: int
    owned_qty: int
    owned_usd: float
    printing: CardDiffPool
    functional: CardDiffPool
    variant_chase: CardDiffPool


def _build_family_diff(
    parent_code: str,
    parent_name: str,
    family_code_set: set[str],
    missing_rows: list,
    prices: dict,
) -> FamilyDiff:
    """Assemble a FamilyDiff from already-materialized missing rows + a
    (scryfall_id -> prices dict) price map. Shared by `family_diff` (single
    anchor, fetches its own price map) and `collection_diff` (batches ONE
    price fetch over every family, per the overview's pattern)."""
    owned_rows = family_status._owned_rows_for_codes(family_code_set)
    owned_prints = len(owned_rows)
    owned_qty = sum(r.quantity for r in owned_rows)
    owned_usd = round(sum(
        family_status._unit(prices.get(r.scryfall_id, {}), r.finish) * r.quantity
        for r in owned_rows
    ), 2)

    printing_usd = round(sum(
        family_status._unit(prices.get(r.scryfall_id, {}), r.finish) for r in missing_rows
    ), 2)
    printing_pool = CardDiffPool(name="printing", count=len(missing_rows),
                                 usd=printing_usd, rows=missing_rows)

    functional = missing_mod.functional_missing(parent_code, precomputed_missing=missing_rows)
    functional_pool = CardDiffPool(name="functional", count=functional.n_cards,
                                   usd=functional.family_total_usd, rows=functional.cards)

    variant_rows = missing_mod.variant_chase_printings(parent_code, precomputed_missing=missing_rows)
    variant_usd = round(sum(
        family_status._unit(prices.get(r.scryfall_id, {}), r.finish) for r in variant_rows
    ), 2)
    variant_pool = CardDiffPool(name="variant-chase", count=len(variant_rows),
                                usd=variant_usd, rows=variant_rows)

    return FamilyDiff(
        code=parent_code, name=parent_name,
        owned_prints=owned_prints, owned_qty=owned_qty, owned_usd=owned_usd,
        printing=printing_pool, functional=functional_pool, variant_chase=variant_pool,
    )


def family_diff(code: str, *, price_map: dict | None = None) -> FamilyDiff | None:
    """None if the family is unconfigured (SelectorParseError/LookupError from
    missing) or the anchor is unresolvable."""
    try:
        parent_code, parent_name, related = family_status.resolve_family(code)
    except LookupError:
        return None
    family_code_set = family_status._family_code_set(parent_code, related)
    try:
        missing_rows = missing_mod.missing_printings(parent_code)
    except (sel_mod.SelectorParseError, LookupError):
        return None

    if price_map is None:
        owned_rows = family_status._owned_rows_for_codes(family_code_set)
        ids = {r.scryfall_id for r in owned_rows} | {r.scryfall_id for r in missing_rows}
        prices = family_status._live_prices(list(ids))
    else:
        prices = price_map

    return _build_family_diff(parent_code, parent_name, family_code_set, missing_rows, prices)


def collection_diff() -> list[FamilyDiff]:
    """One FamilyDiff per owned+characterized family, sorted by owned_usd desc.

    Mirrors `family_status.render_overview`'s batching: ONE bulk price fetch
    over every family's owned ids ∪ missing ids, and `missing_printings` rows
    are materialized once per family and threaded into both `functional_missing`
    and `variant_chase_printings` via their `precomputed_missing` params.
    """
    parents = family_status._owned_family_parents()
    if not parents:
        return []

    fam_codes_by_parent: dict[str, set[str]] = {}
    for pc in parents:
        try:
            _, _, related = family_status.resolve_family(pc)
        except LookupError:
            related = [{"code": pc}]
        fam_codes_by_parent[pc] = family_status._family_code_set(pc, related)

    missing_rows_by_parent: dict[str, list | None] = {}
    for pc in parents:
        if pc in family_status.NON_FAMILY_SETS:
            continue
        try:
            missing_rows_by_parent[pc] = missing_mod.missing_printings(pc)
        except (sel_mod.SelectorParseError, LookupError):
            missing_rows_by_parent[pc] = None  # unconfigured

    all_rows = family_status._owned_rows_for_codes(
        {c for codes in fam_codes_by_parent.values() for c in codes}
    )
    ids = {r.scryfall_id for r in all_rows}
    for mrows in missing_rows_by_parent.values():
        if mrows:
            ids.update(r.scryfall_id for r in mrows)
    price_map = family_status._live_prices(list(ids))

    diffs: list[FamilyDiff] = []
    for pc, pn in parents.items():
        if pc in family_status.NON_FAMILY_SETS:
            continue
        mrows = missing_rows_by_parent.get(pc)
        if mrows is None:
            continue  # unconfigured — no missing-set rules for this family
        diffs.append(_build_family_diff(pc, pn, fam_codes_by_parent[pc], mrows, price_map))

    diffs.sort(key=lambda f: f.owned_usd, reverse=True)
    return diffs

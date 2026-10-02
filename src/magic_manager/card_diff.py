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

from . import family_status, missing as missing_mod, selectors as sel_mod, sets as sets_mod


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
    owned_rows: list | None = None,
) -> FamilyDiff:
    """Assemble a FamilyDiff from already-materialized missing rows + a
    (scryfall_id -> prices dict) price map. Shared by `family_diff` (single
    anchor, fetches its own price map) and `collection_diff` (batches ONE
    price fetch over every family, per the overview's pattern).

    ``owned_rows`` lets a caller that already materialized owned rows for this
    family (e.g. `collection_diff`'s global `_owned_rows_for_codes` call, sliced
    per family) pass them in directly, avoiding a per-family re-fetch. ``None``
    falls back to fetching here (unchanged behavior for standalone callers)."""
    if owned_rows is None:
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

    # Owned-oracle set for this family (same scope `functional_missing`/
    # `variant_chase_printings` would compute internally from
    # `sets.resolve(parent_code).all_codes` — NOT `family_code_set`, which can
    # differ from the Scryfall graph when set_targets groups extra codes under
    # the anchor). Computed once here and threaded into both calls (F4).
    try:
        scryfall_family_codes = {c.lower() for c in sets_mod.resolve(parent_code).all_codes}
    except LookupError:
        scryfall_family_codes = {parent_code.lower()}
    owned_oids = missing_mod.owned_oracle_ids(scryfall_family_codes)

    functional = missing_mod.functional_missing(
        parent_code, precomputed_missing=missing_rows, precomputed_owned=owned_oids,
    )
    functional_pool = CardDiffPool(name="functional", count=functional.n_cards,
                                   usd=functional.family_total_usd, rows=functional.cards)

    variant_rows = missing_mod.variant_chase_printings(
        parent_code, precomputed_missing=missing_rows, precomputed_owned=owned_oids,
    )
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


def family_diff(code: str, *, price_map: dict | None = None, refresh: bool = False,
                warn=None, log=None) -> FamilyDiff | None:
    """None if the family is unconfigured (SelectorParseError/LookupError from
    missing) or the anchor is unresolvable.

    Prices resolve LOCAL-FIRST via `family_status._local_prices` (→
    `sets.priced_map`) unless ``price_map`` is supplied. ``refresh`` syncs
    stale sets before pricing; ``warn`` (a list-of-codes callable) surfaces
    stale sets left un-refreshed; ``log`` surfaces diagnostics (unresolved ids,
    sync failures)."""
    try:
        parent_code, parent_name, related = family_status.resolve_family(code)
    except LookupError:
        return None
    family_code_set = family_status._family_code_set(parent_code, related)
    try:
        missing_rows = missing_mod.missing_printings(parent_code)
    except (sel_mod.SelectorParseError, LookupError):
        return None

    owned_rows = None
    if price_map is None:
        owned_rows = family_status._owned_rows_for_codes(family_code_set)
        ids = {r.scryfall_id for r in owned_rows} | {r.scryfall_id for r in missing_rows}
        prices = family_status._local_prices(list(ids), refresh=refresh, warn=warn, log=log)
    else:
        prices = price_map

    return _build_family_diff(parent_code, parent_name, family_code_set, missing_rows, prices,
                               owned_rows=owned_rows)


def collection_diff(*, refresh: bool = False, warn=None, log=None) -> list[FamilyDiff]:
    """One FamilyDiff per owned+characterized family, sorted by owned_usd desc.

    Shares the 4-step pre-pass (enumerate families → per-family code set →
    per-family `missing_printings` → ONE local-first price resolve) with
    `set_status.render_overview` via `family_status.collection_prepass`; each
    caller keeps only its own final per-family loop. `missing_printings` rows
    are threaded into both `functional_missing` and `variant_chase_printings`
    via `precomputed_missing`, and the bulk owned-rows list is grouped by set
    code ONCE and sliced per family into `_build_family_diff`'s `owned_rows`
    param, so no family re-fetches owned rows individually. ``refresh``/``warn``/
    ``log`` pass straight through to `collection_prepass`.
    """
    (parents, fam_codes_by_parent, missing_rows_by_parent,
     price_map, all_rows) = family_status.collection_prepass(refresh=refresh, warn=warn, log=log)
    if not parents:
        return []

    # DELIBERATE (not drift): card-diff is about the three missing pools, so
    # non-family (sld/mar/…) and unconfigured families — which have no missing-set
    # notion — are DROPPED entirely. set_status.render_overview, sharing the same
    # collection_prepass, instead emits them as owned-only rows with '-' cells.
    # Both are intended; the final loops differ by design.
    resolved = [
        (pc, pn, fam_codes_by_parent[pc], missing_rows_by_parent[pc])
        for pc, pn in parents.items()
        if pc not in family_status.NON_FAMILY_SETS
        and missing_rows_by_parent.get(pc) is not None
    ]
    return _assemble_family_diffs(resolved, price_map=price_map, owned_rows=all_rows)


def _assemble_family_diffs(
    resolved: list[tuple[str, str, set[str], list]],
    *, price_map: dict, owned_rows: list,
) -> list[FamilyDiff]:
    """Build + value a FamilyDiff per already-resolved family, sorted by owned_usd
    desc. The shared tail of `collection_diff` and `multi_family_diff`: given each
    family's ``(parent_code, parent_name, family_code_set, missing_rows)`` plus ONE
    pre-fetched ``price_map`` and the flat ``owned_rows`` list, group owned rows by
    set code ONCE and slice per family into `_build_family_diff` — so no family
    re-fetches owned rows or re-resolves prices.

    Grouping is sound because each card has exactly one set_code and families
    partition set codes disjointly (no code is grouped under two anchors), so the
    global ``(scryfall_id, finish)`` dedup equals the per-family dedup."""
    owned_rows_by_set: dict[str, list] = {}
    for r in owned_rows:
        owned_rows_by_set.setdefault((r.card.get("set") or "").lower(), []).append(r)

    diffs: list[FamilyDiff] = []
    for pc, pn, codes, mrows in resolved:
        fam_owned = [r for c in codes for r in owned_rows_by_set.get(c, [])]
        diffs.append(_build_family_diff(pc, pn, codes, mrows, price_map, owned_rows=fam_owned))

    diffs.sort(key=lambda f: f.owned_usd, reverse=True)
    return diffs


def multi_family_diff(codes, *, refresh: bool = False, warn=None, log=None,
                      on_skip=None) -> list[FamilyDiff]:
    """FamilyDiffs for an explicit list of family codes, batched like
    `collection_diff` — ONE local-first price resolve over the union of every
    requested family's owned + missing ids, instead of a per-family resolve.

    The multi-code sibling of `family_diff` (single anchor) and `collection_diff`
    (all owned families). Resolves each code's rows ONCE, unions the ids, does one
    `family_status._local_prices`, then builds each FamilyDiff from the shared
    price map with no re-materialization (the gallery's `--codes` path, F4).

    ``refresh``/``warn``/``log`` match `family_diff`. ``on_skip(code)`` (optional)
    is called for each code that doesn't resolve to a configured family (unknown
    anchor or no missing-set rules), so the caller can warn per code; such codes
    are omitted from the result."""
    # Resolve + materialize each family ONCE (parent, name, code set, missing rows).
    resolved: list[tuple[str, str, set[str], list]] = []
    for code in codes:
        try:
            parent_code, parent_name, related = family_status.resolve_family(code)
        except LookupError:
            if on_skip:
                on_skip(code)
            continue
        family_code_set = family_status._family_code_set(parent_code, related)
        try:
            missing_rows = missing_mod.missing_printings(parent_code)
        except (sel_mod.SelectorParseError, LookupError):
            if on_skip:
                on_skip(code)
            continue
        resolved.append((parent_code, parent_name, family_code_set, missing_rows))

    if not resolved:
        return []

    # Materialize owned rows per family ONCE, union every id (owned ∪ missing),
    # then ONE local-first price resolve across the whole set.
    owned_by_parent = {
        pc: family_status._owned_rows_for_codes(fcs)
        for pc, _pn, fcs, _mr in resolved
    }
    all_owned_rows = [r for rows in owned_by_parent.values() for r in rows]
    ids = {r.scryfall_id for r in all_owned_rows}
    for _pc, _pn, _fcs, mrows in resolved:
        ids.update(r.scryfall_id for r in mrows)
    price_map = family_status._local_prices(list(ids), refresh=refresh, warn=warn, log=log)

    return _assemble_family_diffs(resolved, price_map=price_map, owned_rows=all_owned_rows)

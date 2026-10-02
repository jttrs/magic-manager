"""Shared family-resolution + owned-summary + live-price helpers.

Extracted from ``scripts/set_status.py`` (behavior-preserving — same logic,
same docstrings) so a second consumer (``card_diff.py``) can reuse family
enumeration / owned-summary / live-price plumbing without reimplementing it.
``scripts/set_status.py`` imports these names rather than redefining them.
"""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path

from . import db, sets as sets_mod

ROOT = Path(__file__).resolve().parent.parent.parent


# Grab-bag / promo / collector sets that reprint cards from many OTHER sets and
# are NOT coherent "families" — there's no meaningful "missing from set" notion,
# and they should never be characterized. Rendered with the `-` (n/a) glyph in
# the overview's Char + Missing columns, distinct from `✗` ("characterizable but
# not yet done"). Hardcoded because no set_type/topology rule cleanly separates
# these from real masterpiece/expansion families.
#
# NOTE (2026-09-17): `spg` (Special Guests) was REMOVED from this set — it's a
# finite, completable 175-card masterpiece set (13 release waves, each an exact
# released_at match to a companion expansion), so it's now a normal characterized
# family (docs/sets/spg.md) with real missing-set/status. `sld` stays: it's a
# 2,757-card ever-growing box whose only sane completion unit is the DROP (MTGJSON
# deck-per-drop, via the secret-lair-value tooling), not the whole set.
#
# `mar` "Marvel Universe" is here because it's a cross-set masterpiece series
# feeding the booster packs of MULTIPLE Marvel expansions (SPM, MSH, + 4 more to
# come) — like SLD spanning the whole game, not one family. Unlike the flat
# grab-bags it has its OWN children (`omb` masterpiece + `lmar` promo,
# parent_set_code: mar), so it's registered as its own set_target anchor
# grouping mar+omb+lmar; NON_FAMILY membership just means owned-only reporting
# (no Char/Missing). See docs/sets/spm.md §1 + docs/scryfall-set-families-and-bonus-sheets.md.
# `cmm`/`scd`/`plst` (2026-09-15): reprint-only Masters / starter / grab-bag
# products the user holds incidentally — "missing from set" = "buy the entire
# reprint set's variant tiers" ($4.7k for cmm, a 5,595-card pool for plst, $0 for
# the reprint-starter scd), which is not a completion target. Owned-only, like sld.
NON_FAMILY_SETS: frozenset[str] = frozenset({"sld", "pw25", "pmei", "sch", "mar",
                                             "cmm", "scd", "plst"})


# ---------- family resolution (member → parent normalization) ----------

def resolve_family(anchor: str) -> tuple[str, str, list[dict]]:
    """(parent_code, parent_name, related). The parent is the .related member
    whose scryfall parent_set_code is None — NOT sets.resolve().code, which
    stays the MEMBER when a member code is passed (resolve('ncc').code=='ncc').
    Raises LookupError on an unknown code."""
    resolved = sets_mod.resolve(anchor)          # may raise LookupError
    related = resolved.related
    parent = next((s for s in related if not s.get("parent_set_code")), None)
    if parent is None:  # defensive; _walk_to_parent should always include it
        parent = related[0]
        print(f"warning: no null-parent member in family; falling back to "
              f"{parent['code']!r}", file=sys.stderr)
    return parent["code"].lower(), parent.get("name") or parent["code"], related


# ---------- set_targets-authoritative family grouping ----------
#
# The Scryfall parent_set_code graph (sets.resolve) and the user's registered
# `set_targets.related_codes` can DISAGREE: e.g. `mar` (Marvel Universe) has
# parent_set_code null on Scryfall (roots as its own family), but the user's
# set_targets['spm'] lists mar as a Spider-Man family member. For the overview
# and single-anchor metrics we treat set_targets as AUTHORITATIVE — a code that
# the user has grouped under an anchor belongs to that anchor's family, even if
# Scryfall roots it elsewhere. Codes not in any set_targets grouping fall back to
# the Scryfall graph.

_ST_INDEX: tuple[dict[str, str], dict[str, set[str]]] | None = None


def _set_targets_index() -> tuple[dict[str, str], dict[str, set[str]]]:
    """(member_to_anchor, anchor_to_codes), cached. member_to_anchor maps every
    code in every anchor's related_codes (plus the anchor itself) to that anchor;
    anchor_to_codes maps anchor → the full member set. First-wins on overlap."""
    global _ST_INDEX
    if _ST_INDEX is not None:
        return _ST_INDEX
    member_to_anchor: dict[str, str] = {}
    anchor_to_codes: dict[str, set[str]] = {}
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT anchor_code, related_codes FROM set_targets"
        ).fetchall()
    for r in rows:
        anchor = (r["anchor_code"] or "").lower()
        if not anchor:
            continue
        try:
            codes = {c.lower() for c in _json.loads(r["related_codes"] or "[]")}
        except (ValueError, TypeError):
            codes = set()
        codes.add(anchor)
        anchor_to_codes[anchor] = codes
        for c in codes:
            if c in member_to_anchor and member_to_anchor[c] != anchor:
                print(f"warning: set code {c!r} is grouped under both "
                      f"{member_to_anchor[c]!r} and {anchor!r}; keeping the first.",
                      file=sys.stderr)
                continue
            member_to_anchor[c] = anchor
    _ST_INDEX = (member_to_anchor, anchor_to_codes)
    return _ST_INDEX


def _family_parent(code: str) -> tuple[str, str]:
    """(parent_code, parent_name) for an owned set code, set_targets-first.
    A code the user registered under an anchor → that anchor (so mar → spm).
    Otherwise the Scryfall-graph parent — but if THAT parent is itself a
    set_targets member (e.g. code `lmar` → Scryfall parent `mar` → registered
    under `spm`), follow the grouping one more hop so the whole Scryfall family
    folds into the user's anchor."""
    member_to_anchor, _ = _set_targets_index()

    def _anchor_name(anchor: str) -> tuple[str, str]:
        try:
            pc, pn, _ = resolve_family(anchor)
            return pc, pn
        except LookupError:
            return anchor, anchor

    anchor = member_to_anchor.get(code.lower())
    if anchor:
        return _anchor_name(anchor)
    pc, pn, _ = resolve_family(code)  # may raise LookupError → caller skips
    # The Scryfall parent may itself be grouped under a user anchor (lmar→mar→spm).
    anchor = member_to_anchor.get(pc)
    if anchor and anchor != pc:
        return _anchor_name(anchor)
    return pc, pn


def _family_code_set(parent_code: str, related: list[dict]) -> set[str]:
    """The full set of set codes for a family's metrics: the Scryfall family
    (`related`) UNION the user's set_targets grouping for this anchor UNION the
    Scryfall family of each grouped member. That last hop matters because a
    set_targets member can itself root a Scryfall sub-family (spm groups `mar`,
    and `mar` roots `lmar`/`omb` on Scryfall) — all of it should count under spm."""
    _, anchor_to_codes = _set_targets_index()
    codes = {(s.get("code") or "").lower() for s in related if s.get("code")}
    grouped = anchor_to_codes.get(parent_code, set())
    codes |= grouped
    # Expand each grouped member's own Scryfall family (mar → lmar/omb).
    for member in grouped:
        if member == parent_code:
            continue
        try:
            codes |= {(s.get("code") or "").lower()
                      for s in resolve_family(member)[2] if s.get("code")}
        except LookupError:
            continue
    codes.discard("")
    return codes


# ---------- price helpers (local-first) ----------

def _local_prices(scryfall_ids: list[str], *, refresh: bool = False, warn=None,
                   log=None) -> dict[str, dict]:
    """scryfall_id -> prices dict ({'usd':..,'usd_foil':..,'prices_updated_at':..}).

    LOCAL-FIRST via `sets.priced_map` — reads prices from the local `cards`
    table (never a blanket live fetch); syncs ONLY stale sets when
    `refresh=True`, else warns via `warn([set_codes])` (if given) and uses
    local as-is. `log` is a print-like diagnostics callable passed through to
    `sets.priced_map` (unresolved ids, sync failures)."""
    if not scryfall_ids:
        return {}
    return sets_mod.priced_map(scryfall_ids, refresh=refresh, warn=warn, log=log)


def _unit(prices: dict, finish: str) -> float:
    """Finish-aware USD unit price from a live prices dict (0.0 if unpriced)."""
    v = prices.get("usd_foil") if finish == "foil" else prices.get("usd")
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


# ---------- owned-summary (set_targets-authoritative) ----------

def _owned_rows_for_codes(codes) -> list:
    """Owned MaterializedRows across a set of bare set codes, unioned by
    (scryfall_id, finish). Used where a family's code set is set_targets-derived
    (e.g. spm ∪ mar) and can't be expressed as a single `set:X+related` term
    (the selector grammar has no multi-code union, and `+related` re-expands via
    the Scryfall graph which excludes mar). Keying on (scryfall_id, finish) — not
    scryfall_id alone — preserves legit nonfoil+foil pairs while guarding against
    a printing being counted twice if code sets overlap."""
    from . import selectors
    union: dict[tuple[str, str], object] = {}
    for c in sorted(codes):
        try:
            for r in selectors.materialize(f"set:{c} owned"):
                union[(r.scryfall_id, r.finish)] = r
        except (selectors.SelectorParseError, LookupError):
            continue
    return list(union.values())


def _owned_summary_for_codes(codes, price_map: dict[str, dict] | None = None, *,
                             refresh: bool = False, warn=None, log=None) -> tuple[int, int, float]:
    """(distinct_printings, total_qty, live_usd) over an explicit code set —
    the set_targets-authoritative sibling of owned_summary. ``price_map`` supplies
    pre-batched prices (overview); None resolves (local-first) for just these
    codes. ``refresh``/``warn``/``log`` are passed through to the local resolve."""
    rows = _owned_rows_for_codes(codes)
    prints = len(rows)
    qty = sum(r.quantity for r in rows)
    prices = (price_map if price_map is not None
              else _local_prices([r.scryfall_id for r in rows], refresh=refresh, warn=warn, log=log))
    usd = sum(_unit(prices.get(r.scryfall_id, {}), r.finish) * r.quantity for r in rows)
    return prints, qty, usd


def is_characterized(parent_code: str) -> bool:
    return (ROOT / "docs" / "sets" / f"{parent_code}.md").exists()


# ---------- collection-wide pre-pass (shared by set_status + card_diff) ----------

def collection_prepass(*, refresh: bool = False, warn=None, log=None) -> tuple[
    dict[str, str], dict[str, set[str]], dict[str, list | None], dict[str, dict], list
]:
    """The 4-step pre-pass both `set_status.render_overview` and
    `card_diff.collection_diff` need before their own per-family loop:

    1. ``parents`` — every owned+registered family, via `_owned_family_parents`.
    2. ``fam_codes_by_parent`` — set_targets-authoritative code set per parent.
    3. ``missing_rows_by_parent`` — `missing.missing_printings` materialized
       ONCE per family (skipping `NON_FAMILY_SETS`; `None` = unconfigured).
    4. ``price_map`` — ONE local-first resolve (`sets.priced_map`, via
       `_local_prices`) over owned ids ∪ every family's missing ids. ``refresh``/
       ``warn``/``log`` thread through to that resolve.

    Also returns ``all_owned_rows`` (the flat owned-rows list from step 4's
    `_owned_rows_for_codes` call) so a caller doing a global dedup (e.g.
    `card_diff`'s price-fetch id gathering) can group it by `card["set"]`
    itself instead of re-fetching per family.

    Callers each keep their OWN distinct final per-family loop — this only
    extracts the shared setup, not the rendering/aggregation that follows."""
    from . import missing as missing_mod, selectors

    parents = _owned_family_parents()
    if not parents:
        return {}, {}, {}, {}, []

    fam_codes_by_parent: dict[str, set[str]] = {}
    for pc in parents:
        try:
            _, _, related = resolve_family(pc)
        except LookupError:
            related = [{"code": pc}]
        fam_codes_by_parent[pc] = _family_code_set(pc, related)

    missing_rows_by_parent: dict[str, list | None] = {}
    for pc in parents:
        if pc in NON_FAMILY_SETS:
            continue
        try:
            missing_rows_by_parent[pc] = missing_mod.missing_printings(pc)
        except (selectors.SelectorParseError, LookupError):
            missing_rows_by_parent[pc] = None  # unconfigured

    all_owned_rows = _owned_rows_for_codes(
        {c for codes in fam_codes_by_parent.values() for c in codes}
    )
    ids = {r.scryfall_id for r in all_owned_rows}
    for mrows in missing_rows_by_parent.values():
        if mrows:
            ids.update(r.scryfall_id for r in mrows)
    price_map = _local_prices(list(ids), refresh=refresh, warn=warn, log=log)

    return parents, fam_codes_by_parent, missing_rows_by_parent, price_map, all_owned_rows


# ---------- all-families enumeration (no-arg mode) ----------

def _owned_family_parents() -> dict[str, str]:
    """{parent_code: parent_name} for every family the collection touches.

    Union of (a) families the user owns cards in — distinct owned set codes,
    each normalized to its family parent — and (b) registered families in
    set_targets (so a master-list'd-but-not-yet-owned family still shows, with
    zeros). Deduped to parents so siblings don't resolve repeatedly."""
    with db.connect() as conn:
        owned_codes = [
            r[0].lower() for r in conn.execute(
                "SELECT DISTINCT c.set_code FROM cards c "
                "JOIN inventory i ON i.scryfall_id = c.scryfall_id "
                "WHERE i.quantity > 0"
            ).fetchall() if r[0]
        ]
        target_anchors = [
            r[0].lower() for r in conn.execute(
                "SELECT anchor_code FROM set_targets"
            ).fetchall() if r[0]
        ]
    parents: dict[str, str] = {}
    seen_codes: set[str] = set()
    for code in owned_codes + target_anchors:
        if code in seen_codes:
            continue
        seen_codes.add(code)
        try:
            pc, pn = _family_parent(code)  # set_targets-first (mar → spm)
        except LookupError:
            continue
        # A member code maps to the same parent as its siblings; record once.
        if pc not in parents:
            parents[pc] = pn
    return parents

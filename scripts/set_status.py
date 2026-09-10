"""Concise status report for a Magic set family.

Takes a family anchor OR any member code (snc, ncc, tmt, tle, …), normalizes to
the true family parent, and prints ONE compact markdown metrics block to stdout
(relayed verbatim to chat). Commentary/warnings go to stderr.

Metrics: family set codes (+types), # checklist ingests, owned printings/qty/$,
precons by format, TWO missing figures — distinct-printing missing (every art/
frame variant, live $) and functional missing (mechanically-unique cards owned
in zero printings, cheapest fill: in-family + anywhere floors) — and
characterization status.

Prices are LIVE (fetched from Scryfall via the rate-limited wrapper each run),
so the $ figures are current — output is therefore NOT byte-identical across
days. Read-only: no DB writes, no queries/ artifacts.

Exit codes: 0 = rendered (including uncharacterized families), 2 = bad anchor.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import (  # noqa: E402
    db, scryfall, sets as sets_mod, selectors, missing as missing_mod, util,
)


# Grab-bag / promo / collector sets that reprint cards from many OTHER sets and
# are NOT coherent "families" — there's no meaningful "missing from set" notion,
# and they should never be characterized. Rendered with the `-` (n/a) glyph in
# the overview's Char + Missing columns, distinct from `✗` ("characterizable but
# not yet done"). Hardcoded because no set_type/topology rule cleanly separates
# these from real masterpiece/expansion families (spg is masterpiece like mar;
# sld resolves to a real Scryfall family + is a registered set_target).
#
# `mar` "Marvel Universe" is here because it's a cross-set masterpiece series
# feeding the booster packs of MULTIPLE Marvel expansions (SPM, MSH, + 4 more to
# come) — like SLD spanning the whole game, not one family. Unlike the flat
# grab-bags it has its OWN children (`omb` masterpiece + `lmar` promo,
# parent_set_code: mar), so it's registered as its own set_target anchor
# grouping mar+omb+lmar; NON_FAMILY membership just means owned-only reporting
# (no Char/Missing). See docs/sets/spm.md §1 + docs/scryfall-set-families-and-bonus-sheets.md.
NON_FAMILY_SETS: frozenset[str] = frozenset({"sld", "spg", "pw25", "pmei", "sch", "mar"})


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
    import json as _json
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


# ---------- price helpers (live) ----------

def _live_prices(scryfall_ids: list[str]) -> dict[str, dict]:
    """scryfall_id -> prices dict ({'usd':..,'usd_foil':..}), live-fetched."""
    if not scryfall_ids:
        return {}
    found, _ = scryfall.collection([{"id": s} for s in sorted(set(scryfall_ids))])
    return {c["id"]: (c.get("prices") or {}) for c in found}


def _unit(prices: dict, finish: str) -> float:
    """Finish-aware USD unit price from a live prices dict (0.0 if unpriced)."""
    v = prices.get("usd_foil") if finish == "foil" else prices.get("usd")
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


# ---------- anywhere-floor (cheapest printing of a card in ANY set) ----------

_ANYWHERE_FLOOR_CACHE: dict[str, tuple[float | None, str | None]] = {}


def _anywhere_floor(oracle_id: str) -> tuple[float | None, str | None] | None:
    """Cheapest ``(usd, finish)`` across EVERY printing of a card (any set), via
    a live ``oracleid:`` Scryfall search. Memoized across families (a card
    reprinted in several families costs one lookup). Prefers nonfoil on tie."""
    if oracle_id in _ANYWHERE_FLOOR_CACHE:
        return _ANYWHERE_FLOOR_CACHE[oracle_id]
    nf: list[float] = []
    ff: list[float] = []
    try:
        for p in scryfall.search(f"oracleid:{oracle_id}", unique="prints"):
            pr = p.get("prices") or {}
            for key, bucket in (("usd", nf), ("usd_foil", ff)):
                v = pr.get(key)
                if v not in (None, ""):
                    try:
                        bucket.append(float(v))
                    except (TypeError, ValueError):
                        pass
    except Exception:  # noqa: BLE001 — a lookup failure just leaves anywhere unresolved
        _ANYWHERE_FLOOR_CACHE[oracle_id] = (None, None)
        return None
    res = _cheapest_pair(min(nf) if nf else None, min(ff) if ff else None)
    _ANYWHERE_FLOOR_CACHE[oracle_id] = res
    return res if res[0] is not None else None


def _cheapest_pair(nonfoil: float | None, foil: float | None) -> tuple[float | None, str | None]:
    if nonfoil is not None and (foil is None or nonfoil <= foil):
        return nonfoil, "nonfoil"
    if foil is not None:
        return foil, "foil"
    return None, None


# ---------- metrics ----------

def family_codes_with_types(parent_code: str, related: list[dict],
                            extra_codes: set[str] | None = None) -> list[tuple[str, str]]:
    """[(code, set_type)] — parent first, remainder sorted by code. ``extra_codes``
    folds in set_targets-grouped members not in the Scryfall ``related`` (e.g. mar
    /lmar/omb under spm); their set_type is looked up via the cached set list."""
    by_code = {(s.get("code") or "").lower(): (s.get("set_type") or "?") for s in related}
    if extra_codes:
        need = {c for c in extra_codes if c and c not in by_code}
        if need:
            all_sets = {s["code"].lower(): (s.get("set_type") or "?")
                        for s in scryfall.all_sets()}
            for c in need:
                by_code[c] = all_sets.get(c, "?")
    out = [(code, st) for code, st in by_code.items()]
    out.sort(key=lambda t: (t[0] != parent_code, t[0]))  # parent first, then alpha
    return out


def ingest_count(family_codes: list[str]) -> int:
    """# distinct successful ingest_log rows referencing a family code via an
    exact prefix (set:/jumpstart:/precon:). Excludes deck-assigned:* to avoid
    double-counting a precon ingest."""
    fam = set(family_codes)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, label FROM ingest_log WHERE status = 'success'"
        ).fetchall()
    n = 0
    for r in rows:
        label = r["label"] or ""
        for code in fam:
            if (label == f"set:{code}"
                    or label.startswith(f"jumpstart:{code}")
                    or label.startswith(f"precon:{code}")):
                n += 1
                break
    return n


def owned_summary(parent_code: str, price_map: dict[str, dict] | None = None) -> tuple[int, int, float]:
    """(distinct_printings, total_qty, live_usd) for owned family cards.

    ``price_map`` (scryfall_id -> prices dict) lets a caller supply prices it
    already fetched in bulk (the all-families overview batches every owned id
    into ONE /cards/collection call). When None, prices are fetched here for
    just this family (the single-anchor path)."""
    rows = selectors.materialize(f"set:{parent_code}+related owned")
    prints = len(rows)
    qty = sum(r.quantity for r in rows)
    prices = price_map if price_map is not None else _live_prices([r.scryfall_id for r in rows])
    usd = sum(_unit(prices.get(r.scryfall_id, {}), r.finish) * r.quantity for r in rows)
    return prints, qty, usd


def _owned_rows_for_codes(codes) -> list:
    """Owned MaterializedRows across a set of bare set codes, unioned by
    (scryfall_id, finish). Used where a family's code set is set_targets-derived
    (e.g. spm ∪ mar) and can't be expressed as a single `set:X+related` term
    (the selector grammar has no multi-code union, and `+related` re-expands via
    the Scryfall graph which excludes mar). Keying on (scryfall_id, finish) — not
    scryfall_id alone — preserves legit nonfoil+foil pairs while guarding against
    a printing being counted twice if code sets overlap."""
    union: dict[tuple[str, str], object] = {}
    for c in sorted(codes):
        try:
            for r in selectors.materialize(f"set:{c} owned"):
                union[(r.scryfall_id, r.finish)] = r
        except (selectors.SelectorParseError, LookupError):
            continue
    return list(union.values())


def _owned_summary_for_codes(codes, price_map: dict[str, dict] | None = None) -> tuple[int, int, float]:
    """(distinct_printings, total_qty, live_usd) over an explicit code set —
    the set_targets-authoritative sibling of owned_summary. ``price_map`` supplies
    pre-batched prices (overview); None fetches for just these codes."""
    rows = _owned_rows_for_codes(codes)
    prints = len(rows)
    qty = sum(r.quantity for r in rows)
    prices = price_map if price_map is not None else _live_prices([r.scryfall_id for r in rows])
    usd = sum(_unit(prices.get(r.scryfall_id, {}), r.finish) * r.quantity for r in rows)
    return prints, qty, usd


def precon_summary(family_codes: list[str]) -> dict[str, int]:
    """{format_bucket: count} of decks hard-linked (source_set_code) to the
    family. Falls back to the >=50%-of-cards heuristic for any deck whose
    source_set_code is still NULL (pre-backfill), noting the fallback on stderr."""
    fam = set(family_codes)
    placeholders = ",".join("?" for _ in fam)
    buckets: Counter = Counter()
    fallback_used = 0
    with db.connect() as conn:
        linked = conn.execute(
            f"SELECT format FROM decks WHERE LOWER(source_set_code) IN ({placeholders})",
            list(fam),
        ).fetchall()
        for r in linked:
            buckets[r["format"] or "other"] += 1
        # Heuristic fallback for NULL-source decks (should be none post-backfill).
        null_decks = conn.execute(
            "SELECT deck_id, format FROM decks WHERE source_set_code IS NULL"
        ).fetchall()
        for d in null_decks:
            share = conn.execute(
                f"""
                SELECT
                  SUM(CASE WHEN LOWER(c.set_code) IN ({placeholders}) THEN dc.count ELSE 0 END) AS in_fam,
                  SUM(dc.count) AS total
                FROM deck_cards dc JOIN cards c ON c.scryfall_id = dc.scryfall_id
                WHERE dc.deck_id = ?
                """,
                list(fam) + [d["deck_id"]],
            ).fetchone()
            if share and share["total"] and (share["in_fam"] or 0) / share["total"] >= 0.5:
                buckets[d["format"] or "other"] += 1
                fallback_used += 1
    if fallback_used:
        print(f"note: {fallback_used} deck(s) matched via the >=50% card heuristic "
              f"(no source_set_code — run decks.backfill_source_set_codes)", file=sys.stderr)
    return dict(buckets)


def missing_summary(parent_code: str) -> tuple[int, float, dict] | None:
    """(count, live_usd, concentration) of missing family printings, or None if
    the family is unconfigured (SelectorParseError) or unresolvable. The third
    element is ``missing.concentration(...)`` over the same live prices, so
    ``main`` can flag a likely scarcity chase tier. Side-effect-free — calls
    missing.missing_printings directly (never shells `mm query missing-set`,
    which writes files to queries/)."""
    try:
        rows = missing_mod.missing_printings(parent_code)
    except (selectors.SelectorParseError, LookupError) as e:
        print(f"note: missing-set not available for {parent_code!r}: {e}", file=sys.stderr)
        return None
    prices = _live_prices([r.scryfall_id for r in rows])
    price_fn = lambda sid, finish: _unit(prices.get(sid, {}), finish)  # noqa: E731
    usd = sum(price_fn(r.scryfall_id, r.finish) for r in rows)
    conc = missing_mod.concentration(rows, price_fn)
    return len(rows), usd, conc


def functional_missing_summary(parent_code: str) -> tuple[int, float, float] | None:
    """(n_cards, in_family_usd, anywhere_usd) of FUNCTIONALLY-missing cards
    (mechanically-unique cards owned in zero printings), or None when unconfigured.
    The anywhere floor uses the memoized live ``oracleid:`` lookup. Delegates to
    ``missing.functional_missing`` — the in-family price is local (no fetch)."""
    try:
        fm = missing_mod.functional_missing(parent_code, anywhere_floor_fn=_anywhere_floor)
    except (selectors.SelectorParseError, LookupError):
        return None
    return fm.n_cards, fm.family_total_usd, fm.anywhere_total_usd


def is_characterized(parent_code: str) -> bool:
    return (ROOT / "docs" / "sets" / f"{parent_code}.md").exists()


# ---------- render ----------

def render(parent_code, parent_name, codes_types, ingests, owned, precons,
           missing, characterized, *, functional=None, non_family: bool = False) -> str:
    prints, qty, owned_usd = owned
    codes_str = ", ".join(f"{c} ({t})" for c, t in codes_types)
    if precons:
        precon_str = " · ".join(f"{n} {fmt}" for fmt, n in sorted(precons.items()))
    else:
        precon_str = "none"
    # Non-family sets (SLD/SPG/MAR/…) have no missing-from-set or characterization
    # notion → the universal `-` (n/a) glyph, matching the overview.
    if non_family:
        dist_str = func_str = "— (cross-set; n/a)"
        char_str = "— (cross-set; n/a)"
    else:
        if missing is None:
            dist_str = "not configured"
        else:
            m_n, m_usd = missing[0], missing[1]
            dist_str = f"{m_n} prints · {util.fmt_usd(m_usd)}"
        if functional is None:
            func_str = "not configured" if missing is None else "—"
        else:
            f_n, f_fam, f_any = functional
            any_part = "" if f_any == f_fam else f" / anywhere {util.fmt_usd(f_any)}"
            func_str = f"{f_n} cards · in-family {util.fmt_usd(f_fam)}{any_part}"
        char_str = f"yes → docs/sets/{parent_code}.md" if characterized else "no"

    lines = [
        f"## {parent_code} — {parent_name} · family status",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Family | {parent_code} (parent) + {len(codes_types) - 1} codes |",
        f"| Set codes | {codes_str} |",
        f"| Ingests | {ingests} |",
        f"| Owned | {prints} printings / {qty} cards · {util.fmt_usd(owned_usd)} |",
        f"| Precons | {precon_str} |",
        f"| Missing (distinct) | {dist_str} |",
        f"| Missing (functional) | {func_str} |",
        f"| Characterized | {char_str} |",
    ]
    return "\n".join(lines)


# ---------- all-families overview (no-arg mode) ----------

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


def _missing_count(parent_code: str) -> int | None:
    """# missing family printings, or None if unconfigured. Count only — no
    live-$ fetch (the overview keeps to ONE bulk price call for owned cards)."""
    try:
        return len(missing_mod.missing_printings(parent_code))
    except (selectors.SelectorParseError, LookupError):
        return None


def render_overview() -> str:
    parents = _owned_family_parents()
    if not parents:
        return ("## Collection overview\n\n"
                "No owned families yet — add cards (`mm inventory add-card …`), "
                "ingest a checklist, or register a family with `mm set master-list <name>`.")

    # Family code set per parent — set_targets-authoritative (spm ∪ mar, etc.).
    fam_codes_by_parent: dict[str, set[str]] = {}
    for pc in parents:
        try:
            _, _, related = resolve_family(pc)
        except LookupError:
            related = [{"code": pc}]
        fam_codes_by_parent[pc] = _family_code_set(pc, related)

    # Materialize each family's distinct-printing missing ONCE (reused for the
    # distinct-$ sum and as the candidate set for functional_missing).
    missing_rows_by_parent: dict[str, list] = {}
    for pc in parents:
        if pc in NON_FAMILY_SETS:
            continue
        try:
            missing_rows_by_parent[pc] = missing_mod.missing_printings(pc)
        except (selectors.SelectorParseError, LookupError):
            missing_rows_by_parent[pc] = None  # unconfigured

    # ONE bulk price fetch: owned ids ∪ every family's distinct-missing ids.
    all_rows = _owned_rows_for_codes(
        {c for codes in fam_codes_by_parent.values() for c in codes}
    )
    ids = {r.scryfall_id for r in all_rows}
    for mrows in missing_rows_by_parent.values():
        if mrows:
            ids.update(r.scryfall_id for r in mrows)
    price_map = _live_prices(list(ids))

    rows_data = []
    tot_prints = tot_qty = 0
    tot_usd = tot_dist_usd = tot_func_fam = tot_func_any = 0.0
    tot_miss_prints = tot_func_cards = 0
    for pc, pn in parents.items():
        codes = fam_codes_by_parent[pc]
        prints, qty, usd = _owned_summary_for_codes(codes, price_map)
        precons = precon_summary(sorted(codes))
        n_precon = sum(precons.values())
        non_family = pc in NON_FAMILY_SETS
        mrows = missing_rows_by_parent.get(pc)
        # distinct-missing: count + live $ (from the bulk price_map).
        if non_family or mrows is None:
            dist = None
        else:
            dist_usd = sum(_unit(price_map.get(r.scryfall_id, {}), r.finish) for r in mrows)
            dist = (len(mrows), dist_usd)
        # functional-missing: reuse the materialized rows as the candidate set.
        # IN-FAMILY floor only here (local, instant) — the anywhere floor does a
        # rate-limited oracleid: search per missing card, which across ~20
        # families would make the overview take many minutes. Single-family mode
        # (`set_status.py <anchor>`) adds the anywhere floor (cheap for one family).
        if non_family or mrows is None:
            func = None
        else:
            fm = missing_mod.functional_missing(pc, precomputed_missing=mrows)
            func = (fm.n_cards, fm.family_total_usd, fm.family_total_usd)
        rows_data.append((pc, pn, prints, qty, usd, n_precon, dist, func, non_family))
        tot_prints += prints
        tot_qty += qty
        tot_usd += usd
        if dist:
            tot_miss_prints += dist[0]
            tot_dist_usd += dist[1]
        if func:
            tot_func_cards += func[0]
            tot_func_fam += func[1]
            tot_func_any += func[2]

    rows_data.sort(key=lambda t: t[4], reverse=True)  # by owned-$ desc

    lines = [
        f"## Collection overview · {len(rows_data)} families",
        "",
        "| Family | Printings | Cards | $ (owned) | Precons | Miss prints ($) | Miss func ($ in-fam) | Char |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]
    for pc, pn, prints, qty, usd, n_precon, dist, func, non_family in rows_data:
        if non_family:
            char_cell = "-"
            dist_cell = func_cell = "-"
        else:
            char_cell = "✓" if is_characterized(pc) else "✗"
            dist_cell = "-" if dist is None else f"{dist[0]}p · {util.fmt_usd(dist[1])}"
            if func is None:
                func_cell = "-"
            else:
                f_n, f_fam, f_any = func
                any_part = "" if f_any == f_fam else f"→{util.fmt_usd(f_any)}"
                func_cell = f"{f_n}c · {util.fmt_usd(f_fam)}{any_part}"
        precon_cell = str(n_precon) if n_precon else "-"
        lines.append(
            f"| {pc} — {pn} | {prints} | {qty} | {util.fmt_usd(usd)} | "
            f"{precon_cell} | {dist_cell} | {func_cell} | {char_cell} |"
        )
    any_part = "" if tot_func_any == tot_func_fam else f"→{util.fmt_usd(tot_func_any)}"
    lines.append(
        f"| **Total** | **{tot_prints}** | **{tot_qty}** | **{util.fmt_usd(tot_usd)}** | | "
        f"**{tot_miss_prints}p · {util.fmt_usd(tot_dist_usd)}** | "
        f"**{tot_func_cards}c · {util.fmt_usd(tot_func_fam)}{any_part}** | |"
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Concise status report for a set family.")
    ap.add_argument("anchor", nargs="?", default=None,
                    help="Family anchor OR any member code (snc, ncc, tmt, tle, …). "
                         "Omit for a collection-wide overview of all owned families.")
    args = ap.parse_args()

    if args.anchor is None:
        print(render_overview())
        return 0

    try:
        parent_code, parent_name, related = resolve_family(args.anchor)
    except LookupError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    # set_targets-authoritative family codes (folds e.g. mar into spm). For
    # characterized families whose set_targets grouping matches their Scryfall
    # family, this equals the Scryfall code set → output byte-identical.
    family_code_set = _family_code_set(parent_code, related)
    family_codes = sorted(family_code_set)
    codes_types = family_codes_with_types(parent_code, related, extra_codes=family_code_set)
    ingests = ingest_count(family_codes)
    owned = _owned_summary_for_codes(family_code_set)
    if owned[0] == 0:
        # Distinguish "never synced" from "synced but nothing owned".
        placeholders = ",".join("?" for _ in family_codes)
        with db.connect() as conn:
            synced = conn.execute(
                f"SELECT COUNT(*) FROM cards WHERE LOWER(set_code) IN ({placeholders})",
                family_codes,
            ).fetchone()[0]
        if synced == 0:
            print(f"note: family not synced — run "
                  f"`mm set sync {parent_code} --include-related`.", file=sys.stderr)
        else:
            print(f"note: {synced} cards synced for the family but none owned yet.",
                  file=sys.stderr)
    precons = precon_summary(family_codes)
    # Non-family sets (SLD, SPG, MAR, …) reprint cards from many OTHER sets and
    # have no meaningful "missing from set" / characterization notion — report
    # owned-only, and skip the missing_summary call (its "go characterize" note
    # would be noise). render() shows Missing/Characterized as n/a for these.
    non_family = parent_code in NON_FAMILY_SETS
    missing = None if non_family else missing_summary(parent_code)
    functional = None if non_family else functional_missing_summary(parent_code)
    characterized = False if non_family else is_characterized(parent_code)

    print(render(parent_code, parent_name, codes_types, ingests, owned, precons,
                 missing, characterized, functional=functional, non_family=non_family))

    # Advisory: flag a likely scarcity chase tier concentrated in a few pricey
    # prints (the pattern that made SPM show $4,230 for a ~$440 attainable gap).
    # Never auto-excludes — just prompts a value-sorted review. See the note in
    # missing.py: concentration ≠ a decision (fin/tmt are concentrated but KEPT).
    if missing is not None:
        conc = missing[2]
        if missing_mod.is_concentrated(conc):
            top = conc["top_prints"][0] if conc["top_prints"] else None
            top_str = f" (top: {top[0]} {top[1]} {top[2]} {top[3]} {util.fmt_usd(top[4])})" if top else ""
            print(
                f"⚠ missing $ is concentrated: top 5 prints = {conc['top5_share']:.0%} of "
                f"{util.fmt_usd(conc['total_usd'])}, {conc['n_over_100']} print(s) over $100"
                f"{top_str}.",
                file=sys.stderr)
            print(
                f"   Likely a scarcity chase tier — review with:\n"
                f"     uv run mm query show 'set:{parent_code}+related missing "
                f"treatment=preferred' --sort value-desc --first 20\n"
                f"   If they're cards you won't chase, add a "
                f"FAMILY_UNOBTAINABLE_RULES['{parent_code}'] entry (characterize-set §9). "
                f"Concentration is a REVIEW prompt, not a verdict — expensive attainable "
                f"chase (e.g. fin/tmt) is legitimately kept.",
                file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

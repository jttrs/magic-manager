"""Concise status report for a Magic set family.

Takes a family anchor OR any member code (snc, ncc, tmt, tle, …), normalizes to
the true family parent, and prints ONE compact markdown metrics block to stdout
(relayed verbatim to chat). Commentary/warnings go to stderr.

Metrics: family set codes (+types), # checklist ingests, owned prints/qty/$,
precons by format, missing $ (+count), characterization status.

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
NON_FAMILY_SETS: frozenset[str] = frozenset({"sld", "spg", "pw25", "pmei", "sch"})


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


def missing_summary(parent_code: str) -> tuple[int, float] | None:
    """(count, live_usd) of missing family printings, or None if the family is
    unconfigured (SelectorParseError) or unresolvable. Side-effect-free —
    calls missing.missing_printings directly (never shells `mm query
    missing-set`, which writes files to queries/)."""
    try:
        rows = missing_mod.missing_printings(parent_code)
    except (selectors.SelectorParseError, LookupError) as e:
        print(f"note: missing-set not available for {parent_code!r}: {e}", file=sys.stderr)
        return None
    prices = _live_prices([r.scryfall_id for r in rows])
    usd = sum(_unit(prices.get(r.scryfall_id, {}), r.finish) for r in rows)
    return len(rows), usd


def is_characterized(parent_code: str) -> bool:
    return (ROOT / "docs" / "sets" / f"{parent_code}.md").exists()


# ---------- render ----------

def render(parent_code, parent_name, codes_types, ingests, owned, precons,
           missing, characterized) -> str:
    prints, qty, owned_usd = owned
    codes_str = ", ".join(f"{c} ({t})" for c, t in codes_types)
    if precons:
        precon_str = " · ".join(f"{n} {fmt}" for fmt, n in sorted(precons.items()))
    else:
        precon_str = "none"
    if missing is None:
        missing_str = "not configured"
    else:
        m_n, m_usd = missing
        missing_str = f"{util.fmt_usd(m_usd)} / {m_n} prints"
    char_str = f"yes → docs/sets/{parent_code}.md" if characterized else "no"

    lines = [
        f"## {parent_code} — {parent_name} · family status",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Family | {parent_code} (parent) + {len(codes_types) - 1} codes |",
        f"| Set codes | {codes_str} |",
        f"| Ingests | {ingests} |",
        f"| Owned | {prints} prints / {qty} cards · {util.fmt_usd(owned_usd)} |",
        f"| Precons | {precon_str} |",
        f"| Missing | {missing_str} |",
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

    # ONE bulk price fetch for every owned card across all families (deduped ids).
    all_rows = _owned_rows_for_codes(
        {c for codes in fam_codes_by_parent.values() for c in codes}
    )
    price_map = _live_prices([r.scryfall_id for r in all_rows])

    rows_data = []
    tot_prints = tot_qty = 0
    tot_usd = 0.0
    for pc, pn in parents.items():
        codes = fam_codes_by_parent[pc]
        prints, qty, usd = _owned_summary_for_codes(codes, price_map)
        precons = precon_summary(sorted(codes))
        n_precon = sum(precons.values())
        non_family = pc in NON_FAMILY_SETS
        miss = None if non_family else _missing_count(pc)
        rows_data.append((pc, pn, prints, qty, usd, n_precon, miss, non_family))
        tot_prints += prints
        tot_qty += qty
        tot_usd += usd

    rows_data.sort(key=lambda t: t[4], reverse=True)  # by owned-$ desc

    lines = [
        f"## Collection overview · {len(rows_data)} families",
        "",
        "| Family | Owned | $ (owned) | Precons | Missing | Char |",
        "|---|---|---|---|---|---|",
    ]
    for pc, pn, prints, qty, usd, n_precon, miss, non_family in rows_data:
        # Universal `-` = n/a in these chart outputs.
        if non_family:
            char_cell = "-"      # not a characterizable family
            miss_cell = "-"
        else:
            char_cell = "✓" if is_characterized(pc) else "✗"
            miss_cell = "-" if miss is None else f"{miss} prints"
        precon_cell = str(n_precon) if n_precon else "-"
        lines.append(
            f"| {pc} — {pn} | {prints} / {qty} | {util.fmt_usd(usd)} | "
            f"{precon_cell} | {miss_cell} | {char_cell} |"
        )
    lines.append(
        f"| **Total** | **{tot_prints} / {tot_qty}** | **{util.fmt_usd(tot_usd)}** | | | |"
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
    missing = missing_summary(parent_code)
    characterized = is_characterized(parent_code)

    print(render(parent_code, parent_name, codes_types, ingests, owned, precons,
                 missing, characterized))
    return 0


if __name__ == "__main__":
    sys.exit(main())

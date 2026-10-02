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
days. Read-only: no DB writes, no output/ artifacts.

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
    mtgjson, card_floor,
)
from magic_manager.family_status import (  # noqa: E402
    NON_FAMILY_SETS,
    resolve_family,
    _set_targets_index,
    _family_parent,
    _family_code_set,
    _live_prices,
    _unit,
    _owned_summary_for_codes,
    is_characterized,
    collection_prepass,
)


# ---------- anywhere-floor (cheapest printing of a card in ANY set) ----------
#
# The cheapest-printing-anywhere lookup lives in the central card_floor engine
# (batched: ⌈N/20⌉ Scryfall searches, not one per oracle_id — the old per-id
# loop here was flagged slow across ~20 families). This module keeps a per-run
# memo so a card reprinted in several families costs one lookup, and exposes a
# per-id adapter (`_anywhere_floor`) for the `functional_missing(anywhere_floor_fn=…)`
# seam — pre-warm the memo in ONE batched call, then the adapter is pure dict reads.

_ANYWHERE_FLOOR_CACHE: dict[str, tuple[float | None, str | None]] = {}


def _prewarm_anywhere_floors(oracle_ids: list[str]) -> None:
    """Batch-fetch the anywhere floor for every not-yet-cached oracle_id in ONE
    chunked pass and populate ``_ANYWHERE_FLOOR_CACHE`` with the collapsed
    ``(usd, finish)`` (cheaper finish, nonfoil preferred on tie). A Scryfall
    failure degrades the batch to unresolved (``(None, None)``), matching the old
    per-id loop's fail-soft behavior."""
    need = [o for o in dict.fromkeys(oracle_ids) if o and o not in _ANYWHERE_FLOOR_CACHE]
    if not need:
        return
    try:
        floors = card_floor.anywhere_floors(need, finish_mode="either")
    except scryfall.ScryfallError:
        for o in need:
            _ANYWHERE_FLOOR_CACHE[o] = (None, None)
        return
    for o in need:
        fl = floors.get(o)
        _ANYWHERE_FLOOR_CACHE[o] = (fl.usd, fl.finish) if fl else (None, None)


def _anywhere_floor(oracle_id: str) -> tuple[float | None, str | None] | None:
    """Per-id adapter over the batched engine for the ``functional_missing``
    injection seam. Returns the memoized collapsed ``(usd, finish)``, fetching a
    single id on a cold miss (callers that know their id set should
    ``_prewarm_anywhere_floors`` first for the batched win). Prefers nonfoil on
    tie; ``None`` when unresolved/unpriced."""
    if oracle_id not in _ANYWHERE_FLOOR_CACHE:
        _prewarm_anywhere_floors([oracle_id])
    res = _ANYWHERE_FLOOR_CACHE.get(oracle_id, (None, None))
    return res if res[0] is not None else None


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
    """# distinct successful ingest_events rows referencing a family code via an
    exact prefix (set:/jumpstart:/precon:). Excludes deck-assigned:* to avoid
    double-counting a precon ingest.

    Reads ``ingest_events`` (the V19 provenance ledger's dimension table, which
    subsumed the old ``ingest_log``; labels were carried forward verbatim)."""
    fam = set(family_codes)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT ingest_id AS id, label FROM ingest_events WHERE status = 'success'"
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


def _precon_bucket(fmt: str | None, file_name: str | None, name: str | None) -> str:
    """Bucket label for one precon deck row. Commander-format decks stay in the
    ``commander`` bucket; everything non-commander is split by its MTGJSON
    product archetype (``starter kit`` / ``box set`` / ``scene box`` / …) via
    ``mtgjson.deck_archetype`` so the report enumerates real product types
    instead of one opaque ``other`` bucket. Falls back to ``format or 'other'``
    when there's no fileName to classify by (network-tolerant)."""
    if fmt == "commander":
        return "commander"
    if file_name:
        arch = mtgjson.deck_archetype(file_name, name=name)
        if arch != "other":
            return arch
    return fmt or "other"


def precon_summary(family_codes: list[str]) -> dict[str, int]:
    """{bucket: count} of decks hard-linked (source_set_code) to the family.
    Commander decks bucket by format; non-commander decks bucket by MTGJSON
    product archetype (Starter Kit / Box Set / Scene Box / …). Falls back to the
    >=50%-of-cards heuristic for any deck whose source_set_code is still NULL
    (pre-backfill), noting the fallback on stderr."""
    fam = set(family_codes)
    placeholders = ",".join("?" for _ in fam)
    buckets: Counter = Counter()
    fallback_used = 0
    with db.connect() as conn:
        linked = conn.execute(
            f"SELECT format, source_precon_file_name, name FROM decks "
            f"WHERE LOWER(source_set_code) IN ({placeholders})",
            list(fam),
        ).fetchall()
        for r in linked:
            buckets[_precon_bucket(r["format"], r["source_precon_file_name"], r["name"])] += 1
        # Heuristic fallback for NULL-source decks (should be none post-backfill).
        null_decks = conn.execute(
            "SELECT deck_id, format, source_precon_file_name, name FROM decks "
            "WHERE source_set_code IS NULL"
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
                buckets[_precon_bucket(d["format"], d["source_precon_file_name"], d["name"])] += 1
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
    which writes files to output/)."""
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
        rows = missing_mod.missing_printings(parent_code)
    except (selectors.SelectorParseError, LookupError):
        return None
    # Pre-warm EVERY candidate oracle_id's anywhere floor in ONE batched pass
    # (⌈N/20⌉ searches) before functional_missing calls the per-id adapter —
    # that's the batching win over the old per-oracle search loop. Scope the
    # prewarm to the actually-missing oracles (candidates − owned) so we don't
    # fetch floors for functionally-owned cards.
    try:
        family_codes = {c.lower() for c in sets_mod.resolve(parent_code).all_codes}
    except LookupError:
        family_codes = {parent_code.lower()}
    owned = missing_mod.owned_oracle_ids(family_codes)
    candidate_oids = {oid for r in rows if (oid := (r.card or {}).get("oracle_id"))}
    _prewarm_anywhere_floors(sorted(candidate_oids - owned))
    fm = missing_mod.functional_missing(
        parent_code, precomputed_missing=rows, precomputed_owned=owned,
        anywhere_floor_fn=_anywhere_floor)
    return fm.n_cards, fm.family_total_usd, fm.anywhere_total_usd


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

def _missing_count(parent_code: str) -> int | None:
    """# missing family printings, or None if unconfigured. Count only — no
    live-$ fetch (the overview keeps to ONE bulk price call for owned cards)."""
    try:
        return len(missing_mod.missing_printings(parent_code))
    except (selectors.SelectorParseError, LookupError):
        return None


def render_overview() -> str:
    parents, fam_codes_by_parent, missing_rows_by_parent, price_map, _all_owned_rows = \
        collection_prepass()
    if not parents:
        return ("## Collection overview\n\n"
                "No owned families yet — add cards (`mm inventory add-card …`), "
                "ingest a checklist, or register a family with `mm set master-list <name>`.")

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
        # IN-FAMILY floor only here (local, instant) — the overview deliberately
        # skips the (live) anywhere floor to stay network-light: it already holds
        # to ONE bulk price call, and layering a live floor search per family on
        # top isn't worth it for a glance view. Single-family mode
        # (`set_status.py <anchor>`) adds the anywhere floor (one batched call).
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

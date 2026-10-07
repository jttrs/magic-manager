"""Deterministic EDHREC report generator.

Three workflows, one script (subcommand-dispatched, the single source of truth
for all EDHREC report math + formatting — the CLI/skills are thin relays):

  commander <card>   Workflow A — cards with the highest inclusion rate when
                     <card> is the commander.
  card <card>        Workflow B — the most common commanders that run <card> in
                     the 99 (not as the commander).
  rankings <scope>   Workflow C — general rankings: 'commanders' (by deck count),
                     'cards' (top played), or 'salt' (saltiest).

<card> is a user-facing reference — a NAME ("Sol Ring") or a printing
("SET CN", e.g. "cmm 425"). It's up-leveled to its oracle name via Scryfall
(all reprints collapse to one EDHREC page) before the EDHREC slug is derived.

Every report emits (matching sealed-value / construct-value):
  * a markdown table to stdout (Scryfall-hyperlinked names) for chat relay, and
  * JSON + XLSX artifacts under output/edhrec/reports/.

Usage:
    uv run python scripts/edhrec_report.py commander "Atraxa, Praetors' Voice" --top 25
    uv run python scripts/edhrec_report.py card "Sol Ring"
    uv run python scripts/edhrec_report.py rankings commanders --timeframe week
    uv run python scripts/edhrec_report.py rankings salt

Exit codes:
    0 — report written
    2 — bad invocation / card not found / EDHREC page missing
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_OUTPUT_TYPE = "edhrec"  # → output/edhrec/reports/
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import edhrec, exports, gallery, scryfall_urls, sets, util  # noqa: E402
from magic_manager.gallery import GallerySection, PoolSpec, SortSpec  # noqa: E402


# ---------- rendering ----------

def _scryfall_search_url(name: str) -> str:
    return scryfall_urls.scryfall_search_url(f'!"{name}"')


def _md_commander(res, top: int, prices_note: str) -> str:
    rows = [r for r in res.rows if r.list_tag == "topcards"]
    rows.sort(key=lambda r: -(r.inclusion_pct or 0))
    rows = rows[:top]
    out = [
        f"## EDHREC — top cards in **{res.name}** decks",
        "",
        f"Highest inclusion rate across {res.name} decks (workflow A). {prices_note}",
        "",
        "| # | Card | Incl % | Decks | Synergy | Type | MV | Lowest $ |",
        "|--:|------|-------:|------:|--------:|------|---:|---------:|",
    ]
    for i, r in enumerate(rows, 1):
        out.append(
            f"| {i} | [{r.name}]({_scryfall_search_url(r.name)}) "
            f"| {r.inclusion_pct if r.inclusion_pct is not None else '—'} "
            f"| {r.num_decks or '—'} "
            f"| {round(r.synergy, 3) if r.synergy is not None else '—'} "
            f"| {r.type_line or '—'} "
            f"| {int(r.cmc) if r.cmc is not None else '—'} "
            f"| {util.fmt_usd(r.lowest_usd)} |"
        )
    return "\n".join(out)


def _md_card(res, top: int, prices_note: str) -> str:
    rows = [r for r in res.rows if r.list_tag == "topcommanders"]
    rows.sort(key=lambda r: -(r.num_decks or 0))
    rows = rows[:top]
    out = [
        f"## EDHREC — top commanders running **{res.name}**",
        "",
        f"Most common commanders whose decks include {res.name} in the 99 (workflow B). {prices_note}",
        "",
        "| # | Commander | Decks | Incl % | Type | MV | Lowest $ |",
        "|--:|-----------|------:|-------:|------|---:|---------:|",
    ]
    for i, r in enumerate(rows, 1):
        out.append(
            f"| {i} | [{r.name}]({_scryfall_search_url(r.name)}) "
            f"| {r.num_decks or '—'} "
            f"| {r.inclusion_pct if r.inclusion_pct is not None else '—'} "
            f"| {r.type_line or '—'} "
            f"| {int(r.cmc) if r.cmc is not None else '—'} "
            f"| {util.fmt_usd(r.lowest_usd)} |"
        )
    return "\n".join(out)


def _md_rankings(res, top: int, prices_note: str) -> str:
    rows = res.rows[:top]
    is_salt = res.scope == "salt"
    metric_hdr = "Salt" if is_salt else "Decks"
    entity_hdr = "Commander" if res.scope == "commanders" else "Card"
    title = res.name
    out = [
        f"## EDHREC rankings — {title}",
        "",
        f"Ranking (workflow C). {prices_note}",
        "",
        f"| Rank | {entity_hdr} | {metric_hdr} | Type | MV | Lowest $ |",
        "|-----:|------------|------:|------|---:|---------:|",
    ]
    for r in rows:
        metric = r.salt if is_salt else r.num_decks
        metric_s = (round(metric, 2) if is_salt and metric is not None
                    else (metric if metric is not None else "—"))
        out.append(
            f"| {r.rank} | [{r.name}]({_scryfall_search_url(r.name)}) "
            f"| {metric_s} "
            f"| {r.type_line or '—'} "
            f"| {int(r.cmc) if r.cmc is not None else '—'} "
            f"| {util.fmt_usd(r.lowest_usd)} |"
        )
    return "\n".join(out)


# ---------- compare (workflow D) ----------

# EDHREC category tags → gallery color vars (cycled). Order mirrors
# edhrec.COMMANDER_CARD_TAGS so the common lists get stable colors.
_TAG_COLOR_VARS = ("p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8")

_COMPARE_SORTS = {
    "inclusion": lambda c: -(max(c.a_pct or 0, c.b_pct or 0)),
    "synergy": lambda c: -(max(c.synergy_a or 0, c.synergy_b or 0)),
    "trend": lambda c: -(max(c.trend_a or 0, c.trend_b or 0)),
    "delta": lambda c: -(c.delta or 0),
}


def _pct(v) -> str:
    return f"{v}" if v is not None else "—"


def _md_compare(res, top: int, prices_note: str, sort: str) -> str:
    """Two views: (1) three bucket tables (Only A / Both / Only B) sorted by the
    chosen axis; (2) a rank-delta table of shared cards by |A% − B%|."""
    keyfn = _COMPARE_SORTS.get(sort, _COMPARE_SORTS["inclusion"])
    a_only = sorted([c for c in res.cards if c.bucket == "a_only"], key=keyfn)[:top]
    both = sorted([c for c in res.cards if c.bucket == "both"], key=keyfn)[:top]
    b_only = sorted([c for c in res.cards if c.bucket == "b_only"], key=keyfn)[:top]
    n_a = sum(1 for c in res.cards if c.bucket in ("a_only", "both"))
    n_b = sum(1 for c in res.cards if c.bucket in ("b_only", "both"))
    n_both = sum(1 for c in res.cards if c.bucket == "both")

    out = [
        f"## EDHREC compare — **{res.name_a}** vs **{res.name_b}**",
        "",
        f"Recommended-card overlap (workflow D). {res.name_a}: {n_a} cards · "
        f"{res.name_b}: {n_b} cards · shared: {n_both}. Sorted by {sort}. {prices_note}",
    ]

    def _bucket_table(title: str, cards: list, show_both: bool) -> list[str]:
        lines = ["", f"### {title} ({len(cards)} shown)", ""]
        if show_both:
            lines += ["| # | Card | A % | B % | Δ | Type | MV | Lowest $ |",
                      "|--:|------|----:|----:|--:|------|---:|---------:|"]
            for i, c in enumerate(cards, 1):
                lines.append(
                    f"| {i} | [{c.name}]({_scryfall_search_url(c.name)}) "
                    f"| {_pct(c.a_pct)} | {_pct(c.b_pct)} "
                    f"| {round(c.delta, 2) if c.delta is not None else '—'} "
                    f"| {c.type_line or '—'} "
                    f"| {int(c.cmc) if c.cmc is not None else '—'} "
                    f"| {util.fmt_usd(c.lowest_usd)} |"
                )
        else:
            lines += ["| # | Card | Incl % | Type | MV | Lowest $ |",
                      "|--:|------|-------:|------|---:|---------:|"]
            for i, c in enumerate(cards, 1):
                pct = c.a_pct if c.bucket == "a_only" else c.b_pct
                lines.append(
                    f"| {i} | [{c.name}]({_scryfall_search_url(c.name)}) "
                    f"| {_pct(pct)} "
                    f"| {c.type_line or '—'} "
                    f"| {int(c.cmc) if c.cmc is not None else '—'} "
                    f"| {util.fmt_usd(c.lowest_usd)} |"
                )
        return lines

    out += _bucket_table(f"Only {res.name_a}", a_only, show_both=False)
    out += _bucket_table(f"Both", both, show_both=True)
    out += _bucket_table(f"Only {res.name_b}", b_only, show_both=False)

    # View 2: biggest-disagreement shared cards.
    by_delta = sorted([c for c in res.cards if c.bucket == "both"],
                      key=lambda c: -(c.delta or 0))[:top]
    out += [
        "", "### Biggest disagreement (shared cards by |A % − B %|)", "",
        "| # | Card | A % | B % | Δ | Type | Lowest $ |",
        "|--:|------|----:|----:|--:|------|---------:|",
    ]
    for i, c in enumerate(by_delta, 1):
        out.append(
            f"| {i} | [{c.name}]({_scryfall_search_url(c.name)}) "
            f"| {_pct(c.a_pct)} | {_pct(c.b_pct)} "
            f"| {round(c.delta, 2) if c.delta is not None else '—'} "
            f"| {c.type_line or '—'} "
            f"| {util.fmt_usd(c.lowest_usd)} |"
        )
    return "\n".join(out)


def _compare_tag_pools(res) -> list:
    """Build the gallery PoolSpec list from the category tags actually present,
    in edhrec.COMMANDER_CARD_TAGS order, each assigned a cycled color var."""
    present = {t for c in res.cards for t in c.tags}
    ordered = [t for t in edhrec.COMMANDER_CARD_TAGS if t in present]
    ordered += sorted(present - set(ordered))  # any unexpected tags last
    return [
        PoolSpec(tag, tag.replace("cards", " cards").replace("utility", "utility ").title(),
                 _TAG_COLOR_VARS[i % len(_TAG_COLOR_VARS)])
        for i, tag in enumerate(ordered)
    ]


def _compare_html(res, pools: list) -> str:
    """Render the comparison as an image-first gallery: sections = buckets
    (Only A / Both / Only B), pool chips = category tags, per-tile badge = each
    commander's inclusion %, numeric sorts = inclusion / synergy / trend / delta."""
    bucket_meta = [
        ("a_only", f"Only {res.name_a}"),
        ("both", "Both"),
        ("b_only", f"Only {res.name_b}"),
    ]
    tiles_by_section: dict[str, list[dict]] = {k: [] for k, _ in bucket_meta}
    for c in res.cards:
        if c.bucket == "both":
            badge = f"A {_pct(c.a_pct)}% · B {_pct(c.b_pct)}%"
        elif c.bucket == "a_only":
            badge = f"A {_pct(c.a_pct)}%"
        else:
            badge = f"B {_pct(c.b_pct)}%"
        tiles_by_section[c.bucket].append({
            "sid_key": ("oid", c.oracle_id or c.slug),
            "pools": set(c.tags) if c.tags else set(),
            "family": c.bucket,
            "name": c.name,
            "set": (c.set_code or "").upper() if c.set_code else None,
            "cn": c.collector_number,
            "rarity": c.rarity,
            "finish": None,
            "usd": c.lowest_usd,
            "image_uri": c.image_uri,
            "scryfall_url": gallery.scryfall_card_url(c.set_code, c.collector_number),
            "badge": badge,
            "sort_values": {
                "inclusion": max(c.a_pct or 0, c.b_pct or 0),
                "synergy": max(c.synergy_a or 0, c.synergy_b or 0),
                "trend": max(c.trend_a or 0, c.trend_b or 0),
                "delta": c.delta or 0,
            },
            "row": None,
        })
    for k in tiles_by_section:
        tiles_by_section[k].sort(key=gallery.tile_sort_key)

    sections = []
    for code, label in bucket_meta:
        tiles = tiles_by_section[code]
        total = sum(t["usd"] for t in tiles if t["usd"] is not None)
        sections.append(GallerySection(code, label, f"{len(tiles)} cards · {util.fmt_usd(total)}"))

    return gallery.render_gallery(
        sections, tiles_by_section, pools,
        title=f"EDHREC compare — {res.name_a} vs {res.name_b}",
        hint="click a card to open on Scryfall · chips = EDHREC category",
        group_label="Bucket", pool_label="Category",
        extra_sorts=[
            SortSpec("Inclusion %: high→low", "inclusion"),
            SortSpec("Synergy: high→low", "synergy"),
            SortSpec("Trend: high→low", "trend"),
            SortSpec("Disagreement Δ: high→low", "delta"),
        ],
        generated=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
    )


# ---------- artifacts ----------

def _row_dict(r) -> dict:
    return {
        "name": r.name, "slug": r.slug, "oracle_id": r.oracle_id,
        "list_tag": r.list_tag, "num_decks": r.num_decks,
        "potential_decks": r.potential_decks, "inclusion_pct": r.inclusion_pct,
        "synergy": r.synergy, "lift": r.lift, "trend_zscore": r.trend_zscore,
        "salt": r.salt, "rank": r.rank, "type_line": r.type_line, "cmc": r.cmc,
        "mana_cost": r.mana_cost, "color_identity": r.color_identity,
        "rarity": r.rarity, "lowest_usd": r.lowest_usd,
        "lowest_usd_foil": r.lowest_usd_foil,
    }


def _write_json(res, kind: str, out_path: Path, prices_as_of: str | None) -> None:
    payload = {
        "kind": kind,
        "slug": res.slug,
        "name": res.name,
        "scope": res.scope,
        "timeframe": res.timeframe,
        "prices_as_of": prices_as_of,
        "generated_at": datetime.now(UTC).isoformat(),
        "rows": [_row_dict(r) for r in res.rows],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_xlsx(res, kind: str, out_path: Path) -> None:
    headers = ["list_tag", "name", "num_decks", "potential_decks", "inclusion_pct",
               "synergy", "lift", "salt", "rank", "type_line", "mana_value",
               "lowest_usd", "lowest_usd_foil", "oracle_id"]
    cell_rows = [
        [r.list_tag, r.name, r.num_decks, r.potential_decks, r.inclusion_pct,
         r.synergy, r.lift, r.salt, r.rank, r.type_line,
         int(r.cmc) if r.cmc is not None else None,
         r.lowest_usd, r.lowest_usd_foil, r.oracle_id]
        for r in res.rows
    ]
    widths = {1: 16, 2: 34, 3: 10, 4: 12, 5: 11, 6: 9, 7: 8, 8: 8, 9: 6,
              10: 30, 11: 6, 12: 11, 13: 13, 14: 38}
    results = exports.xlsx.SheetSpec(
        title=kind, headers=headers, rows=cell_rows,
        money_cols=(12, 13), widths=widths,
    )
    exports.xlsx.write_workbook(out_path, [results])


def _compare_card_dict(c) -> dict:
    return {
        "name": c.name, "oracle_id": c.oracle_id, "slug": c.slug,
        "bucket": c.bucket, "tags": c.tags,
        "a_pct": c.a_pct, "b_pct": c.b_pct, "a_decks": c.a_decks, "b_decks": c.b_decks,
        "delta": c.delta, "synergy_a": c.synergy_a, "synergy_b": c.synergy_b,
        "trend_a": c.trend_a, "trend_b": c.trend_b,
        "type_line": c.type_line, "cmc": c.cmc, "mana_cost": c.mana_cost,
        "color_identity": c.color_identity, "rarity": c.rarity,
        "lowest_usd": c.lowest_usd, "lowest_usd_foil": c.lowest_usd_foil,
        "scryfall_id": c.scryfall_id, "set_code": c.set_code,
        "collector_number": c.collector_number,
    }


def _write_compare_json(res, out_path: Path, prices_as_of: str | None) -> None:
    payload = {
        "kind": "compare",
        "name_a": res.name_a, "name_b": res.name_b,
        "slug_a": res.slug_a, "slug_b": res.slug_b,
        "prices_as_of": prices_as_of,
        "generated_at": datetime.now(UTC).isoformat(),
        "cards": [_compare_card_dict(c) for c in res.cards],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_compare_xlsx(res, out_path: Path) -> None:
    headers = ["bucket", "name", "a_pct", "b_pct", "delta", "a_decks", "b_decks",
               "tags", "type_line", "mana_value", "lowest_usd", "lowest_usd_foil",
               "oracle_id"]
    cell_rows = [
        [c.bucket, c.name, c.a_pct, c.b_pct, c.delta, c.a_decks, c.b_decks,
         ", ".join(c.tags), c.type_line,
         int(c.cmc) if c.cmc is not None else None,
         c.lowest_usd, c.lowest_usd_foil, c.oracle_id]
        for c in res.cards
    ]
    widths = {1: 9, 2: 34, 3: 8, 4: 8, 5: 8, 6: 9, 7: 9, 8: 28, 9: 30,
              10: 6, 11: 11, 12: 13, 13: 38}
    spec = exports.xlsx.SheetSpec(
        title="compare", headers=headers, rows=cell_rows,
        money_cols=(11, 12), widths=widths,
    )
    exports.xlsx.write_workbook(out_path, [spec])


# ---------- driver ----------

def _prices_note(oids: list[str], *, refresh: bool) -> str:
    """Ensure prices for the resolved oracle set, return a 'prices as of' note."""
    # Resolve the sets those oracle cards belong to, ensure fresh, then report.
    if not oids:
        return ""
    with sets.db.connect() as c:
        placeholders = ",".join("?" for _ in oids)
        rows = c.execute(
            f"SELECT DISTINCT set_code, scryfall_id FROM cards WHERE oracle_id IN ({placeholders})",
            oids,
        ).fetchall()
    codes = sorted({r[0] for r in rows})
    sids = [r[1] for r in rows]
    if codes:
        sets.ensure_priced(codes, refresh_stale=refresh, log=lambda m: print(m, file=sys.stderr))
    return sets.prices_fetched_note(
        sids, oldest_style="range", period=True,
        local_fallback="Prices: local (best-effort).",
    )


def _run_compare(args, ts: str, out_dir: Path, refresh: bool) -> int:
    """Workflow D driver: build the comparison, ensure prices, emit md + json +
    xlsx + an image-first HTML gallery under output/edhrec/reports/."""
    try:
        res = edhrec.compare_commanders(args.commander_a, args.commander_b)
    except edhrec.EdhrecError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    oids = [c.oracle_id for c in res.cards if c.oracle_id]
    note = _prices_note(oids, refresh=refresh)
    # Re-enrich if we just synced prices (compare_commanders enriched once already
    # from local; a --refresh may have updated them).
    if refresh:
        res = edhrec.compare_commanders(args.commander_a, args.commander_b)

    md = _md_compare(res, args.top, note, args.sort)
    pools = _compare_tag_pools(res)
    html_out = _compare_html(res, pools)

    base = f"compare-{res.slug_a}-vs-{res.slug_b}-{ts}"
    json_path = out_dir / f"{base}.json"
    xlsx_path = out_dir / f"{base}.xlsx"
    html_path = out_dir / f"{base}.html"
    _write_compare_json(res, json_path, note or None)
    _write_compare_xlsx(res, xlsx_path)
    html_path.write_text(html_out, encoding="utf-8")

    print(md)
    print()
    print(f"→ {json_path}")
    print(f"→ {xlsx_path}")
    print(f"→ file://{html_path.resolve()}")
    return 0


def main() -> int:
    # Shared options live on a parent parser so they can appear AFTER the
    # subcommand (argparse won't accept a top-level flag post-subcommand).
    common = argparse.ArgumentParser(add_help=False)
    util.add_price_refresh_arg(common)

    ap = argparse.ArgumentParser(description="EDHREC report generator.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_cmd = sub.add_parser("commander", parents=[common],
                           help="Workflow A: top cards for a commander.")
    p_cmd.add_argument("card")
    p_cmd.add_argument("--top", type=int, default=25)

    p_card = sub.add_parser("card", parents=[common],
                            help="Workflow B: top commanders running a card.")
    p_card.add_argument("card")
    p_card.add_argument("--top", type=int, default=25)

    p_rank = sub.add_parser("rankings", parents=[common],
                            help="Workflow C: general rankings (optionally filtered).")
    p_rank.add_argument("scope", choices=["commanders", "cards", "salt"])
    p_rank.add_argument("--timeframe", default="week")
    p_rank.add_argument("--top", type=int, default=50)
    # Commander-only, mutually-exclusive filters (enforced below).
    p_rank.add_argument("--color", help="Color identity: WUBRG letters ('wu'), a "
                        "guild/shard/wedge name ('azorius','bant'), 'mono-red', "
                        "'five-color', or 'colorless'.")
    p_rank.add_argument("--tag", help="Creature type OR theme (EDHREC serves both "
                        "from /tags/<slug>): e.g. 'goblins', 'treasure'.")
    p_rank.add_argument("--set", dest="set_family",
                        help="Set name or code (family-expanded, e.g. 'fin').")

    p_cmp = sub.add_parser("compare", parents=[common],
                           help="Workflow D: compare two commanders' recommended cards.")
    p_cmp.add_argument("commander_a")
    p_cmp.add_argument("commander_b")
    p_cmp.add_argument("--top", type=int, default=25,
                       help="Rows per bucket table in the markdown (default 25).")
    p_cmp.add_argument("--sort", choices=list(_COMPARE_SORTS), default="inclusion",
                       help="Markdown bucket-table sort axis (default: inclusion).")

    args = ap.parse_args()
    refresh = args.refresh
    ts = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
    out_dir = util.output_dir(_OUTPUT_TYPE, "reports")

    if args.cmd == "compare":
        return _run_compare(args, ts, out_dir, refresh)

    try:
        if args.cmd in ("commander", "card"):
            # Symmetric ingest: warm BOTH EDHREC views (gated by eligibility),
            # then render from the one the user asked for.
            dual = edhrec.sync_both(args.card)
            if args.cmd == "commander":
                res = dual.commander
                if res is None:
                    why = ("not commander-eligible" if not dual.eligible
                           else "EDHREC has no commander page for it yet")
                    print(f"error: {dual.name!r} — {why}; no commander report.",
                          file=sys.stderr)
                    return 2
                renderer, base = _md_commander, f"{res.slug}-commander-{ts}"
            else:  # card
                res = dual.card
                if res is None:
                    print(f"error: EDHREC has no card page for {dual.name!r}.",
                          file=sys.stderr)
                    return 2
                renderer, base = _md_card, f"{res.slug}-card-{ts}"
        else:  # rankings
            # validation (mutually-exclusive, commander-only filters) lives in
            # the engine; a bad request raises EdhrecError → exit 2 below.
            res = edhrec.sync_rankings(args.scope, args.timeframe, color=args.color,
                                       tag=args.tag, set_family=args.set_family)
            renderer = _md_rankings
            base = f"rankings-{res.scope}-{res.slug}-{res.timeframe or 'all'}-{ts}"
    except edhrec.EdhrecError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    # sync -> ensure prices for the resolved oracle set -> enrich ONCE (so the
    # local metadata reflects any freshly-synced prices) -> render.
    oids = [r.oracle_id for r in res.rows if r.oracle_id]
    note = _prices_note(oids, refresh=refresh)
    edhrec.enrich_rows(res.rows)
    md = renderer(res, args.top, note)

    json_path = out_dir / f"{base}.json"
    xlsx_path = out_dir / f"{base}.xlsx"
    _write_json(res, args.cmd, json_path, note or None)
    _write_xlsx(res, args.cmd, xlsx_path)

    print(md)
    print()
    print(f"→ {json_path}")
    print(f"→ {xlsx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

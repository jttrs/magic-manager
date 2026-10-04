"""Self-contained HTML gallery of the three card-diff pools, image-first.

Renders what `mm query card-diff` reports as tables (via `card_diff.py`) as a
single local HTML file instead: a Scryfall-style image grid, filterable by
family and pool (printing / functional / variant-chase) via a collapsible
left sidebar, with a name search box and a value/name/collector-number sort
control. No server, no external CSS/JS — card images lazy-load from
Scryfall's CDN at browser render time (the local `cards` table already
carries `image_uri` for 100% of rows; this script fetches it with ONE
targeted query, not a selector-projection change).

Each printing is rendered ONCE per family even if it belongs to more than one
pool (e.g. every variant-chase printing is also in the printing pool); pool
membership is shown as a segmented underline bar + caption text instead of
duplicating the tile.

The generic grid/filter/sort/export engine lives in `magic_manager.gallery`;
this script is the card-diff-specific adapter (FamilyDiff → tiles) over it.

Usage:
    uv run python scripts/card_diff_html.py                  # every owned+configured family
    uv run python scripts/card_diff_html.py acr tdm           # just these families
    uv run python scripts/card_diff_html.py --pool functional # narrow which pools render
    uv run python scripts/card_diff_html.py --refresh         # sync stale sets before pricing

Prices are LOCAL-FIRST (read from the local `cards` table, not re-fetched live
each run) — pass --refresh to sync stale (>7d) referenced sets before pricing.

Exit codes:
    0 — gallery written (even if a named code has nothing to show)
    2 — bad invocation (no families resolved from the given codes)
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import card_diff as card_diff_mod, gallery, sets as sets_mod, util  # noqa: E402
from magic_manager.card_diff_tiles import (  # noqa: E402
    POOL_CHOICES, _EXPORTS, _POOL_BY_KEY, build_tiles, family_summary as _family_summary,
)
from magic_manager.gallery import GallerySection  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Self-contained HTML gallery of card-diff pools, image-first.")
    ap.add_argument("codes", nargs="*",
                     help="Family anchor/member code(s). Omit for every owned+configured family.")
    ap.add_argument("--pool", choices=("printing", "functional", "variant-chase", "all"),
                     default="all", help="Which pool(s) to render (default: all).")
    ap.add_argument("--refresh", action="store_true",
                     help="Sync stale (>7d) referenced sets before pricing. Default: "
                          "local-first (fast, uses local prices as-is).")
    ap.add_argument("--chase", choices=("exclude", "include", "only"), default="exclude",
                     help="Grey/chase-tier handling (tier='chase' premium-art rules): "
                          "exclude (default), include (chase prints also feed the pools), "
                          "or only (chase prints only).")
    args = ap.parse_args()

    pools = list(POOL_CHOICES) if args.pool == "all" else [args.pool]

    stale_codes: list[str] = []
    log = lambda m: print(m, file=sys.stderr)  # noqa: E731

    if args.codes:
        # Batched: ONE local-first price resolve over the union of every requested
        # family's ids (F4), not a per-family resolve.
        diffs = card_diff_mod.multi_family_diff(
            args.codes, refresh=args.refresh, warn=stale_codes.extend, log=log,
            chase=args.chase,
            on_skip=lambda c: print(
                f"warning: {c!r} is not a resolvable/configured family — skipped.",
                file=sys.stderr),
        )
        if not diffs:
            print("error: none of the given codes resolved to a configured family.",
                  file=sys.stderr)
            return 2
    else:
        print("Computing collection-wide card diff (local-first; pass --refresh to sync "
              "stale sets first)…", file=sys.stderr)
        diffs = card_diff_mod.collection_diff(refresh=args.refresh, warn=stale_codes.extend, log=log, chase=args.chase)
        if not diffs:
            print("error: no owned+configured families found.", file=sys.stderr)
            return 2

    msg = sets_mod.stale_warning(stale_codes)
    if msg:
        print(msg, file=sys.stderr)

    all_tiles = build_tiles(diffs, pools)
    tiles_by_family: dict[str, list[dict]] = {}
    for t in all_tiles:
        tiles_by_family.setdefault(t["family"], []).append(t)

    pool_specs = [_POOL_BY_KEY[p] for p in pools]
    sections = [GallerySection(fd.code, fd.name, _family_summary(fd, pools)) for fd in diffs]
    html_out = gallery.render_gallery(
        sections, tiles_by_family, pool_specs,
        title="Card diff gallery",
        group_label="Family",
        exports=_EXPORTS,
        generated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    out_dir = util.output_dir("card-diff", "reports")
    out_path = out_dir / f"card-diff-gallery-{ts}.html"
    out_path.write_text(html_out, encoding="utf-8")

    n_total = sum(len(v) for v in tiles_by_family.values())
    print(f"Card diff gallery — {len(diffs)} family(ies) · {n_total} card(s)")
    print(f"  → file://{out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

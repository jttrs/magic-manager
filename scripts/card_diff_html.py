"""Self-contained HTML gallery of the three card-diff pools, image-first.

Renders what `mm query card-diff` reports as tables (via `card_diff.py`) as a
single local HTML file instead: a Scryfall-style image grid, filterable by
family and pool (printing / functional / variant-chase), with a name search
box and a value/name sort control. No server, no external CSS/JS — card
images lazy-load from Scryfall's CDN at browser render time (the local
`cards` table already carries `image_uri` for 100% of rows; this script
fetches it with ONE targeted query, not a selector-projection change).

Usage:
    uv run python scripts/card_diff_html.py                  # every owned+configured family
    uv run python scripts/card_diff_html.py acr tdm           # just these families
    uv run python scripts/card_diff_html.py --pool functional # narrow which pools render

Exit codes:
    0 — gallery written (even if a named code has nothing to show)
    2 — bad invocation (no families resolved from the given codes)
"""
from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import card_diff as card_diff_mod, db, util  # noqa: E402

POOL_CHOICES = ("printing", "functional", "variant-chase")
POOL_LABELS = {"printing": "Printing", "functional": "Functional", "variant-chase": "Variant-chase"}
POOL_COLORS = {"printing": "#4a7fd6", "functional": "#c25b2a", "variant-chase": "#3a9c6b"}


def _scryfall_card_url(set_code: str | None, cn: str | None) -> str | None:
    if not set_code or not cn:
        return None
    return f"https://scryfall.com/card/{set_code.lower()}/{cn}"


def _tile_from_materialized(r, pool: str, family_code: str, images: dict) -> dict:
    """Normalize a MaterializedRow (printing / variant-chase pool) into a tile
    dict the renderer understands."""
    c = r.card
    finish = r.finish
    unit = c.get("prices_usd_foil") if finish == "foil" else c.get("prices_usd")
    usd = (unit * r.quantity) if unit is not None else None
    set_code = c.get("set")
    cn = c.get("collector_number")
    return {
        "pool": pool,
        "family": family_code,
        "name": c.get("name") or "",
        "set": (set_code or "").upper(),
        "cn": cn,
        "rarity": c.get("rarity"),
        "finish": finish,
        "usd": usd,
        "image_uri": images.get(("sid", r.scryfall_id)),
        "scryfall_url": _scryfall_card_url(set_code, cn),
    }


def _tile_from_functional(c, family_code: str, images: dict) -> dict:
    """Normalize a FunctionalMissingCard (functional pool) into a tile dict."""
    set_code = c.set_code
    cn = c.family_cn
    image_uri = None
    if set_code and cn:
        image_uri = images.get(("setcn", (set_code or "").lower(), cn))
    return {
        "pool": "functional",
        "family": family_code,
        "name": c.name or "",
        "set": (set_code or "").upper() if set_code else None,
        "cn": cn,
        "rarity": None,
        "finish": c.family_finish,
        "usd": c.family_usd,
        "image_uri": image_uri,
        "scryfall_url": _scryfall_card_url(set_code, cn),
    }


def _fetch_images(sids: set[str], setcns: set[tuple[str, str]]) -> dict:
    """ONE batched lookup of image_uri, keyed by both access patterns the
    tiles need: ("sid", scryfall_id) for printing/variant-chase rows, and
    ("setcn", set_code_lower, collector_number) for functional cards (which
    carry no scryfall_id of their own)."""
    images: dict = {}
    if not sids and not setcns:
        return images
    with db.connect() as conn:
        if sids:
            placeholders = ",".join("?" for _ in sids)
            rows = conn.execute(
                f"SELECT scryfall_id, image_uri FROM cards WHERE scryfall_id IN ({placeholders})",
                list(sids),
            ).fetchall()
            for row in rows:
                images[("sid", row["scryfall_id"])] = row["image_uri"]
        if setcns:
            placeholders = ",".join("(?,?)" for _ in setcns)
            params = [p for pair in setcns for p in pair]
            rows = conn.execute(
                "SELECT set_code, collector_number, image_uri FROM cards "
                f"WHERE (LOWER(set_code), collector_number) IN ({placeholders})",
                params,
            ).fetchall()
            for row in rows:
                images[("setcn", (row["set_code"] or "").lower(), row["collector_number"])] = row["image_uri"]
    return images


def _tile_sort_key(t: dict) -> tuple:
    """Deterministic within-pool order: value desc, then set/cn."""
    usd = t["usd"] if t["usd"] is not None else -1.0
    return (-usd, t["set"] or "", util.cn_sort_key(t["cn"]))


def build_tiles(diffs: list, pools: list[str]) -> list[dict]:
    """Flatten every requested pool of every FamilyDiff into tile dicts,
    deterministically sorted (family order from `diffs`, pool order from
    `pools`, within-pool by value desc then set/cn)."""
    # Pre-pass: collect every id this run needs images for, ONE query.
    sids: set[str] = set()
    setcns: set[tuple[str, str]] = set()
    for fd in diffs:
        if "printing" in pools:
            sids |= {r.scryfall_id for r in fd.printing.rows}
        if "variant-chase" in pools:
            sids |= {r.scryfall_id for r in fd.variant_chase.rows}
        if "functional" in pools:
            setcns |= {
                (c.set_code.lower(), c.family_cn)
                for c in fd.functional.rows if c.set_code and c.family_cn
            }
    images = _fetch_images(sids, setcns)

    tiles: list[dict] = []
    for fd in diffs:
        if "printing" in pools:
            pool_tiles = [_tile_from_materialized(r, "printing", fd.code, images) for r in fd.printing.rows]
            pool_tiles.sort(key=_tile_sort_key)
            tiles.extend(pool_tiles)
        if "functional" in pools:
            pool_tiles = [_tile_from_functional(c, fd.code, images) for c in fd.functional.rows]
            pool_tiles.sort(key=_tile_sort_key)
            tiles.extend(pool_tiles)
        if "variant-chase" in pools:
            pool_tiles = [_tile_from_materialized(r, "variant-chase", fd.code, images) for r in fd.variant_chase.rows]
            pool_tiles.sort(key=_tile_sort_key)
            tiles.extend(pool_tiles)
    return tiles


# ---------- HTML rendering ----------

_STYLE = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0; background: #15171c; color: #e6e6e6;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}
header {
  position: sticky; top: 0; z-index: 10; background: #1d2026;
  border-bottom: 1px solid #333; padding: 10px 16px;
}
header h1 { font-size: 15px; margin: 0 0 8px; font-weight: 600; color: #ddd; }
.controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.chip-group { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  display: inline-block; padding: 3px 10px; border-radius: 12px; cursor: pointer;
  border: 1px solid #444; background: #262a33; color: #ccc; font-size: 12px;
  user-select: none;
}
.chip.active { background: #3a5fa0; border-color: #4a7fd6; color: #fff; }
.chip.pool-functional.active { background: #8a4420; border-color: #c25b2a; }
.chip.pool-variant-chase.active { background: #2d6b4a; border-color: #3a9c6b; }
input#search {
  background: #262a33; border: 1px solid #444; color: #eee; border-radius: 6px;
  padding: 4px 8px; font-size: 12px; width: 220px;
}
select#sort {
  background: #262a33; border: 1px solid #444; color: #eee; border-radius: 6px;
  padding: 4px 6px; font-size: 12px;
}
.summary { font-size: 11px; color: #999; margin-left: auto; }
main { padding: 16px; }
.family-section { margin-bottom: 28px; }
.family-header {
  font-size: 14px; font-weight: 600; color: #f0f0f0; margin-bottom: 4px;
  padding-bottom: 4px; border-bottom: 1px solid #333;
}
.family-header .sub { font-weight: 400; color: #999; font-size: 12px; margin-left: 8px; }
.grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}
.tile {
  background: #1d2026; border: 1px solid #2d313a; border-radius: 8px;
  overflow: hidden; display: flex; flex-direction: column;
}
.tile a.imglink { display: block; position: relative; }
.tile img { width: 100%; display: block; aspect-ratio: 5 / 7; object-fit: cover; background: #0d0e10; }
.tile .noimg {
  width: 100%; aspect-ratio: 5 / 7; background: #0d0e10; display: flex;
  align-items: center; justify-content: center; color: #666; font-size: 11px;
  text-align: center; padding: 6px;
}
.badge {
  position: absolute; top: 4px; left: 4px; font-size: 9px; padding: 1px 6px;
  border-radius: 8px; color: #fff; opacity: 0.9;
}
.badge.printing { background: #4a7fd6; }
.badge.functional { background: #c25b2a; }
.badge.variant-chase { background: #3a9c6b; }
.caption { padding: 6px 8px; font-size: 11px; line-height: 1.4; }
.caption .name { font-weight: 600; color: #eee; display: block; }
.caption .meta { color: #999; }
.caption .usd { color: #8fd68f; float: right; }
.hidden { display: none !important; }
footer { padding: 10px 16px; color: #666; font-size: 11px; }
"""

_SCRIPT = """
function applyFilters() {
  var activeFamilies = new Set();
  document.querySelectorAll('.chip[data-family]').forEach(function (c) {
    if (c.classList.contains('active')) activeFamilies.add(c.dataset.family);
  });
  var activePools = new Set();
  document.querySelectorAll('.chip[data-pool]').forEach(function (c) {
    if (c.classList.contains('active')) activePools.add(c.dataset.pool);
  });
  var q = document.getElementById('search').value.trim().toLowerCase();

  document.querySelectorAll('.tile').forEach(function (t) {
    var famOk = activeFamilies.has(t.dataset.family);
    var poolOk = activePools.has(t.dataset.pool);
    var nameOk = !q || t.dataset.name.indexOf(q) !== -1;
    t.classList.toggle('hidden', !(famOk && poolOk && nameOk));
  });
  document.querySelectorAll('.family-section').forEach(function (sec) {
    var anyVisible = sec.querySelectorAll('.tile:not(.hidden)').length > 0;
    sec.classList.toggle('hidden', !anyVisible);
  });
}

function applySort() {
  var mode = document.getElementById('sort').value;
  document.querySelectorAll('.grid').forEach(function (grid) {
    var tiles = Array.prototype.slice.call(grid.children);
    tiles.sort(function (a, b) {
      if (mode === 'name-asc') {
        return a.dataset.name.localeCompare(b.dataset.name);
      }
      var av = parseFloat(a.dataset.usd), bv = parseFloat(b.dataset.usd);
      av = isNaN(av) ? -1 : av;
      bv = isNaN(bv) ? -1 : bv;
      return mode === 'value-asc' ? av - bv : bv - av;
    });
    tiles.forEach(function (t) { grid.appendChild(t); });
  });
}

document.querySelectorAll('.chip').forEach(function (c) {
  c.addEventListener('click', function () {
    c.classList.toggle('active');
    applyFilters();
  });
});
document.getElementById('search').addEventListener('input', applyFilters);
document.getElementById('sort').addEventListener('change', applySort);
"""


def _tile_html(t: dict) -> str:
    name = html.escape(t["name"])
    set_code = html.escape(t["set"] or "")
    cn = html.escape(str(t["cn"] or ""))
    rarity = html.escape(t["rarity"] or "") if t["rarity"] else ""
    finish = html.escape(t["finish"] or "") if t["finish"] else ""
    usd_str = util.fmt_usd(t["usd"])
    usd_attr = f"{t['usd']:.2f}" if t["usd"] is not None else ""
    pool = t["pool"]
    family = html.escape(t["family"])
    name_attr = html.escape(t["name"].lower())

    meta_bits = [b for b in (set_code, cn, rarity, finish) if b]
    meta = " · ".join(meta_bits)

    if t["image_uri"]:
        img_src = html.escape(t["image_uri"])
        if t["scryfall_url"]:
            media = (
                f'<a class="imglink" href="{html.escape(t["scryfall_url"])}" target="_blank" rel="noopener">'
                f'<img src="{img_src}" loading="lazy" alt="{name}">'
                f'<span class="badge {pool}">{POOL_LABELS[pool]}</span></a>'
            )
        else:
            media = (
                f'<span class="imglink"><img src="{img_src}" loading="lazy" alt="{name}">'
                f'<span class="badge {pool}">{POOL_LABELS[pool]}</span></span>'
            )
    else:
        text_bits = f"{name}<br>{meta}<br>{usd_str}"
        media = f'<div class="noimg">{text_bits}</div>'

    return (
        f'<div class="tile" data-family="{family}" data-pool="{pool}" '
        f'data-name="{name_attr}" data-usd="{usd_attr}">'
        f'{media}'
        f'<div class="caption"><span class="name">{name}</span>'
        f'<span class="usd">{html.escape(usd_str)}</span>'
        f'<span class="meta">{meta}</span></div>'
        f'</div>'
    )


def render_html(diffs: list, tiles_by_family: dict[str, list[dict]], pools: list[str]) -> str:
    family_chips = "".join(
        f'<span class="chip active" data-family="{html.escape(fd.code)}">{html.escape(fd.code)}</span>'
        for fd in diffs
    )
    pool_chips = "".join(
        f'<span class="chip pool-{p} active" data-pool="{p}">{POOL_LABELS[p]}</span>'
        for p in pools
    )

    sections = []
    for fd in diffs:
        tiles = tiles_by_family.get(fd.code, [])
        if not tiles:
            continue
        pool_summary = " · ".join(
            f"{POOL_LABELS[p]} {getattr(fd, p.replace('-', '_')).count}·"
            f"{util.fmt_usd(getattr(fd, p.replace('-', '_')).usd)}"
            for p in pools
        )
        header = (
            f'<div class="family-header">{html.escape(fd.code)} — {html.escape(fd.name)}'
            f'<span class="sub">owned {util.fmt_usd(fd.owned_usd)} · {pool_summary}</span></div>'
        )
        grid = "".join(_tile_html(t) for t in tiles)
        sections.append(
            f'<section class="family-section">{header}<div class="grid">{grid}</div></section>'
        )

    n_total = sum(len(v) for v in tiles_by_family.values())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Card diff gallery</title>
<style>{_STYLE}</style>
</head>
<body>
<header>
  <h1>Card diff gallery — {len(diffs)} family(ies) · {n_total} card(s) · generated {ts}</h1>
  <div class="controls">
    <div class="chip-group">{family_chips}</div>
    <div class="chip-group">{pool_chips}</div>
    <input id="search" type="text" placeholder="search card name…">
    <select id="sort">
      <option value="value-desc">Value: high→low</option>
      <option value="value-asc">Value: low→high</option>
      <option value="name-asc">Name: A→Z</option>
    </select>
    <span class="summary">click a chip to toggle · click a card to open on Scryfall</span>
  </div>
</header>
<main>
{"".join(sections)}
</main>
<footer>Images load lazily from Scryfall's CDN — requires a browser with network access to cards.scryfall.io.</footer>
<script>{_SCRIPT}</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Self-contained HTML gallery of card-diff pools, image-first.")
    ap.add_argument("codes", nargs="*",
                     help="Family anchor/member code(s). Omit for every owned+configured family.")
    ap.add_argument("--pool", choices=("printing", "functional", "variant-chase", "all"),
                     default="all", help="Which pool(s) to render (default: all).")
    args = ap.parse_args()

    pools = list(POOL_CHOICES) if args.pool == "all" else [args.pool]

    if args.codes:
        diffs = []
        for code in args.codes:
            fd = card_diff_mod.family_diff(code)
            if fd is None:
                print(f"warning: {code!r} is not a resolvable/configured family — skipped.",
                      file=sys.stderr)
                continue
            diffs.append(fd)
        if not diffs:
            print("error: none of the given codes resolved to a configured family.",
                  file=sys.stderr)
            return 2
    else:
        print("Computing collection-wide card diff (this can take a few minutes)…",
              file=sys.stderr)
        diffs = card_diff_mod.collection_diff()
        if not diffs:
            print("error: no owned+configured families found.", file=sys.stderr)
            return 2

    all_tiles = build_tiles(diffs, pools)
    tiles_by_family: dict[str, list[dict]] = {}
    for t in all_tiles:
        tiles_by_family.setdefault(t["family"], []).append(t)

    html_out = render_html(diffs, tiles_by_family, pools)

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

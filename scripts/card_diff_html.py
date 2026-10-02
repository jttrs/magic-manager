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
import html
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import (  # noqa: E402
    card_diff as card_diff_mod, db, exports, sets as sets_mod, util,
)

POOL_CHOICES = ("printing", "functional", "variant-chase")
POOL_LABELS = {"printing": "Printing", "functional": "Functional", "variant-chase": "Variant-chase"}
# Fixed display/segment order used everywhere pools are enumerated together.
POOL_ORDER = ("printing", "functional", "variant-chase")


def _scryfall_card_url(set_code: str | None, cn: str | None) -> str | None:
    if not set_code or not cn:
        return None
    return f"https://scryfall.com/card/{set_code.lower()}/{cn}"


def _tile_from_materialized(r, pool: str, family_code: str, images: dict) -> dict:
    """Normalize a MaterializedRow (printing / variant-chase pool) into a tile
    dict the renderer understands. ``pools`` starts as a one-element set; the
    caller unions further pool membership onto it during dedup."""
    c = r.card
    finish = r.finish
    unit = c.get("prices_usd_foil") if finish == "foil" else c.get("prices_usd")
    usd = (unit * r.quantity) if unit is not None else None
    set_code = c.get("set")
    cn = c.get("collector_number")
    return {
        "sid_key": ("sid", r.scryfall_id),
        "pools": {pool},
        "family": family_code,
        "name": c.get("name") or "",
        "set": (set_code or "").upper(),
        "cn": cn,
        "rarity": c.get("rarity"),
        "finish": finish,
        "usd": usd,
        "image_uri": images.get(("sid", r.scryfall_id)),
        "scryfall_url": _scryfall_card_url(set_code, cn),
        "row": r,  # source MaterializedRow — for exports.build (buy-list lines)
    }


class _ExportRow:
    """Minimal MaterializedRow stand-in so a FunctionalMissingCard can feed
    ``exports.build`` (which reads ``.card`` / ``.finish`` / ``.quantity``). The
    functional pool's representative printing is the cheapest in-family one; its
    full ``cards``-table row is fetched once in ``build_tiles`` and attached here
    so the TCGplayer formatter (treatment suffix + collision prefix) has the
    fields it needs — same as a printing-pool row."""
    __slots__ = ("card", "finish", "quantity", "scryfall_id")

    def __init__(self, card: dict, finish: str):
        self.card = card
        self.finish = finish or "nonfoil"
        self.quantity = 1
        self.scryfall_id = card.get("scryfall_id")


def _tile_from_functional(c, family_code: str, images: dict) -> dict:
    """Normalize a FunctionalMissingCard (functional pool) into a tile dict.
    Functional cards carry no scryfall_id of their own; the caller resolves
    one via (set_code, family_cn) so this tile can merge with a printing/
    variant-chase tile of the same underlying printing."""
    set_code = c.set_code
    cn = c.family_cn
    image_uri = None
    sid = None
    card_dict = None
    if set_code and cn:
        setcn_key = (set_code.lower(), cn)
        image_uri = images.get(("setcn-img", setcn_key))
        sid = images.get(("setcn-sid", setcn_key))
        card_dict = images.get(("setcn-card", setcn_key))
    sid_key = ("sid", sid) if sid else ("fn", set_code or "", cn or "")
    # Row for exports.build (buy-list lines); None when the printing has no local
    # cards row (shouldn't happen — functional reps come from cards — but guard).
    row = _ExportRow(card_dict, c.family_finish) if card_dict else None
    return {
        "sid_key": sid_key,
        "pools": {"functional"},
        "family": family_code,
        "name": c.name or "",
        "set": (set_code or "").upper() if set_code else None,
        "cn": cn,
        "rarity": None,
        "finish": c.family_finish,
        "usd": c.family_usd,
        "image_uri": image_uri,
        "scryfall_url": _scryfall_card_url(set_code, cn),
        "row": row,
    }


def _fetch_images(sids: set[str], setcns: set[tuple[str, str]]) -> dict:
    """ONE batched lookup of image_uri + scryfall_id, keyed by both access
    patterns the tiles need: ("sid", scryfall_id) for printing/variant-chase
    rows' image_uri; ("setcn-img", (set_code_lower, cn)) and
    ("setcn-sid", (set_code_lower, cn)) for functional cards (which carry no
    scryfall_id of their own but need both their image AND their scryfall_id
    so they can be deduped against a printing/variant-chase tile of the same
    printing)."""
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
                "SELECT scryfall_id, oracle_id, name, set_code, collector_number, "
                "rarity, prices_usd, prices_usd_foil, type_line, promo_types, "
                "frame_effects, border_color, full_art, finishes, image_uri "
                f"FROM cards WHERE (LOWER(set_code), collector_number) IN ({placeholders})",
                params,
            ).fetchall()
            for row in rows:
                key = ((row["set_code"] or "").lower(), row["collector_number"])
                images[("setcn-img", key)] = row["image_uri"]
                images[("setcn-sid", key)] = row["scryfall_id"]
                # Full card dict (set=lower, mirroring selectors' _card_dict) so a
                # functional tile can build a proper exports row for the buy-list.
                images[("setcn-card", key)] = {
                    "scryfall_id": row["scryfall_id"], "oracle_id": row["oracle_id"],
                    "name": row["name"], "set": (row["set_code"] or "").lower(),
                    "collector_number": row["collector_number"], "rarity": row["rarity"],
                    "prices_usd": row["prices_usd"], "prices_usd_foil": row["prices_usd_foil"],
                    "type_line": row["type_line"], "promo_types": row["promo_types"],
                    "frame_effects": row["frame_effects"], "border_color": row["border_color"],
                    "full_art": row["full_art"], "finishes": row["finishes"],
                }
    return images


def _tile_sort_key(t: dict) -> tuple:
    """Deterministic within-family order: value desc, then set/cn."""
    usd = t["usd"] if t["usd"] is not None else -1.0
    return (-usd, t["set"] or "", util.cn_sort_key(t["cn"]))


def build_tiles(diffs: list, pools: list[str]) -> list[dict]:
    """Flatten every requested pool of every FamilyDiff into UNIQUE-printing
    tile dicts: one tile per distinct scryfall_id per family, each carrying
    the SET of pools it belongs to (deduped — a printing in both the
    printing and variant-chase pools renders ONCE with both pools unioned
    onto it). Deterministic order: family order from `diffs`, within-family
    by value desc then set/cn."""
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
        by_sid: dict = {}

        def _merge(new_tile: dict) -> None:
            key = new_tile["sid_key"]
            existing = by_sid.get(key)
            if existing is None:
                by_sid[key] = new_tile
                return
            existing["pools"] |= new_tile["pools"]
            if existing.get("rarity") is None and new_tile.get("rarity") is not None:
                existing["rarity"] = new_tile["rarity"]
            # Prefer a source row that exists (functional tiles may lack one if the
            # printing isn't local); keep whichever has it for the buy-list export.
            if existing.get("row") is None and new_tile.get("row") is not None:
                existing["row"] = new_tile["row"]

        if "printing" in pools:
            for r in fd.printing.rows:
                _merge(_tile_from_materialized(r, "printing", fd.code, images))
        if "functional" in pools:
            for c in fd.functional.rows:
                _merge(_tile_from_functional(c, fd.code, images))
        if "variant-chase" in pools:
            for r in fd.variant_chase.rows:
                _merge(_tile_from_materialized(r, "variant-chase", fd.code, images))

        family_tiles = list(by_sid.values())
        family_tiles.sort(key=_tile_sort_key)
        tiles.extend(family_tiles)
    return tiles


# ---------- HTML rendering ----------

_STYLE = """
:root {
  color-scheme: dark;
  --bg: oklch(0.18 0.008 60);
  --card: oklch(0.22 0.008 60);
  --ink: oklch(0.92 0.008 85);
  --muted-fg: oklch(0.74 0.010 85);
  --border: oklch(1 0.005 85 / 14%);
  --rule-strong: oklch(1 0.005 85 / 24%);
  --sidebar: oklch(0.22 0.008 60);
  --accent: oklch(0.78 0.11 145);
  --accent-soft: oklch(0.30 0.05 145);
  --accent-soft-fg: oklch(0.92 0.06 145);
  --info: oklch(0.72 0.09 250);
  --warning: oklch(0.80 0.13 72);
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0; background: var(--bg); color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}
.layout { display: flex; min-height: 100vh; }
.rail-wrap {
  width: 16rem; flex: 0 0 16rem; transition: width 180ms ease, flex-basis 180ms ease;
  position: relative;
}
.rail-wrap.collapsed { width: 0; flex: 0 0 0; overflow: hidden; }
aside.rail {
  width: 16rem; height: 100%; background: var(--sidebar); border-right: 1px solid var(--border);
  padding: 14px 12px; overflow-y: auto; box-sizing: border-box;
}
.rail-wrap.collapsed aside.rail { opacity: 0; }
.rail-section { padding: 10px 2px; border-bottom: 1px solid var(--rule-strong); }
.rail-section:last-child { border-bottom: none; }
.eyebrow {
  text-transform: uppercase; letter-spacing: .18em; font-size: .72rem;
  color: var(--muted-fg); font-family: ui-monospace, monospace; margin: 0 0 8px;
}
.rail-links { display: flex; gap: 10px; margin-bottom: 6px; font-size: 11px; }
.rail-links a {
  color: var(--accent); cursor: pointer; text-decoration: none;
}
.rail-links a.disabled { color: var(--muted-fg); cursor: default; pointer-events: none; opacity: .5; }
.rail-list { display: flex; flex-direction: column; gap: 2px; }
.rail-list.scroll { max-height: 46vh; overflow-y: auto; }
.rail-row {
  display: flex; align-items: center; gap: 8px; padding: 3px 4px; border-radius: 5px;
  font-size: 12px; cursor: pointer;
}
.rail-row:hover { background: var(--accent-soft); color: var(--accent-soft-fg); }
.rail-row input[type="checkbox"] { accent-color: var(--accent); }
.rail-row .swatch { width: 10px; height: 10px; border-radius: 2px; flex: 0 0 auto; }
.rail-row .fam-code { font-weight: 600; }
.rail-row .fam-name { color: var(--muted-fg); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rail-row .fam-count { color: var(--muted-fg); font-size: 11px; }
.rail-section input#search {
  width: 100%; background: var(--card); border: 1px solid var(--border); color: var(--ink);
  border-radius: 6px; padding: 5px 8px; font-size: 12px;
}
.rail-section select#sort {
  width: 100%; background: var(--card); border: 1px solid var(--border); color: var(--ink);
  border-radius: 6px; padding: 5px 6px; font-size: 12px;
}
.export-btn {
  display: block; width: 100%; margin-bottom: 6px; cursor: pointer;
  background: var(--accent-soft); color: var(--accent-soft-fg);
  border: 1px solid var(--accent); border-radius: 6px; padding: 6px 8px; font-size: 12px;
}
.export-btn:hover { background: var(--accent); color: var(--bg); }
.copy-status { display: block; font-size: 11px; color: var(--muted-fg); min-height: 14px; }
.reopen-tab {
  position: fixed; left: 0; top: 12px; z-index: 20; background: var(--sidebar);
  border: 1px solid var(--border); border-left: none; border-radius: 0 6px 6px 0;
  color: var(--muted-fg); padding: 6px 5px; cursor: pointer; font-size: 13px; display: none;
}
.rail-wrap.collapsed ~ .reopen-tab, body.rail-collapsed .reopen-tab { display: block; }
main { flex: 1; min-width: 0; overflow-y: auto; }
.topstrip {
  position: sticky; top: 0; z-index: 10; background: var(--card);
  border-bottom: 1px solid var(--border); padding: 10px 16px;
  display: flex; align-items: center; gap: 12px;
}
.topstrip h1 { font-size: 15px; margin: 0; font-weight: 600; color: var(--ink); }
.topstrip .hint { font-size: 11px; color: var(--muted-fg); margin-left: auto; }
.rail-toggle {
  background: var(--card); border: 1px solid var(--border); color: var(--ink);
  border-radius: 6px; padding: 4px 8px; font-size: 12px; cursor: pointer;
}
.content { padding: 16px; }
.family-section { margin-bottom: 28px; }
.family-header {
  font-size: 14px; font-weight: 600; color: var(--ink); margin-bottom: 4px;
  padding-bottom: 4px; border-bottom: 1px solid var(--rule-strong);
}
.family-header .sub { font-weight: 400; color: var(--muted-fg); font-size: 12px; margin-left: 8px; }
.grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}
.tile {
  background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  overflow: hidden; display: flex; flex-direction: column;
}
.tile a.imglink { display: block; position: relative; }
.tile img { width: 100%; display: block; aspect-ratio: 5 / 7; object-fit: cover; background: oklch(0.14 0.006 60); }
.tile .noimg {
  width: 100%; aspect-ratio: 5 / 7; background: oklch(0.14 0.006 60); display: flex;
  align-items: center; justify-content: center; color: var(--muted-fg); font-size: 11px;
  text-align: center; padding: 6px;
}
.poolbar { display: flex; height: 4px; }
.seg { flex: 1; }
.seg.printing { background: var(--info); }
.seg.functional { background: var(--warning); }
.seg.variant-chase { background: var(--accent); }
.caption { padding: 6px 8px; font-size: 11px; line-height: 1.4; }
.caption .name { font-weight: 600; color: var(--ink); display: block; }
.caption .meta { color: var(--muted-fg); }
.caption .pools { color: var(--muted-fg); display: block; }
.caption .usd { color: var(--accent); float: right; }
.hidden { display: none !important; }
footer { padding: 10px 16px; color: var(--muted-fg); font-size: 11px; }
"""

_SCRIPT = """
function syncGroupLinks(groupSel, selAllSel, clrAllSel) {
  var boxes = document.querySelectorAll(groupSel);
  var checked = Array.prototype.filter.call(boxes, function (b) { return b.checked; });
  var selAll = document.querySelector(selAllSel);
  var clrAll = document.querySelector(clrAllSel);
  if (selAll) selAll.classList.toggle('disabled', checked.length === boxes.length);
  if (clrAll) clrAll.classList.toggle('disabled', checked.length === 0);
}

function wireGroup(groupSel, selAllSel, clrAllSel) {
  var boxes = document.querySelectorAll(groupSel);
  boxes.forEach(function (b) {
    b.addEventListener('change', function () {
      syncGroupLinks(groupSel, selAllSel, clrAllSel);
      applyFilters();
    });
  });
  var selAll = document.querySelector(selAllSel);
  var clrAll = document.querySelector(clrAllSel);
  if (selAll) {
    selAll.addEventListener('click', function (e) {
      e.preventDefault();
      boxes.forEach(function (b) { b.checked = true; });
      syncGroupLinks(groupSel, selAllSel, clrAllSel);
      applyFilters();
    });
  }
  if (clrAll) {
    clrAll.addEventListener('click', function (e) {
      e.preventDefault();
      boxes.forEach(function (b) { b.checked = false; });
      syncGroupLinks(groupSel, selAllSel, clrAllSel);
      applyFilters();
    });
  }
  syncGroupLinks(groupSel, selAllSel, clrAllSel);
}

function applyFilters() {
  var activeFamilies = new Set();
  document.querySelectorAll('.rail-row input[data-family]:checked').forEach(function (c) {
    activeFamilies.add(c.dataset.family);
  });
  var activePools = new Set();
  document.querySelectorAll('.rail-row input[data-pool]:checked').forEach(function (c) {
    activePools.add(c.dataset.pool);
  });
  var q = document.getElementById('search').value.trim().toLowerCase();

  document.querySelectorAll('.tile').forEach(function (t) {
    var famOk = activeFamilies.has(t.dataset.family);
    var tilePools = t.dataset.pools.split(' ');
    var poolOk = tilePools.some(function (p) { return activePools.has(p); });
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
      if (mode === 'cn-asc') {
        var setCmp = a.dataset.set.localeCompare(b.dataset.set);
        if (setCmp !== 0) return setCmp;
        var acn = parseInt(a.dataset.cn, 10), bcn = parseInt(b.dataset.cn, 10);
        var aNan = isNaN(acn), bNan = isNaN(bcn);
        if (aNan && bNan) return a.dataset.cn.localeCompare(b.dataset.cn);
        if (aNan) return 1;
        if (bNan) return -1;
        return acn - bcn;
      }
      var av = parseFloat(a.dataset.usd), bv = parseFloat(b.dataset.usd);
      av = isNaN(av) ? -1 : av;
      bv = isNaN(bv) ? -1 : bv;
      return mode === 'value-asc' ? av - bv : bv - av;
    });
    tiles.forEach(function (t) { grid.appendChild(t); });
  });
}

wireGroup('.rail-row input[data-pool]', '[data-select-all="pool"]', '[data-clear-all="pool"]');
wireGroup('.rail-row input[data-family]', '[data-select-all="family"]', '[data-clear-all="family"]');
document.getElementById('search').addEventListener('input', applyFilters);
document.getElementById('sort').addEventListener('change', applySort);

var railWrap = document.getElementById('rail-wrap');
var railToggle = document.getElementById('rail-toggle');
var reopenTab = document.getElementById('reopen-tab');
function setRailCollapsed(collapsed) {
  railWrap.classList.toggle('collapsed', collapsed);
  document.body.classList.toggle('rail-collapsed', collapsed);
}
if (railToggle) railToggle.addEventListener('click', function () { setRailCollapsed(true); });
if (reopenTab) reopenTab.addEventListener('click', function () { setRailCollapsed(false); });

// --- Export the currently-displayed tiles as a paste-ready buy-list ---
function collectLines(attr) {
  var lines = [];
  document.querySelectorAll('.tile:not(.hidden)').forEach(function (t) {
    var v = t.getAttribute(attr);
    if (v) lines.push(v);
  });
  return lines;
}
function copyText(text, done) {
  // navigator.clipboard needs a secure context (fails on file://); fall back to
  // a hidden textarea + execCommand, which works when the page is opened locally.
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function () { done(true); },
                                              function () { done(fallbackCopy(text)); });
  } else {
    done(fallbackCopy(text));
  }
}
function fallbackCopy(text) {
  try {
    var ta = document.createElement('textarea');
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.focus(); ta.select();
    var ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch (e) { return false; }
}
function wireExport(btnId, attr, label) {
  var btn = document.getElementById(btnId);
  var status = document.getElementById('copy-status');
  if (!btn) return;
  btn.addEventListener('click', function () {
    var lines = collectLines(attr);
    if (!lines.length) { status.textContent = 'Nothing to copy.'; return; }
    copyText(lines.join('\\n') + '\\n', function (ok) {
      status.textContent = ok ? ('Copied ' + lines.length + ' ' + label + ' lines.')
                              : 'Copy failed — select & copy manually.';
    });
  });
}
wireExport('copy-mp', 'data-mp', 'ManaPool');
wireExport('copy-tcg', 'data-tcg', 'TCGplayer');
"""


def _tile_html(t: dict) -> str:
    name = html.escape(t["name"])
    set_code = html.escape(t["set"] or "")
    cn = html.escape(str(t["cn"] or ""))
    rarity = html.escape(t["rarity"] or "") if t["rarity"] else ""
    finish = html.escape(t["finish"] or "") if t["finish"] else ""
    usd_str = util.fmt_usd(t["usd"])
    usd_attr = f"{t['usd']:.2f}" if t["usd"] is not None else ""
    pools_sorted = [p for p in POOL_ORDER if p in t["pools"]]
    pools_attr = html.escape(" ".join(pools_sorted))
    family = html.escape(t["family"])
    name_attr = html.escape(t["name"].lower())
    set_attr = html.escape(t["set"] or "")
    cn_attr = html.escape(str(t["cn"] or ""))

    meta_bits = [b for b in (set_code, cn, rarity, finish) if b]
    meta = " · ".join(meta_bits)
    pools_label = " · ".join(POOL_LABELS[p] for p in pools_sorted)

    # Pre-render the canonical ManaPool + TCGplayer buy-list lines for this tile
    # (via the ONE exports engine — the TCGplayer formatter needs full-row context
    # the DOM lacks: treatment-suffix product names + collision (NNNN) prefixes).
    # The JS "copy buy-list" button collects these from the visible tiles. A tile
    # with no source row (rare: no local printing) carries empty attrs → skipped.
    row = t.get("row")
    mp_line = tcg_line = ""
    if row is not None:
        mp_line = exports.build("manapool", [row]).strip()
        tcg_line = exports.build("tcgplayer", [row]).strip()
    mp_attr = html.escape(mp_line)
    tcg_attr = html.escape(tcg_line)

    poolbar = "".join(f'<span class="seg {p}"></span>' for p in pools_sorted)
    poolbar_html = f'<div class="poolbar">{poolbar}</div>'

    if t["image_uri"]:
        img_src = html.escape(t["image_uri"])
        if t["scryfall_url"]:
            media = (
                f'<a class="imglink" href="{html.escape(t["scryfall_url"])}" target="_blank" rel="noopener">'
                f'<img src="{img_src}" loading="lazy" alt="{name}"></a>'
            )
        else:
            media = f'<span class="imglink"><img src="{img_src}" loading="lazy" alt="{name}"></span>'
    else:
        text_bits = f"{name}<br>{meta}<br>{usd_str}"
        media = f'<div class="noimg">{text_bits}</div>'

    return (
        f'<div class="tile" data-family="{family}" data-pools="{pools_attr}" '
        f'data-name="{name_attr}" data-usd="{usd_attr}" data-set="{set_attr}" data-cn="{cn_attr}" '
        f'data-mp="{mp_attr}" data-tcg="{tcg_attr}">'
        f'{media}'
        f'{poolbar_html}'
        f'<div class="caption"><span class="name">{name}</span>'
        f'<span class="usd">{html.escape(usd_str)}</span>'
        f'<span class="meta">{meta}</span>'
        f'<span class="pools">{html.escape(pools_label)}</span></div>'
        f'</div>'
    )


def render_html(diffs: list, tiles_by_family: dict[str, list[dict]], pools: list[str]) -> str:
    family_rows = "".join(
        f'<label class="rail-row"><input type="checkbox" checked data-family="{html.escape(fd.code)}">'
        f'<span class="fam-code">{html.escape(fd.code)}</span>'
        f'<span class="fam-name">{html.escape(fd.name)}</span>'
        f'<span class="fam-count">{len(tiles_by_family.get(fd.code, []))}</span></label>'
        for fd in diffs
    )
    pool_rows = "".join(
        f'<label class="rail-row"><input type="checkbox" checked data-pool="{p}">'
        f'<span class="swatch" style="background: var(--{"info" if p == "printing" else "warning" if p == "functional" else "accent"})"></span>'
        f'<span class="fam-name">{POOL_LABELS[p]}</span></label>'
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
<div class="layout">
  <div class="rail-wrap" id="rail-wrap">
    <aside class="rail">
      <div class="rail-section">
        <p class="eyebrow">Pool</p>
        <div class="rail-links">
          <a data-select-all="pool">Select All</a>
          <a data-clear-all="pool">Clear All</a>
        </div>
        <div class="rail-list">{pool_rows}</div>
      </div>
      <div class="rail-section">
        <p class="eyebrow">Family</p>
        <div class="rail-links">
          <a data-select-all="family">Select All</a>
          <a data-clear-all="family">Clear All</a>
        </div>
        <div class="rail-list scroll">{family_rows}</div>
      </div>
      <div class="rail-section">
        <p class="eyebrow">Search</p>
        <input id="search" type="text" placeholder="search card name…">
      </div>
      <div class="rail-section">
        <p class="eyebrow">Sort</p>
        <select id="sort">
          <option value="value-desc">Value: high→low</option>
          <option value="value-asc">Value: low→high</option>
          <option value="name-asc">Name: A→Z</option>
          <option value="cn-asc">Collector no.: low→high</option>
        </select>
      </div>
      <div class="rail-section">
        <p class="eyebrow">Export (shown)</p>
        <button class="export-btn" id="copy-mp">Copy ManaPool list</button>
        <button class="export-btn" id="copy-tcg">Copy TCGplayer list</button>
        <span id="copy-status" class="copy-status"></span>
      </div>
    </aside>
  </div>
  <button class="reopen-tab" id="reopen-tab" aria-label="Show filters" title="Show filters">&#9661;</button>
  <main>
    <div class="topstrip">
      <button class="rail-toggle" id="rail-toggle" aria-label="Hide filters">&#9661; Filters</button>
      <h1>Card diff gallery — {len(diffs)} family(ies) · {n_total} card(s) · generated {ts}</h1>
      <span class="hint">click a card to open on Scryfall</span>
    </div>
    <div class="content">
{"".join(sections)}
    </div>
  </main>
</div>
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

"""Generic, image-first HTML gallery renderer (no server, self-contained).

A Scryfall-style image grid with a collapsible left sidebar: filter by a
single-valued **section** dimension (checkbox list) AND a multi-valued **pool**
dimension (colored chips + a segmented underline bar per tile), a name search
box, a sort control, and optional "copy the shown tiles as a list" export
buttons. Card images lazy-load from Scryfall's CDN at browser render time.

This is the shared engine behind two callers:

  * ``scripts/card_diff_html.py`` — the three card-diff pools (printing /
    functional / variant-chase) grouped by set family; export = ManaPool /
    TCGplayer buy-lists.
  * ``scripts/edhrec_report.py compare`` — two commanders' recommended cards,
    sectioned by A-only / Both / B-only, pools = EDHREC category tags.

The renderer is parameterized by:
  * ``pools: list[PoolSpec]`` — the pool keys, labels, and CSS color vars
    (segment/chip color comes from ``PoolSpec.color_var`` via inline style, so
    there are no per-pool CSS rules to edit).
  * ``sections: list[GallerySection]`` — the section dimension; each carries a
    precomputed ``summary`` string so the renderer never reaches into a
    caller's domain objects.
  * ``extra_sorts`` — extra numeric sort options (``data-sort-<key>`` on tiles).
  * ``exports`` — extra "copy shown" buttons (``data-<attr>`` on tiles).

Tile dict contract (built by the caller):
    {
      "sid_key": hashable,          # dedup key within a section
      "pools": set[str],            # pool keys this tile belongs to
      "family": str,                # section code
      "name": str,
      "set": str | None,            # UPPER
      "cn": str | None,
      "rarity": str | None,
      "finish": str | None,
      "usd": float | None,
      "image_uri": str | None,
      "scryfall_url": str | None,
      # optional:
      "badge": str | None,          # extra caption line (e.g. "A 61% · B 12%")
      "sort_values": dict[str, float],   # → data-sort-<key> (numeric sorts)
      "data_attrs": dict[str, str],      # → data-<key> (export line payloads)
      "row": object | None,         # opaque; preserved on merge (caller's use)
    }
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field

from magic_manager import util


@dataclass(frozen=True)
class PoolSpec:
    """One pool/chip dimension value: its key, display label, and the CSS
    custom-property name (sans ``--``) used for its chip + segment color."""
    key: str
    label: str
    color_var: str


@dataclass
class GallerySection:
    """One section (the single-valued grouping dimension). ``summary`` is a
    caller-precomputed sub-header string so the renderer stays domain-agnostic."""
    code: str
    name: str
    summary: str = ""


@dataclass(frozen=True)
class ExportSpec:
    """A sidebar "copy the shown tiles" button: ``button_id`` wires to the
    ``data-<attr>`` the tiles carry, ``label`` names the format in status text."""
    button_id: str
    label: str
    attr: str


@dataclass(frozen=True)
class SortSpec:
    """An extra numeric sort option. ``value`` is the <option> value (routed to
    the generic ``num:<key>`` JS branch), ``label`` the display text, ``key`` the
    ``data-sort-<key>`` attribute to read (descending)."""
    label: str
    key: str


def scryfall_card_url(set_code: str | None, cn: str | None) -> str | None:
    if not set_code or not cn:
        return None
    return f"https://scryfall.com/card/{set_code.lower()}/{cn}"


def tile_sort_key(t: dict) -> tuple:
    """Deterministic within-section order: value desc, then set/cn."""
    usd = t["usd"] if t["usd"] is not None else -1.0
    return (-usd, t["set"] or "", util.cn_sort_key(t["cn"]))


def merge_tiles(tiles: list[dict]) -> list[dict]:
    """Dedupe a (section-scoped) tile list by ``sid_key``, unioning pool
    membership and preferring the first non-null ``rarity`` / ``row`` / ``badge``.
    ``data_attrs`` and ``sort_values`` of the first-seen tile win. Preserves
    first-seen order (the caller sorts afterwards via ``tile_sort_key``)."""
    by_key: dict = {}
    for t in tiles:
        key = t["sid_key"]
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = t
            continue
        existing["pools"] |= t["pools"]
        if existing.get("rarity") is None and t.get("rarity") is not None:
            existing["rarity"] = t["rarity"]
        if existing.get("row") is None and t.get("row") is not None:
            existing["row"] = t["row"]
        if not existing.get("badge") and t.get("badge"):
            existing["badge"] = t["badge"]
    return list(by_key.values())


# ---------- styling + behavior (static; pool colors are inline, data-driven) ----------

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
  /* Extra palette for callers with more than three pools (e.g. EDHREC tags). */
  --p1: oklch(0.72 0.09 250);
  --p2: oklch(0.80 0.13 72);
  --p3: oklch(0.78 0.11 145);
  --p4: oklch(0.72 0.13 20);
  --p5: oklch(0.74 0.12 320);
  --p6: oklch(0.78 0.11 190);
  --p7: oklch(0.80 0.12 110);
  --p8: oklch(0.72 0.10 285);
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
.caption { padding: 6px 8px; font-size: 11px; line-height: 1.4; }
.caption .name { font-weight: 600; color: var(--ink); display: block; }
.caption .meta { color: var(--muted-fg); }
.caption .badge { color: var(--accent-soft-fg); display: block; font-weight: 600; }
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
      if (mode.indexOf('num:') === 0) {
        var key = 'data-sort-' + mode.slice(4);
        var ax = parseFloat(a.getAttribute(key)), bx = parseFloat(b.getAttribute(key));
        ax = isNaN(ax) ? -1 : ax;
        bx = isNaN(bx) ? -1 : bx;
        return bx - ax;  // numeric sorts are descending (highest first)
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

// --- Export the currently-displayed tiles as a paste-ready list ---
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
"""


# ---------- rendering ----------

def _tile_html(t: dict, pools: list[PoolSpec]) -> str:
    label_by_key = {p.key: p.label for p in pools}
    color_by_key = {p.key: p.color_var for p in pools}
    order = [p.key for p in pools]

    name = html.escape(t["name"])
    set_code = html.escape(t["set"] or "")
    cn = html.escape(str(t["cn"] or ""))
    rarity = html.escape(t["rarity"] or "") if t["rarity"] else ""
    finish = html.escape(t["finish"] or "") if t["finish"] else ""
    usd_str = util.fmt_usd(t["usd"])
    usd_attr = f"{t['usd']:.2f}" if t["usd"] is not None else ""
    pools_sorted = [k for k in order if k in t["pools"]]
    pools_attr = html.escape(" ".join(pools_sorted))
    family = html.escape(t["family"])
    name_attr = html.escape(t["name"].lower())
    set_attr = html.escape(t["set"] or "")
    cn_attr = html.escape(str(t["cn"] or ""))

    meta_bits = [b for b in (set_code, cn, rarity, finish) if b]
    meta = " · ".join(meta_bits)
    pools_label = " · ".join(label_by_key.get(k, k) for k in pools_sorted)

    # Optional extra data-* attributes: numeric sort keys + export line payloads.
    extra_attrs = []
    for k, v in (t.get("sort_values") or {}).items():
        av = f"{v:.4f}" if v is not None else ""
        extra_attrs.append(f'data-sort-{html.escape(k)}="{html.escape(av)}"')
    for k, v in (t.get("data_attrs") or {}).items():
        extra_attrs.append(f'data-{html.escape(k)}="{html.escape(v or "")}"')
    extra_attr_str = (" " + " ".join(extra_attrs)) if extra_attrs else ""

    poolbar = "".join(
        f'<span class="seg" style="background: var(--{color_by_key.get(k, "accent")})"></span>'
        for k in pools_sorted
    )
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

    badge_html = (
        f'<span class="badge">{html.escape(t["badge"])}</span>' if t.get("badge") else ""
    )

    return (
        f'<div class="tile" data-family="{family}" data-pools="{pools_attr}" '
        f'data-name="{name_attr}" data-usd="{usd_attr}" data-set="{set_attr}" data-cn="{cn_attr}"'
        f'{extra_attr_str}>'
        f'{media}'
        f'{poolbar_html}'
        f'<div class="caption"><span class="name">{name}</span>'
        f'<span class="usd">{html.escape(usd_str)}</span>'
        f'{badge_html}'
        f'<span class="meta">{meta}</span>'
        f'<span class="pools">{html.escape(pools_label)}</span></div>'
        f'</div>'
    )


def render_gallery(
    sections: list[GallerySection],
    tiles_by_section: dict[str, list[dict]],
    pools: list[PoolSpec],
    *,
    title: str,
    hint: str = "click a card to open on Scryfall",
    group_label: str = "Family",
    pool_label: str = "Pool",
    extra_sorts: list[SortSpec] = (),
    exports: list[ExportSpec] = (),
    generated: str = "",
) -> str:
    """Render a complete self-contained gallery HTML document.

    ``sections`` drives the section checkbox list + the per-section grids (in
    order; empty sections are dropped). ``pools`` drives the pool chips and each
    tile's segment colors. ``extra_sorts`` append numeric sort options,
    ``exports`` append "copy the shown tiles" buttons.
    """
    section_rows = "".join(
        f'<label class="rail-row"><input type="checkbox" checked data-family="{html.escape(s.code)}">'
        f'<span class="fam-code">{html.escape(s.code)}</span>'
        f'<span class="fam-name">{html.escape(s.name)}</span>'
        f'<span class="fam-count">{len(tiles_by_section.get(s.code, []))}</span></label>'
        for s in sections
    )
    pool_rows = "".join(
        f'<label class="rail-row"><input type="checkbox" checked data-pool="{html.escape(p.key)}">'
        f'<span class="swatch" style="background: var(--{p.color_var})"></span>'
        f'<span class="fam-name">{html.escape(p.label)}</span></label>'
        for p in pools
    )

    body_sections = []
    for s in sections:
        tiles = tiles_by_section.get(s.code, [])
        if not tiles:
            continue
        sub = f'<span class="sub">{html.escape(s.summary)}</span>' if s.summary else ""
        header = f'<div class="family-header">{html.escape(s.code)} — {html.escape(s.name)}{sub}</div>'
        grid = "".join(_tile_html(t, pools) for t in tiles)
        body_sections.append(
            f'<section class="family-section">{header}<div class="grid">{grid}</div></section>'
        )

    extra_sort_opts = "".join(
        f'<option value="num:{html.escape(ss.key)}">{html.escape(ss.label)}</option>'
        for ss in extra_sorts
    )

    export_section = ""
    export_wiring = ""
    if exports:
        buttons = "".join(
            f'<button class="export-btn" id="{html.escape(e.button_id)}">Copy {html.escape(e.label)} list</button>'
            for e in exports
        )
        export_section = (
            '<div class="rail-section">'
            '<p class="eyebrow">Export (shown)</p>'
            f'{buttons}'
            '<span id="copy-status" class="copy-status"></span>'
            '</div>'
        )
        export_wiring = "".join(
            f"wireExport('{e.button_id}', 'data-{e.attr}', '{e.label}');\n"
            for e in exports
        )

    n_total = sum(len(v) for v in tiles_by_section.values())
    # Count ALL sections (matching the sidebar list), not just non-empty ones.
    n_sections = len(sections)
    gen = f" · generated {generated}" if generated else ""
    script = _SCRIPT + export_wiring

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{_STYLE}</style>
</head>
<body>
<div class="layout">
  <div class="rail-wrap" id="rail-wrap">
    <aside class="rail">
      <div class="rail-section">
        <p class="eyebrow">{html.escape(pool_label)}</p>
        <div class="rail-links">
          <a data-select-all="pool">Select All</a>
          <a data-clear-all="pool">Clear All</a>
        </div>
        <div class="rail-list">{pool_rows}</div>
      </div>
      <div class="rail-section">
        <p class="eyebrow">{html.escape(group_label)}</p>
        <div class="rail-links">
          <a data-select-all="family">Select All</a>
          <a data-clear-all="family">Clear All</a>
        </div>
        <div class="rail-list scroll">{section_rows}</div>
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
          {extra_sort_opts}
        </select>
      </div>
      {export_section}
    </aside>
  </div>
  <button class="reopen-tab" id="reopen-tab" aria-label="Show filters" title="Show filters">&#9661;</button>
  <main>
    <div class="topstrip">
      <button class="rail-toggle" id="rail-toggle" aria-label="Hide filters">&#9661; Filters</button>
      <h1>{html.escape(title)} — {n_sections} {html.escape(group_label.lower())}(ies) · {n_total} card(s){gen}</h1>
      <span class="hint">{html.escape(hint)}</span>
    </div>
    <div class="content">
{"".join(body_sections)}
    </div>
  </main>
</div>
<footer>Images load lazily from Scryfall's CDN — requires a browser with network access to cards.scryfall.io.</footer>
<script>{script}</script>
</body>
</html>
"""

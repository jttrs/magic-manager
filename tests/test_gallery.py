"""Smoke tests for the generic HTML gallery renderer.

The gallery internals used to live inside scripts/card_diff_html.py (no test
imported them). After the extraction into magic_manager.gallery, this locks the
new import path and asserts the renderer produces well-formed, data-driven HTML
for a tiny fixture — pure (no DB, no network).
"""

from __future__ import annotations

from magic_manager import gallery
from magic_manager.gallery import (
    ExportSpec, GallerySection, PoolSpec, SortSpec, merge_tiles, tile_sort_key,
)


def _tile(sid, section, name, pools, usd, *, badge=None, sort_values=None, data_attrs=None):
    return {
        "sid_key": ("sid", sid),
        "pools": set(pools),
        "family": section,
        "name": name,
        "set": "TST",
        "cn": "1",
        "rarity": "rare",
        "finish": "nonfoil",
        "usd": usd,
        "image_uri": f"https://cards.scryfall.io/normal/{sid}.jpg",
        "scryfall_url": f"https://scryfall.com/card/tst/1",
        "badge": badge,
        "sort_values": sort_values or {},
        "data_attrs": data_attrs or {},
        "row": None,
    }


def test_render_gallery_wellformed():
    pools = [PoolSpec("x", "Ecks", "p1"), PoolSpec("y", "Why", "p2")]
    sections = [GallerySection("a", "Section A", "2 cards · $3.00"),
                GallerySection("b", "Section B", "1 card · $5.00")]
    tiles = {
        "a": [_tile("s1", "a", "Alpha", ["x"], 1.0, badge="A 50%"),
              _tile("s2", "a", "Beta", ["x", "y"], 2.0)],
        "b": [_tile("s3", "b", "Gamma", ["y"], 5.0)],
    }
    html = gallery.render_gallery(
        sections, tiles, pools,
        title="Test Gallery", group_label="Bucket", pool_label="Category",
        extra_sorts=[SortSpec("Incl: high→low", "inclusion")],
        exports=[ExportSpec("copy-x", "Thing", "thing")],
        generated="2026-01-01 00:00:00",
    )
    # Document shell + title.
    assert html.startswith("<!DOCTYPE html>")
    assert "<title>Test Gallery</title>" in html
    assert html.rstrip().endswith("</html>")
    # Pool chips + section rows (data-driven).
    assert 'data-pool="x"' in html and 'data-pool="y"' in html
    assert 'data-family="a"' in html and 'data-family="b"' in html
    # Pool color comes from PoolSpec.color_var via INLINE style (no .seg.x CSS).
    assert "var(--p1)" in html and "var(--p2)" in html
    assert ".seg.x" not in html
    # All three tiles rendered; the badge shows; the extra sort + export wired.
    assert html.count('class="tile"') == 3
    assert "A 50%" in html
    assert 'value="num:inclusion"' in html
    assert "wireExport('copy-x', 'data-thing', 'Thing')" in html
    # Section count in the strapline = number of sections (incl. would-be-empty).
    assert "2 bucket(ies)" in html


def test_merge_tiles_unions_pools_and_prefers_nonnull():
    t1 = _tile("same", "a", "Dup", ["x"], 1.0, badge=None)
    t2 = _tile("same", "a", "Dup", ["y"], 1.0, badge="kept")
    t2["rarity"] = None
    merged = merge_tiles([t1, t2])
    assert len(merged) == 1
    m = merged[0]
    assert m["pools"] == {"x", "y"}          # unioned
    assert m["rarity"] == "rare"             # first non-null kept
    assert m["badge"] == "kept"              # first non-empty badge kept


def test_tile_sort_key_value_desc_then_setcn():
    tiles = [_tile("a", "s", "A", ["x"], 1.0), _tile("b", "s", "B", ["x"], 9.0),
             _tile("c", "s", "C", ["x"], None)]
    ordered = sorted(tiles, key=tile_sort_key)
    # Highest value first; None value sorts last.
    assert [t["name"] for t in ordered] == ["B", "A", "C"]


def test_scryfall_card_url():
    assert gallery.scryfall_card_url("TDM", "399") == "https://scryfall.com/card/tdm/399"
    assert gallery.scryfall_card_url(None, "1") is None
    assert gallery.scryfall_card_url("tdm", None) is None

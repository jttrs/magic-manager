"""tabs + vendors + deals.open_tabs — offline: osascript and ps are faked."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from magic_manager import config, deals, tabs, vendors

F, R = "\x1f", "\x1e"


def _copy_real_config(tmp_path):
    """Point-at-tmp tests replace only features.toml; copy the rest so a route that
    reads another config file works whether or not an earlier test cached it."""
    import shutil
    from pathlib import Path
    for f in (Path(__file__).resolve().parents[1] / "config").glob("*.toml"):
        if f.name != "features.toml" and not (tmp_path / f.name).exists():
            shutil.copy(f, tmp_path / f.name)


def _raw(windows: int, rows: list[tuple[str, str, int, int]]) -> str:
    return f"{windows}{R}" + "".join(f"{u}{F}{t}{F}{w}{F}{i}{R}" for u, t, w, i in rows)


ROWS = [
    ("https://www.pokeboxusa.com/products/kaldheim-elven-empire-commander-deck", "Elven Empire", 1, 1),
    ("https://manyrealms.com/collections/sealed/products/foundations-commander-set", "FDN set", 1, 2),
    ("https://www.bestbuy.com/product/wizards-fdn-commander/JJ8VP75X34", "Best Buy FDN", 2, 1),
    ("https://www.ebay.com/itm/287495891505", "eBay listing", 2, 2),
    ("https://manapool.com/cart", "Cart", 2, 3),
    ("https://shop.example/products/some-box", "Unknown store box", 3, 1),
    ("http://localhost:5173/market", "magic-manager", 3, 2),
    ("https://github.com/jttrs/magic-manager", "GitHub", 3, 3),
    ("https://www.ebay.com/itm/287495891505", "eBay listing (again)", 3, 4),
    ("chrome://settings", "Settings", 3, 5),
]
ONE_CHROME = "  1 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome\n"


def _read(raw, ps=ONE_CHROME):
    return dict(runner=lambda script: raw, ps=lambda: ps, system="Darwin")


def test_read_tabs_drops_local_and_dupes_and_keys_by_url():
    r = tabs.read_tabs(**_read(_raw(3, ROWS)))
    urls = [t.url for t in r.tabs]
    assert "http://localhost:5173/market" not in urls and len(urls) == len(set(urls)) == 7
    assert (r.dropped_local, r.duplicates, r.windows, r.windows_read, r.warnings) == (1, 1, 3, 3, [])
    assert r.tabs[0].host == "pokeboxusa.com"


def test_read_tabs_warns_about_the_known_failure_modes():
    automation = ONE_CHROME + "  2 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome --user-data-dir=/x/ms-playwright-mcp/p --remote-debugging-port=9222\n"
    r = tabs.read_tabs(**_read(_raw(3, ROWS[:2]), ps=automation))
    assert any("Another Chrome" in w for w in r.warnings)
    assert any("Only 1 of 3 windows" in w for w in r.warnings)


def test_read_tabs_explains_failures():
    with pytest.raises(tabs.TabsUnavailable, match="macOS only"):
        tabs.read_tabs(system="Linux")

    def denied(script):
        raise tabs.TabsUnavailable(tabs._explain("execution error: Not authorized to send Apple events to Google Chrome. (-1743)"))
    with pytest.raises(tabs.TabsUnavailable, match="Automation"):
        tabs.read_tabs(runner=denied, ps=lambda: "", system="Darwin")
    assert "isn’t running" in tabs._explain("Google Chrome is not running")


def test_classify_store_product_pages():
    assert vendors.classify("www.ebay.com", "/itm/287495891505").kind == "product"
    assert vendors.classify("manapool.com", "/cart").kind == "other"
    assert vendors.classify("bestbuy.com", "/cart").kind == "store_page"
    assert vendors.classify("shop.example", "/products/x").kind == "maybe_shopify"
    assert vendors.classify("manyrealms.com", "/collections/a/products/b").vendor.mode == "shopify"


def test_open_tabs_groups_by_store():
    out = deals.open_tabs(**_read(_raw(3, ROWS)))
    assert [(s["key"], len(s["tabs"]), s["mode"]) for s in out["stores"]] == [
        ("manyrealms", 1, "shopify"), ("pokebox", 1, "shopify"), ("bestbuy", 1, "rendered"), ("ebay", 1, "rendered")]
    assert out["uncatalogued"][0]["host"] == "shop.example"
    assert (out["other"], out["store_pages"]) == (2, 0)


def test_deals_route_is_gated(tmp_db, tmp_path, monkeypatch):
    from magic_manager.web.app import create_app  # import before pointing config at a temp dir
    monkeypatch.setenv("MAGIC_MANAGER_CONFIG_DIR", str(tmp_path))
    (tmp_path / "features.toml").write_text("[features]\ndeals = false\n")
    _copy_real_config(tmp_path)  # every other config file the routes read
    monkeypatch.delenv("MM_FEATURES", raising=False)
    config._cached_toml.cache_clear()
    monkeypatch.setattr(tabs, "_osascript", lambda script: _raw(3, ROWS))
    monkeypatch.setattr(tabs, "_ps", lambda: ONE_CHROME)
    monkeypatch.setattr(tabs.platform, "system", lambda: "Darwin")
    client = TestClient(create_app(serve_frontend=False))
    assert client.get("/api/deals/tabs").status_code == 403
    monkeypatch.setenv("MM_FEATURES", "deals")
    r = client.get("/api/deals/tabs")
    assert r.status_code == 200 and len(r.json()["stores"]) == 4
    config._cached_toml.cache_clear()

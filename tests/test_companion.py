"""The browser companion — least privilege, one error catalog, and the reader →
app → engine chain.

The page readers themselves are pinned in real Chromium by
``web/e2e/companion-readers.spec.ts`` against saved pages; that suite writes the
``tests/fixtures/companion/*.expected.json`` goldens which these tests push
through the server's strict models and the existing engine seams, so a reader
change that the server can't take fails here. Fully offline.
"""
from __future__ import annotations

import gzip
import io
import json
import re
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from magic_manager import cart, companion, config, deals, decksource, storefetch, storepage, vendors
from magic_manager.api import companion as companion_api

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "companion"
EXT = ROOT / "extension"
CODE = re.compile(r"""['"]((?:companion|request|permission|cart|tabs|moxfield|archidekt|collection|deck)\.(?!com\b|net\b|app\b)[a-z_]+)['"]""")


def _golden(name: str) -> dict:
    return json.loads((FIX / name).read_text())


# ---------- least privilege + supply chain ----------

def test_generated_files_match_vendors_toml():
    assert companion.stale_files() == [], "run: uv run python scripts/build_extension.py"


def test_manifest_asks_for_the_least():
    m = json.loads((EXT / "manifest.json").read_text())
    assert m["manifest_version"] == 3
    assert sorted(m["permissions"]) == ["scripting", "storage"]
    assert m["host_permissions"] == ["https://manapool.com/*"]           # the cart page, never its API host
    banned = {"tabs", "cookies", "webRequest", "webRequestBlocking", "debugger", "history", "management",
              "nativeMessaging", "clipboardRead", "declarativeNetRequest", "<all_urls>", "activeTab"}
    assert not banned & set(m["permissions"])
    opt = m["optional_host_permissions"]
    assert not any(p in ("<all_urls>", "*://*/*", "https://*/*", "http://*/*") for p in opt)
    assert all(p.startswith("https://") or p in ("http://localhost/*", "http://127.0.0.1/*") for p in opt)
    for key in ("externally_connectable", "web_accessible_resources", "content_scripts", "update_url", "key"):
        assert key not in m, f"{key} widens who can reach the extension"
    csp = m["content_security_policy"]["extension_pages"]
    assert "script-src 'self'" in csp and "unsafe" not in csp and "object-src 'none'" in csp


def _ext_js() -> dict[Path, str]:
    return {p: p.read_text() for p in EXT.rglob("*.js")}


def test_no_remote_code_eval_or_html_injection():
    for p, src in _ext_js().items():
        for bad in ("eval(", "new Function", "importScripts", "innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "setTimeout('", 'setTimeout("'):
            assert bad not in src, f"{p.name}: {bad}"
        for url in re.findall(r"https?://[a-z0-9*$][^\s'\"`)]*", src):
            assert re.match(r"https://(?:manapool\.com|store\.tcgplayer\.com|api2\.moxfield\.com|moxfield\.com|\*\.moxfield\.com|archidekt\.com|\$\{h\}|\*\.\$\{h\}|www\.)", url) or "localhost" in url, f"{p.name}: unexpected URL {url}"
    for html in EXT.rglob("*.html"):
        src = html.read_text()
        assert not re.search(r"<script(?![^>]*\bsrc=)", src), f"{html.name}: inline script"
        assert not re.search(r"""(?:src|href)=["']https?://""", src), f"{html.name}: remote resource"


def test_pages_use_generated_tokens_and_a_bundled_font_only():
    css = {p.name: p.read_text() for p in EXT.rglob("*.css")}
    assert "@font-face" in css["tokens.css"] and companion.FONT_FILE in css["tokens.css"]
    font = EXT / "src" / companion.FONT_FILE
    assert font.read_bytes()[:4] == b"wOF2" and (font.parent / "OFL.txt").exists()   # the face + its licence ship
    for name, src in css.items():
        assert not re.search(r"url\(\s*['\"]?(?:https?:)?//", src), f"{name}: remote resource"
        assert "@import" not in src, f"{name}: @import"
    # page.css never hand-copies colours: every colour comes from the generated tokens.
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", css["page.css"]), "page.css: raw colour, use var(--theme-*)"
    for html in EXT.rglob("*.html"):
        assert html.read_text().index('href="tokens.css"') < html.read_text().index('href="page.css"')


def test_no_dependencies_or_build_step():
    assert not (EXT / "package.json").exists() and not (EXT / "node_modules").exists()


def test_zip_is_reproducible_and_ships_only_the_extension():
    a, b = companion.build_zip(), companion.build_zip()
    assert a == b
    names = zipfile.ZipFile(io.BytesIO(a)).namelist()
    assert "magic-manager-companion/manifest.json" in names
    assert "magic-manager-companion/src/readers/manapool-cart.js" in names
    assert not any(n.endswith("README.md") for n in names)


def test_bookmarklet_is_the_extension_reader_verbatim():
    src = companion.bookmarklet_source()
    assert src.startswith((EXT / "src/readers/manapool-cart.js").read_text())
    assert companion.bookmarklet_href().startswith("javascript:")
    assert "fetch(" not in src and "XMLHttpRequest" not in src and "cookie" not in src.lower().replace("never reads cookies", "")


# ---------- one error catalog ----------

def test_error_codes_are_area_dot_reason_with_plain_messages():
    cat = companion.error_catalog()
    for code, e in cat.items():
        assert re.fullmatch(r"[a-z]+\.[a-z_]+", code)
        assert e["where"] in ("app", "extension", "server") and e["message"].strip()


def test_every_code_used_anywhere_is_catalogued():
    cat = companion.error_catalog()
    sources = [*EXT.rglob("*.js"), *(ROOT / "src/magic_manager").rglob("*.py"),
               *(p for p in (ROOT / "web/src").rglob("*.ts*") if ".test." not in p.name)]
    events = set(config.load_toml("analytics_events.toml", required=True)["events"])   # event names, not error codes
    used = {(c, p.name) for p in sources for c in CODE.findall(p.read_text()) if c not in events}
    missing = sorted({f"{c} ({f})" for c, f in used if c not in cat})
    assert not missing, f"uncatalogued: {missing}"


def test_analytics_catalog_lists_exactly_the_companion_codes():
    from magic_manager.analytics import catalog as analytics_catalog
    raw = config.load_toml("analytics_events.toml", required=True)
    values = raw["events"]["companion.error"]["props"]["code"]["values"]
    assert sorted(values) == sorted(companion.error_catalog())
    assert analytics_catalog.load()                                      # the catalog still loads


def test_error_helper_refuses_unknown_codes():
    assert companion.error("cart.empty")["fix"]
    with pytest.raises(KeyError):
        companion.error("cart.nope")


# ---------- reader goldens → server models → engine ----------

def test_cart_reader_output_is_exactly_what_the_server_accepts():
    out = _golden("manapool-cart.expected.json")
    req = companion_api.CartLinesIn(items=out["items"], source="extension")
    assert [i.scryfall_id for i in req.items] == ["8d8432a7-1c8a-4cfb-947c-ecf9791063eb", "e91ba1d4-3bca-45a2-ad9f-7abbcfe50dbd", "8d8432a7-1c8a-4cfb-947c-ecf9791063eb"]
    with pytest.raises(ValueError):
        companion_api.CartLinesIn(items=[{**out["items"][0], "cookie": "x"}], source="extension")


def test_cart_lines_audit_by_exact_printing(tmp_db, seed_cards, make_card, monkeypatch):
    out = _golden("manapool-cart.expected.json")
    sire, ajani = out["items"][0]["scryfall_id"], out["items"][1]["scryfall_id"]
    seed_cards([make_card(id=sire, oracle_id="os", set="fdn", collector_number="1", name="Sire of Seven Deaths", prices={"usd": "18.50", "usd_foil": "19.39"})])
    from magic_manager import scryfall
    monkeypatch.setattr(scryfall, "collection", lambda ids: ([make_card(id=ajani, oracle_id="oa", set="mh3", collector_number="442", name="Ajani, Nacatl Pariah // Ajani, Nacatl Avenger")], []))
    monkeypatch.setattr(cart, "infer_set_anchors", lambda mapped: [])
    r = cart.audit([i for i in out["items"]], remote=True)
    assert (r["lines"], r["copies"], r["total"]) == (3, 4, 71.0)
    assert r["unidentified"] == []                                     # Ajani filled from Scryfall, not dropped
    assert [d["name"] for d in r["dupes"]] == ["Sire of Seven Deaths"]  # nonfoil + foil of the same printing


@pytest.mark.parametrize("vendor", ["coolstuff", "starcity", "cardkingdom", "miniaturemarket"])
def test_store_reader_extract_prices_like_the_full_page(vendor):
    """The companion's page reading of a real store page gives the server the
    same price + title the server reads from the whole page."""
    v = vendors.by_key(vendor)
    full = vendors.read_listing(v, gzip.decompress((ROOT / f"tests/fixtures/vendors/{vendor}.html.gz").read_bytes()).decode())
    html, text = storefetch.page_from_extract(_golden("store-extracts.expected.json")[vendor])
    extract = vendors.read_listing(v, html, text=text)
    assert extract.price == full.price and extract.price is not None
    if not v.title_pattern:                      # title_pattern reads the page body — server fetches only
        assert extract.title == full.title


def test_open_tab_recipes_need_nothing_the_companion_doesnt_read():
    for v in vendors.catalog():
        if v.mode == "rendered":
            assert v.title_pattern is None, f"{v.key}: title_pattern needs the page body, which the companion doesn't send"


def test_rendered_store_extract_reads_price_and_stock():
    ex = _golden("store-rendered.expected.json")
    page = deals_api_page(ex)
    html, text = storefetch.page_from_extract(page)
    listing = vendors.read_listing(vendors.by_key("bestbuy"), html, text=text)
    assert (listing.price, listing.available) == (144.99, True)
    assert listing.title == "Magic: The Gathering – Foundations Play Booster Box"


def deals_api_page(ex: dict) -> dict:
    from magic_manager.api.deals import RenderedPageIn
    return RenderedPageIn(**ex).model_dump()


def test_page_from_extract_escapes_the_title():
    html, _ = storefetch.page_from_extract({"title": "Box</title><title>Evil", "head": "", "ld": [], "text": ""})
    assert storepage.title_of(html) == "Box</title><title>Evil"


def test_moxfield_reader_output_becomes_deck_lines(tmp_db, seed_cards, make_card):
    out = _golden("moxfield-deck.expected.json")
    req = companion_api.DeckFromBrowserIn(source="moxfield", deck=out["deck"])
    payload = decksource.payload_from_moxfield(req.deck.model_dump(), req.deck.publicId)
    assert (payload["source"], payload["id"], payload["name"], payload["author"]) == ("moxfield", "AbCd1234", "Goblin Party", "goblinfan")
    by_name = {c["name"]: c for c in payload["cards"]}
    assert by_name["Krenko, Mob Boss"]["board"] == "commander" and by_name["Krenko, Mob Boss"]["finish"] == "foil"
    assert by_name["Mountain"]["qty"] == 30
    with pytest.raises(ValueError):
        companion_api.DeckFromBrowserIn(source="moxfield", deck={**out["deck"], "authors": []})


# ---------- deals seams ----------

def test_supplied_tabs_sort_like_a_local_read():
    out = deals.supplied_tabs([
        {"url": "https://manyrealms.com/products/fdn-set", "title": "Set"},
        {"url": "https://manyrealms.com/products/fdn-set", "title": "dupe"},
        {"url": "https://www.bestbuy.com/site/x/123.p", "title": "BB"},
        {"url": "https://manyrealms.com/cart", "title": "Cart"},
        {"url": "http://localhost:8765/market", "title": "app"},
    ])
    assert out["browser"] == "extension"
    assert {s["key"]: [t["url"] for t in s["tabs"]] for s in out["stores"]} == {
        "manyrealms": ["https://manyrealms.com/products/fdn-set"], "bestbuy": ["https://www.bestbuy.com/site/x/123.p"]}
    assert (out["store_pages"], out["dropped_local"], out["duplicates"]) == (1, 1, 1)


def test_read_prices_uses_the_companion_page_instead_of_this_mac(monkeypatch):
    def no_applescript(*a, **k):
        raise AssertionError("must not read the tab on this Mac")
    monkeypatch.setattr(storefetch, "read_tab", no_applescript)
    url = "https://www.bestbuy.com/site/foundations/6589123.p"
    rows = deals.read_prices([url], pages={url: _golden("store-rendered.expected.json")})
    assert (rows[0]["price"], rows[0]["available"], rows[0]["error"]) == (144.99, True, None)


def test_read_prices_in_browser_never_falls_back_to_this_mac(monkeypatch):
    """The companion read the open-tab stores: a page it couldn't read is reported, not read via AppleScript."""
    def no_applescript(*a, **k):
        raise AssertionError("must not read the tab on this Mac")
    monkeypatch.setattr(storefetch, "read_tab", no_applescript)
    read, unread = "https://www.bestbuy.com/site/foundations/6589123.p", "https://www.bestbuy.com/site/other/1.p"
    rows = deals.read_prices([read, unread], pages={read: _golden("store-rendered.expected.json")}, tabs_on_mac=False)
    assert rows[0]["price"] == 144.99
    assert (rows[1]["price"], rows[1]["error"]) == (None, deals.COMPANION_UNREAD)


def test_reads_in_browser_is_open_tab_store_product_pages():
    assert deals.reads_in_browser("https://www.bestbuy.com/site/foundations/6589123.p")
    assert not deals.reads_in_browser("https://www.bestbuy.com/cart")            # not a product page
    assert not deals.reads_in_browser("https://manyrealms.com/products/fdn-set")  # read by the server
    assert not deals.reads_in_browser("https://www.tcgplayer.com/product/1")


def test_watchlist_job_hands_companion_pages_to_the_read(tmp_db, monkeypatch):
    from magic_manager.api import deals as deals_api
    seen = {}

    def fake(*, progress=None, pages=None, tabs_on_mac=True):
        seen.update(pages=pages, tabs_on_mac=tabs_on_mac)
        return {"rows": [], "read": [], "newly_met": []}
    monkeypatch.setattr(deals, "read_watched", fake)
    monkeypatch.setattr(deals_api.features, "require", lambda name: None)
    url = "https://www.bestbuy.com/site/foundations/6589123.p"
    page = _golden("store-rendered.expected.json")
    inp = deals_api.WatchlistInput(refresh=True, in_browser=True, pages={url: page})
    deals_api._run_watchlist(inp, lambda ev: None)
    assert seen["tabs_on_mac"] is False and seen["pages"][url]["title"] == page["title"]
    deals_api._run_watchlist(deals_api.WatchlistInput(refresh=True), lambda ev: None)
    assert seen == {"pages": {}, "tabs_on_mac": True}                 # no companion: this Mac, as before
    with pytest.raises(ValueError):
        deals_api.WatchlistInput(refresh=True, pages={url: {**page, "cookie": "x"}})   # strict page model


def test_watched_reader_revalidates_and_stays_within_its_lane():
    """extension/src/watched.js: only rendered-store product pages; opened tabs always closed; plan before read."""
    js = (ROOT / "extension/src/watched.js").read_text()
    bg = (ROOT / "extension/src/background.js").read_text()
    assert "store.mode !== 'rendered'" in js and "product_path" in js and "u.protocol !== 'https:'" in js
    assert "active: false" in js and "finally" in js and "chrome.tabs.remove(tab.id)" in js
    assert "readers/store-page.js" in js                       # the same reader as the open-tab Deals read
    assert "planWatched(params" in bg and "stage: msg.kind === 'watched' ? 'confirm'" in bg
    assert "pending.stage === 'confirm') return readApproved" in bg
    assert "(pending.stage || 'send') !== 'send') return fail('request.invalid')" in bg   # never send a plan


# ---------- API ----------

@pytest.fixture
def client(tmp_db, tmp_path, monkeypatch, copy_real_config):
    monkeypatch.setenv("MAGIC_MANAGER_CONFIG_DIR", str(tmp_path))
    (tmp_path / "features.toml").write_text("[features]\ncompanion = false\ncart_check = false\ndeals = false\n")
    copy_real_config(tmp_path)  # every other config file the routes read
    monkeypatch.delenv("MM_FEATURES", raising=False)
    monkeypatch.setattr(cart, "infer_set_anchors", lambda mapped: [])
    config._cached_toml.cache_clear()
    from magic_manager.web.app import create_app
    yield TestClient(create_app(serve_frontend=False))
    config._cached_toml.cache_clear()


def test_routes_are_gated_by_their_flags(client, monkeypatch):
    lines = {"items": _golden("manapool-cart.expected.json")["items"], "source": "extension"}
    assert client.get("/api/companion").status_code == 200                   # catalog: unflagged
    assert client.get("/api/companion/extension.zip").status_code == 403
    assert client.post("/api/cart/lines", json=lines).status_code == 403
    assert client.post("/api/deals/tabs", json={"tabs": []}).status_code == 403
    monkeypatch.setenv("MM_FEATURES", "companion,cart_check,deals")
    z = client.get("/api/companion/extension.zip")
    assert z.status_code == 200 and z.headers["content-type"] == "application/zip" and z.content == companion.build_zip()
    assert client.get("/api/companion/bookmarklet").json()["href"].startswith("javascript:")
    assert client.post("/api/deals/tabs", json={"tabs": [{"url": "https://manyrealms.com/products/a", "title": "A"}]}).json()["stores"][0]["key"] == "manyrealms"


def test_cart_lines_route_audits_and_refuses_extras(client, monkeypatch):
    monkeypatch.setenv("MM_FEATURES", "cart_check")
    monkeypatch.setattr(cart, "_fill_ids", lambda ids: {})
    items = _golden("manapool-cart.expected.json")["items"]
    r = client.post("/api/cart/lines", json={"items": items, "source": "extension"})
    assert r.status_code == 200 and r.json()["copies"] == 4
    assert client.post("/api/cart/lines", json={"items": [{**items[0], "session": "jwt"}], "source": "extension"}).status_code == 422
    empty = client.post("/api/cart/lines", json={"items": [], "source": "bookmarklet"})
    assert empty.status_code == 422 and empty.json()["detail"]["code"] == "cart.no_lines"


@pytest.mark.parametrize("site,ok", [(None, True), ("same-origin", True), ("none", True), ("same-site", False), ("cross-site", False)])
def test_writes_only_from_the_apps_own_pages(client, monkeypatch, site, ok):
    monkeypatch.setenv("MM_FEATURES", "cart_check")
    headers = {"sec-fetch-site": site} if site else {}
    r = client.post("/api/cart/lines", json={"items": [], "source": "extension"}, headers=headers)
    if ok:
        assert r.json()["detail"]["code"] == "cart.no_lines"
    else:
        assert r.status_code == 403 and r.json()["detail"]["code"] == "request.cross_site"
    assert client.get("/api/companion", headers=headers).status_code == 200      # reads aren't blocked


# ---------- Chrome Web Store distribution ----------

def test_zips_ship_icons_never_the_store_kit():
    folder = zipfile.ZipFile(io.BytesIO(companion.build_zip())).namelist()
    store = zipfile.ZipFile(io.BytesIO(companion.build_zip(store=True))).namelist()
    assert "magic-manager-companion/icons/icon-128.png" in folder
    assert "manifest.json" in store and "icons/icon-128.png" in store            # the store wants the manifest at the root
    assert all(not n.startswith("magic-manager-companion/") for n in store)
    assert [f"magic-manager-companion/{n}" for n in store] == folder              # same files, same order
    assert not any("/store/" in f"/{n}" for n in folder + store)                 # listing kit + screenshots stay out
    assert companion.build_zip(store=True) == companion.build_zip(store=True)


def test_icons_are_generated_pngs_the_manifest_points_at():
    m = companion.manifest()
    for size in companion.ICON_SIZES:
        png = (EXT / m["icons"][str(size)]).read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert int.from_bytes(png[16:20], "big") == int.from_bytes(png[20:24], "big") == size
        assert png == companion.icon_png(size)
    assert set(m["action"]["default_icon"].values()) <= set(m["icons"].values())


def _rgba(png: bytes, x: int, y: int) -> tuple[int, ...]:
    ihdr, raw = companion.png_pixels(png)
    size = int.from_bytes(ihdr[:4], "big")
    row = 1 + size * 4                                                         # filter byte + RGBA
    assert raw[y * row] == 0                                                   # unfiltered rows
    off = y * row + 1 + x * 4
    return tuple(raw[off:off + 4])


def test_icons_draw_the_favicon():
    dark, bone = (0x16, 0x13, 0x0E, 255), (0xEF, 0xE7, 0xD6, 255)
    for size in (16, 32, 48):
        png = companion.icon_png(size)
        assert _rgba(png, size // 2, size // 4) == bone                       # the card
        assert _rgba(png, size // 2, size // 32 or 1)[:3] == dark[:3]         # the tile's top edge
        band = _rgba(png, size // 2, round(size * 19 / 32))
        assert band[0] > band[2] and band != bone                              # the amber band over the card
    big = companion.icon_png(128)
    assert _rgba(big, 0, 0)[3] == 0 and _rgba(big, 8, 64)[3] == 0             # 16 px transparent padding
    assert _rgba(big, 64, 40) == bone and _rgba(big, 20, 64)[:3] == dark[:3]


def test_icon_check_ignores_how_zlib_compressed_it(tmp_path):
    """--check compares pixels, so a platform whose zlib deflates differently still passes."""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    want = companion.icon_png(32)
    ihdr, raw = companion.png_pixels(want)
    alt = want[:8] + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 1)) + chunk(b"IEND", b"")
    assert alt != want and companion.png_pixels(alt) == companion.png_pixels(want)
    p = tmp_path / "icon.png"
    p.write_bytes(alt)
    assert companion._current(p, want)
    p.write_bytes(companion.icon_png(16))
    assert not companion._current(p, want)


def test_manifest_fits_the_store():
    m = companion.manifest()
    assert len(m["description"]) <= 132                                       # the store's summary limit
    assert len(m["name"]) <= 75
    assert re.fullmatch(r"\d+\.\d+\.\d+", m["version"])


def test_store_url_is_configurable_and_only_a_store_page(monkeypatch, tmp_path):
    monkeypatch.delenv(companion.STORE_URL_ENV, raising=False)
    toml = tmp_path / "store.toml"
    monkeypatch.setattr(companion, "STORE_TOML", toml)
    assert companion.store_url() is None                                      # no file
    toml.write_text('[chrome_web_store]\nurl = ""\n')
    assert companion.store_url() is None                                      # not published yet
    page = "https://chromewebstore.google.com/detail/magic-manager-companion/abcdefghijklmnopabcdefghijklmnop"
    toml.write_text(f'[chrome_web_store]\nurl = "{page}"\n')
    assert companion.store_url() == page
    monkeypatch.setenv(companion.STORE_URL_ENV, page + "x")
    assert companion.store_url() == page + "x"                                # env wins
    monkeypatch.setenv(companion.STORE_URL_ENV, "https://evil.example/detail/x")
    assert companion.store_url() is None                                      # never another site
    monkeypatch.delenv(companion.STORE_URL_ENV)
    for broken in ('[chrome_web_store\nurl = "', 'chrome_web_store = 3\n', '[chrome_web_store]\nurl = 7\n'):
        toml.write_text(broken)
        assert companion.store_url() is None                                  # a typo never 500s /api/companion


def test_committed_store_toml_is_unpublished_or_a_store_page():
    raw = companion.tomllib.loads(companion.STORE_TOML.read_text())["chrome_web_store"]["url"]
    assert raw == "" or raw.startswith(companion.STORE_URL_PREFIX)


def test_info_carries_store_and_privacy_urls(monkeypatch):
    page = "https://chromewebstore.google.com/detail/x/abcdefghijklmnopabcdefghijklmnop"
    monkeypatch.setenv(companion.STORE_URL_ENV, page)
    out = companion_api.info()
    assert out.store_url == page and out.privacy_url == companion.PRIVACY_URL
    monkeypatch.delenv(companion.STORE_URL_ENV)
    monkeypatch.setattr(companion, "STORE_TOML", Path("/nonexistent/store.toml"))
    assert companion_api.info().store_url is None


@pytest.mark.parametrize("fn,env,section,prefix", [
    (companion.store_url, companion.STORE_URL_ENV, "chrome_web_store", companion.STORE_URL_PREFIX),
    (companion.edge_store_url, companion.EDGE_STORE_URL_ENV, "edge_add_ons", companion.EDGE_STORE_URL_PREFIX),
])
def test_store_urls_are_a_strict_allowlist(monkeypatch, tmp_path, fn, env, section, prefix):
    monkeypatch.delenv(companion.STORE_URL_ENV, raising=False)
    monkeypatch.delenv(companion.EDGE_STORE_URL_ENV, raising=False)
    toml = tmp_path / "store.toml"
    monkeypatch.setattr(companion, "STORE_TOML", toml)
    assert fn() is None                                                       # no file
    toml.write_text(f'[{section}]\nurl = ""\n')
    assert fn() is None                                                       # not listed
    ok = [prefix + "magic-manager-companion/abcdefghijklmnopabcdefghijklmnop",
          prefix + "magic-manager-companion/abcdefghijklmnopabcdefghijklmnop?hl=en-US"]
    for url in ok:
        toml.write_text(f'[{section}]\nurl = "{url}"\n')
        assert fn() == url
        monkeypatch.setenv(env, "  " + url + "  ")
        assert fn() == url                                                    # env wins, trimmed
        monkeypatch.delenv(env)
    other = companion.EDGE_STORE_URL_PREFIX if prefix == companion.STORE_URL_PREFIX else companion.STORE_URL_PREFIX
    bad = [prefix, prefix.replace("https://", "http://"), "https://evil.example/addons/detail/x",
           prefix.rstrip("/") + ".evil.example/x", prefix.replace("/detail/", "/detailx/") + "x",
           other + "x/abc", "javascript:alert(1)//" + prefix + "x",
           prefix + "x/../../../evil", prefix + "x/%2e%2e/evil", prefix + "x#frag", prefix + "x y",
           prefix + 'x" onclick="a', prefix + "x\nhttps://evil.example", prefix + "//evil.example/x",
           prefix + "x?a=<b>"]
    for url in bad:
        monkeypatch.setenv(env, url)
        assert fn() is None, url                                              # never another site, never a trick
    monkeypatch.delenv(env)
    for broken in (f'[{section}\nurl = "', f'{section} = 3\n', f'[{section}]\nurl = 7\n'):
        toml.write_text(broken)
        assert fn() is None                                                   # a typo never 500s /api/companion


def test_edge_and_chrome_urls_are_independent(monkeypatch, tmp_path):
    monkeypatch.delenv(companion.STORE_URL_ENV, raising=False)
    monkeypatch.delenv(companion.EDGE_STORE_URL_ENV, raising=False)
    toml = tmp_path / "store.toml"
    monkeypatch.setattr(companion, "STORE_TOML", toml)
    edge = companion.EDGE_STORE_URL_PREFIX + "magic-manager-companion/abcdefghijklmnopabcdefghijklmnop"
    toml.write_text(f'[chrome_web_store]\nurl = ""\n[edge_add_ons]\nurl = "{edge}"\n')
    assert companion.edge_store_url() == edge and companion.store_url() is None
    toml.write_text(f'[chrome_web_store]\nurl = "{edge}"\n')                # an Edge page in the Chrome slot
    assert companion.store_url() is None and companion.edge_store_url() is None


def test_committed_edge_listing_is_unlisted_or_an_edge_page():
    raw = companion.tomllib.loads(companion.STORE_TOML.read_text())["edge_add_ons"]["url"]
    assert raw == "" or raw.startswith(companion.EDGE_STORE_URL_PREFIX)


def test_info_carries_the_edge_url_only_when_configured(monkeypatch):
    monkeypatch.delenv(companion.EDGE_STORE_URL_ENV, raising=False)
    monkeypatch.setattr(companion, "STORE_TOML", Path("/nonexistent/store.toml"))
    assert companion_api.info().edge_store_url is None
    page = companion.EDGE_STORE_URL_PREFIX + "x/abcdefghijklmnopabcdefghijklmnop"
    monkeypatch.setenv(companion.EDGE_STORE_URL_ENV, page)
    assert companion_api.info().edge_store_url == page


def test_shipped_extension_names_no_single_store():
    """One store zip serves Chrome Web Store and Edge Add-ons: nothing shipped may pin an
    install/update source (update_url, key) or link a store page."""
    m = companion.manifest()
    assert "update_url" not in m and "key" not in m
    with zipfile.ZipFile(io.BytesIO(companion.build_zip(store=True))) as z:
        for name in z.namelist():
            text = z.read(name).decode("utf-8", "ignore")
            for host in ("chromewebstore.google.com", "chrome.google.com/webstore", "microsoftedge.microsoft.com"):
                assert host not in text, f"{name} links {host}"


def test_extension_icon_matches_the_app_favicon():
    """companion._ICON_SHAPES is web/public/favicon.svg, shape for shape — so the
    extension icon can't silently drift from the app's favicon."""
    import xml.etree.ElementTree as ET
    svg = ET.parse(Path(companion.EXT_DIR.parent / "web" / "public" / "favicon.svg")).getroot()
    assert svg.get("viewBox") == "0 0 32 32"                                  # the icon's 32-unit grid
    kids = list(svg)
    assert all(k.tag.rsplit("}", 1)[-1] == "rect" for k in kids)              # only rects are rasterized
    for k in kids:                                                            # ...with only these attributes
        assert set(k.attrib) <= {"x", "y", "width", "height", "rx", "fill", "opacity"}, k.attrib

    def num(el, attr):
        v = float(el.get(attr, 0))
        return int(v) if v.is_integer() else v

    def rgba(el):
        h = el.get("fill").lstrip("#")
        assert len(h) == 6, h
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), round(float(el.get("opacity", 1)) * 255))

    from_svg = tuple((num(k, "x"), num(k, "y"), num(k, "width"), num(k, "height"), num(k, "rx"), rgba(k)) for k in kids)
    assert from_svg == companion._ICON_SHAPES


def test_bump_version(monkeypatch, tmp_path):
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"name": "x", "version": "0.4.5"}))
    monkeypatch.setattr(companion, "MANIFEST", m)
    assert companion.bump_version("patch") == "0.4.6"
    assert companion.bump_version("minor") == "0.5.0"
    assert companion.bump_version("major") == "1.0.0"
    assert json.loads(m.read_text()) == {"name": "x", "version": "1.0.0"}
    with pytest.raises(ValueError):
        companion.bump_version("tiny")


def test_privacy_policy_and_listing_cover_every_permission():
    policy = ROOT / "docs" / "privacy-companion.md"
    assert companion.PRIVACY_URL.endswith("/blob/main/docs/privacy-companion.md") and policy.exists()
    listing = (companion.STORE_DIR / "listing.md").read_text()
    m = companion.manifest()
    for p in m["permissions"] + m["host_permissions"]:
        assert f"`{p}`" in listing, f"listing.md has no justification for {p}"
    assert companion.PRIVACY_URL in listing
    assert m["description"] in listing


def test_build_script_release_flags(tmp_path):
    import subprocess
    import sys as _sys
    script = ROOT / "scripts" / "build_extension.py"
    out = subprocess.run([_sys.executable, str(script), "--print-version"], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == companion.version()
    z = tmp_path / "s.zip"
    subprocess.run([_sys.executable, str(script), "--check"], check=True)
    subprocess.run([_sys.executable, str(script), "--store-zip", str(z)], capture_output=True, check=True)
    assert z.read_bytes() == companion.build_zip(store=True)

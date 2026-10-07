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
CODE = re.compile(r"""['"]((?:companion|request|permission|cart|tabs|moxfield|deck)\.(?!com\b|net\b|app\b)[a-z_]+)['"]""")


def _copy_real_config(tmp_path):
    """Point-at-tmp tests replace only features.toml; copy the rest so a route that
    reads another config file works whether or not an earlier test cached it."""
    import shutil
    from pathlib import Path
    for f in (Path(__file__).resolve().parents[1] / "config").glob("*.toml"):
        if f.name != "features.toml" and not (tmp_path / f.name).exists():
            shutil.copy(f, tmp_path / f.name)


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
            assert re.match(r"https://(?:manapool\.com|api2\.moxfield\.com|moxfield\.com|\*\.moxfield\.com|\$\{h\}|\*\.\$\{h\}|www\.)", url) or "localhost" in url, f"{p.name}: unexpected URL {url}"
    for html in EXT.rglob("*.html"):
        src = html.read_text()
        assert not re.search(r"<script(?![^>]*\bsrc=)", src), f"{html.name}: inline script"
        assert not re.search(r"""(?:src|href)=["']https?://""", src), f"{html.name}: remote resource"


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


# ---------- API ----------

@pytest.fixture
def client(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_MANAGER_CONFIG_DIR", str(tmp_path))
    (tmp_path / "features.toml").write_text("[features]\ncompanion = false\ncart_check = false\ndeals = false\n")
    _copy_real_config(tmp_path)  # every other config file the routes read
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

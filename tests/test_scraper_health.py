"""Scraper health (docs/scraper-health.md): every scraper, per site, has an
offline pin and a live-canary sample; the canary's verdicts fold into a status
file the app reads ("temporarily down"); real use flags and clears it too.

Offline: the live reads are faked at their seams (storefetch.read,
addcards.fetch_deck_payload, the EDHREC page client, a fake browser page).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from magic_manager import addcards, deals, decksource, edhrec, scrape_canary, scraper_health as sh, storefetch, storepage, vendors

TESTS = Path(__file__).parent


@pytest.fixture
def health_file(tmp_path, monkeypatch):
    p = tmp_path / "scraper_health.json"
    monkeypatch.setenv("MM_SCRAPER_HEALTH", str(p))
    return p


def _status(key):
    return next(h for h in sh.health() if h.scraper.key == key)


# ---------- the inventory: every scraper, per site ----------

def test_registry_covers_every_store_deck_source_reader_and_edhrec():
    keys = [s.key for s in sh.registry()]
    assert len(keys) == len(set(keys))
    assert {f"store-price/{v.key}" for v in vendors.catalog()} <= set(keys)
    assert {f"deck-import/{s}" for s in sh.DECK_SOURCES} <= set(keys)
    assert {"companion-cart/manapool", "companion-deck/moxfield", "edhrec-commander/edhrec",
            "edhrec-card/edhrec", "edhrec-rankings/edhrec"} <= set(keys)


def test_a_store_added_to_the_catalog_is_covered_with_no_other_change(monkeypatch):
    extra = vendors.Vendor("newshop", "New Shop", ("newshop.com",), "meta", r"/p/\d+",
                           sample_url="https://newshop.com/p/1")
    real = vendors.catalog()
    monkeypatch.setattr(vendors, "catalog", lambda: (*real, extra))
    s = sh.by_key()["store-price/newshop"]
    assert (s.canary, s.sample, s.where) == ("http", "https://newshop.com/p/1", "Deals")


# Offline pins (the deterministic golden tests) per non-store scraper. Stores are
# pinned generically: server-read ones by EXPECT in test_vendor_recipes.py (it
# enforces that), open-tab ones by a recipe test naming the store.
PINS = {
    "deck-import/archidekt": ("test_decksource.py", "test_parse_archidekt_categories_and_modifier"),
    "deck-import/mtggoldfish": ("test_decksource.py", "test_parse_mtggoldfish_delegates_to_parse_text"),
    "deck-import/manabox": ("test_decksource.py", "test_parse_manabox_shape"),
    "deck-import/scryfall": ("test_decksource.py", "test_parse_scryfall_shape"),
    "deck-import/moxfield": ("test_decksource.py", "test_parse_moxfield_boards_and_finishes"),
    "companion-deck/moxfield": ("test_companion.py", "test_moxfield_reader_output_becomes_deck_lines"),
    "companion-deck/archidekt": ("test_companion_imports.py", "test_archidekt_reader_output_becomes_the_same_payload_as_the_api_import"),
    "companion-collection/moxfield": ("test_companion_imports.py", "test_collection_reader_output_is_exactly_what_the_server_accepts"),
    "companion-cart/manapool": ("test_companion.py", "test_cart_reader_output_is_exactly_what_the_server_accepts"),
    "companion-cart/tcgplayer": ("test_companion_carts.py", "test_tcgplayer_cart_from_the_reader_golden"),
    "companion-cart/cardkingdom": ("test_companion_carts.py", "test_cardkingdom_cart_from_the_reader_golden"),
    "companion-orders/manapool": ("test_companion_orders.py", "test_manapool_order_from_the_reader_golden"),
    "companion-orders/tcgplayer": ("test_companion_orders.py", "test_tcgplayer_orders_resolve_by_product_id"),
    "companion-orders/cardkingdom": ("test_companion_orders.py", "test_cardkingdom_unverified_lines_are_never_cards"),
    "edhrec-commander/edhrec": ("test_edhrec.py", "def test_"),
    "edhrec-card/edhrec": ("test_edhrec.py", "def test_"),
    "edhrec-rankings/edhrec": ("test_edhrec.py", "def test_"),
}


def test_every_scraper_has_an_offline_pin():
    for s in sh.registry():
        if s.scraper == "store-price":
            assert f'"{s.site}"' in "".join(p.read_text() for p in TESTS.glob("test_*.py") if p.name != Path(__file__).name), \
                f"{s.key}: no recipe test names this store"
            continue
        file, name = PINS[s.key]
        assert name in (TESTS / file).read_text(), f"{s.key}: pin {file}::{name} is missing"


def test_canary_samples_are_valid_for_their_scraper():
    samples = sh.canary_samples()
    for src, sample in samples["deck"].items():
        assert decksource.source_of(sample["url"]) == src
        assert decksource.deck_id_from_url(sample["url"])
        assert int(sample["min_cards"]) > 0 and sample["card"]
    for key, sample in samples.get("store", {}).items():
        v = vendors.by_key(key)
        assert v.mode == "rendered", f"{key}: server-read stores use sample_url in vendors.toml"
        assert v.is_product(urlsplit(sample["url"]).path), key
    assert samples["cart"]["manapool"]["expect_code"] == "cart.empty"
    # Only eBay (listings end) and the signed-in order-history readers (no public sample)
    # have no live canary; everything else is reached.
    assert {s.key for s in sh.registry() if s.canary == "none"} <= (
        {f"store-price/{v.key}" for v in vendors.catalog() if v.mode == "rendered"}
        | {f"companion-orders/{k}" for k in sh.ORDER_STORES})


# ---------- the status machine ----------

def test_fail_flags_down_and_a_pass_clears_it(health_file):
    k = "store-price/manyrealms"
    assert _status(k).status == "unknown"
    assert sh.record([(k, "ok", None, None, {"price": 1})], at="2026-01-01T00:00:00+00:00") == []
    [t] = sh.record([(k, "fail", "scrape.no_price", None, None)], at="2026-01-02T00:00:00+00:00")
    assert (t.change, t.code) == ("down", "scrape.no_price")
    assert sh.record([(k, "fail", "scrape.no_price", None, None)], at="2026-01-03T00:00:00+00:00") == []
    h = _status(k)
    assert (h.status, h.since, h.checked_at, h.last_ok) == ("down", "2026-01-02T00:00:00+00:00",
                                                           "2026-01-03T00:00:00+00:00", "2026-01-01T00:00:00+00:00")
    assert h.message and h.fix                                     # filled from the reason catalog
    # A check that couldn't run neither clears nor re-dates the flag.
    assert sh.record([(k, "unverified", "scrape.blocked", None, None)], at="2026-01-04T00:00:00+00:00") == []
    assert (_status(k).status, _status(k).since) == ("down", "2026-01-02T00:00:00+00:00")
    [t] = sh.record([(k, "ok", None, None, None)], at="2026-01-05T00:00:00+00:00")
    assert t.change == "recovered"
    assert (_status(k).status, _status(k).code) == ("ok", None)
    assert json.loads(health_file.read_text())["version"] == sh.VERSION


def test_unverified_never_flags_and_a_removed_sample_is_announced_once(health_file):
    k = "deck-import/archidekt"
    [t] = sh.record([(k, "unverified", "scrape.sample_gone", None, None)])
    assert t.change == "sample_gone" and _status(k).status == "unverified"
    assert sh.record([(k, "unverified", "scrape.sample_gone", None, None)]) == []


def test_real_use_flags_and_clears_and_never_raises(health_file, monkeypatch):
    k = "deck-import/moxfield"
    sh.record_use(k, "unverified", "scrape.blocked")                 # a private deck says nothing
    assert _status(k).status == "unknown"
    sh.record_use(k, "fail", "scrape.no_cards")
    assert (_status(k).status, _status(k).via) == ("down", "use")
    sh.record_use(k, "ok")
    assert _status(k).status == "ok"
    monkeypatch.setattr(sh, "record", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    sh.record_use(k, "fail", "scrape.no_cards")                      # swallowed


def test_a_confirming_read_skips_the_write(health_file, monkeypatch):
    sh.record_use("edhrec-card/edhrec", "ok")
    calls = []
    monkeypatch.setattr(sh, "record", lambda *a, **k: calls.append(a))
    sh.record_use("edhrec-card/edhrec", "ok")
    assert calls == []


@pytest.mark.parametrize("text,outcome,code", [
    ("import_deck: no cards parsed (empty deck, or the payload shape changed)", "fail", "scrape.no_cards"),
    ("import_deck: fetch failed: HTTP Error 404: Not Found", "unverified", "scrape.sample_gone"),
    ("import_deck: fetch failed: HTTP Error 403: Forbidden", "unverified", "scrape.blocked"),
    ("import_deck: fetch failed: <urlopen error [Errno 8] nodename nor servname>", "unverified", "scrape.unreachable"),
    ("import_deck: Moxfield api2 returned HTTP 503", "unverified", "scrape.unreachable"),
    ("json.decoder.JSONDecodeError: Expecting value", "fail", "scrape.shape_changed"),
    ("Moxfield deck page never fired its api2 call (Cloudflare interstitial …)", "unverified", "scrape.blocked"),
    ("something odd", "unverified", "scrape.error"),
    ("import_deck: deck is empty", "unverified", "scrape.empty_deck"),
])
def test_classify_error(text, outcome, code):
    assert sh.classify_error(text) == (outcome, code)


def test_classify_error_wrapper_backoff_is_blocked_not_a_failure():
    text = "edhrec.sh: in backoff window after a 429, 42s remaining. Aborting."
    assert sh.classify_error(text, unknown="fail") == ("unverified", "scrape.blocked")


def test_classify_error_for_fixed_endpoints():
    assert sh.classify_error("edhrec.sh: HTTP 404 from …", missing="fail") == ("fail", "scrape.shape_changed")
    assert sh.classify_error("weird", unknown="fail") == ("fail", "scrape.error")


# ---------- canary checks (live seams faked) ----------

def _listing(price, title="Box", available=True):
    return storepage.Listing(price, "USD", available, title, "meta")


@pytest.mark.parametrize("effect,outcome,code", [
    (lambda: _listing(10.0), "ok", None),
    (lambda: _listing(None), "fail", "scrape.no_price"),
    (lambda: _listing(5.0, title=None), "fail", "scrape.no_title"),
    (LookupError("the store no longer has this product"), "unverified", "scrape.sample_gone"),
    (storepage.Blocked("403"), "unverified", "scrape.blocked"),
    (httpx.ConnectTimeout("slow"), "unverified", "scrape.unreachable"),
    (KeyError("variants"), "fail", "scrape.error"),
])
def test_store_check(monkeypatch, effect, outcome, code):
    v = vendors.by_key("manyrealms")

    def fake_read(url, fresh=False, **_):
        assert url == v.sample_url and fresh
        if isinstance(effect, Exception):
            raise effect
        return v, effect()
    monkeypatch.setattr(storefetch, "read", fake_read)
    c = scrape_canary.check_store(v)
    assert (c.key, c.outcome, c.code) == ("store-price/manyrealms", outcome, code)


SAMPLE = {"url": "https://archidekt.com/decks/1", "min_cards": 3, "card": "Sol Ring", "commander": "Krenko, Mob Boss"}
CARDS = [{"qty": 1, "board": "commander", "name": "Krenko, Mob Boss"},
         {"qty": 1, "board": "main", "name": "Sol Ring"}, {"qty": 2, "board": "main", "name": "Mountain"}]


@pytest.mark.parametrize("cards,outcome,code", [
    (CARDS, "ok", None),
    ([], "fail", "scrape.no_cards"),
    (CARDS[:2], "fail", "scrape.expectation"),                       # too few
    ([{**c, "board": "main"} for c in CARDS], "fail", "scrape.expectation"),  # commander lost its board
    ([*CARDS, {"qty": 1, "board": "main"}], "fail", "scrape.shape_changed"),  # a card with nothing to resolve
])
def test_validate_deck(cards, outcome, code):
    c = scrape_canary.validate_deck("deck-import/archidekt", {"cards": cards}, SAMPLE)
    assert (c.outcome, c.code) == (outcome, code)


def test_deck_check_runs_the_apps_fetcher_and_classifies_failures(monkeypatch):
    monkeypatch.setattr(addcards, "fetch_deck_payload", lambda url, **_: {"cards": CARDS})
    assert scrape_canary.check_deck("archidekt", SAMPLE).outcome == "ok"

    def boom(url, **_):
        raise RuntimeError("import_deck: fetch failed: HTTP Error 404: Not Found")
    monkeypatch.setattr(addcards, "fetch_deck_payload", boom)
    c = scrape_canary.check_deck("archidekt", SAMPLE)
    assert (c.outcome, c.code) == ("unverified", "scrape.sample_gone")

    # Real use treats an empty deck as nothing to check; the canary's sample is known to have cards.
    def empty(url, **_):
        raise RuntimeError("import_deck: deck is empty")
    monkeypatch.setattr(addcards, "fetch_deck_payload", empty)
    c = scrape_canary.check_deck("archidekt", SAMPLE)
    assert (c.outcome, c.code) == ("fail", "scrape.expectation")


def test_every_deck_sample_is_checked_except_moxfield_which_needs_the_browser(monkeypatch):
    seen = []
    monkeypatch.setattr(scrape_canary, "check_deck", lambda src, s: seen.append(src) or scrape_canary.Check(sh.deck_key(src), "ok"))
    scrape_canary.check_decks()
    assert sorted(seen) == ["archidekt", "manabox", "mtggoldfish", "scryfall"]


def _cv(name, **kw):
    return {"name": name, "num_decks": 10, "potential_decks": 100, **kw}


def _page(tag_rows: dict) -> dict:
    return {"container": {"json_dict": {"cardlists": [{"tag": t, "cardviews": r} for t, r in tag_rows.items()]}}}


def test_edhrec_checks(monkeypatch):
    monkeypatch.setattr(sh, "canary_samples", lambda: {"edhrec": {"commander": "A", "card": "B", "min_cards": 2,
                                                                  "min_commanders": 1, "min_ranked": 1}})
    monkeypatch.setattr(edhrec, "commander_page", lambda slug: _page({"topcards": [_cv("x"), _cv("y")]}))
    monkeypatch.setattr(edhrec, "card_page", lambda slug: _page({"topcommanders": [{"name": "z"}]}))  # num_decks gone

    def ranking(*a, **k):
        raise edhrec.EdhrecError("edhrec.sh commanders week exited 6: edhrec.sh: HTTP 404 from …")
    monkeypatch.setattr(edhrec, "commanders_ranking", ranking)
    got = {c.key: (c.outcome, c.code) for c in scrape_canary.check_edhrec()}
    assert got == {"edhrec-commander/edhrec": ("ok", None),
                   "edhrec-card/edhrec": ("fail", "scrape.expectation"),
                   "edhrec-rankings/edhrec": ("fail", "scrape.shape_changed")}   # a fixed endpoint moved


class _Resp:
    def __init__(self, status, body=None):
        self.status, self._body, self.url = status, body, "https://api2.moxfield.com/v3/decks/all/ogBt"

    def json(self):
        return self._body


class _Page:
    def __init__(self, title="Moxfield", resp=None, reader=None):
        self._title, self._resp, self._reader = title, resp, reader

    def title(self):
        return self._title

    def goto(self, *a, **k):
        return self._resp

    def wait_for_load_state(self, *a, **k):
        pass

    def add_script_tag(self, **k):
        pass

    def evaluate(self, *a):
        return self._reader

    def close(self):
        pass

    def expect_response(self, *a, **k):
        page = self

        class _Info:
            def __enter__(self):
                if page._resp is None:
                    raise TimeoutError("no deck call")
                self.value = page._resp
                return self

            def __exit__(self, *e):
                return False
        return _Info()


class _Ctx:
    def __init__(self, page):
        self.page = page

    def new_page(self):
        return self.page


MOX = {"url": "https://moxfield.com/decks/ogBt", "min_cards": 1, "card": "Krenko, Mob Boss",
       "commander": "Krenko, Mob Boss"}
MOX_DECK = {"publicId": "ogBt", "name": "D", "boards": {"commanders": {"cards": {"0": {
    "quantity": 1, "isFoil": False, "finish": "nonFoil",
    "card": {"scryfall_id": "11111111-1111-4111-8111-111111111111", "set": "fdn", "cn": "1", "name": "Krenko, Mob Boss"}}}}}}


def test_moxfield_canary_checks_the_server_import_and_the_companion_reader_in_one_visit():
    ok = scrape_canary.check_moxfield(_Ctx(_Page(resp=_Resp(200, MOX_DECK), reader={"ok": True, "deck": MOX_DECK})), MOX)
    assert {(c.key, c.outcome) for c in ok} == {("deck-import/moxfield", "ok"), ("companion-deck/moxfield", "ok")}
    changed = scrape_canary.check_moxfield(_Ctx(_Page(resp=_Resp(200, {"mainboard": []}), reader={"ok": False, "code": "moxfield.changed"})), MOX)
    assert {(c.key, c.outcome, c.code) for c in changed} == {("deck-import/moxfield", "fail", "scrape.no_cards"),
                                                            ("companion-deck/moxfield", "fail", "moxfield.changed")}
    walled = scrape_canary.check_moxfield(_Ctx(_Page(title="Just a moment...", resp=None)), MOX)
    assert {(c.outcome, c.code) for c in walled} == {("unverified", "scrape.blocked")}


class _NavFailPage(_Page):
    def goto(self, *a, **k):
        raise TimeoutError("net::ERR_INTERNET_DISCONNECTED")

    def expect_response(self, *a, **k):
        page = self

        class _Info:
            def __enter__(self):
                return self

            def __exit__(self, *e):
                return False   # let the goto error propagate, as Playwright does
        return _Info()


class _ReaderCrashPage(_Page):
    def evaluate(self, *a):
        raise RuntimeError("readMoxfieldDeck is not defined")


def test_moxfield_navigation_failure_is_unverified_unreachable_for_both_keys():
    got = scrape_canary.check_moxfield(_Ctx(_NavFailPage()), MOX)
    assert {(c.key, c.outcome, c.code) for c in got} == {
        ("deck-import/moxfield", "unverified", "scrape.unreachable"),
        ("companion-deck/moxfield", "unverified", "scrape.unreachable")}


def test_moxfield_reader_crash_fails_only_the_reader_key_and_keeps_the_server_check():
    got = scrape_canary.check_moxfield(_Ctx(_ReaderCrashPage(resp=_Resp(200, MOX_DECK))), MOX)
    assert {(c.key, c.outcome, c.code) for c in got} == {
        ("deck-import/moxfield", "ok", None), ("companion-deck/moxfield", "fail", "moxfield.changed")}
    got = scrape_canary.check_moxfield(_Ctx(_Page(resp=_Resp(200, MOX_DECK), reader=None)), MOX)
    assert ("companion-deck/moxfield", "fail", "moxfield.changed") in {(c.key, c.outcome, c.code) for c in got}


def test_browser_pass_continues_past_a_crashing_target(monkeypatch):
    import sys
    import types
    from magic_manager import browser_launch

    class _C:
        def close(self):
            pass

    class _B:
        def new_context(self, **k):
            return _C()

        def close(self):
            pass

    class _PW:
        def stop(self):
            pass

    pw_mod = types.ModuleType("playwright.sync_api")
    pw_mod.sync_playwright = lambda: types.SimpleNamespace(start=lambda: _PW())
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", pw_mod)
    monkeypatch.setattr(browser_launch, "launch", lambda pw, headless: _B())

    def boom(ctx):
        raise RuntimeError("page crashed")
    targets = [("a", ["k/a"], boom), ("b", ["k/b"], lambda ctx: [scrape_canary.Check("k/b", "ok")])]
    got = {c.key: (c.outcome, c.code) for c in scrape_canary._browser_pass(targets, headless=True, progress=None)}
    assert got == {"k/a": ("unverified", "scrape.unreachable"), "k/b": ("ok", None)}


@pytest.mark.parametrize("reader,outcome,code", [
    ({"ok": False, "code": "cart.empty"}, "ok", None),
    ({"ok": False, "code": "cart.page_changed"}, "fail", "cart.page_changed"),
    ({"ok": False, "code": "cart.sign_in"}, "fail", "scrape.expectation"),
])
def test_cart_canary(reader, outcome, code):
    c = scrape_canary.check_cart(_Ctx(_Page(resp=_Resp(200), reader=reader)), {"url": "https://manapool.com/cart", "expect_code": "cart.empty"})
    assert (c.outcome, c.code) == (outcome, code)


def test_every_cart_reader_has_a_canary_and_its_own_key():
    samples = sh.canary_samples()["cart"]
    assert set(samples) == set(scrape_canary.CART_READERS) == set(sh.CART_STORES)
    targets = {ks[0] for _, ks, _ in scrape_canary._browser_targets() if ks[0].startswith("companion-cart/")}
    assert targets == {f"companion-cart/{s}" for s in sh.CART_STORES}
    c = scrape_canary.check_cart(_Ctx(_Page(resp=_Resp(200), reader={"ok": False, "code": "cart.page_changed"})),
                                 samples["tcgplayer"], "tcgplayer")
    assert (c.key, c.outcome) == ("companion-cart/tcgplayer", "fail")


def test_browser_failures_headless_are_retried_in_a_window_and_never_flag_without_one(monkeypatch):
    calls = []

    def fake_pass(targets, *, headless, progress):
        calls.append((headless, sorted(k for _, ks, _ in targets for k in ks)))
        return [scrape_canary.Check(k, "fail" if headless else "ok", "scrape.no_price" if headless else None)
                for _, ks, _ in targets for k in ks]
    monkeypatch.setattr(scrape_canary, "_browser_pass", fake_pass)
    assert all(c.outcome == "ok" for c in scrape_canary.check_browser())
    assert [h for h, _ in calls] == [True, False]
    calls.clear()
    assert {c.outcome for c in scrape_canary.check_browser(headed=False)} == {"unverified"}
    assert [h for h, _ in calls] == [True]


# ---------- real use feeds health ----------

def test_store_reads_in_deals_record_health(health_file, monkeypatch):
    def fake_read(url, fresh=False, rendered=None):
        price = None if "pokebox" in url else 10.0
        if "costco" in url:
            raise storepage.Blocked("the store blocked the request (403)")
        key = "pokebox" if "pokebox" in url else "manyrealms"
        return vendors.by_key(key), storepage.Listing(price, "USD", True, "Box", "shopify")
    monkeypatch.setattr(storefetch, "read", fake_read)
    deals.read_prices(["https://manyrealms.com/products/a", "https://www.pokeboxusa.com/products/b",
                       "https://www.costco.com/p/-/x/123"])
    assert _status("store-price/manyrealms").status == "ok"
    assert (_status("store-price/pokebox").status, _status("store-price/pokebox").code) == ("down", "scrape.no_price")
    assert _status("store-price/costco").status == "unknown"            # a block says nothing


def test_deck_fetch_in_the_app_records_health(health_file, monkeypatch):
    def boom(url, **_):
        raise RuntimeError("import_deck: no cards parsed (empty deck, or the payload shape changed)")
    monkeypatch.setattr(addcards, "fetch_deck_payload", boom)
    with pytest.raises(RuntimeError):
        addcards.fetch_deck_lines("https://archidekt.com/decks/1")
    assert _status("deck-import/archidekt").status == "down"


# ---------- API ----------

@pytest.fixture
def client(tmp_db, health_file):
    from magic_manager.web.app import create_app
    return TestClient(create_app(serve_frontend=False))


def test_health_api_lists_every_scraper_and_the_down_count(client):
    sh.record([("deck-import/manabox", "fail", "scrape.no_cards", None, None)])
    body = client.get("/api/scrapers/health").json()
    assert body["down"] == 1
    row = next(r for r in body["scrapers"] if r["key"] == "deck-import/manabox")
    assert (row["status"], row["code"], row["site_name"]) == ("down", "scrape.no_cards", "ManaBox")
    assert row["message"] and row["fix"] and row["since"]


def test_report_api_flags_only_page_changed_codes_from_this_app(client):
    r = client.post("/api/scrapers/report", json={"code": "cart.page_changed"})
    assert r.status_code == 200 and (r.json()["key"], r.json()["status"]) == ("companion-cart/manapool", "down")
    r = client.post("/api/scrapers/report", json={"code": "cart.page_changed", "store": "cardkingdom"})
    assert r.status_code == 200 and r.json()["key"] == "companion-cart/cardkingdom"
    assert client.post("/api/scrapers/report", json={"code": "cart.empty"}).status_code == 422
    assert client.post("/api/scrapers/report", json={"code": "moxfield.changed"},
                       headers={"sec-fetch-site": "cross-site"}).status_code == 403


def test_reason_codes_are_plain_and_complete():
    for code, (msg, fix) in sh.REASONS.items():
        assert re.fullmatch(r"[a-z]+\.[a-z_]+", code) and msg.endswith(".") and fix
    assert set(sh.REPORTABLE_CODES) <= set(sh.REASONS)


def test_import_deck_script_tells_an_empty_deck_from_a_changed_shape():
    import importlib.util
    spec = importlib.util.spec_from_file_location("import_deck_script", TESTS.parent / "scripts" / "import_deck.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with pytest.raises(mod.EmptyDeck, match="deck is empty"):
        mod._moxfield_cards({"boards": {"mainboard": {"cards": {}}}})
    assert mod._moxfield_cards({"mainboard": []}) == []      # unrecognised structure → caller says "no cards parsed"
    # Entries present (whatever their shape) are never reported as an empty deck.
    assert mod._moxfield_cards({"boards": {"mainboard": {"cards": {"x": {"renamed": {}}}}}}) != []
    assert mod._moxfield_cards(MOX_DECK)

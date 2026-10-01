"""Phase 0 shared helpers: scryfall_urls.scryfall_search_url,
selectors.materialize_or_raise, and sets.prices_fetched_note.

Pure/offline — no DB or network. scryfall_search_url and prices_fetched_note
are string/format helpers; materialize_or_raise is exercised only on its
error-normalization path (the happy path is covered by the selector tests).
"""

from __future__ import annotations

from unittest import mock

from magic_manager import scryfall_urls, selectors, sets


# ---------- scryfall_search_url ----------

def test_search_url_bare_query_is_quote_plus_encoded():
    url = scryfall_urls.scryfall_search_url('set:sld (cn:1 or cn:2)')
    assert url == "https://scryfall.com/search?q=set%3Asld+%28cn%3A1+or+cn%3A2%29"


def test_search_url_appends_only_given_params():
    assert scryfall_urls.scryfall_search_url("x") == "https://scryfall.com/search?q=x"
    assert scryfall_urls.scryfall_search_url(
        "x", unique="prints", order="usd", dir="asc"
    ) == "https://scryfall.com/search?q=x&unique=prints&order=usd&dir=asc"
    # a single param in isolation
    assert scryfall_urls.scryfall_search_url("x", unique="prints") == \
        "https://scryfall.com/search?q=x&unique=prints"


def test_search_url_encodes_ampersand_and_space():
    # The old edhrec builder used quote() which left '&' bare — Scryfall would
    # read it as a URL-param separator. quote_plus escapes it to %26.
    url = scryfall_urls.scryfall_search_url('!"Fire & Ice"')
    assert "%26" in url
    assert "&unique" not in url  # no stray param boundary introduced by the name


def test_printing_url_chunks_routes_through_the_shared_builder():
    chunks = scryfall_urls.printing_url_chunks([("fin", "1"), ("fin", "2")],
                                               prices=[1.0, 2.0])
    assert chunks[0].url == (
        "https://scryfall.com/search?q="
        "%28set%3Afin+cn%3A%221%22%29+or+%28set%3Afin+cn%3A%222%22%29"
        "&unique=prints&order=usd&dir=asc"
    )


# ---------- materialize_or_raise ----------

def test_materialize_or_raise_wraps_parse_error():
    try:
        selectors.materialize_or_raise("bogus:::")
    except selectors.SelectorInputError as e:
        assert e.message.startswith("error: invalid selector:")
        assert e.exit_code == 2
    else:
        raise AssertionError("expected SelectorInputError")


def test_materialize_or_raise_wraps_lookup_error(monkeypatch):
    # Force materialize to raise a LookupError (e.g. unknown set code).
    monkeypatch.setattr(selectors, "materialize",
                        mock.Mock(side_effect=LookupError("no such set 'zzz'")))
    try:
        selectors.materialize_or_raise("set:zzz")
    except selectors.SelectorInputError as e:
        assert e.message == "error: no such set 'zzz'"
        assert e.exit_code == 2
    else:
        raise AssertionError("expected SelectorInputError")


def test_materialize_or_raise_passes_through_unexpected_errors(monkeypatch):
    # A real bug (not bad user input) must propagate unchanged.
    monkeypatch.setattr(selectors, "materialize",
                        mock.Mock(side_effect=RuntimeError("boom")))
    try:
        selectors.materialize_or_raise("inventory")
    except RuntimeError as e:
        assert str(e) == "boom"
    else:
        raise AssertionError("expected RuntimeError to propagate")


# ---------- prices_fetched_note ----------

def test_prices_note_parenthetical_style(monkeypatch):
    monkeypatch.setattr(sets, "prices_as_of",
                        lambda ids: ("2026-09-30", "2026-09-01"))
    assert sets.prices_fetched_note(["x"]) == \
        "Prices fetched: 2026-09-30 (oldest referenced: 2026-09-01)"


def test_prices_note_range_style_with_period(monkeypatch):
    monkeypatch.setattr(sets, "prices_as_of",
                        lambda ids: ("2026-09-30", "2026-09-01"))
    assert sets.prices_fetched_note(["x"], oldest_style="range", period=True) == \
        "Prices fetched: 2026-09-01–2026-09-30."


def test_prices_note_equal_newest_oldest_collapses(monkeypatch):
    monkeypatch.setattr(sets, "prices_as_of",
                        lambda ids: ("2026-09-30", "2026-09-30"))
    assert sets.prices_fetched_note(["x"]) == "Prices fetched: 2026-09-30"
    assert sets.prices_fetched_note(["x"], oldest_style="range", period=True) == \
        "Prices fetched: 2026-09-30."


def test_prices_note_none_returns_fallback(monkeypatch):
    monkeypatch.setattr(sets, "prices_as_of", lambda ids: (None, None))
    assert sets.prices_fetched_note(["x"]) is None  # caller omits the line
    assert sets.prices_fetched_note(["x"], local_fallback="Prices: local (best-effort).") == \
        "Prices: local (best-effort)."

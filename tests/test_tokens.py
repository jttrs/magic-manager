"""Tests for token tracking (V14).

Tokens are collected and tracked: precon tokens (the MTGJSON `tokens` board) ride
the deck on the new 'token' deck_cards board AND flow to inventory; deck_show
orders token last; and a one-off backfill moves pre-V14 tokens off the 'main'
board. Read paths that treat the deck as its PLAYABLE recipe (deck_value, the
deck:<slug> selector feeding exports, compose/construct-from-loose) EXCLUDE the
token board. (Missing-set token exclusion is tested in
test_missing_printings.py::test_tokens_excluded_even_when_rare_or_emblem.)

Offline: tmp_db + fake_scryfall (drives import_precon's auto-sync) + fake_mtgjson.
"""

from __future__ import annotations

import pytest


def test_import_precon_captures_token_board(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """A precon's `tokens` board lands on deck_cards board='token' AND inventory."""
    from magic_manager import decks, db
    sids = ["cmd1", "main1", "tok1"]
    deck = make_precon_deck(
        "Turtle Power!", "Commander Deck",
        [{"sid": sids[0], "name": "Cmdr", "set": "tmc", "cn": "1", "count": 1, "board": "commander"},
         {"sid": sids[1], "name": "Body", "set": "tmc", "cn": "2", "count": 40, "board": "mainBoard"},
         {"sid": sids[2], "name": "Turtle Token", "set": "ttmc", "cn": "3", "count": 4, "board": "tokens"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[
        make_card(id=sids[0], set="tmc", collector_number="1", name="Cmdr"),
        make_card(id=sids[1], set="tmc", collector_number="2", name="Body"),
        make_card(id=sids[2], set="ttmc", collector_number="3", name="Turtle Token", layout="token"),
    ])

    result = decks.import_precon("TurtlePower_TMC")

    with db.connect() as conn:
        board = conn.execute(
            "SELECT board, count FROM deck_cards dc "
            "JOIN decks d ON d.current_version_id=dc.deck_version_id "
            "WHERE d.slug=? AND dc.scryfall_id=?", (result["effective_slugs"][0], "tok1")
        ).fetchone()
        assert board is not None, "token card not added to the deck recipe"
        assert board["board"] == "token"
        assert board["count"] == 4
        inv = conn.execute(
            "SELECT quantity FROM inventory WHERE scryfall_id='tok1'").fetchone()
        assert inv is not None and inv["quantity"] == 4, "token not added to inventory"
    # inv_qty_total counts the 4 tokens too (40 main + 1 cmdr + 4 token = 45)
    assert result["inv_qty_total"] == 45


def test_deck_value_excludes_token_board(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """deck_value reflects the PLAYABLE recipe only — token/emblem boards are
    excluded (a deck's $ isn't its tokens). Regression for the token read-path
    leak: pre-fix this summed tokens into the total."""
    from magic_manager import decks
    deck = make_precon_deck(
        "Tok Value", "Commander Deck",
        [{"sid": "b1", "name": "Body", "set": "tmc", "cn": "1", "count": 1, "board": "mainBoard"},
         {"sid": "t1", "name": "Pricey Token", "set": "ttmc", "cn": "2", "count": 2, "board": "tokens"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[
        make_card(id="b1", set="tmc", collector_number="1", name="Body",
                  prices={"usd": "1.00", "usd_foil": None}),
        make_card(id="t1", set="ttmc", collector_number="2", name="Pricey Token",
                  layout="token", prices={"usd": "5.00", "usd_foil": None}),
    ])
    slug = decks.import_precon("TokValue_TMC")["effective_slugs"][0]
    val = decks.deck_value(slug)
    # 1×$1 body only; the 2×$5 token board is excluded → $1 (not $11).
    assert val["total"] == pytest.approx(1.0)


def test_deck_show_orders_token_last(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    from magic_manager import decks
    deck = make_precon_deck(
        "Order Test", "Commander Deck",
        [{"sid": "c", "name": "Cmdr", "set": "tmc", "cn": "1", "count": 1, "board": "commander"},
         {"sid": "m", "name": "Body", "set": "tmc", "cn": "2", "count": 1, "board": "mainBoard"},
         {"sid": "t", "name": "Tok", "set": "ttmc", "cn": "3", "count": 1, "board": "tokens"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[
        make_card(id="c", set="tmc", collector_number="1", name="Cmdr"),
        make_card(id="m", set="tmc", collector_number="2", name="Body"),
        make_card(id="t", set="ttmc", collector_number="3", name="Tok", layout="token"),
    ])
    slug = decks.import_precon("OrderTest_TMC")["effective_slugs"][0]
    boards = [r.board for r in decks.deck_show(slug)]
    assert boards == ["commander", "main", "token"], f"unexpected order: {boards}"


def test_backfill_token_board_idempotent(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """A token mis-filed on 'main' (pre-V14 state) moves to 'token' on run 1 and
    is a no-op on run 2."""
    from magic_manager import decks, db
    # Import a deck whose token is (simulating the old bug) on the main board.
    deck = make_precon_deck(
        "Legacy", "Commander Deck",
        [{"sid": "real", "name": "Body", "set": "tmc", "cn": "1", "count": 1, "board": "mainBoard"},
         {"sid": "legacytok", "name": "Legacy Token", "set": "ttmc", "cn": "2", "count": 3, "board": "mainBoard"}],
    )
    fake_mtgjson(deck=deck)
    fake_scryfall(search=[
        make_card(id="real", set="tmc", collector_number="1", name="Body"),
        make_card(id="legacytok", set="ttmc", collector_number="2", name="Legacy Token", layout="token"),
    ])
    decks.import_precon("Legacy_TMC")
    # Precondition: the token is on 'main' (import put it there because we faked
    # it onto mainBoard, and is_token=1 in cards).
    with db.connect() as conn:
        pre = conn.execute("SELECT board FROM deck_cards WHERE scryfall_id='legacytok'").fetchone()
        assert pre["board"] == "main"

    moved1 = decks.backfill_token_board()
    assert moved1 == 1
    moved2 = decks.backfill_token_board()
    assert moved2 == 0, "backfill should be idempotent"

    with db.connect() as conn:
        post = conn.execute("SELECT board FROM deck_cards WHERE scryfall_id='legacytok'").fetchone()
        assert post["board"] == "token"
        # the non-token main card stayed put
        assert conn.execute("SELECT board FROM deck_cards WHERE scryfall_id='real'").fetchone()["board"] == "main"


# ---------- token READ-PATH exclusion (the post-review remediation) ----------

def _precon_with_token(fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """Import a precon with a commander + a token; return its slug."""
    from magic_manager import decks
    fake_mtgjson(deck=make_precon_deck(
        "Tok Deck", "Commander Deck",
        [{"sid": "c1", "name": "Cmdr", "set": "tmc", "cn": "1", "count": 1, "board": "commander"},
         {"sid": "tk", "name": "Goblin Token", "set": "ttmc", "cn": "2", "count": 1, "board": "tokens"}]))
    fake_scryfall(search=[
        make_card(id="c1", set="tmc", collector_number="1", name="Cmdr",
                  prices={"usd": "2.00", "usd_foil": None}),
        make_card(id="tk", set="ttmc", collector_number="2", name="Goblin Token",
                  layout="token", prices={"usd": "9.00", "usd_foil": None}),
    ])
    return decks.import_precon("TokDeck_TMC")["effective_slugs"][0]


def test_deck_selector_excludes_tokens_from_exports_and_value(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """The deck:<slug> selector (feeds exports + query value) must not emit the
    token board; `deck show` (decks.deck_show) still shows it."""
    from magic_manager import selectors, decks
    slug = _precon_with_token(fake_scryfall, fake_mtgjson, make_card, make_precon_deck)
    rows = selectors.materialize(f"deck:{slug}")
    sids = {r.scryfall_id for r in rows}
    assert "c1" in sids
    assert "tk" not in sids, "token leaked into the deck: selector (exports/value)"
    # deck_show (the `mm deck show` path) still lists the token.
    assert "tk" in {r.scryfall_id for r in decks.deck_show(slug)}


def test_construct_from_loose_ignores_tokens(
        tmp_db, fake_scryfall, fake_mtgjson, make_card, make_precon_deck):
    """construct_precon_from_loose must NOT count the precon's tokens as
    shortfalls: owning the playable card (loose) should fully compose without
    --allow-shortfall, even though the token is never in inventory."""
    from magic_manager import decks, inventory, db
    # Seed cards + own the commander loose (NOT the token).
    fake_mtgjson(deck=make_precon_deck(
        "Loose Tok", "Commander Deck",
        [{"sid": "lc", "name": "Cmdr", "set": "tmc", "cn": "1", "count": 1, "board": "commander"},
         {"sid": "ltk", "name": "Token", "set": "ttmc", "cn": "2", "count": 1, "board": "tokens"}]))
    cards = [
        make_card(id="lc", set="tmc", collector_number="1", name="Cmdr"),
        make_card(id="ltk", set="ttmc", collector_number="2", name="Token", layout="token"),
    ]
    with db.connect() as conn:
        db.upsert_cards(conn, cards)
        inventory.inventory_add("lc", "nonfoil", 1, conn=conn)  # own commander loose, not token
    fake_scryfall(search=cards)

    # Must NOT raise AssignmentOverflow (tokens excluded from the plan).
    res = decks.construct_precon_from_loose("LooseTok_TMC")
    assert res["fully_covered"] is True
    assert res["assigned_qty"] == 1  # the commander; token not pledged
    # inventory untouched; token never entered inventory.
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM inventory WHERE scryfall_id='ltk'").fetchone()[0] == 0


def test_v15_migration_backfills_is_token(tmp_db):
    """The V15 python hook re-derives is_token from stored type_line (layout is
    not stored) for rows the old narrow projection missed."""
    from magic_manager import db
    with db.connect() as conn:
        # Simulate a pre-V15 row: an emblem stored with is_token=0.
        conn.execute(
            "INSERT INTO cards (scryfall_id, oracle_id, name, set_code, collector_number, "
            "rarity, type_line, is_token) VALUES "
            "('emb1','o-emb','The Ring Emblem','tmc','99','rare','Emblem', 0)"
        )
        db._run_v15_python_migration(conn)
        assert conn.execute("SELECT is_token FROM cards WHERE scryfall_id='emb1'").fetchone()[0] == 1

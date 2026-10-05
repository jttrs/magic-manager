"""Deck Manager engine: summaries of every tracked deck and one deck's cards
with exact printings and owned / pledged / free counts.

Single source of truth behind :mod:`magic_manager.api.decks`.
"""
from __future__ import annotations

import json

from . import addcards, db, decks, inventory, mtgjson, scryfall
from .decks import _BOARD_ORDER_SQL

# Per-deck aggregates over the CURRENT version's non-token rows, set-based.
# image: the commander's art if any, else the priciest card's (window function).
_SUMMARY_SQL = """
WITH rows_ AS (
    SELECT d.deck_id, dc.board, dc.count, c.image_uri,
           COALESCE(CASE WHEN dc.finish = 'foil' THEN c.prices_usd_foil ELSE c.prices_usd END, 0) AS unit
    FROM decks d
    JOIN deck_cards dc ON dc.deck_version_id = d.current_version_id AND dc.board != 'token'
    JOIN cards c ON c.scryfall_id = dc.scryfall_id
    {where}
), agg AS (
    SELECT deck_id, SUM(count) AS cards, SUM(count * unit) AS value FROM rows_ GROUP BY deck_id
), img AS (
    SELECT deck_id, image_uri FROM (
        SELECT deck_id, image_uri,
               ROW_NUMBER() OVER (PARTITION BY deck_id
                                  ORDER BY (board = 'commander') DESC, unit DESC) AS rn
        FROM rows_ WHERE image_uri IS NOT NULL
    ) WHERE rn = 1
), pl AS (
    SELECT deck_id, SUM(count) AS pledged FROM deck_assignments GROUP BY deck_id
)
SELECT d.deck_id, d.slug, d.name, d.format, d.precon_state, d.source_precon_file_name,
       d.source, d.author, d.source_set_code, d.kind,
       COALESCE(agg.cards, 0) AS cards, COALESCE(agg.value, 0) AS value,
       COALESCE(pl.pledged, 0) AS pledged, img.image_uri
FROM decks d
LEFT JOIN agg ON agg.deck_id = d.deck_id
LEFT JOIN img ON img.deck_id = d.deck_id
LEFT JOIN pl ON pl.deck_id = d.deck_id
{dwhere}
"""


def _precon_index() -> dict[str, dict]:
    try:
        return mtgjson._decklist_by_filename()
    except Exception:
        return {}


def _sets_index() -> dict[str, dict]:
    try:
        return {s["code"].lower(): s for s in scryfall.all_sets() if s.get("code")}
    except Exception:
        return {}


# Deck type = the game format the deck is built for. Scryfall's format keys
# (legalities) plus deck-builder spellings; precons without a format fall back to
# their MTGJSON product type. Labels are what the UI filters and groups on.
_FORMAT_LABEL = {
    "commander": "Commander", "edh": "Commander", "duel": "Commander",
    "brawl": "Brawl", "standardbrawl": "Brawl", "historicbrawl": "Brawl",
    "paupercommander": "Pauper Commander", "pdh": "Pauper Commander",
    "oathbreaker": "Oathbreaker", "predh": "Commander",
    "standard": "Standard", "future": "Standard", "pioneer": "Pioneer",
    "modern": "Modern", "legacy": "Legacy", "vintage": "Vintage",
    "pauper": "Pauper", "premodern": "Premodern", "oldschool": "Old School",
    "historic": "Arena", "timeless": "Arena", "alchemy": "Arena", "explorer": "Arena", "gladiator": "Arena",
    "penny": "Penny Dreadful", "jumpstart": "Jumpstart",
    "limited": "Limited", "draft": "Limited", "sealed": "Limited", "cube": "Cube",
}
_PRODUCT_TYPE_LABEL = {
    "Commander Deck": "Commander", "Brawl Deck": "Brawl", "Jumpstart": "Jumpstart",
    "Enemy Deck": "Archenemy", "Archenemy Deck": "Archenemy", "Planechase Deck": "Planechase",
    "Secret Lair Drop": "Secret Lair", "Bundle Land Pack": "Land pack",
    "Challenger Deck": "Standard", "Game Night Deck": "Game Night", "Clash Pack": "Starter / intro",
    "Box Set": "Starter / intro", "Starter Kit": "Starter / intro", "Starter Deck": "Starter / intro",
    "Theme Deck": "Starter / intro", "Welcome Deck": "Starter / intro", "Intro Pack": "Starter / intro",
    "Planeswalker Deck": "Starter / intro", "Duel Deck": "Starter / intro", "Guild Kit": "Starter / intro",
}


def deck_type(fmt: str | None, product_type: str | None) -> str:
    """One label for what kind of deck this is (see ``_FORMAT_LABEL``)."""
    key = (fmt or "").strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    if key:
        return _FORMAT_LABEL.get(key, (fmt or "").strip().title())
    return _PRODUCT_TYPE_LABEL.get(product_type or "", "Other")


def _summaries(where: str = "", params: tuple = ()) -> list[dict]:
    """One summary per deck ROW matching ``where`` (a SQL predicate on ``d``)."""
    clause = f"WHERE {where}" if where else ""
    sql = _SUMMARY_SQL.format(where=clause, dwhere=clause)
    with db.connect() as conn:
        rows = conn.execute(sql, params + params).fetchall()
    precons, sets = _precon_index(), _sets_index()
    out = []
    for r in rows:
        fn = r["source_precon_file_name"]
        entry = precons.get(fn) if fn else None
        if fn:
            origin, source = "precon", (entry or {}).get("type")
            code = ((entry or {}).get("code") or "").lower() or None
            released = (entry or {}).get("releaseDate")
        else:
            origin = "import" if r["source"] else "custom"
            source = r["source"] or None
            code = (r["source_set_code"] or "").lower() or None
            released = None
        sset = sets.get(code) if code else None
        released = released or (sset or {}).get("released_at")
        cards = int(r["cards"])
        out.append({
            "slug": r["slug"], "name": r["name"], "format": r["format"],
            "deck_type": deck_type(r["format"], source if origin == "precon" else None),
            "state": r["precon_state"], "origin": origin, "source": source,
            "author": r["author"], "set_code": code,
            "set_name": (sset or {}).get("name"), "released": released,
            "cards": cards, "value_usd": round(float(r["value"]), 2),
            "pledged_pct": round(100.0 * min(1, r["pledged"] / cards), 1) if cards else 0.0,
            "image_uri": r["image_uri"],
            "_kind": r["kind"], "_recipe": fn or r["slug"],
        })
    return out


def _group(rows: list[dict]) -> list[dict]:
    """Collapse deck rows into recipes: precon copies of one fileName become one
    summary (built/loose counts, every copy's slug); the representative is the
    first copy, built ones first then by slug. Recipe facts are identical across
    copies, so every other field comes from the representative."""
    groups: dict[str, list[dict]] = {}
    for r in sorted(rows, key=lambda r: (r["state"] != "built", r["slug"])):
        groups.setdefault(r["_recipe"], []).append(r)
    out = []
    for copies in groups.values():
        built = sum(1 for c in copies if c["state"] == "built")
        rep = {k: v for k, v in copies[0].items() if not k.startswith("_")}
        rep.update(built=built, loose=len(copies) - built, slugs=[c["slug"] for c in copies],
                   state="built" if built else "deconstructed")
        out.append(rep)
    return out


def deck_summaries() -> list[dict]:
    """Playable recipes only (kind='deck'), precon copies grouped."""
    if decks.unclassified_precon_count():
        decks.backfill_kinds()  # lazy one-off: rows predating V29 have no kind yet
    out = _group([r for r in _summaries("d.kind = 'deck'")])
    out.sort(key=lambda d: d["name"])
    out.sort(key=lambda d: d["released"] or "", reverse=True)
    # released desc with nulls last (stable: name order kept within ties)
    out.sort(key=lambda d: d["released"] is None)
    return out


def deck_detail(slug: str) -> dict:
    with db.connect() as conn:
        row = conn.execute("SELECT source_precon_file_name FROM decks WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise LookupError(f"deck with slug {slug!r} not found")
    fn = row["source_precon_file_name"]
    # The whole recipe group (any copy, pool or deck), so the inspector shows ×built/×loose.
    found = _group(_summaries("d.source_precon_file_name = ?", (fn,)) if fn
                   else _summaries("d.slug = ?", (slug,)))
    with db.connect() as conn:
        deck_id = conn.execute("SELECT deck_id FROM decks WHERE slug = ?", (slug,)).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT dc.scryfall_id, dc.board, dc.finish, dc.count, c.type_line, c.cmc,
                   c.color_identity, c.name,
                   (SELECT COALESCE(SUM(a.count), 0) FROM deck_assignments a
                     WHERE a.deck_id = d.deck_id AND a.scryfall_id = dc.scryfall_id) AS pledged_here
            FROM decks d
            JOIN deck_cards dc ON dc.deck_version_id = d.current_version_id
            JOIN cards c ON c.scryfall_id = dc.scryfall_id
            WHERE d.deck_id = ?
            ORDER BY {_BOARD_ORDER_SQL.replace('board', 'dc.board')}, c.cmc, c.name
            """,
            (deck_id,),
        ).fetchall()
    sids = [r["scryfall_id"] for r in rows]
    printings = addcards.printings_for_ids(sids)
    free = inventory.free_quantities(sids)
    cards = []
    for r in rows:
        sid = r["scryfall_id"]
        if sid not in printings:
            continue
        cards.append({
            "printing": printings[sid], "board": r["board"], "finish": r["finish"],
            "count": r["count"], "type_line": r["type_line"], "cmc": r["cmc"],
            "color_identity": json.loads(r["color_identity"]) if r["color_identity"] else [],
            "pledged_here": r["pledged_here"], "free": free.get(sid, 0),
        })
    return {"deck": found[0], "cards": cards}

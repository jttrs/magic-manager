"""Earmarked cards — singles you're interested in, owned or not (V37).

A card earmark marks a CARD (``oracle_id``) as "of interest": something you
mean to collect, or an idea for a deck. Each carries an optional preferred
printing + finish, an optional ``reason`` (``collect`` | ``deck``), an optional
pointer to a deck (that deck's Earmarked tab lists it under "For this deck"; the
decklist itself is never touched) and an optional note.

Store-independent, so deliberately NOT the V12/V31 ``earmarked_products`` store
watchlist (every row there is a storefront URL + asking price) — the two share a
shape (identity checkpoint → CRUD → enriched listing), not tables.

:func:`for_deck` is the deterministic deck filter behind the editor's Earmarked
tab: format legality from Scryfall's per-format legalities, and for
Commander-like formats the card's colour identity within the commander's (the
union over partners). Illegal cards are returned with plain-words reasons, never
silently dropped.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

from . import db, decks, legality

REASONS = ("collect", "deck")
FINISHES = ("nonfoil", "foil")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


@dataclass
class CardEarmark:
    oracle_id: str
    name: str
    scryfall_id: str | None
    finish: str | None
    reason: str | None
    deck_slug: str | None
    deck_name: str | None
    note: str | None
    earmarked_at: str
    updated_at: str

    def to_json(self) -> dict:
        return asdict(self)


_SELECT = """SELECT e.oracle_id, e.name, e.scryfall_id, e.finish, e.reason, d.slug AS deck_slug,
                    d.name AS deck_name, e.note, e.earmarked_at, e.updated_at
             FROM card_earmarks e LEFT JOIN decks d ON d.deck_id = e.deck_id"""


def _row(r) -> CardEarmark:
    return CardEarmark(**{k: r[k] for k in CardEarmark.__dataclass_fields__})


# ---------- identity ----------

def resolve_card(ref: str) -> dict:
    """``ref`` (a card name or a scryfall_id) → ``{oracle_id, name, scryfall_id}``.
    Local first; a printing or name the catalog lacks is fetched from Scryfall
    once and upserted. Raises ``LookupError``."""
    from . import addcards, edhrec

    ref = (ref or "").strip()
    if not ref:
        raise LookupError("name a card")
    if _UUID.match(ref):
        addcards.ensure_printings([ref])
        with db.connect() as conn:
            r = conn.execute("SELECT oracle_id, name, scryfall_id FROM cards WHERE scryfall_id = ?", (ref,)).fetchone()
        if r is None or not r["oracle_id"]:
            raise LookupError(f"no printing {ref}")
        return {"oracle_id": r["oracle_id"], "name": r["name"], "scryfall_id": r["scryfall_id"]}
    hit = edhrec.resolve_names_to_oracle([ref]).get(ref.casefold())
    if not hit or not hit.get("oracle_id"):
        raise LookupError(f"no card named {ref!r}")
    return {"oracle_id": hit["oracle_id"], "name": hit.get("name") or ref, "scryfall_id": hit.get("scryfall_id")}


def printing_ref(set_code: str, collector_number: str) -> str:
    """``SET`` + ``CN`` → the printing's scryfall_id (local, else Scryfall). Raises ``LookupError``."""
    from . import earmarks

    row = earmarks.printing_row(set_code, collector_number)
    if row is None:
        raise LookupError(f"no printing {set_code.upper()} #{collector_number}")
    return row["scryfall_id"]


# ---------- CRUD ----------

def save(card: str, *, printing: str | None = None, finish: str | None = None, reason: str | None = None,
         deck: str | None = None, note: str | None = None) -> CardEarmark:
    """Earmark a card (or replace its earmark's details). ``card`` is a name or
    any printing's scryfall_id; ``printing`` (a scryfall_id of the SAME card) is
    the preferred printing, ``finish`` its finish; ``deck`` a deck slug. Every
    field is set as given (None clears it). Raises ``LookupError`` / ``ValueError``."""
    from . import addcards

    ident = resolve_card(card)
    if reason is not None and reason not in REASONS:
        raise ValueError(f"reason must be one of {', '.join(REASONS)}")
    if finish is not None and finish not in FINISHES:
        raise ValueError(f"finish must be one of {', '.join(FINISHES)}")
    if finish is not None and printing is None:
        raise ValueError("a finish needs a preferred printing")
    note = (note or "").strip() or None
    if note and len(note) > 500:
        raise ValueError("keep the note under 500 characters")
    if printing:
        addcards.ensure_printings([printing])
    now = db._utcnow_iso()
    with db.transaction() as conn:
        deck_id = None
        if deck:
            row = decks._fetch_deck(conn, deck)
            if row is None:
                raise LookupError(f"no deck {deck!r}")
            deck_id = row["deck_id"]
        if printing:
            db.require_cards(conn, [printing])
            p = conn.execute("SELECT oracle_id, finishes, name FROM cards WHERE scryfall_id = ?", (printing,)).fetchone()
            if p["oracle_id"] != ident["oracle_id"]:
                raise ValueError(f"that printing is {p['name']!r}, not {ident['name']!r}")
            if finish and finish not in json.loads(p["finishes"] or "[]"):
                raise ValueError(f"that printing has no {finish} finish")
        conn.execute(
            """INSERT INTO card_earmarks (oracle_id, name, scryfall_id, finish, reason, deck_id, note, earmarked_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(oracle_id) DO UPDATE SET name = excluded.name, scryfall_id = excluded.scryfall_id,
                   finish = excluded.finish, reason = excluded.reason, deck_id = excluded.deck_id,
                   note = excluded.note, updated_at = excluded.updated_at""",
            (ident["oracle_id"], ident["name"], printing, finish, reason, deck_id, note, now, now),
        )
        r = conn.execute(f"{_SELECT} WHERE e.oracle_id = ?", (ident["oracle_id"],)).fetchone()
    return _row(r)


def remove(oracle_id: str) -> bool:
    """Drop a card's earmark. True when there was one."""
    with db.transaction() as conn:
        return conn.execute("DELETE FROM card_earmarks WHERE oracle_id = ?", (oracle_id,)).rowcount > 0


def listing(*, reason: str | None = None, deck: str | None = None) -> list[CardEarmark]:
    """Every earmark, newest first; optionally only one reason or one deck's."""
    sql, args = _SELECT, []
    where = []
    if reason:
        where.append("e.reason = ?")
        args.append(reason)
    if deck:
        where.append("d.slug = ?")
        args.append(deck)
    if where:
        sql += " WHERE " + " AND ".join(where)
    with db.connect() as conn:
        return [_row(r) for r in conn.execute(sql + " ORDER BY e.updated_at DESC, e.earmark_id DESC", args)]


def marks(oracle_ids) -> set[str]:
    """Which of these cards are earmarked (one batched lookup, for list views)."""
    oids = list(dict.fromkeys(o for o in oracle_ids if o))
    out: set[str] = set()
    with db.connect() as conn:
        for i in range(0, len(oids), 500):
            part = oids[i:i + 500]
            out |= {r[0] for r in conn.execute(
                f"SELECT oracle_id FROM card_earmarks WHERE oracle_id IN ({','.join('?' * len(part))})", part)}
    return out


# ---------- enriched entries ----------

def entries(earmarks: list[CardEarmark]) -> list[dict]:
    """Each earmark with the printing to show/add (the preferred one, else your
    most-free printing, else its first standard one — ``deck_edit.usable_printings``),
    PrintingOut-shaped, plus copies owned / free across printings. Earmarks whose
    card has no local printing get ``printing`` None."""
    from . import addcards, deck_edit

    pick, owned_by_oracle, free = deck_edit.usable_printings([e.oracle_id for e in earmarks])
    sids = {e.oracle_id: e.scryfall_id or pick.get(e.oracle_id) for e in earmarks}
    printings = addcards.printings_for_ids([s for s in sids.values() if s])
    out = []
    for e in earmarks:
        mine = owned_by_oracle.get(e.oracle_id, [])
        out.append({
            "earmark": e.to_json(), "printing": printings.get(sids[e.oracle_id] or ""),
            "owned": sum(q for _, q in mine), "free": sum(free.get(s, 0) for s, _ in mine),
        })
    return out


# ---------- the deck filter ----------

_COLOR = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}


def _colours(ci) -> str:
    return ", ".join(_COLOR.get(c, c) for c in "WUBRG" if c in set(ci)) or "colorless"


def _oracle_facts(conn, oids: list[str]) -> dict[str, dict]:
    """Per oracle: colour identity + legalities (identical across printings; first
    printing that has legalities wins)."""
    out: dict[str, dict] = {}
    for i in range(0, len(oids), 500):
        part = oids[i:i + 500]
        for r in conn.execute(
            f"""SELECT oracle_id, color_identity, legalities FROM cards
                WHERE oracle_id IN ({','.join('?' * len(part))}) ORDER BY legalities IS NULL""", part,
        ):
            if r["oracle_id"] in out:
                continue
            out[r["oracle_id"]] = {
                "ci": json.loads(r["color_identity"]) if r["color_identity"] else [],
                "legalities": json.loads(r["legalities"]) if r["legalities"] else None,
            }
    return out


def _blocker(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def blockers(fmt: str | None, commander_ci: set[str] | None, facts: dict | None) -> list[dict]:
    """Why a card can't go in a deck of ``fmt`` led by ``commander_ci`` (None = no
    commander yet): ``[{code, message}]`` with ``code`` ∈ not_in_catalog |
    no_legality | banned | not_legal | colour_identity; [] when it can. The one
    rule the tab and tests share."""
    from . import deck_view

    if facts is None:
        return [_blocker("not_in_catalog", "Not in your card catalog yet — open it once to load it")]
    out = []
    if fmt:
        legal = facts["legalities"]
        label = deck_view.deck_type(fmt, None)
        if not legal:
            out.append(_blocker("no_legality", "No legality data — sync its set"))
        elif fmt in legal:
            status = legal[fmt]
            if status == "banned":
                out.append(_blocker("banned", f"Banned in {label}"))
            elif status not in ("legal", "restricted"):
                out.append(_blocker("not_legal", f"Not legal in {label}"))
    if commander_ci is not None and not set(facts["ci"]) <= commander_ci:
        out.append(_blocker("colour_identity", f"Outside the commander’s colors ({_colours(commander_ci)})"))
    return out


def _rule(fmt: str, commander_ci: set[str] | None) -> str:
    """The filter in words, for the tab's header."""
    from . import deck_view

    if not fmt:
        return "No format set, so nothing is filtered"
    parts = [f"Legal in {deck_view.deck_type(fmt, None)}"]
    if fmt in legality._COMMANDER_LIKE_FORMATS:
        parts.append(f"within {_colours(commander_ci)}" if commander_ci is not None
                     else "no commander yet, so colors aren’t checked")
    return " · ".join(parts)


def for_deck(slug: str, draft) -> dict:
    """Earmarked cards for a deck being edited. ``draft`` = the editor's unsaved
    ``deck_edit.DraftCard`` rows (so a commander just added counts); the format
    rule is ``deck_edit.draft_rows``'s. Returns ``{format, commander_colors, rule,
    for_deck, legal, hidden}``: ``for_deck`` = earmarks pointed at this deck
    (always shown, any blockers attached as ``reasons``), ``legal`` = the rest
    that fit, ``hidden`` = the rest that don't, each with ``reasons``. Every entry
    carries ``in_deck`` (the card is already in the draft, any board)."""
    from . import deck_edit

    fmt, rows = deck_edit.draft_rows(slug, draft)
    commander_ci: set[str] | None = None
    if fmt in legality._COMMANDER_LIKE_FORMATS:
        leaders = [r for r in rows if r["board"] == "commander"]
        if leaders:
            commander_ci = {c for r in leaders for c in r["color_identity"]}
    in_draft = {r["oracle_id"] for r in rows}
    marks_ = listing()
    with db.connect() as conn:
        facts = _oracle_facts(conn, [e.oracle_id for e in marks_])
    out: dict = {"format": fmt or None,
                 "commander_colors": sorted(commander_ci, key="WUBRG".index) if commander_ci is not None else None,
                 "rule": _rule(fmt, commander_ci), "for_deck": [], "legal": [], "hidden": []}
    for e, entry in zip(marks_, entries(marks_)):
        entry["in_deck"] = e.oracle_id in in_draft
        entry["reasons"] = blockers(fmt or None, commander_ci, facts.get(e.oracle_id))
        if e.deck_slug == slug:
            out["for_deck"].append(entry)
        elif entry["reasons"]:
            out["hidden"].append(entry)
        else:
            out["legal"].append(entry)
    return out

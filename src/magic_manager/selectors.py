"""V2 selector grammar — parse + materialize.

A selector is a TERM optionally followed by MODIFIERs. The TERM picks the
universe of (printing, finish, qty) tuples to consider; MODIFIERs filter
or set-operate that universe down to the final result.

Grammar (BNF):

    SELECTOR ::= TERM (' ' MODIFIER)*

    TERM ::=
        | 'inventory'                 — every printing I own (qty>0)
        | 'wishlist' [':' CATEGORY]   — every wishlist entry, optionally one category
        | 'deck:' SLUG                — every card in a named deck
        | 'set:' CODE ['+related']    — every printing in a set/family from cards table
        | 'cards:' SCRYFALL_QUERY     — Scryfall API query, intersected with cards table
        | 'scryfall:' SCRYFALL_QUERY  — live Scryfall API query (qty=1 nonfoil placeholders)

    MODIFIER ::=
        | 'missing' | 'missing:nonfoil' | 'missing:foil' | 'missing:either'
        | 'owned'
        | 'qty>=N' | 'qty<=N' | 'qty=N'
        | 'finish=foil' | 'finish=nonfoil'
        | 'rarity=common|uncommon|rare|mythic|special|bonus'
        | 'cn>=N' | 'cn<=N'
        | 'value>=N' | 'value<=N'
        | 'scryfall:Q'                — POST-FILTER, AND-ed with the term

Modifiers are pure filters and commute — order in the selector doesn't
affect the result. The materializer evaluates the TERM, then applies all
modifiers as set operations / row filters.
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field

from . import db, scryfall, sets as sets_mod


# ---------- AST ----------

VALID_TERMS = ("inventory", "wishlist", "deck", "set", "cards", "scryfall")
VALID_MODIFIERS = (
    "missing", "owned",
    "qty", "finish", "rarity", "cn", "value",
    "scryfall",
)
VALID_RARITIES = ("common", "uncommon", "rare", "mythic", "special", "bonus")
VALID_FINISHES = ("nonfoil", "foil")
VALID_MISSING_FINISHES = ("nonfoil", "foil", "either")


@dataclass
class Term:
    kind: str               # one of VALID_TERMS
    arg: str | None = None  # category for wishlist, slug for deck, code for set, query for cards/scryfall
    include_related: bool = False  # set:CODE+related


@dataclass
class Modifier:
    kind: str               # one of VALID_MODIFIERS
    op: str | None = None   # for qty/cn/value: '>=', '<=', '='. for missing: ':finish'
    value: str | None = None


@dataclass
class Selector:
    term: Term
    modifiers: list[Modifier] = field(default_factory=list)


@dataclass
class MaterializedRow:
    scryfall_id: str
    quantity: int
    finish: str             # 'nonfoil' | 'foil' (modifiers normalize 'either')
    card: dict              # cards-table row normalized to dict


# ---------- parse ----------

class SelectorParseError(ValueError):
    """Raised when a selector string can't be parsed."""


def parse(s: str) -> Selector:
    """Parse a selector string into a Selector AST.

    Raises SelectorParseError on any malformed input. The error message
    points at the specific token that failed and lists the valid choices.
    """
    if not s or not s.strip():
        raise SelectorParseError("empty selector")

    try:
        tokens = shlex.split(s.strip(), posix=True)
    except ValueError as e:
        raise SelectorParseError(f"cannot tokenize selector {s!r}: {e}") from e

    if not tokens:
        raise SelectorParseError("empty selector")

    term = _parse_term(tokens[0])
    modifiers = [_parse_modifier(tok) for tok in tokens[1:]]
    sel = Selector(term=term, modifiers=modifiers)
    _validate_combination(sel)
    return sel


def _parse_term(tok: str) -> Term:
    low = tok.lower()
    if low == "inventory":
        return Term(kind="inventory")
    if low == "wishlist":
        return Term(kind="wishlist", arg=None)
    if low.startswith("wishlist:"):
        cat = tok.split(":", 1)[1].strip()
        if not cat:
            raise SelectorParseError("wishlist: term needs a category after the colon (or use 'wishlist' for all)")
        return Term(kind="wishlist", arg=cat)
    if low.startswith("deck:"):
        slug = tok.split(":", 1)[1].strip()
        if not slug:
            raise SelectorParseError("deck: term needs a slug after the colon")
        return Term(kind="deck", arg=slug)
    if low.startswith("set:"):
        rest = tok.split(":", 1)[1].strip()
        if not rest:
            raise SelectorParseError("set: term needs a code after the colon")
        include_related = False
        if rest.endswith("+related"):
            include_related = True
            rest = rest[: -len("+related")]
        if not rest or not re.fullmatch(r"[a-zA-Z0-9]+", rest):
            raise SelectorParseError(f"set: code must be alphanumeric, got {rest!r}")
        return Term(kind="set", arg=rest.lower(), include_related=include_related)
    if low.startswith("cards:"):
        q = tok.split(":", 1)[1].strip()
        if not q:
            raise SelectorParseError("cards: term needs a Scryfall query after the colon")
        return Term(kind="cards", arg=q)
    if low.startswith("scryfall:"):
        q = tok.split(":", 1)[1].strip()
        if not q:
            raise SelectorParseError("scryfall: term needs a query after the colon")
        return Term(kind="scryfall", arg=q)

    raise SelectorParseError(
        f"unknown TERM {tok!r}; valid: {', '.join(VALID_TERMS)}"
    )


_NUMERIC_OPS_RE = re.compile(r"^(qty|cn|value)(>=|<=|=)(.+)$")


def _parse_modifier(tok: str) -> Modifier:
    low = tok.lower()

    # missing[:finish]
    if low == "missing":
        return Modifier(kind="missing", value="either")
    if low.startswith("missing:"):
        side = tok.split(":", 1)[1].strip().lower()
        if side not in VALID_MISSING_FINISHES:
            raise SelectorParseError(
                f"missing: must be one of {VALID_MISSING_FINISHES}, got {side!r}"
            )
        return Modifier(kind="missing", value=side)

    # owned
    if low == "owned":
        return Modifier(kind="owned")

    # finish=foil|nonfoil
    if low.startswith("finish="):
        v = tok.split("=", 1)[1].strip().lower()
        if v not in VALID_FINISHES:
            raise SelectorParseError(
                f"finish= must be one of {VALID_FINISHES}, got {v!r}"
            )
        return Modifier(kind="finish", op="=", value=v)

    # rarity=common|uncommon|...
    if low.startswith("rarity="):
        v = tok.split("=", 1)[1].strip().lower()
        if v not in VALID_RARITIES:
            raise SelectorParseError(
                f"rarity= must be one of {VALID_RARITIES}, got {v!r}"
            )
        return Modifier(kind="rarity", op="=", value=v)

    # qty/cn/value with comparator
    m = _NUMERIC_OPS_RE.match(low)
    if m:
        kind, op, val = m.group(1), m.group(2), m.group(3)
        try:
            float(val)  # cn is integer-ish but stored as text; we coerce later
        except ValueError as e:
            raise SelectorParseError(f"{kind}{op} expects a number, got {val!r}") from e
        return Modifier(kind=kind, op=op, value=val)

    # scryfall:Q (post-filter modifier)
    if low.startswith("scryfall:"):
        q = tok.split(":", 1)[1].strip()
        if not q:
            raise SelectorParseError("scryfall: post-filter needs a query")
        return Modifier(kind="scryfall", value=q)

    raise SelectorParseError(
        f"unknown MODIFIER {tok!r}; valid prefixes: missing, owned, qty, finish, rarity, cn, value, scryfall"
    )


def _validate_combination(sel: Selector) -> None:
    """Reject combinations the grammar disallows.

    `missing` requires a TERM that defines a card universe — applying it to
    `inventory` or `wishlist` or `deck` is a tautology (the term IS the
    inventory/wishlist/deck, so subtracting inventory makes no sense).
    """
    has_missing = any(m.kind == "missing" for m in sel.modifiers)
    if has_missing and sel.term.kind in ("inventory", "wishlist"):
        raise SelectorParseError(
            f"'missing' modifier requires a TERM that defines a card universe "
            f"(set:, cards:, scryfall:, deck:); '{sel.term.kind}' IS the "
            f"{sel.term.kind}, so the result would always be empty."
        )

    has_owned = any(m.kind == "owned" for m in sel.modifiers)
    if has_owned and sel.term.kind in ("inventory", "wishlist"):
        raise SelectorParseError(
            f"'owned' modifier requires a TERM that defines a card universe "
            f"(set:, cards:, scryfall:, deck:); '{sel.term.kind}' is already "
            f"derived from inventory."
        )

    if has_missing and has_owned:
        raise SelectorParseError(
            "'missing' and 'owned' are inverses; pick one"
        )


# ---------- materialize ----------

def materialize(sel_or_str: Selector | str) -> list[MaterializedRow]:
    """Evaluate a selector and return the matching rows.

    Accepts either a parsed `Selector` or a raw selector string. Rows are
    returned in a deterministic order (set_code, collector_number, finish).
    """
    sel = parse(sel_or_str) if isinstance(sel_or_str, str) else sel_or_str

    rows = _materialize_term(sel.term)

    for mod in sel.modifiers:
        rows = _apply_modifier(rows, mod)

    rows.sort(key=lambda r: (r.card.get("set") or "", _cn_sort_key(r.card.get("collector_number") or ""), r.finish))
    return rows


def _materialize_term(term: Term) -> list[MaterializedRow]:
    if term.kind == "inventory":
        return _materialize_inventory()
    if term.kind == "wishlist":
        return _materialize_wishlist(term.arg)
    if term.kind == "deck":
        return _materialize_deck(term.arg)
    if term.kind == "set":
        return _materialize_set(term.arg, term.include_related)
    if term.kind == "cards":
        return _materialize_cards_query(term.arg)
    if term.kind == "scryfall":
        return _materialize_scryfall(term.arg)
    raise SelectorParseError(f"unhandled term kind {term.kind!r}")


_CARD_COLS = (
    "c.scryfall_id, c.name, c.flavor_name, c.set_code, c.collector_number, "
    "c.rarity, c.prices_usd, c.prices_usd_foil, c.cmc, c.type_line, c.mana_cost, "
    "c.frame_effects, c.colors, c.color_identity, c.is_promo, c.is_token, c.finishes"
)


def _materialize_inventory() -> list[MaterializedRow]:
    out: list[MaterializedRow] = []
    with db.connect() as conn:
        rows = conn.execute(
            f"""
            SELECT inv.scryfall_id AS inv_scryfall_id, inv.finish AS inv_finish,
                   inv.quantity AS inv_quantity, {_CARD_COLS}
            FROM inventory inv
            JOIN cards c ON c.scryfall_id = inv.scryfall_id
            ORDER BY c.set_code, c.collector_number, inv.finish
            """
        ).fetchall()
    for r in rows:
        out.append(MaterializedRow(
            scryfall_id=r["inv_scryfall_id"],
            quantity=r["inv_quantity"],
            finish=r["inv_finish"],
            card=_card_dict(r),
        ))
    return out


def _materialize_wishlist(category: str | None) -> list[MaterializedRow]:
    out: list[MaterializedRow] = []
    with db.connect() as conn:
        if category is None:
            rows = conn.execute(
                f"""
                SELECT we.scryfall_id AS w_scryfall_id, we.finish AS w_finish,
                       we.qty_wanted AS w_qty, {_CARD_COLS}
                FROM wishlist_entries we
                JOIN cards c ON c.scryfall_id = we.scryfall_id
                ORDER BY c.set_code, c.collector_number, we.finish
                """
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT we.scryfall_id AS w_scryfall_id, we.finish AS w_finish,
                       we.qty_wanted AS w_qty, {_CARD_COLS}
                FROM wishlist_entries we
                JOIN cards c ON c.scryfall_id = we.scryfall_id
                WHERE we.category = ?
                ORDER BY c.set_code, c.collector_number, we.finish
                """,
                (category,),
            ).fetchall()
    for r in rows:
        # Wishlist 'either' rows materialize as nonfoil (cheaper-finish convention,
        # mirrors wishlist.WishlistRow.unit_price). modifier finish= can override.
        finish = r["w_finish"] if r["w_finish"] in VALID_FINISHES else "nonfoil"
        out.append(MaterializedRow(
            scryfall_id=r["w_scryfall_id"],
            quantity=r["w_qty"],
            finish=finish,
            card=_card_dict(r),
        ))
    return out


def _materialize_deck(slug: str) -> list[MaterializedRow]:
    out: list[MaterializedRow] = []
    with db.connect() as conn:
        deck = conn.execute(
            "SELECT deck_id FROM decks WHERE slug = ?", (slug,)
        ).fetchone()
        if deck is None:
            raise LookupError(f"no deck with slug {slug!r}")
        rows = conn.execute(
            f"""
            SELECT dc.scryfall_id AS d_scryfall_id, dc.finish AS d_finish,
                   dc.count AS d_count, {_CARD_COLS}
            FROM deck_cards dc
            JOIN cards c ON c.scryfall_id = dc.scryfall_id
            WHERE dc.deck_id = ?
            ORDER BY c.set_code, c.collector_number, dc.finish
            """,
            (deck["deck_id"],),
        ).fetchall()
    for r in rows:
        finish = r["d_finish"] if r["d_finish"] in VALID_FINISHES else "nonfoil"
        out.append(MaterializedRow(
            scryfall_id=r["d_scryfall_id"],
            quantity=r["d_count"],
            finish=finish,
            card=_card_dict(r),
        ))
    return out


def _materialize_set(code: str, include_related: bool) -> list[MaterializedRow]:
    codes = [code]
    if include_related:
        try:
            resolved = sets_mod.resolve(code)
            codes = resolved.all_codes
        except LookupError:
            pass

    placeholders = ",".join("?" for _ in codes)
    with db.connect() as conn:
        cards = conn.execute(
            f"""
            SELECT {_CARD_COLS}, c.finishes AS c_finishes
            FROM cards c
            WHERE c.set_code IN ({placeholders})
            ORDER BY c.set_code, c.collector_number
            """,
            codes,
        ).fetchall()

    out: list[MaterializedRow] = []
    for c in cards:
        finishes = json.loads(c["c_finishes"] or "[]") or ["nonfoil"]
        for fin in finishes:
            if fin not in VALID_FINISHES:
                continue
            out.append(MaterializedRow(
                scryfall_id=c["scryfall_id"], quantity=1, finish=fin,
                card=_card_dict(c),
            ))
    return out


def _materialize_cards_query(query: str) -> list[MaterializedRow]:
    """Run a Scryfall query, intersect by id with the local cards table.

    Live API call. Only returns rows that exist in cards (i.e., the user
    has synced them). Use this when you want "every card matching this
    query that I've already cataloged."
    """
    api_ids: list[str] = []
    for card in scryfall.search(query, unique="prints"):
        sid = card.get("id")
        if sid:
            api_ids.append(sid)
    if not api_ids:
        return []

    out: list[MaterializedRow] = []
    placeholders = ",".join("?" for _ in api_ids)
    with db.connect() as conn:
        cards = conn.execute(
            f"""
            SELECT {_CARD_COLS}, c.finishes AS c_finishes
            FROM cards c
            WHERE c.scryfall_id IN ({placeholders})
            """,
            api_ids,
        ).fetchall()
    for c in cards:
        finishes = json.loads(c["c_finishes"] or "[]") or ["nonfoil"]
        for fin in finishes:
            if fin in VALID_FINISHES:
                out.append(MaterializedRow(
                    scryfall_id=c["scryfall_id"], quantity=1, finish=fin,
                    card=_card_dict(c),
                ))
    return out


def _materialize_scryfall(query: str) -> list[MaterializedRow]:
    """Live Scryfall query. Upserts each result into cards as a side effect."""
    out: list[MaterializedRow] = []
    with db.connect() as conn:
        for card in scryfall.search(query, unique="prints"):
            db.upsert_card(conn, card)
            out.append(MaterializedRow(
                scryfall_id=card["id"], quantity=1, finish="nonfoil",
                card=_card_dict_from_scryfall(card),
            ))
    return out


# ---------- modifiers ----------

def _apply_modifier(rows: list[MaterializedRow], mod: Modifier) -> list[MaterializedRow]:
    if mod.kind == "missing":
        return _modifier_missing(rows, mod.value or "either")
    if mod.kind == "owned":
        return _modifier_owned(rows)
    if mod.kind == "qty":
        return _filter_numeric(rows, "quantity", mod.op, float(mod.value))
    if mod.kind == "finish":
        return [r for r in rows if r.finish == mod.value]
    if mod.kind == "rarity":
        return [r for r in rows if (r.card.get("rarity") or "").lower() == mod.value]
    if mod.kind == "cn":
        return _filter_cn(rows, mod.op, int(float(mod.value)))
    if mod.kind == "value":
        return _filter_value(rows, mod.op, float(mod.value))
    if mod.kind == "scryfall":
        return _modifier_scryfall_intersect(rows, mod.value)
    raise SelectorParseError(f"unhandled modifier {mod.kind!r}")


def _modifier_missing(rows: list[MaterializedRow], finish_filter: str) -> list[MaterializedRow]:
    """Set-difference: rows minus what's in inventory at the same (id, finish).

    finish_filter:
      'either'  → keep rows where the matching (id, finish) is NOT in inventory
      'nonfoil' → only consider/keep nonfoil rows; strip foils from output
      'foil'    → only consider/keep foil rows; strip nonfoils from output
    """
    inv = _inventory_index()
    out: list[MaterializedRow] = []
    for r in rows:
        if finish_filter == "nonfoil" and r.finish != "nonfoil":
            continue
        if finish_filter == "foil" and r.finish != "foil":
            continue
        if (r.scryfall_id, r.finish) in inv:
            continue
        out.append(r)
    return out


def _modifier_owned(rows: list[MaterializedRow]) -> list[MaterializedRow]:
    """Set-intersection with inventory by (scryfall_id, finish). Replaces the
    placeholder qty with the actual owned quantity.
    """
    inv = _inventory_index()
    out: list[MaterializedRow] = []
    for r in rows:
        owned_qty = inv.get((r.scryfall_id, r.finish))
        if owned_qty is None:
            continue
        out.append(MaterializedRow(
            scryfall_id=r.scryfall_id, quantity=owned_qty, finish=r.finish, card=r.card,
        ))
    return out


def _modifier_scryfall_intersect(rows: list[MaterializedRow], query: str) -> list[MaterializedRow]:
    """Intersect rows with Scryfall query results by scryfall_id."""
    api_ids: set[str] = set()
    for card in scryfall.search(query, unique="prints"):
        sid = card.get("id")
        if sid:
            api_ids.add(sid)
    return [r for r in rows if r.scryfall_id in api_ids]


def _inventory_index() -> dict[tuple[str, str], int]:
    """Return {(scryfall_id, finish): quantity} for everything in inventory."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT scryfall_id, finish, quantity FROM inventory"
        ).fetchall()
    return {(r["scryfall_id"], r["finish"]): r["quantity"] for r in rows}


def _filter_numeric(rows: list[MaterializedRow], attr: str, op: str, threshold: float) -> list[MaterializedRow]:
    out = []
    for r in rows:
        v = getattr(r, attr)
        if v is None:
            continue
        if op == ">=" and v >= threshold: out.append(r)
        elif op == "<=" and v <= threshold: out.append(r)
        elif op == "=" and v == threshold: out.append(r)
    return out


def _filter_cn(rows: list[MaterializedRow], op: str, threshold: int) -> list[MaterializedRow]:
    """Filter by collector_number. Numeric prefix; letter suffixes (1858a)
    coerce by stripping non-digits."""
    out = []
    for r in rows:
        cn_raw = r.card.get("collector_number") or ""
        digits = re.match(r"^(\d+)", cn_raw)
        if not digits:
            continue
        cn = int(digits.group(1))
        if op == ">=" and cn >= threshold: out.append(r)
        elif op == "<=" and cn <= threshold: out.append(r)
        elif op == "=" and cn == threshold: out.append(r)
    return out


def _filter_value(rows: list[MaterializedRow], op: str, threshold: float) -> list[MaterializedRow]:
    """Filter by current Scryfall USD price for the row's finish.

    Rows with no price are dropped (consistent with `value>=0` returning
    only priced rows; the alternative — keeping them — would silently
    inflate `missing value<=20` results with all the unpriced cards).
    """
    out = []
    for r in rows:
        if r.finish == "foil":
            p = r.card.get("prices_usd_foil")
        else:
            p = r.card.get("prices_usd")
        if p is None:
            continue
        if op == ">=" and p >= threshold: out.append(r)
        elif op == "<=" and p <= threshold: out.append(r)
        elif op == "=" and p == threshold: out.append(r)
    return out


# ---------- helpers ----------

def _cn_sort_key(cn: str) -> tuple[int, str]:
    """Sort collector numbers '1858' < '1858a' < '1859'."""
    m = re.match(r"^(\d+)(.*)$", cn)
    if not m:
        return (0, cn)
    return (int(m.group(1)), m.group(2))


def _card_dict(row) -> dict:
    """Normalize a sqlite Row (with the c.* columns aliased) into a plain dict."""
    return {
        "scryfall_id":      row["scryfall_id"],
        "name":             row["name"],
        "flavor_name":      row["flavor_name"],
        "set":              row["set_code"],
        "collector_number": row["collector_number"],
        "rarity":           row["rarity"],
        "prices_usd":       row["prices_usd"],
        "prices_usd_foil":  row["prices_usd_foil"],
        "cmc":              row["cmc"],
        "type_line":        row["type_line"],
        "mana_cost":        row["mana_cost"],
    }


def _card_dict_from_scryfall(c: dict) -> dict:
    return {
        "scryfall_id":      c.get("id"),
        "name":             c.get("name"),
        "flavor_name":      c.get("flavor_name") or (
            ((c.get("card_faces") or [{}])[0] or {}).get("flavor_name")
        ),
        "set":              (c.get("set") or "").lower(),
        "collector_number": c.get("collector_number"),
        "rarity":           c.get("rarity"),
        "prices_usd":       _f(c.get("prices", {}).get("usd")),
        "prices_usd_foil":  _f(c.get("prices", {}).get("usd_foil")),
        "cmc":              c.get("cmc"),
        "type_line":        c.get("type_line"),
        "mana_cost":        c.get("mana_cost"),
    }


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None

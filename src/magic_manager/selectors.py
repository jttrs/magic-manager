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

VALID_TERMS = ("inventory", "free", "wishlist", "deck", "assigned", "set", "cards", "scryfall")
VALID_MODIFIERS = (
    "missing", "owned", "available", "assigned",
    "qty", "finish", "rarity", "cn", "value",
    "scryfall", "treatment", "chase",
)
VALID_TREATMENT_CLASSES = (
    "regular", "alt", "collectible-alt", "preferred", "any-alt",
    "b", "fa", "shw", "ext", "sm", "ff",
)


# Per-family configuration: which promo_types on a fancy-foil print signal
# "same art as a cheaper sibling, just on a fancy-foil sheet" (i.e. dupe).
# A `ff`-treatment print is filtered as a dupe iff:
#   - a same-name sibling exists with the same treatment-codes-minus-ff
#   - AND the print's promo_types differ from that sibling's ONLY by entries
#     in this family's dupe-foil set
#
# Example: FIN 532 Prompto (b|ff, promo_types includes 'surgefoil') has FIN 387
# (b, no surgefoil) as a sibling. The diff is exactly {'surgefoil'} ⊆ FIN's
# dupe-foil set, so FIN 532 is dropped.
#
# Counter-example: FIN 564 Cloud (b, promo_types includes 'chocobotrackfoil')
# has FIN 375 (b, no chocobo) as a sibling. The diff is {'chocobotrackfoil'},
# which is NOT in FIN's dupe-foil set — chocobo-track is unique art on a
# fancy-foil sheet. FIN 564 is kept.
#
# Each family must be explicitly configured. The `preferred` treatment class
# (and `mm query missing-set`) refuse to silently fall back to a less-strict
# class when a family is unconfigured — instead they error out with a clear
# instruction for the user to configure or to opt into a looser class.
FAMILY_DUPE_FOIL_PROMO_TYPES: dict[str, frozenset[str]] = {
    # Final Fantasy: surgefoil is "same art, fancy-foil sheet" (FIN 532-ish).
    # chocobotrackfoil is intentionally NOT here — it marks unique art (FIN 564 etc.).
    "fin": frozenset({"surgefoil"}),
    # Lord of the Rings: surgefoil and doublerainbow are both same-art-as-sibling
    # dupe foils. surgefoil prints (e.g. LTC 378 The Great Henge) match the
    # borderless inverted siblings (LTC 348). doublerainbow serialized prints
    # (e.g. LTC 378z) likewise match. silverfoil/scroll showcase prints (LTC
    # 411-431) are intentionally NOT here — those are a unique scroll-frame art
    # treatment, not a dupe of any other print. poster prints (LTR 731-746)
    # are unique poster-art treatment, also intentionally not in this set.
    "ltr": frozenset({"surgefoil", "doublerainbow"}),
    # Spider-Man: no dupe-foil signals per survey_treatment_signature.py audit
    # (2026-07-08). textured (SPM 235-241) is a 7-print series of DISTINCT
    # comic-panel arts, not a dupe of any base print. cosmicfoil is a singleton
    # (needs visual audit if encountered but not worth a rule for one print).
    # Empty frozenset satisfies the `treatment=preferred` config requirement
    # without filtering anything. See docs/sets/spm.md §2.
    "spm": frozenset(),
    # Avatar: The Last Airbender: no dupe-foil signals per audit (2026-07-08).
    # neonink (TLA 359-362) is a 4-print themed chase (Aang/Zuko/Katara/Toph
    # by Flavio Girón) with distinct art, not a dupe. raisedfoil singleton
    # (TLA 363 Avatar Aang, Bryan Konietzko + headliner) probably unique-art.
    # Empty frozenset per docs/sets/tla.md §2.
    "tla": frozenset(),
    # TMNT: surgefoil is same-art-as-sibling (TMT 309 Forest BEMOCS surgefoil
    # matches TMT 195 Forest BEMOCS base). fracturefoil is same-art-as-sibling
    # (TMT 291 Leonardo A4Mitsuori fracturefoil+japanshowcase matches TMT 281
    # Leonardo A4Mitsuori japanshowcase). japanshowcase itself is unique art
    # (different artist from base) — kept. See docs/sets/tmt.md §2.
    "tmt": frozenset({"surgefoil", "fracturefoil"}),
}


# Per-family "unobtainable in practice" rules — prints the user has decided
# they will not attempt to acquire (rarity / distribution / personal taste),
# even though the cardboard exists. Filtered from `mm query missing-set` and
# from any `treatment=preferred` query, but NOT from master-list checklists
# (the user might still ingest one if it lands in their hands incidentally).
#
# Schema: anchor_code -> list of rules. A rule matches a card if EVERY
# condition in the rule holds; a card is excluded if it matches ANY rule.
# Conditions supported:
#   - promo_types_all_of: frozenset[str]
#       The card's promo_types must include every member of this set.
#       Use for treatment families that combine multiple promo_types
#       (e.g. silverfoil AND scroll for LTR's showcase scroll-frame prints).
#   - promo_types_any_of: frozenset[str]
#       The card's promo_types must include at least one of these. Use for
#       single-promo-type signals like a hypothetical "neonink" treatment.
#   - frame_effects_all_of: frozenset[str]
#       The card's frame_effects must include every member.
#   - border_color: str
#       The card's border_color must equal this string.
# Conditions can be combined within a rule for AND semantics.
#
# When adding a new family: survey its prints with the script in
# `scripts/survey_treatment_signature.py` (added 2026-06-14), then write the
# rule that matches the user's "I will never shop for these" criteria.
FAMILY_UNOBTAINABLE_RULES: dict[str, list[dict]] = {
    "ltr": [
        # Showcase scroll-frame silverfoil prints (LTR 452-490, LTC 411-431):
        # parchment-style scroll frame, foil-only, distributed via Bundle/special
        # products and rarely surfaced on the secondary market in the user's
        # experience. The two promo_types co-occur on 349 prints in the LTR
        # family; matching on both rules out a few non-scroll silverfoils
        # (LTC 517, 525, etc.) that ARE in standard distribution.
        {"promo_types_all_of": frozenset({"silverfoil", "scroll"})},
    ],
}


def _card_promo_types(card: dict) -> set[str]:
    """Coerce a card's ``promo_types`` field to a set, regardless of whether
    it arrived as JSON-encoded string (DB row) or list (Scryfall API dict).
    """
    import json as _json
    raw = card.get("promo_types")
    if raw is None:
        return set()
    if isinstance(raw, str):
        try:
            return set(_json.loads(raw))
        except (ValueError, TypeError):
            return set()
    return set(raw)


def _card_frame_effects(card: dict) -> set[str]:
    """Same coercion as `_card_promo_types` for ``frame_effects``."""
    import json as _json
    raw = card.get("frame_effects")
    if raw is None:
        return set()
    if isinstance(raw, str):
        try:
            return set(_json.loads(raw))
        except (ValueError, TypeError):
            return set()
    return set(raw)


def _matches_unobtainable_rule(card: dict, rule: dict) -> bool:
    """True iff the card matches every condition in the rule."""
    if "promo_types_all_of" in rule:
        if not rule["promo_types_all_of"].issubset(_card_promo_types(card)):
            return False
    if "promo_types_any_of" in rule:
        if not (rule["promo_types_any_of"] & _card_promo_types(card)):
            return False
    if "frame_effects_all_of" in rule:
        if not rule["frame_effects_all_of"].issubset(_card_frame_effects(card)):
            return False
    if "border_color" in rule:
        if (card.get("border_color") or "") != rule["border_color"]:
            return False
    return True


def _is_family_unobtainable(card: dict, anchor_code: str) -> bool:
    """True iff any of the family's unobtainable rules match this card."""
    rules = FAMILY_UNOBTAINABLE_RULES.get(anchor_code.lower())
    if not rules:
        return False
    return any(_matches_unobtainable_rule(card, rule) for rule in rules)


# Global exclusion: prints that are effectively unobtainable for a physical
# collector. Two categories, same exclusion rule:
#
# 1. Digital-only: Arena/Alchemy rebalanced cards. No physical counterpart
#    exists. Examples: FIN A-248 'A-Vivi Ornitier', FCA A-19 'A-Winota,
#    Joiner of Forces' — `security_stamp: "arena"`, `finishes: ["nonfoil"]`.
# 2. Serialized 1-of-N chase prints. Each individually-numbered copy is
#    unique and rarely surfaces on the secondary market; aggregating them
#    into a "missing" shopping list is noise. Examples: LTR 731z–750z
#    'Lord of the Rings' poster series, LTC 378z–407z borderless lands.
#
# Both categories are filtered globally from physical-collection queries
# (missing-set, treatment=preferred, etc.) regardless of set/family. The
# master-list writer in sets.py also drops 'serialized' via
# EXCLUDED_PROMO_TYPES; this list is the selectors-side equivalent so the
# query path matches.
UNOBTAINABLE_PROMO_TYPES: frozenset[str] = frozenset({
    "rebalanced", "alchemy",  # Arena/Alchemy digital-only
    "serialized",             # 1-of-N chase prints
})

# Backwards-compat alias — older callers import this name.
DIGITAL_ONLY_PROMO_TYPES: frozenset[str] = frozenset({"rebalanced", "alchemy"})


def _is_digital_only(card: dict) -> bool:
    """True iff the card is unobtainable for a physical collector — Arena/Alchemy
    rebalanced or serialized 1-of-N. Name kept for backwards compat; the
    underlying set is now ``UNOBTAINABLE_PROMO_TYPES``.
    """
    import json as _json
    pt_raw = card.get("promo_types")
    if pt_raw is None:
        return False
    if isinstance(pt_raw, str):
        try:
            pt = set(_json.loads(pt_raw))
        except (ValueError, TypeError):
            return False
    else:
        pt = set(pt_raw)
    return bool(pt & UNOBTAINABLE_PROMO_TYPES)
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
    if low == "free":
        # V5: 'free' = 'inventory' minus deck_assignments. See _materialize_free.
        return Term(kind="free")
    if low.startswith("assigned:"):
        slug = tok.split(":", 1)[1].strip()
        if not slug:
            raise SelectorParseError("assigned: term needs a deck slug after the colon")
        return Term(kind="assigned", arg=slug)
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

    # available — inventory minus deck commitments (V5: same as materializing 'free')
    if low == "available":
        return Modifier(kind="available")

    # assigned — restrict inventory rows to those with SUM(deck_assignments) > 0
    if low == "assigned":
        return Modifier(kind="assigned")

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

    # treatment=<class>
    if low.startswith("treatment="):
        v = tok.split("=", 1)[1].strip().lower()
        if v not in VALID_TREATMENT_CLASSES:
            raise SelectorParseError(
                f"treatment= must be one of {VALID_TREATMENT_CLASSES}, got {v!r}"
            )
        return Modifier(kind="treatment", op="=", value=v)

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

    # chase[:N] — keep rows whose (name, treatment) group has ≥N distinct-art
    # printings in the family present in the input rows. Catches chase-variant
    # sheets (LTR Nazgûl x9, FIN Cid x16) that are technically uncommon but
    # every collector wants every art. Default N=3 — ordinary reprints across
    # a base set + one commander deck top out at 2, so 3+ reliably identifies
    # a multi-variant chase sheet without false positives.
    if low == "chase":
        return Modifier(kind="chase", value="3")
    if low.startswith("chase:"):
        n = tok.split(":", 1)[1].strip()
        try:
            if int(n) < 2:
                raise ValueError
        except ValueError as e:
            raise SelectorParseError(f"chase:N expects an integer ≥2, got {n!r}") from e
        return Modifier(kind="chase", value=n)

    raise SelectorParseError(
        f"unknown MODIFIER {tok!r}; valid prefixes: missing, owned, qty, finish, "
        f"rarity, treatment, cn, value, scryfall, chase"
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
    if has_owned and sel.term.kind in ("inventory", "free", "wishlist", "assigned"):
        raise SelectorParseError(
            f"'owned' modifier requires a TERM that defines a card universe "
            f"(set:, cards:, scryfall:, deck:); '{sel.term.kind}' is already "
            f"derived from inventory."
        )

    has_assigned_mod = any(m.kind == "assigned" for m in sel.modifiers)
    if has_assigned_mod and sel.term.kind not in ("inventory", "free"):
        raise SelectorParseError(
            f"'assigned' modifier restricts inventory-shaped rows to those with "
            f"active deck_assignments; got term kind {sel.term.kind!r}. "
            f"Use 'inventory assigned' to see everything currently pledged, or "
            f"'assigned:<slug>' as a term to see one deck's pledges."
        )

    if has_missing and has_owned:
        raise SelectorParseError(
            "'missing' and 'owned' are inverses; pick one"
        )

    has_available = any(m.kind == "available" for m in sel.modifiers)
    if has_available and sel.term.kind != "inventory":
        # `available` subtracts deck commitments from owned quantities. It
        # only makes sense on raw inventory rows; `set:`/`cards:`/etc. don't
        # carry per-row owned quantities to subtract from.
        raise SelectorParseError(
            f"'available' modifier requires the 'inventory' term — "
            f"got {sel.term.kind!r}. Use `inventory available` (optionally "
            f"composed with finish=/value=/treatment= filters)."
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
    if term.kind == "free":
        return _materialize_free()
    if term.kind == "wishlist":
        return _materialize_wishlist(term.arg)
    if term.kind == "deck":
        return _materialize_deck(term.arg)
    if term.kind == "assigned":
        return _materialize_assigned(term.arg)
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
    "c.frame_effects, c.full_art, c.promo_types, c.border_color, c.scryfall_uri, "
    "c.colors, c.color_identity, c.is_promo, c.is_token, c.finishes"
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


def _materialize_free() -> list[MaterializedRow]:
    """V5: inventory rows with quantity reduced by current deck_assignments.

    Fully-committed rows drop out of the result (qty would be 0). Callers use
    this for "what can I actually deploy elsewhere right now?" — the same
    question ``inventory available`` answers via the modifier path.
    """
    out: list[MaterializedRow] = []
    with db.connect() as conn:
        rows = conn.execute(
            f"""
            SELECT inv.scryfall_id AS inv_scryfall_id, inv.finish AS inv_finish,
                   inv.quantity AS inv_quantity,
                   COALESCE(
                       (SELECT SUM(count) FROM deck_assignments da
                        WHERE da.scryfall_id = inv.scryfall_id AND da.finish = inv.finish),
                       0
                   ) AS assigned_qty,
                   {_CARD_COLS}
            FROM inventory inv
            JOIN cards c ON c.scryfall_id = inv.scryfall_id
            ORDER BY c.set_code, c.collector_number, inv.finish
            """
        ).fetchall()
    for r in rows:
        free = r["inv_quantity"] - r["assigned_qty"]
        if free <= 0:
            continue
        out.append(MaterializedRow(
            scryfall_id=r["inv_scryfall_id"],
            quantity=free,
            finish=r["inv_finish"],
            card=_card_dict(r),
        ))
    return out


def _materialize_assigned(slug: str) -> list[MaterializedRow]:
    """V5: current physical fulfillment of a deck's recipe.

    Distinct from ``deck:<slug>`` (which is the recipe). Yields one row per
    ``(scryfall_id, finish)`` currently pledged to the deck, with quantity =
    the pledged count.
    """
    out: list[MaterializedRow] = []
    with db.connect() as conn:
        deck = conn.execute(
            "SELECT deck_id FROM decks WHERE slug = ?", (slug,)
        ).fetchone()
        if deck is None:
            raise LookupError(f"no deck with slug {slug!r}")
        rows = conn.execute(
            f"""
            SELECT da.scryfall_id AS d_scryfall_id, da.finish AS d_finish,
                   da.count AS d_count, {_CARD_COLS}
            FROM deck_assignments da
            JOIN cards c ON c.scryfall_id = da.scryfall_id
            WHERE da.deck_id = ?
            ORDER BY c.set_code, c.collector_number, da.finish
            """,
            (deck["deck_id"],),
        ).fetchall()
    for r in rows:
        out.append(MaterializedRow(
            scryfall_id=r["d_scryfall_id"],
            quantity=r["d_count"],
            finish=r["d_finish"],
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
    if mod.kind == "available":
        return _modifier_available(rows)
    if mod.kind == "assigned":
        return _modifier_assigned(rows)
    if mod.kind == "qty":
        return _filter_numeric(rows, "quantity", mod.op, float(mod.value))
    if mod.kind == "finish":
        return [r for r in rows if r.finish == mod.value]
    if mod.kind == "rarity":
        return [r for r in rows if (r.card.get("rarity") or "").lower() == mod.value]
    if mod.kind == "treatment":
        return _filter_treatment(rows, mod.value)
    if mod.kind == "cn":
        return _filter_cn(rows, mod.op, int(float(mod.value)))
    if mod.kind == "value":
        return _filter_value(rows, mod.op, float(mod.value))
    if mod.kind == "scryfall":
        return _modifier_scryfall_intersect(rows, mod.value)
    if mod.kind == "chase":
        return _modifier_chase(rows, int(mod.value))
    raise SelectorParseError(f"unhandled modifier {mod.kind!r}")


def _modifier_chase(rows: list[MaterializedRow], threshold: int) -> list[MaterializedRow]:
    """Keep rows whose (name, treatment) group has ≥threshold distinct-art
    printings in the family spanned by the input row set codes.

    "Distinct-art printings" is measured across the FULL cards table for those
    set codes, not just the input rows — so `set:ltr+related missing chase`
    correctly counts all 9 base Nazgûls even when the user already owns some
    (which are filtered from the input by `missing`).

    Rationale: a card name that has ≥3 unique-art printings at the same
    treatment inside one release family is a "chase sheet" (LTR Nazgûl,
    FIN Cid, TLA Aang…). Every completionist wants every variant regardless
    of rarity. Ordinary reprints across a base set + one commander deck top
    out at 2 printings per (name, treatment), so 3 is a safe floor.
    """
    from . import treatments
    if not rows:
        return []
    set_codes = {(r.card.get("set") or "").lower() for r in rows if r.card.get("set")}
    if not set_codes:
        return []
    placeholders = ",".join("?" for _ in set_codes)
    with db.connect() as conn:
        fam_rows = conn.execute(
            f"SELECT name, frame_effects, full_art, promo_types "
            f"FROM cards WHERE set_code IN ({placeholders})",
            list(set_codes),
        ).fetchall()
    counts: dict[tuple[str, str], int] = {}
    for fr in fam_rows:
        key = (fr["name"] or "", treatments.compute_treatment(dict(fr)))
        counts[key] = counts.get(key, 0) + 1
    keep_keys = {k for k, v in counts.items() if v >= threshold}
    out: list[MaterializedRow] = []
    for r in rows:
        key = (r.card.get("name") or "", treatments.compute_treatment(r.card))
        if key in keep_keys:
            out.append(r)
    return out


def _modifier_missing(rows: list[MaterializedRow], finish_filter: str) -> list[MaterializedRow]:
    """Set-difference: rows minus what's in inventory.

    finish_filter:
      'either'  → PRINTING-LEVEL. Drop the printing entirely if ANY finish is in
                  inventory; collapse remaining rows so each scryfall_id appears
                  at most once (with finish='nonfoil' if available, else 'foil').
                  This is the default for `missing` (no suffix). Matches the
                  user-facing intent of 'unique art I'm missing' rather than
                  'every (printing, finish) tuple I haven't bought'.
      'nonfoil' → FINISH-LEVEL. Keep nonfoil rows whose (id, 'nonfoil') is NOT
                  in inventory; strip foils from output entirely.
      'foil'    → FINISH-LEVEL. Same shape, foil only.
    """
    inv = _inventory_index()

    if finish_filter == "either":
        # PRINTING-LEVEL: a printing is "missing" iff zero finishes are owned.
        # Collapse to one row per scryfall_id, preferring nonfoil for display
        # when both finishes exist in the rows.
        owned_ids = {sid for (sid, _f) in inv.keys()}
        prefer = sorted(rows, key=lambda r: (r.scryfall_id, 0 if r.finish == "nonfoil" else 1))
        out: list[MaterializedRow] = []
        seen: set[str] = set()
        for r in prefer:
            if r.scryfall_id in owned_ids:
                continue
            if r.scryfall_id in seen:
                continue
            seen.add(r.scryfall_id)
            out.append(r)
        return out

    out = []
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


def _modifier_available(rows: list[MaterializedRow]) -> list[MaterializedRow]:
    """Subtract deck commitments from inventory quantities.

    Inputs are inventory rows (qty = total physical copies owned). Deck
    commitments are summed across all decks per (scryfall_id, finish), and
    the difference becomes the new qty.

    Rows where the difference is <= 0 are dropped from the result and a
    one-line stderr warning is emitted per drop, so the user notices when
    they've committed more copies than they actually own.
    """
    import sys as _sys
    committed = _deck_commitment_index()
    out: list[MaterializedRow] = []
    for r in rows:
        com = committed.get((r.scryfall_id, r.finish), 0)
        avail = r.quantity - com
        if avail > 0:
            out.append(MaterializedRow(
                scryfall_id=r.scryfall_id, quantity=avail, finish=r.finish, card=r.card,
            ))
            continue
        if com > r.quantity:
            # Over-commitment: more deck copies than owned. The user wants this
            # surfaced so they can fix the inconsistency (probably forgot to
            # add inventory after a precon was opened, or double-counted a
            # deck import).
            name = r.card.get("name") or "?"
            setc = (r.card.get("set") or "?").upper()
            cn = r.card.get("collector_number") or "?"
            print(
                f"over-committed: {name} ({setc} {cn}) [{r.finish}] "
                f"owned={r.quantity} committed={com}",
                file=_sys.stderr,
            )
        # avail == 0 (fully committed) — silently drop. The user knows the deck
        # has it; no need to noise the chat.
    return out


def _modifier_assigned(rows: list[MaterializedRow]) -> list[MaterializedRow]:
    """V5: keep only rows where ``SUM(deck_assignments.count) > 0`` for the
    (scryfall_id, finish) pair. Quantity in the emitted row is set to the
    assigned count (not the raw inventory quantity), so ``value assigned``
    reports the value that's currently pledged rather than the value of the
    whole inventory row it came from.
    """
    committed = _deck_commitment_index()
    out: list[MaterializedRow] = []
    for r in rows:
        com = committed.get((r.scryfall_id, r.finish), 0)
        if com <= 0:
            continue
        out.append(MaterializedRow(
            scryfall_id=r.scryfall_id,
            quantity=min(com, r.quantity),
            finish=r.finish,
            card=r.card,
        ))
    return out


def _deck_commitment_index() -> dict[tuple[str, str], int]:
    """Return {(scryfall_id, finish): SUM(count)} aggregated across all decks.

    V5: reads from ``deck_assignments`` (actual physical pledges), NOT from
    ``deck_cards`` (recipes). Under the pre-V5 conflated model this queried
    deck_cards because that's where "committed to a deck" lived; under V5
    "committed" specifically means "an inventory copy is currently pledged
    to a deck," which is exactly what deck_assignments records.
    """
    out: dict[tuple[str, str], int] = {}
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT scryfall_id, finish, SUM(count) AS total "
            "FROM deck_assignments GROUP BY scryfall_id, finish"
        ).fetchall()
    for r in rows:
        out[(r["scryfall_id"], r["finish"])] = r["total"]
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


def _filter_treatment(rows: list[MaterializedRow], cls: str) -> list[MaterializedRow]:
    """Filter rows by treatment class (computed from frame_effects/full_art/promo_types).

    Class values:
      regular  — compute_treatment() returns empty string
      b/fa/shw/ext/sm/ff — treatment string contains that exact code
      alt      — non-empty AND does not contain 'ext'
      collectible-alt — alt minus pure-`ff` (fancy-foil-only rows excluded)
      preferred — collectible-alt minus (a) datestamped prints with a non-stamped
                  same-treatment sibling in the family AND (b) `ff`-treatment
                  prints that are visually identical to a cheaper sibling per
                  the family's FAMILY_DUPE_FOIL_PROMO_TYPES configuration.
                  Requires the family to be configured; raises if not.
      any-alt  — non-empty (includes ext)
    """
    from . import treatments
    cache: dict[str, set[str]] = {}
    out: list[MaterializedRow] = []

    if cls == "preferred":
        return _filter_treatment_preferred(rows)

    for r in rows:
        sid = r.scryfall_id
        codes = cache.get(sid)
        if codes is None:
            t = treatments.compute_treatment(r.card)
            codes = set(t.split("|")) if t else set()
            cache[sid] = codes
        if cls == "regular":
            keep = not codes
        elif cls == "alt":
            keep = bool(codes) and "ext" not in codes
        elif cls == "collectible-alt":
            keep = bool(codes) and "ext" not in codes and codes != {"ff"}
        elif cls == "any-alt":
            keep = bool(codes)
        else:
            keep = cls in codes
        if keep:
            out.append(r)
    return out


def _filter_treatment_preferred(rows: list[MaterializedRow]) -> list[MaterializedRow]:
    """`preferred` = collectible-alt MINUS (datestamped-with-sibling) MINUS (ff-dupes).

    Step 1 — start from the collectible-alt subset (alt minus pure-ff).
    Step 2 — drop datestamped prints that have a non-stamped same-name same-codes
             sibling anywhere in the local cards table.
    Step 3 — drop ff-treatment prints whose promo_types differ from a same-name
             same-codes-minus-ff sibling ONLY by family-configured dupe-foil
             markers (e.g. {'surgefoil'} for FIN). Chocobo-track foils and other
             unique-art-on-fancy-foil prints are kept because their distinctive
             promo_type is NOT in the dupe-foil set.

    Requires the family's anchor to be present in FAMILY_DUPE_FOIL_PROMO_TYPES.
    If unconfigured, raises SelectorParseError with a clear message instructing
    the caller to either configure the family or fall back to a looser class.
    """
    from . import treatments
    import json as _json

    if not rows:
        return []

    # Resolve anchor code(s) from row set codes by walking the family graph.
    set_codes = {(r.card.get("set") or "").lower() for r in rows if r.card.get("set")}
    anchors: set[str] = set()
    for setc in set_codes:
        try:
            resolved = sets_mod.resolve(setc)
            anchors.add(resolved.code)  # parent anchor of the family
        except LookupError:
            pass
    # Of the anchors found, do we have config for any?
    configured = [a for a in anchors if a in FAMILY_DUPE_FOIL_PROMO_TYPES]
    if not configured:
        anchors_str = ", ".join(sorted(anchors)) if anchors else "(none resolvable)"
        raise SelectorParseError(
            f"'treatment=preferred' requires per-family dupe-foil config. "
            f"Resolved anchor(s) for these rows: {anchors_str}. "
            f"Configured anchors: {sorted(FAMILY_DUPE_FOIL_PROMO_TYPES.keys())}. "
            f"Either add an entry to FAMILY_DUPE_FOIL_PROMO_TYPES in selectors.py "
            f"(see the Final Fantasy entry as a template — the user must specify "
            f"which promo_types signal 'same art, just on a fancy-foil sheet' "
            f"for this family), or use 'treatment=collectible-alt' instead."
        )
    if len(configured) > 1:
        # Mixed-family rows: can't apply a single dupe-foil set. Reject.
        raise SelectorParseError(
            f"'treatment=preferred' got rows spanning multiple configured families "
            f"({sorted(configured)}); applying a single dupe-foil filter is "
            f"ambiguous. Run separately per family."
        )
    anchor = configured[0]
    dupe_foil_pts = FAMILY_DUPE_FOIL_PROMO_TYPES[anchor]
    # All family codes for this anchor (so the sibling search stays in-family).
    try:
        family_codes = set(sets_mod.resolve(anchor).all_codes)
    except LookupError:
        family_codes = {anchor}

    # Step 0: drop digital-only (Arena / Alchemy rebalanced) prints AND
    # serialized 1-of-N chase prints up-front. Both are categorically
    # unobtainable for a physical collector. Also apply per-family
    # unobtainable rules (FAMILY_UNOBTAINABLE_RULES) which encode set-specific
    # treatments the user has decided not to pursue (e.g. LTR's showcase
    # scroll-frame silverfoil prints, distributed via products the user
    # doesn't engage with). These are NOT dupes of other prints — they're
    # distinct art that the user has personally ruled out of their want list.
    rows = [r for r in rows if not _is_digital_only(r.card)]
    rows = [r for r in rows if not _is_family_unobtainable(r.card, anchor)]

    # Step 1: filter to collectible-alt rows.
    collectible: list[MaterializedRow] = []
    cache_codes: dict[str, set[str]] = {}
    for r in rows:
        t = treatments.compute_treatment(r.card)
        codes = set(t.split("|")) if t else set()
        cache_codes[r.scryfall_id] = codes
        if codes and "ext" not in codes and codes != {"ff"}:
            collectible.append(r)

    if not collectible:
        return []

    # Build family-wide index by (name, codes-minus-ff) for sibling lookup.
    # Pull every family card from db.cards, since rows might only contain a
    # subset (e.g. just "missing" rows). Sibling references go against the full
    # universe.
    placeholders = ",".join("?" for _ in family_codes)
    fam_rows = []
    with db.connect() as conn:
        fam_rows = conn.execute(
            f"SELECT scryfall_id, name, frame_effects, full_art, promo_types "
            f"FROM cards WHERE set_code IN ({placeholders})",
            list(family_codes),
        ).fetchall()
    by_name_codes: dict[tuple[str | None, frozenset[str]], list[dict]] = {}
    promo_index: dict[str, set[str]] = {}
    for fr in fam_rows:
        t = treatments.compute_treatment(dict(fr))
        codes = set(t.split("|")) if t else set()
        no_ff = frozenset(codes - {"ff"})
        pt = set(_json.loads(fr["promo_types"] or "[]"))
        promo_index[fr["scryfall_id"]] = pt
        by_name_codes.setdefault((fr["name"], no_ff), []).append({
            "scryfall_id": fr["scryfall_id"],
            "promo_types": pt,
            "codes": codes,
        })

    out: list[MaterializedRow] = []
    for r in collectible:
        sid = r.scryfall_id
        codes = cache_codes[sid]
        my_pt = promo_index.get(sid, set())
        name = r.card.get("name")

        # Step 2: datestamped + non-stamped sibling → drop.
        if "datestamped" in my_pt:
            sibs_same_codes = by_name_codes.get((name, frozenset(codes)), [])
            non_stamped_sibling_exists = any(
                s["scryfall_id"] != sid and "datestamped" not in s["promo_types"]
                for s in sibs_same_codes
            )
            if non_stamped_sibling_exists:
                continue

        # Step 3: ff-dupe with sibling differing only by dupe-foil markers → drop.
        if "ff" in codes:
            no_ff = frozenset(codes - {"ff"})
            siblings = by_name_codes.get((name, no_ff), [])
            for sib in siblings:
                if sib["scryfall_id"] == sid:
                    continue
                only_in_me = my_pt - sib["promo_types"]
                # The print is a dupe iff what's only-in-me is a non-empty
                # subset of the family's dupe-foil promo_types. Anything
                # in the diff outside that set means it has unique signal
                # (e.g. chocobotrackfoil) and we keep it.
                if only_in_me and only_in_me.issubset(dupe_foil_pts):
                    break
            else:
                # No dupe-marker sibling found — keep.
                out.append(r)
                continue
            # Found a dupe-marker sibling — drop this row.
            continue

        out.append(r)
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
    """Normalize a sqlite Row (with the c.* columns aliased) into a plain dict.

    Includes the treatment-classification inputs (frame_effects, full_art,
    promo_types) so treatments.compute_treatment() can run on the resulting
    dict at filter time.
    """
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
        "frame_effects":    row["frame_effects"],
        "full_art":         row["full_art"],
        "promo_types":      row["promo_types"],
        "border_color":     row["border_color"],
        "scryfall_uri":     row["scryfall_uri"],
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
        "frame_effects":    c.get("frame_effects"),
        "full_art":         c.get("full_art"),
        "promo_types":      c.get("promo_types"),
        "border_color":     c.get("border_color"),
        "scryfall_uri":     c.get("scryfall_uri"),
    }


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None

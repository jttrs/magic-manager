"""Card surfer: an endless feed of random cards to look at — art, flavor text,
artist — narrowed by filters (art tags, set family, colour identity, flavor text,
card type, legendary, rarity, artist, treatment).

Two sources, one filter model:

* **All of Magic** — :func:`build_query` compiles the filters to Scryfall search
  syntax and each card is one ``/cards/random?q=`` call (never cached, paced by
  the wrapper). Random draws can repeat; the client skips repeats and
  :func:`draw` reports how many printings match (``total``) so it knows when
  it has seen them all.
* **Your cards** — owned printings from the local catalog, prefiltered locally
  (art tags via :mod:`scryfall_art`), shuffled deterministically by ``seed`` and
  paged by ``offset`` (no repeats), then read from Scryfall's ``/cards/collection``
  (24h cache) for the fields the local catalog doesn't keep (flavor text, artist,
  frame) and checked against :func:`matches` — the Python twin of the query.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Literal

from . import db, explore, scryfall, scryfall_art, sets

# key → (label, Scryfall syntax). Order is the picker's order.
TREATMENTS: dict[str, tuple[str, str]] = {
    "borderless": ("Borderless", "border:borderless"),
    "fullart": ("Full art", "is:fullart"),
    "showcase": ("Showcase", "is:showcase"),
    "extended": ("Extended art", "is:extendedart"),
    "oldframe": ("Old frame", "(frame:1993 or frame:1997)"),
    "textless": ("Textless", "is:textless"),
}
TYPES = ("creature", "planeswalker", "instant", "sorcery", "artifact", "enchantment", "land", "battle")
RARITIES = ("common", "uncommon", "rare", "mythic")
COLORS = "wubrg"
BASE = "game:paper -t:token -t:emblem"
MAX_DRAW = 8
_COLLECTION_CHUNK = 24
_MAX_CHUNKS = 5

Flavor = Literal["any", "has", "none"]
Legendary = Literal["any", "only", "not"]
ColorMatch = Literal["exact", "within"]
Source = Literal["scryfall", "owned"]


@dataclass(frozen=True)
class Filters:
    art: tuple[str, ...] = ()
    families: tuple[str, ...] = ()
    colors: str = ""
    color_match: ColorMatch = "exact"
    flavor: Flavor = "any"
    types: tuple[str, ...] = ()
    legendary: Legendary = "any"
    rarity: tuple[str, ...] = ()
    artist: str = ""
    treatments: tuple[str, ...] = ()


def _colors(f: Filters) -> tuple[str, bool]:
    """(WUBRG letters in canonical order, colourless-only?)."""
    letters = "".join(ch for ch in COLORS if ch in f.colors.lower())
    return letters, not letters and "c" in f.colors.lower()


def _any(terms: list[str]) -> str:
    return terms[0] if len(terms) == 1 else "(" + " or ".join(terms) + ")"


def family_codes(families) -> list[str]:
    codes: list[str] = []
    for fam in families:
        codes.extend(sets.resolve(fam).all_codes)
    return list(dict.fromkeys(c.lower() for c in codes))


def build_query(f: Filters, *, set_codes: list[str] | None = None) -> str:
    """Scryfall search syntax for ``f`` (``set_codes`` = the families resolved,
    passed in so tests stay offline)."""
    parts = [BASE]
    if f.art:
        parts.append(_any([f"art:{t}" for t in f.art]))
    if f.families:
        codes = set_codes if set_codes is not None else family_codes(f.families)
        parts.append(_any([f"s:{c}" for c in codes]) if codes else "s:none")
    letters, colorless = _colors(f)
    if letters:
        parts.append(f"id{'=' if f.color_match == 'exact' else '<='}{letters}")
    elif colorless:
        parts.append("id=c")
    if f.flavor == "has":
        parts.append("has:flavor")
    elif f.flavor == "none":
        parts.append("-has:flavor")
    if f.types:
        parts.append(_any([f"t:{t}" for t in f.types]))
    if f.legendary == "only":
        parts.append("t:legendary")
    elif f.legendary == "not":
        parts.append("-t:legendary")
    if f.rarity:
        parts.append(_any([f"r:{r}" for r in f.rarity]))
    if f.artist.strip():
        parts.append(f'a:"{f.artist.strip().replace(chr(34), "")}"')
    if f.treatments:
        parts.append(_any([TREATMENTS[t][1] for t in f.treatments if t in TREATMENTS]))
    return " ".join(parts)


def _list(v) -> list:
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            return []
    return list(v or [])


def _flavors(card: dict) -> list[str]:
    out = [card.get("flavor_text")] + [fc.get("flavor_text") for fc in card.get("card_faces") or []]
    return [t for t in out if t]


def _artists(card: dict) -> list[str]:
    out = [card.get("artist")] + [fc.get("artist") for fc in card.get("card_faces") or []]
    return [a for a in out if a]


def matches(card: dict, f: Filters, *, set_codes: list[str] | None = None, local: bool = False) -> bool:
    """Does a Scryfall card dict pass ``f``? The Python twin of :func:`build_query`.
    ``local=True`` checks only the fields the local catalog keeps (skips flavor,
    artist, old frame, textless) — a prefilter, never stricter than the full check."""
    tl = (card.get("type_line") or "").lower()
    if "token" in tl.split("—")[0] or "emblem" in tl:
        return False
    if f.families and set_codes is not None and (card.get("set") or "").lower() not in set_codes:
        return False
    ci = {c.lower() for c in _list(card.get("color_identity"))}
    letters, colorless = _colors(f)
    if letters:
        want = set(letters)
        if (ci != want) if f.color_match == "exact" else not ci <= want:
            return False
    elif colorless and ci:
        return False
    words = set(tl.replace("—", " ").replace("//", " ").split())
    if f.types and not any(t in words for t in f.types):
        return False
    if f.legendary == "only" and "legendary" not in words:
        return False
    if f.legendary == "not" and "legendary" in words:
        return False
    if f.rarity and (card.get("rarity") or "") not in f.rarity:
        return False
    if f.treatments:
        effects = set(_list(card.get("frame_effects")))
        have = {
            "borderless": card.get("border_color") == "borderless",
            "fullart": bool(card.get("full_art")),
            "showcase": "showcase" in effects,
            "extended": "extendedart" in effects,
            "oldframe": None if local else str(card.get("frame")) in ("1993", "1997"),
            "textless": None if local else bool(card.get("textless")),
        }
        # Locally unknown treatments can't rule a card out.
        if not any(have.get(t) is not False for t in f.treatments if t in have):
            return False
    if local:
        return True
    if f.flavor == "has" and not _flavors(card):
        return False
    if f.flavor == "none" and _flavors(card):
        return False
    if f.artist.strip():
        needle = f.artist.strip().lower()
        if not any(needle in a.lower() for a in _artists(card)):
            return False
    return True


# ---------- normalize ----------

def _image(card: dict) -> str | None:
    uris = card.get("image_uris") or ((card.get("card_faces") or [{}])[0].get("image_uris")) or {}
    return uris.get("large") or uris.get("normal")


def _price(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def normalize(card: dict) -> dict:
    """One Scryfall card → the surfer's card shape (faces kept for DFCs)."""
    faces = []
    for fc in card.get("card_faces") or []:
        faces.append({
            "name": fc.get("name") or "",
            "type_line": fc.get("type_line"),
            "oracle_text": fc.get("oracle_text"),
            "flavor_text": fc.get("flavor_text"),
            "artist": fc.get("artist"),
            "image": (fc.get("image_uris") or {}).get("large") or (fc.get("image_uris") or {}).get("normal"),
        })
    flav = _flavors(card)
    prices = card.get("prices") or {}
    return {
        "scryfall_id": card["id"],
        "oracle_id": card.get("oracle_id") or ((card.get("card_faces") or [{}])[0].get("oracle_id")),
        "illustration_id": card.get("illustration_id") or ((card.get("card_faces") or [{}])[0].get("illustration_id")),
        "name": card.get("name") or "",
        "type_line": card.get("type_line") or (faces[0]["type_line"] if faces else None),
        "oracle_text": card.get("oracle_text"),
        "flavor_text": card.get("flavor_text") or (flav[0] if flav and not faces else None),
        "artist": card.get("artist") or (faces[0]["artist"] if faces else None),
        "set_code": (card.get("set") or "").lower(),
        "set_name": card.get("set_name"),
        "collector_number": card.get("collector_number"),
        "rarity": card.get("rarity"),
        "released_at": card.get("released_at"),
        "image": _image(card),
        "faces": faces,
        "scryfall_uri": card.get("scryfall_uri"),
        "color_identity": [c.upper() for c in _list(card.get("color_identity"))],
        "prices": {"nonfoil": _price(prices.get("usd")), "foil": _price(prices.get("usd_foil") or prices.get("usd_etched"))},
    }


def _enrich(cards: list[dict]) -> list[dict]:
    """Your copies (this printing + any printing) and the artwork's art tags."""
    sids = [c["scryfall_id"] for c in cards]
    here: dict[str, int] = {}
    with db.connect() as conn:
        if sids:
            q = ("SELECT scryfall_id, SUM(quantity) FROM inventory "
                 f"WHERE quantity > 0 AND scryfall_id IN ({','.join('?' * len(sids))}) GROUP BY scryfall_id")
            here = {s: n for s, n in conn.execute(q, sids)}
    facts = explore.facts_for([c["oracle_id"] for c in cards if c["oracle_id"]])
    tags = scryfall_art.art_tags_for_illustrations(c["illustration_id"] for c in cards)
    for c in cards:
        fa = facts.get(c["oracle_id"] or "")
        c["owned"] = int(here.get(c["scryfall_id"], 0))
        c["owned_any"] = fa.owned if fa else 0
        c["art_tags"] = tags.get(c["illustration_id"] or "", [])
    return cards


# ---------- draw ----------

@dataclass
class Draw:
    source: Source
    query: str
    cards: list[dict] = field(default_factory=list)
    total: int | None = None
    next_offset: int | None = None
    exhausted: bool = False


def _draw_scryfall(f: Filters, n: int, with_total: bool) -> Draw:
    query = build_query(f)
    out = Draw(source="scryfall", query=query)
    if with_total:
        out.total = scryfall.search_total(query, unique="prints")
        if out.total == 0:
            out.exhausted = True
            return out
    tries = 0
    while len(out.cards) < n and tries < n + 3:
        tries += 1
        card = scryfall.random_card(query)
        if card is None:
            out.exhausted = True
            break
        if card.get("layout") in ("art_series", "token", "double_faced_token", "emblem"):
            continue
        out.cards.append(normalize(card))
    return out


def _owned_candidates(f: Filters, set_codes: list[str] | None) -> list[str]:
    allowed: set[str] | None = None
    if f.art:
        allowed = set()
        for t in f.art:
            try:
                allowed |= {r["scryfall_id"] for r in scryfall_art.printings_with_art(t, owned_only=True)}
            except LookupError:
                pass
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT c.scryfall_id, c.set_code AS \"set\", c.type_line, c.color_identity, c.rarity, "
            "c.border_color, c.full_art, c.frame_effects, c.is_token "
            "FROM cards c JOIN (SELECT scryfall_id FROM inventory WHERE quantity > 0 GROUP BY scryfall_id) i "
            "ON i.scryfall_id = c.scryfall_id").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if d["is_token"] or (allowed is not None and d["scryfall_id"] not in allowed):
            continue
        if matches(d, f, set_codes=set_codes, local=True):
            out.append(d["scryfall_id"])
    return sorted(out)


def _draw_owned(f: Filters, n: int, seed: int, offset: int) -> Draw:
    codes = family_codes(f.families) if f.families else None
    out = Draw(source="owned", query=build_query(f, set_codes=codes))
    sids = _owned_candidates(f, codes)
    random.Random(seed).shuffle(sids)
    out.total = len(sids)
    pos = max(0, offset)
    chunks = 0
    while len(out.cards) < n and pos < len(sids) and chunks < _MAX_CHUNKS:
        chunks += 1
        batch = sids[pos:pos + _COLLECTION_CHUNK]
        found, _missing = scryfall.collection([{"id": s} for s in batch])
        by_id = {c["id"]: c for c in found}
        for s in batch:
            pos += 1
            card = by_id.get(s)
            if card and matches(card, f, set_codes=codes):
                out.cards.append(normalize(card))
                if len(out.cards) >= n:
                    break
    out.next_offset = pos
    out.exhausted = pos >= len(sids)
    return out


def draw(f: Filters, *, source: Source = "scryfall", n: int = 4, seed: int = 0,
         offset: int = 0, with_total: bool = False) -> Draw:
    """The next ``n`` cards for the feed (see the module docstring)."""
    n = max(1, min(n, MAX_DRAW))
    out = _draw_owned(f, n, seed, offset) if source == "owned" else _draw_scryfall(f, n, with_total)
    _enrich(out.cards)
    return out


FAMILY_SET_TYPES = frozenset({"expansion", "core", "masters", "commander", "draft_innovation",
                              "funny", "starter", "duel_deck", "from_the_vault", "spellbook",
                              "premium_deck", "box", "masterpiece", "arsenal"})


def family_options() -> list[dict]:
    """Every paper set family a surfer can narrow to: top-level sets (no parent)
    of the playable set types, newest first."""
    out = [
        {"value": s["code"].lower(), "label": s["name"], "year": (s.get("released_at") or "")[:4] or None}
        for s in scryfall.all_sets()
        if not s.get("parent_set_code") and not s.get("digital") and s.get("set_type") in FAMILY_SET_TYPES
    ]
    out.sort(key=lambda o: (o["year"] or "", o["label"]), reverse=True)
    return out


def options() -> dict:
    """The choice lists the filter rail offers."""
    return {
        "families": family_options(),
        "treatments": [{"value": k, "label": v[0]} for k, v in TREATMENTS.items()],
        "types": [{"value": t, "label": t.capitalize()} for t in TYPES],
        "rarities": [{"value": r, "label": r.capitalize()} for r in RARITIES],
    }

"""Commander Spellbook combos, joined to your collection.

Two reads, both through :mod:`magic_manager.commander_spellbook` (the
rate-limited, disk-cached ``spellbook.sh`` wrapper — never HTTP here):

* :func:`deck_combos` — the combos a decklist CONTAINS and the ones it is ONE
  CARD away from (Spellbook's ``almostIncluded``: same colour identity). Each
  near-miss names the missing card with what you own of it (copies, free
  copies) and its cheapest price, and :attr:`DeckCombos.missing_cards` rolls
  those up per card ("add X → N combos").
* :func:`card_combos` — the most popular combos a card is part of, each piece
  marked with what you own.

Card ownership / price / display printing reuse :func:`explore.facts_for` (one
batched lookup). Pieces are matched to the deck by ``oracle_id`` so double-
faced names never trip the join. A Spellbook outage degrades to
``available=False`` + a plain ``error`` instead of raising.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable

from . import commander_spellbook, db, explore

COMBO_URL = "https://commanderspellbook.com/combo/{id}/"


@dataclass
class Piece:
    """One card a combo uses."""
    name: str
    oracle_id: str | None
    in_deck: bool
    facts: explore.Facts
    image_uri: str | None = None          # Spellbook's art when the card isn't local
    printing_id: str | None = None        # the printing to add: your most-free copy, else the first standard one


@dataclass
class Combo:
    id: str
    url: str
    pieces: list[Piece]
    produces: list[str]
    requires: list[str]                   # templates ("a sac outlet") — any card that fits
    description: str
    prerequisites: str
    mana_needed: str
    popularity: int | None
    identity: str
    missing: Piece | None = None          # one-card-away: the card to add


@dataclass
class MissingCard:
    """A card that would complete one or more near-miss combos."""
    piece: Piece
    combos: list[str]                     # combo ids it completes, most popular first
    popularity: int                       # sum over those combos


@dataclass
class DeckCombos:
    available: bool
    error: str | None = None
    identity: str | None = None
    included: list[Combo] = field(default_factory=list)
    almost: list[Combo] = field(default_factory=list)
    missing_cards: list[MissingCard] = field(default_factory=list)
    off_color: int = 0                    # near-misses that need another colour


@dataclass
class CardCombos:
    available: bool
    name: str
    error: str | None = None
    combos: list[Combo] = field(default_factory=list)


# ---------- parsing ----------

def _pieces_raw(variant: dict) -> list[dict]:
    out = []
    for u in variant.get("uses") or []:
        c = u.get("card") or {}
        if c.get("name"):
            out.append(c)
    return out


def _prereqs(v: dict) -> str:
    parts = [v.get("easyPrerequisites") or "", v.get("notablePrerequisites") or ""]
    return "\n".join(p.strip() for p in parts if p and p.strip())


def _build(variants: list[dict], deck_oids: set[str], facts: dict[str, explore.Facts],
           pick: dict[str, str], *, near_miss: bool) -> list[Combo]:
    combos: list[Combo] = []
    for v in variants:
        pieces = []
        for c in _pieces_raw(v):
            oid = c.get("oracleId")
            pieces.append(Piece(
                name=c["name"], oracle_id=oid, in_deck=bool(oid and oid in deck_oids),
                facts=facts.get(oid or "") or explore.Facts(oracle_id=oid),
                image_uri=c.get("imageUriFrontArtCrop") or c.get("imageUriFrontNormal"),
                printing_id=pick.get(oid or ""),
            ))
        missing = None
        if near_miss:
            out = [p for p in pieces if not p.in_deck]
            if len(out) != 1:
                continue                   # not a single-card gap (defensive; Spellbook guarantees it)
            missing = out[0]
        combos.append(Combo(
            id=str(v.get("id")), url=COMBO_URL.format(id=v.get("id")), pieces=pieces,
            produces=[p["feature"]["name"] for p in v.get("produces") or [] if (p.get("feature") or {}).get("name")],
            requires=[r["template"]["name"] for r in v.get("requires") or [] if (r.get("template") or {}).get("name")],
            description=v.get("description") or "", prerequisites=_prereqs(v),
            mana_needed=v.get("manaNeeded") or "", popularity=v.get("popularity"),
            identity=v.get("identity") or "", missing=missing,
        ))
    combos.sort(key=lambda c: -(c.popularity or 0))
    return combos


def _lookups(variants: Iterable[dict]) -> tuple[dict[str, explore.Facts], dict[str, str]]:
    """One batched pass for every piece: local facts + the printing to add."""
    from . import deck_edit

    oids = [o for v in variants for c in _pieces_raw(v) if (o := c.get("oracleId"))]
    return explore.facts_for(oids), deck_edit.usable_printings(oids)[0]


def _roll_up(almost: list[Combo]) -> list[MissingCard]:
    by: dict[str, MissingCard] = {}
    for c in almost:
        p = c.missing
        key = p.oracle_id or p.name
        m = by.setdefault(key, MissingCard(piece=p, combos=[], popularity=0))
        m.combos.append(c.id)
        m.popularity += c.popularity or 0
    return sorted(by.values(), key=lambda m: (-len(m.combos), -m.popularity, m.piece.name))


# ---------- deck ----------

def _single_face(name: str) -> str:
    """``"X // X"`` (a reversible printing: the same card on both faces) → ``"X"``;
    real double-faced names are left alone."""
    front, sep, back = name.partition(" // ")
    return front if sep and front == back else name


def _deck_names(rows: Iterable[tuple[str, str, int]]) -> tuple[list[str], list[str], set[str]]:
    """``(scryfall_id, board, count)`` rows → (commander names, main names, oracle ids)."""
    rows = [(sid, board) for sid, board, count in rows
            if count > 0 and (board == "commander" or board in commander_spellbook.MAIN_BOARDS)]
    ids = list(dict.fromkeys(sid for sid, _ in rows))
    meta: dict[str, tuple[str, str | None]] = {}
    with db.connect() as conn:
        for i in range(0, len(ids), 500):
            part = ids[i:i + 500]
            for r in conn.execute(
                f"SELECT scryfall_id, name, oracle_id FROM cards WHERE scryfall_id IN ({','.join('?' * len(part))})", part,
            ):
                meta[r[0]] = (_single_face(r[1]), r[2])
        # Reversible printings (e.g. Secret Lair "X // X") carry no oracle id:
        # borrow it from another printing of the same card.
        orphans = list({name for name, oid in meta.values() if not oid})
        found: dict[str, str] = {}
        for i in range(0, len(orphans), 500):
            part = orphans[i:i + 500]
            for name, oid in conn.execute(
                f"SELECT name, oracle_id FROM cards WHERE oracle_id IS NOT NULL AND name IN ({','.join('?' * len(part))})", part,
            ):
                found.setdefault(name, oid)
        meta = {sid: (name, oid or found.get(name)) for sid, (name, oid) in meta.items()}
    commanders, main, oids = [], [], set()
    for sid, board in rows:
        if sid not in meta:
            continue
        name, oid = meta[sid]
        (commanders if board == "commander" else main).append(name)
        if oid:
            oids.add(oid)
    return commanders, main, oids


def combos_for_rows(rows: Iterable[tuple[str, str, int]]) -> DeckCombos:
    """Combos in, and one card away from, a decklist of ``(scryfall_id, board, count)``
    rows (a saved version or an unsaved draft). Sideboard / maybe / tokens are ignored."""
    commanders, main, oids = _deck_names(rows)
    if not commanders and not main:
        return DeckCombos(available=True)
    try:
        resp = commander_spellbook.find_my_combos(commander=commanders, main=main)
    except Exception as e:  # noqa: BLE001 - any failure degrades to "unavailable"
        return DeckCombos(available=False, error=f"Couldn't reach Commander Spellbook: {e}")
    res = (resp or {}).get("results") if isinstance(resp, dict) else None
    if not isinstance(res, dict):
        return DeckCombos(available=False, error="Commander Spellbook sent an unexpected reply")
    inc = res.get("included") or []
    near = res.get("almostIncluded") or []
    facts, pick = _lookups([*inc, *near])
    almost = _build(near, oids, facts, pick, near_miss=True)
    return DeckCombos(
        available=True, identity=res.get("identity"),
        included=_build(inc, oids, facts, pick, near_miss=False), almost=almost,
        missing_cards=_roll_up(almost), off_color=len(res.get("almostIncludedByAddingColors") or []),
    )


def deck_combos(slug: str) -> DeckCombos:
    """:func:`combos_for_rows` over a saved deck's current version."""
    from . import deck_edit

    with db.connect() as conn:
        d = deck_edit._deck(conn, slug)
        cards = deck_edit._current_cards(conn, d["current_version_id"])
    return combos_for_rows([(c.scryfall_id, c.board, c.count) for c in cards])


# ---------- one card ----------

def card_combos(name: str, *, limit: int = 30) -> CardCombos:
    """The ``limit`` most popular combos ``name`` (its oracle name) is part of,
    each piece carrying what you own of it (``facts.owned`` / ``facts.free``)."""
    try:
        resp = commander_spellbook.variants(f'card="{name}"', limit=limit)
    except Exception as e:  # noqa: BLE001
        return CardCombos(available=False, name=name, error=f"Couldn't reach Commander Spellbook: {e}")
    variants = (resp or {}).get("results") if isinstance(resp, dict) else None
    if not isinstance(variants, list):
        return CardCombos(available=False, name=name, error="Commander Spellbook sent an unexpected reply")
    combos = _build(variants, set(), *_lookups(variants), near_miss=False)
    return CardCombos(available=True, name=name, combos=combos[:limit])


def to_json(obj) -> dict:
    """Plain-dict form (dataclasses all the way down) for scripts / snapshots."""
    from dataclasses import asdict
    return json.loads(json.dumps(asdict(obj), default=str))

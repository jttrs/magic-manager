"""Explore a card through EDHREC's community data — as a CARD (one of the 99).

The commander role reuses :func:`edhrec.compare_commanders` (``ref_b`` optional).
This module covers the card role: a card page's commanders, co-played cards
(with lift), similar cards and deck mix, joined to local card facts, Scryfall
Tagger tags and what you own — and a two-card comparison that partitions each
of those into only-A / both / only-B. Descriptive only: no verdicts.

Reads the cached ``edhrec_pages`` card page (synced once on demand).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import db, edhrec, inventory, legality, scryfall_tags, sets

# Card-page cardlists that are co-played cards, grouped by type (EDHREC's tags).
COPLAY_TAGS: dict[str, str] = {
    "creatures": "Creatures", "instants": "Instants", "sorceries": "Sorceries",
    "utilityartifacts": "Artifacts", "manaartifacts": "Mana rocks",
    "enchantments": "Enchantments", "planeswalkers": "Planeswalkers",
    "battles": "Battles", "utilitylands": "Utility lands", "lands": "Lands",
}
TAG_LIMIT = 40


@dataclass
class Facts:
    """Local facts for one oracle card (display printing, cheapest price, ownership)."""
    oracle_id: str | None = None
    type_line: str | None = None
    cmc: float | None = None
    color_identity: list[str] = field(default_factory=list)
    lowest_usd: float | None = None
    scryfall_id: str | None = None
    image_uri: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    owned: int = 0
    free: int = 0


@dataclass
class Entry:
    name: str
    slug: str
    facts: Facts
    num_decks: int | None = None
    potential_decks: int | None = None
    share: float | None = None        # % of the potential decks that run it
    lift: float | None = None         # co-play: how much more often than chance
    group: str | None = None          # co-play type group / commander "top"|"new"


@dataclass
class CardProfile:
    name: str
    slug: str
    facts: Facts
    commander_eligible: bool
    num_decks: int | None
    potential_decks: int | None
    salt: float | None
    functions: list[str]
    tags: list[dict]
    commanders: list[Entry]
    coplayed: list[Entry]
    similar: list[Entry]
    deck_mix: list[dict]


def _pct(num, pot) -> float | None:
    return round(100.0 * num / pot, 2) if num is not None and pot else None


def _local_card(ref: str) -> tuple[str, dict | None]:
    """Resolve ``ref`` to its oracle name locally (front face, case-insensitive);
    falls back to Scryfall via :func:`edhrec.resolve_oracle_card`."""
    with db.connect() as conn:
        row = conn.execute(
            """SELECT name, type_line, oracle_text, oracle_id FROM cards
               WHERE lower(name) = lower(?) OR lower(substr(name, 1, instr(name || ' // ', ' // ') - 1)) = lower(?)
               ORDER BY released_at LIMIT 1""", (ref, ref),
        ).fetchone()
    if row:
        return row["name"].split(" // ")[0], dict(row)
    return edhrec.resolve_oracle_card(ref)


def _card_page(name: str) -> dict:
    slug = edhrec.slugify(name)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT json FROM edhrec_pages WHERE page_type = 'card' AND slug = ? ORDER BY fetched_at DESC LIMIT 1",
            (slug,),
        ).fetchone()
    if row:
        return json.loads(row[0])
    return edhrec.sync_card(name).raw


def facts_for(oracle_ids: list[str]) -> dict[str, Facts]:
    """Batched local facts per oracle id: display printing (first standard),
    cheapest price, and copies owned / free across every printing."""
    oids = list(dict.fromkeys(o for o in oracle_ids if o))
    meta = sets.lowest_price_by_oracle(oids)
    display = sets.standard_printing_by_oracle(oids)
    owned: dict[str, list[tuple[str, int]]] = {}
    with db.connect() as conn:
        for i in range(0, len(oids), 400):
            part = oids[i:i + 400]
            for oid, sid, q in conn.execute(
                f"""SELECT c.oracle_id, i.scryfall_id, SUM(i.quantity) FROM inventory i
                    JOIN cards c ON c.scryfall_id = i.scryfall_id
                    WHERE i.quantity > 0 AND c.oracle_id IN ({','.join('?' * len(part))})
                    GROUP BY i.scryfall_id""", part,
            ):
                owned.setdefault(oid, []).append((sid, q))
    free = inventory.free_quantities([s for v in owned.values() for s, _ in v])
    out: dict[str, Facts] = {}
    for oid in oids:
        m = meta.get(oid) or {}
        p = display.get(oid) or m
        ci = m.get("color_identity")
        mine = owned.get(oid, [])
        out[oid] = Facts(
            oracle_id=oid, type_line=m.get("type_line"), cmc=m.get("cmc"),
            color_identity=json.loads(ci) if isinstance(ci, str) and ci else (ci or []),
            lowest_usd=m.get("lowest_usd"), scryfall_id=p.get("scryfall_id"),
            image_uri=p.get("image_uri"), set_code=p.get("set_code"),
            collector_number=p.get("collector_number"),
            owned=sum(q for _, q in mine), free=sum(free.get(s, 0) for s, _ in mine),
        )
    return out


def card_profile(ref: str) -> CardProfile:
    """Everything EDHREC knows about ``ref`` as a card in the 99, joined locally."""
    name, card = _local_card(ref)
    page = _card_page(name)
    lists = edhrec.cardlists(page)
    head = (page.get("container") or {}).get("json_dict", {}).get("card") or {}

    raw_cmd: list[tuple[dict, str]] = []
    seen: set[str] = set()
    for tag, group in (("topcommanders", "top"), ("newcommanders", "new")):
        for cv in lists.get(tag, []):
            key = cv.get("slug") or cv.get("name")
            if key and key not in seen:
                seen.add(key)
                raw_cmd.append((cv, group))
    raw_co: list[tuple[dict, str]] = []
    seen = set()
    for tag, group in COPLAY_TAGS.items():
        for cv in lists.get(tag, []):
            key = cv.get("slug") or cv.get("name")
            if key and key not in seen:
                seen.add(key)
                raw_co.append((cv, group))
    similar_names = [n for n in (page.get("similar") or []) if isinstance(n, str)]

    names = [cv["name"] for cv, _ in raw_cmd + raw_co if cv.get("name")] + similar_names + [name]
    resolved = edhrec.resolve_names_to_oracle(names)
    oid_of = lambda n: (resolved.get(n.casefold()) or {}).get("oracle_id")  # noqa: E731
    my_oid = oid_of(name) or (card or {}).get("oracle_id")
    facts = facts_for([oid_of(n) for n in names if oid_of(n)] + ([my_oid] if my_oid else []))
    blank = Facts()

    def entry(cv: dict, group: str | None) -> Entry:
        n = cv["name"]
        num, pot = cv.get("num_decks"), cv.get("potential_decks")
        return Entry(name=n, slug=cv.get("slug") or edhrec.slugify(n), facts=facts.get(oid_of(n) or "", blank),
                     num_decks=num, potential_decks=pot, share=_pct(num, pot), lift=cv.get("lift"), group=group)

    summ = scryfall_tags.card_summaries([my_oid], limit=TAG_LIMIT).get(my_oid or "") if my_oid else None
    pie = ((page.get("panels") or {}).get("piechart") or {}).get("content") or []
    return CardProfile(
        name=page.get("header", name).removesuffix(" (Card)") or name,
        slug=edhrec.slugify(name),
        facts=facts.get(my_oid or "", Facts(oracle_id=my_oid)),
        commander_eligible=bool(card) and legality.is_commander_eligible(card),
        num_decks=head.get("num_decks"), potential_decks=head.get("potential_decks"),
        salt=head.get("salt"),
        functions=list(summ.functions) if summ else [],
        tags=[{"id": t.id, "slug": t.slug, "label": t.label} for t in summ.tags] if summ else [],
        commanders=[entry(cv, g) for cv, g in raw_cmd if cv.get("name")],
        coplayed=[entry(cv, g) for cv, g in raw_co if cv.get("name")],
        similar=[Entry(name=n, slug=edhrec.slugify(n), facts=facts.get(oid_of(n) or "", blank)) for n in similar_names],
        deck_mix=[{"label": p.get("label"), "value": p.get("value")} for p in pie if p.get("value")],
    )


@dataclass
class Paired:
    """One commander / co-played card seen from both sides."""
    name: str
    slug: str
    facts: Facts
    bucket: str                      # a_only | both | b_only
    a: Entry | None
    b: Entry | None
    gap: float | None                # |a − b| on the section's metric (share or lift)


def _pair(a: list[Entry], b: list[Entry], metric: str) -> list[Paired]:
    def key(e: Entry) -> str:
        return e.facts.oracle_id or e.slug
    am, bm = {key(e): e for e in a}, {key(e): e for e in b}
    out: list[Paired] = []
    for k in dict.fromkeys([*am, *bm]):
        ea, eb = am.get(k), bm.get(k)
        src = ea or eb
        va, vb = (getattr(ea, metric) if ea else None), (getattr(eb, metric) if eb else None)
        out.append(Paired(
            name=src.name, slug=src.slug, facts=src.facts,
            bucket="both" if ea and eb else "a_only" if ea else "b_only",
            a=ea, b=eb, gap=abs(va - vb) if va is not None and vb is not None else None,
        ))
    # biggest differences first within "both"; otherwise strongest single-side value first
    out.sort(key=lambda p: -(p.gap if p.gap is not None else (getattr(p.a or p.b, metric) or 0)))
    return out


@dataclass
class CardComparison:
    a: CardProfile
    b: CardProfile
    commanders: list[Paired]
    coplayed: list[Paired]
    tags: dict[str, list[dict]]      # a_only / both / b_only


def compare_cards(ref_a: str, ref_b: str) -> CardComparison:
    """Two cards in the 99, side by side: commanders (by share), co-played cards
    (by lift) and Tagger tags, each partitioned into only-A / both / only-B."""
    a, b = card_profile(ref_a), card_profile(ref_b)
    ta, tb = {t["id"]: t for t in a.tags}, {t["id"]: t for t in b.tags}
    return CardComparison(
        a=a, b=b,
        commanders=_pair(a.commanders, b.commanders, "share"),
        coplayed=_pair(a.coplayed, b.coplayed, "lift"),
        tags={
            "a_only": [t for k, t in ta.items() if k not in tb],
            "both": [t for k, t in ta.items() if k in tb],
            "b_only": [t for k, t in tb.items() if k not in ta],
        },
    )


def search_cards(q: str, *, limit: int = 20) -> list[dict]:
    """Any physical, non-token card whose name contains ``q`` (local), one per
    oracle card: prefix matches first, EDHREC-cached next, then alphabetical."""
    q = (q or "").strip()
    if not q:
        return []
    _, card_cached = edhrec._cached_slugs()
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT oracle_id, name, type_line, oracle_text, color_identity, image_uri FROM cards
               WHERE name LIKE ? COLLATE NOCASE AND is_token = 0 AND oracle_id IS NOT NULL
               GROUP BY oracle_id""", (f"%{q}%",),
        ).fetchall()
    ql = q.lower()
    out = []
    for r in rows:
        front = r["name"].split(" // ")[0]
        out.append({
            "name": front, "oracle_id": r["oracle_id"], "type_line": r["type_line"],
            "color_identity": json.loads(r["color_identity"]) if r["color_identity"] else [],
            "image_uri": r["image_uri"], "cached": edhrec.slugify(front) in card_cached,
            "commander_eligible": legality.is_commander_eligible(dict(r)),
        })
    out.sort(key=lambda c: (not c["name"].lower().startswith(ql), not c["cached"], c["name"]))
    return out[:limit]

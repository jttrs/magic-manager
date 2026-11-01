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
from dataclasses import dataclass, field, replace

from . import db, edhrec, inventory, legality, scryfall_tags, sets, util

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
    mana_cost: str | None = None
    color_identity: list[str] = field(default_factory=list)
    lowest_usd: float | None = None
    scryfall_id: str | None = None
    image_uri: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    owned: int = 0
    free: int = 0
    # A partner pairing ("Kraum // Tymna"): these facts are the FIRST card's
    # printing and type; ``partner`` is the second card's own facts. Price,
    # colour identity and copies describe the PAIR (see :func:`pair_facts`).
    partner: Facts | None = None


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
        return util.front_face(row["name"]), dict(row)
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
            oracle_id=oid, type_line=m.get("type_line"), cmc=m.get("cmc"), mana_cost=m.get("mana_cost") or None,
            color_identity=json.loads(ci) if isinstance(ci, str) and ci else (ci or []),
            lowest_usd=m.get("lowest_usd"), scryfall_id=p.get("scryfall_id"),
            image_uri=p.get("image_uri"), set_code=p.get("set_code"),
            collector_number=p.get("collector_number"),
            owned=sum(q for _, q in mine), free=sum(free.get(s, 0) for s, _ in mine),
        )
    return out


_WUBRG = "WUBRG"


def pair_facts(a: Facts, b: Facts) -> Facts:
    """Facts for a partner pairing: the first card's printing and type with the
    second as ``partner``; colour identity is the union, the price is both
    cheapest printings together (None unless both are priced), and copies
    owned / free are the pairs you could put together (the fewer of the two).
    ``oracle_id`` is None — the pair is two cards, not one."""
    ci = sorted(set(a.color_identity) | set(b.color_identity), key=lambda c: (_WUBRG.find(c) % 6, c))
    price = round(a.lowest_usd + b.lowest_usd, 2) if a.lowest_usd is not None and b.lowest_usd is not None else None
    return replace(a, oracle_id=None, color_identity=ci, lowest_usd=price,
                   owned=min(a.owned, b.owned), free=min(a.free, b.free), partner=b)


def facts_by_name(names: list[str], *, local_only: bool = False) -> dict[str, Facts]:
    """Local facts per CASEFOLDED card name, partner pairings included (EDHREC
    names a pair "A // B"; both halves resolve and join via :func:`pair_facts`).
    Unresolved names are absent. ``local_only`` never asks Scryfall."""
    resolved = edhrec.resolve_names_to_oracle(names, local_only=local_only)
    oids = [o for r in resolved.values() for o in [r.get("oracle_id"), *(p.get("oracle_id") for p in r.get("partners") or [])] if o]
    facts = facts_for(oids)
    out: dict[str, Facts] = {}
    for n in dict.fromkeys(names):
        r = resolved.get(n.casefold()) or {}
        if r.get("oracle_id") and r["oracle_id"] in facts:
            out[n.casefold()] = facts[r["oracle_id"]]
        elif r.get("partners"):
            a, b = (facts.get(p["oracle_id"]) for p in r["partners"])
            if a and b:
                out[n.casefold()] = pair_facts(a, b)
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
    by_name = facts_by_name(names)
    mine = by_name.get(name.casefold())
    my_oid = (mine.oracle_id if mine else None) or (card or {}).get("oracle_id")
    if my_oid and not mine:
        mine = facts_for([my_oid]).get(my_oid)
    blank = Facts()
    fact = lambda n: by_name.get(n.casefold(), blank)  # noqa: E731

    def entry(cv: dict, group: str | None) -> Entry:
        n = cv["name"]
        num, pot = cv.get("num_decks"), cv.get("potential_decks")
        return Entry(name=n, slug=cv.get("slug") or edhrec.slugify(n), facts=fact(n),
                     num_decks=num, potential_decks=pot, share=_pct(num, pot), lift=cv.get("lift"), group=group)

    summ = scryfall_tags.card_summaries([my_oid], limit=TAG_LIMIT).get(my_oid or "") if my_oid else None
    pie = ((page.get("panels") or {}).get("piechart") or {}).get("content") or []
    return CardProfile(
        name=page.get("header", name).removesuffix(" (Card)") or name,
        slug=edhrec.slugify(name),
        facts=mine or Facts(oracle_id=my_oid),
        commander_eligible=bool(card) and legality.is_commander_eligible(card),
        num_decks=head.get("num_decks"), potential_decks=head.get("potential_decks"),
        salt=head.get("salt"),
        functions=list(summ.functions) if summ else [],
        tags=[{"id": t.id, "slug": t.slug, "label": t.label} for t in summ.tags] if summ else [],
        commanders=[entry(cv, g) for cv, g in raw_cmd if cv.get("name")],
        coplayed=[entry(cv, g) for cv, g in raw_co if cv.get("name")],
        similar=[Entry(name=n, slug=edhrec.slugify(n), facts=fact(n)) for n in similar_names],
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


_LEADER_PREFILTER = ("(type_line LIKE '%Legendary%' OR oracle_text LIKE '%can be your commander%' "
                     "OR type_line LIKE '%Background%')")


def search_cards(q: str, *, limit: int = 20, commanders_only: bool = False) -> list[dict]:
    """The ONE local card search behind both pickers: physical, non-token cards
    whose name contains ``q``, one per oracle card, named by front face. Prefix
    matches first, then EDHREC-cached (the commander page with
    ``commanders_only``, else the card page), then alphabetical."""
    q = (q or "").strip()
    if not q:
        return []
    cmd_cached, card_cached = edhrec.cached_slugs()
    cached = cmd_cached if commanders_only else card_cached
    leaders = f" AND {_LEADER_PREFILTER}" if commanders_only else ""
    with db.connect() as conn:
        rows = conn.execute(
            f"""SELECT oracle_id, name, type_line, oracle_text, color_identity, image_uri FROM cards
               WHERE name LIKE ? COLLATE NOCASE AND is_token = 0 AND oracle_id IS NOT NULL{leaders}
               GROUP BY oracle_id""", (f"%{q}%",),
        ).fetchall()
    ql = q.lower()
    out = []
    for r in rows:
        eligible = legality.is_commander_eligible(dict(r))
        if commanders_only and not eligible:
            continue
        front = util.front_face(r["name"])
        out.append({
            "name": front, "oracle_id": r["oracle_id"], "type_line": r["type_line"],
            "color_identity": json.loads(r["color_identity"]) if r["color_identity"] else [],
            "image_uri": r["image_uri"], "cached": edhrec.slugify(front) in cached,
            "commander_eligible": eligible,
        })
    out.sort(key=lambda c: (not c["name"].lower().startswith(ql), not c["cached"], c["name"]))
    return out[:limit]


# ---------- rankings (EDHREC workflow C, joined to the collection) ----------

@dataclass
class Ranked:
    rank: int | None
    name: str
    slug: str
    facts: Facts
    num_decks: int | None = None
    salt: float | None = None
    trend: float | None = None


@dataclass
class Ranking:
    key: edhrec.RankingKey        # the base ranking read from EDHREC
    title: str
    cached: bool                  # False = not every list it needs was fetched (run the sync job)
    fetched_at: str | None        # the oldest read among the lists it combines
    rows: list[Ranked]            # the requested page (``offset``/``limit``) of the matches
    total: int = 0                # matches after every filter (name and ownership included)
    base: int = 0                 # entries in the base list read from EDHREC, before local filters
    pool: int = 0                 # entries after the color / tag / set filters only
    owned: int = 0                # of ``pool``: entries you own a copy of
    unused: int = 0               # of ``pool``: entries with a copy not in a built deck
    local_filters: list[str] = field(default_factory=list)  # axes applied locally: color | tag


RANKING_OWN = ("all", "owned", "unused")


def ranking_bases(scope: str = "commanders", timeframe: str = "week", *,
                  color: str | None = None, tag: str | None = None,
                  set_family: str | None = None) -> list[dict]:
    """The EDHREC rankings a request reads. EDHREC's filtered pages don't stack
    (one axis per page; combinations 403), so the MOST SELECTIVE axis is the
    base fetch — a set family (its full commander list), else a color identity
    (read :data:`edhrec.RANKING_POOL_PAGES` deep), else a tag — and the other
    axes narrow it locally (see :func:`ranking`). A tag that narrows another
    base also needs the tag's own list. First entry = the base."""
    if scope != "commanders" or not (color or tag or set_family):
        return [dict(scope=scope, timeframe=timeframe)]
    if set_family:
        base = dict(set_family=set_family)
    elif color:
        base = dict(color=color)
    else:
        base = dict(tag=tag)
    bases = [dict(scope="commanders", timeframe=timeframe, **base)]
    if tag and "tag" not in base:
        bases.append(dict(scope="commanders", timeframe=timeframe, tag=tag))
    return bases


def sync_ranking(scope: str = "commanders", timeframe: str = "week", *,
                 color: str | None = None, tag: str | None = None,
                 set_family: str | None = None, refresh: bool = False,
                 progress=None) -> list[edhrec.SyncResult]:
    """Read-or-sync every list :func:`ranking` needs (``refresh`` re-reads all)."""
    return [edhrec.rankings(**b, refresh=refresh, progress=progress)
            for b in ranking_bases(scope, timeframe, color=color, tag=tag, set_family=set_family)]


_IRREGULAR_PLURALS = {"mouse": "mice", "ox": "oxen", "fungus": "fungi", "octopus": "octopi",
                      "man": "men", "goose": "geese", "child": "children"}


def typal_match(tag_slug: str, type_line: str | None) -> bool:
    """True when a creature subtype on ``type_line`` is the EDHREC typal tag
    (plural slugs: goblins, elves, dwarves, faeries, allies). Themes (treasure,
    spellslinger) never match — they narrow by the tag's own list instead."""
    for face in (type_line or "").split(" // "):
        _, _, subs = face.partition(" — ")
        for sub in subs.split():
            s = edhrec.slugify(sub)
            if not s:
                continue
            forms = {s, s + "s", s + "es"}
            if s.endswith("f"):
                forms.add(s[:-1] + "ves")
            if s.endswith("fe"):
                forms.add(s[:-2] + "ves")
            if s.endswith("y"):
                forms.add(s[:-1] + "ies")
            if s in _IRREGULAR_PLURALS:
                forms.add(_IRREGULAR_PLURALS[s])
            if tag_slug in forms:
                return True
    return False


def _color_letters(color: str) -> set[str]:
    slug = edhrec.color_filter_slug(color)
    return set(next(c["colors"] for c in edhrec.color_options() if c["slug"] == slug))


def ranking_title(scope: str = "commanders", timeframe: str = "week", *,
                  color: str | None = None, tag: str | None = None,
                  set_family: str | None = None) -> str:
    """A stacked ranking's title: the base's (``edhrec.ranking_title``) plus each
    locally applied axis — ``Top commanders · FIN family · Mono-Red · Goblins``."""
    bases = ranking_bases(scope, timeframe, color=color, tag=tag, set_family=set_family)
    key = edhrec.ranking_key(**bases[0])
    title = edhrec.ranking_title(key)
    extra = []
    if color and not key.filter.startswith("color:"):
        extra.append("-".join(p.capitalize() for p in edhrec.color_filter_slug(color).split("-")))
    if tag and not key.filter.startswith("tag:"):
        extra.append(f"{edhrec.slugify(tag).replace('-', ' ').capitalize()} tag")
    if not extra:
        return title
    head, sep, when = title.rpartition(" · past ")
    noun, tail = (head, f"{sep}{when}") if sep else (title, "")
    return " · ".join([noun, *extra]) + tail


def ranking(scope: str = "commanders", timeframe: str = "week", *,
            color: str | None = None, tag: str | None = None,
            set_family: str | None = None, q: str = "", own: str = "all",
            offset: int = 0, limit: int | None = None) -> Ranking:
    """A CACHED EDHREC ranking (never fetches) with each entry joined to local
    facts: display printing, cheapest price, copies owned / unused.

    Filters stack: the base list (:func:`ranking_bases`) is narrowed locally by
    the other axes — color identity exactly (EDHREC's color pages are exact
    identities), a tag by its EDHREC list or a matching creature type — then by
    name (``q``) and ownership (``own`` ∈ all | owned | unused). ``offset`` /
    ``limit`` page the matches; ``total`` counts them all. ``cached`` is False
    until every list is read — the caller runs :func:`sync_ranking` (a job)."""
    if own not in RANKING_OWN:
        raise ValueError(f"own must be one of {RANKING_OWN}")
    bases = ranking_bases(scope, timeframe, color=color, tag=tag, set_family=set_family)
    keys = [edhrec.ranking_key(**b) for b in bases]
    title = ranking_title(scope, timeframe, color=color, tag=tag, set_family=set_family)
    reads = [edhrec.cached_rankings(k) for k in keys]
    if any(r is None for r in reads):
        return Ranking(key=keys[0], title=title, cached=False, fetched_at=None, rows=[])
    res = reads[0]
    facts = facts_for([r.oracle_id for r in res.rows if r.oracle_id])
    # Partner pairings are stored with no oracle id; join both halves locally.
    pair_names = [r.name for r in res.rows if not r.oracle_id and edhrec.partner_halves(r.name)]
    pairs = facts_by_name(pair_names, local_only=True) if pair_names else {}
    pool = [Ranked(rank=r.rank, name=r.name, slug=r.slug,
                   facts=facts.get(r.oracle_id or "") or pairs.get(r.name.casefold()) or Facts(oracle_id=r.oracle_id),
                   num_decks=r.num_decks, salt=r.salt, trend=r.trend_zscore)
            for r in res.rows]
    base = len(pool)

    applied: list[str] = []
    if scope == "commanders" and color and not keys[0].filter.startswith("color:"):
        letters = _color_letters(color)
        pool = [x for x in pool if (x.facts.oracle_id or x.facts.partner) and set(x.facts.color_identity) == letters]
        applied.append("color")
    if scope == "commanders" and tag and not keys[0].filter.startswith("tag:"):
        tslug = edhrec.slugify(tag)
        listed = reads[-1].rows
        in_list = {r.slug for r in listed} | {r.oracle_id for r in listed if r.oracle_id}
        pool = [x for x in pool if x.slug in in_list or (x.facts.oracle_id and x.facts.oracle_id in in_list)
                or typal_match(tslug, x.facts.type_line)
                or (x.facts.partner is not None and typal_match(tslug, x.facts.partner.type_line))]
        applied.append("tag")

    ql = (q or "").strip().casefold()
    hits = [x for x in pool
            if (own == "all" or (own == "owned" and x.facts.owned > 0) or (own == "unused" and x.facts.free > 0))
            and (not ql or ql in x.name.casefold())]
    start = max(0, offset)
    page = hits[start:] if limit is None else hits[start:start + max(0, limit)]
    return Ranking(
        key=keys[0], title=title, cached=True,
        fetched_at=min((r.fetched_at for r in reads if r.fetched_at), default=None),
        rows=page, total=len(hits), base=base, pool=len(pool),
        owned=sum(1 for x in pool if x.facts.owned > 0),
        unused=sum(1 for x in pool if x.facts.free > 0),
        local_filters=applied,
    )


def ranking_options() -> dict:
    """Filter choices for the rankings controls: timeframes, every color
    identity, and the tags already fetched (for suggestions)."""
    with db.connect() as conn:
        tags = [r[0].removeprefix("tag:") for r in conn.execute(
            "SELECT DISTINCT filter FROM edhrec_rankings WHERE filter LIKE 'tag:%' ORDER BY filter")]
    return {"timeframes": list(edhrec.RANKING_TIMEFRAMES), "colors": edhrec.color_options(), "tags": tags}

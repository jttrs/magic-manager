"""Deck recipes: every playable precon and Jumpstart pack in the MTGJSON catalog,
merged with the decks you track, each marked by kind and by what you own.

Single source of truth behind the web Decks list (``api.decks`` recipes).

Kinds. ``precon`` = a catalog product in ``mtgjson.PRECON_MODERN_TYPES``;
``jumpstart`` = a DeckList ``type: Jumpstart`` entry (one pack version);
``import`` / ``custom`` = decks you imported from a builder or built by hand.
Card pools (``mtgjson.precon_kind`` == 'pool', run offline: product type and
name tests before a recipe is read, card-count tests after) are not recipes; a
catalog product you own only as a pool row stays out too.

Ownership. ``built`` (a copy kept assembled), ``loose`` (copies broken down,
cards in the free pool) or ``none``. Counts come from the ``decks`` table — the
same rows ``deck_view.deck_summaries`` groups.

Read. A catalog recipe you don't own is *read* once its MTGJSON deck file is in
the local cache and every card set it uses is synced; only then are its card
count, value, art and free-card coverage known. :func:`ensure_read` is the one
network step (run it as a job). Every other read here is local.

Coverage. Each recipe on its own against FREE copies (owned minus pledged,
finish-agnostic, :func:`inventory.free_quantities`) — two recipes sharing a card
both count the same free copy. ``status`` = build (nothing short) / close
(≤ ``CLOSE_SHORT``) / far.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable, Literal

from . import addcards, db, deck_view, decks, inventory, mtgjson, sets, util

# A recipe this many cards short of free copies (or fewer) is "close".
CLOSE_SHORT = 3

_BOARDS = (("commander", "commander"), ("mainBoard", "main"), ("sideBoard", "side"))
JUMPSTART_TYPE = "Jumpstart"

Kind = Literal["precon", "jumpstart", "import", "custom"]
Status = Literal["build", "close", "far"]


# ---------- recipe contents + coverage (shared with the jumpstart engine) ----------

@dataclass(frozen=True)
class Entry:
    scryfall_id: str
    count: int
    foil: bool
    name: str
    set_code: str
    board: str = "main"


def entries_from(data: dict) -> list[Entry]:
    """A deck file's gameplay cards in board order (commander → main → side)."""
    out: list[Entry] = []
    for key, board in _BOARDS:
        for e in data.get(key) or []:
            sid = (e.get("identifiers") or {}).get("scryfallId")
            if sid:
                out.append(Entry(sid, int(e.get("count", 1) or 1), bool(e.get("isFoil")),
                                 e.get("name") or "", (e.get("setCode") or "").lower(), board))
    return out


_ENTRIES: dict[str, tuple[float, list[Entry]]] = {}


def cached_entries(file_name: str) -> list[Entry] | None:
    """A recipe's cards from the MTGJSON disk cache (offline), ``None`` when its
    deck file isn't cached. Memoized per file mtime — only the small entry list
    is kept, never the parsed deck file."""
    mtime = mtgjson.cached_deck_mtime(file_name)
    if mtime is None:
        return None
    hit = _ENTRIES.get(file_name)
    if hit and hit[0] == mtime:
        return hit[1]
    data = mtgjson.cached_deck(file_name)
    if data is None:
        return None
    es = entries_from(data)
    _ENTRIES[file_name] = (mtime, es)
    return es


def counts_by_id(es: Iterable[Entry]) -> dict[str, int]:
    """Copies per scryfall_id, finishes merged (a foil copy builds the deck too)."""
    out: dict[str, int] = defaultdict(int)
    for e in es:
        out[e.scryfall_id] += e.count
    return dict(out)


def coverage(need: dict[str, int], free: dict[str, int]) -> tuple[int, int]:
    """``(have, short)``: copies of ``need`` your free cards cover, and the rest."""
    have = sum(min(n, free.get(sid, 0)) for sid, n in need.items())
    return have, sum(need.values()) - have


def status(short: int) -> Status:
    if short == 0:
        return "build"
    return "close" if short <= CLOSE_SHORT else "far"


# ---------- the catalog ----------

def kind_of(product_type: str | None) -> Kind:
    return "jumpstart" if product_type == JUMPSTART_TYPE else "precon"


def _is_pool(entry: dict, es: list[Entry] | None = None) -> bool:
    """``mtgjson.precon_kind`` — the one deck/pool classifier — run offline: the
    product-type and name tests always, the card-count tests once ``es`` is read."""
    return mtgjson.precon_kind(entry["fileName"], name=entry.get("name") or entry["fileName"],
                               product_type=entry.get("type"),
                               playable_cards=sum(e.count for e in es) if es is not None else None,
                               offline=True) == "pool"


def _decklist() -> dict[str, dict]:
    """The MTGJSON DeckList by fileName; ``{}`` when it can't be read, so your own
    decks still list without the catalog (as ``deck_view._precon_index``)."""
    try:
        return mtgjson._decklist_by_filename()
    except Exception:  # noqa: BLE001 — catalog is additive; never block your decks
        return {}


def catalog_entries() -> list[dict]:
    """DeckList entries that are playable recipes by their catalog facts alone."""
    types = mtgjson.PRECON_MODERN_TYPES | {JUMPSTART_TYPE}
    return [d for d in _decklist().values()
            if d.get("type") in types and not mtgjson._is_collector_edition(d.get("name") or "")
            and not _is_pool(d)]


def _legacy_pack_slugs(entries: list[dict]) -> dict[str, str]:
    """``pack:<theme>-<code>`` slug → fileName for Jumpstart versions (rows that
    predate ``source_precon_file_name``; the jumpstart engine's ownership rule)."""
    return {sets._slug_theme(e.get("name") or e["fileName"], e.get("code") or ""): e["fileName"]
            for e in entries if e.get("type") == JUMPSTART_TYPE and e.get("code")}


def _owned_file_names() -> dict[str, str]:
    """fileName → kind of every precon row you track (any kind, pools too)."""
    with db.connect() as conn:
        rows = conn.execute("SELECT source_precon_file_name AS fn, kind FROM decks "
                            "WHERE source_precon_file_name IS NOT NULL").fetchall()
    out: dict[str, str] = {}
    for r in rows:
        if out.get(r["fn"]) != "deck":
            out[r["fn"]] = r["kind"] or "deck"
    return out


def _deck_needs(slugs: list[str]) -> dict[str, dict[str, int]]:
    """slug → playable ``{scryfall_id: copies}`` of its current version."""
    if not slugs:
        return {}
    boards = ",".join(f"'{b}'" for b in decks.PLAYABLE_BOARDS)
    out: dict[str, dict[str, int]] = defaultdict(dict)
    with db.connect() as conn:
        for i in range(0, len(slugs), 500):
            part = slugs[i:i + 500]
            ph = ",".join("?" * len(part))
            for r in conn.execute(
                f"SELECT d.slug, dc.scryfall_id, SUM(dc.count) AS n FROM decks d "
                f"JOIN deck_cards dc ON dc.deck_version_id = d.current_version_id AND dc.board IN ({boards}) "
                f"WHERE d.slug IN ({ph}) GROUP BY d.slug, dc.scryfall_id", part):
                out[r["slug"]][r["scryfall_id"]] = int(r["n"])
    return dict(out)


def _card_facts(ids: Iterable[str]) -> dict[str, dict]:
    ids = list(dict.fromkeys(ids))
    out: dict[str, dict] = {}
    with db.connect() as conn:
        for i in range(0, len(ids), 500):
            part = ids[i:i + 500]
            ph = ",".join("?" * len(part))
            for r in conn.execute(
                f"SELECT scryfall_id, name, prices_usd, prices_usd_foil, image_uri, color_identity, "
                f"type_line, cmc FROM cards WHERE scryfall_id IN ({ph})", part):
                out[r["scryfall_id"]] = dict(r)
    return out


def _color(ids: Iterable[str], facts: dict[str, dict]) -> str | None:
    letters: set[str] = set()
    known = False
    for sid in ids:
        f = facts.get(sid)
        if f is None:
            continue
        known = True
        ci = f.get("color_identity")
        letters.update(json.loads(ci) if isinstance(ci, str) and ci else (ci or []))
    return util.format_color_identity(sorted(letters), collapse_multicolor=False) if known else None


def _rollup(es: list[Entry], facts: dict[str, dict]) -> dict:
    """Card count, value at shipped finish, and the art (commander, else priciest)."""
    value = 0.0
    best: tuple[int, float, str] | None = None
    for e in es:
        f = facts.get(e.scryfall_id) or {}
        unit = f.get("prices_usd_foil" if e.foil else "prices_usd")
        unit = float(unit) if unit is not None else (float(f["prices_usd"]) if f.get("prices_usd") is not None else 0.0)
        value += unit * e.count
        if f.get("image_uri"):
            rank = (e.board == "commander", unit)
            if best is None or rank > best[:2]:
                best = (rank[0], rank[1], f["image_uri"])
    return {"cards": sum(e.count for e in es), "value_usd": round(value, 2), "image_uri": best[2] if best else None}


def _fill_read(row: dict, es: list[Entry], facts: dict[str, dict], free: dict[str, int]) -> None:
    """A read recipe's card facts and free-card coverage onto its row."""
    row.update(_rollup(es, facts), read=True, color=_color((e.scryfall_id for e in es), facts))
    row["have"], row["short"] = coverage(counts_by_id(es), free)
    row["status"] = status(row["short"])


def _base(entry: dict, set_names: dict[str, dict]) -> dict:
    code = (entry.get("code") or "").lower() or None
    sset = set_names.get(code) if code else None
    return {
        "key": f"fn:{entry['fileName']}", "slug": None, "slugs": [], "file_name": entry["fileName"],
        "name": entry.get("name") or entry["fileName"], "kind": kind_of(entry.get("type")),
        "deck_type": deck_view.deck_type(None, entry.get("type")), "product_type": entry.get("type"),
        "source": entry.get("type"), "author": None, "set_code": code,
        "set_name": (sset or {}).get("name"),
        "released": entry.get("releaseDate") or (sset or {}).get("released_at"),
        "built": 0, "loose": 0, "ownership": "none", "pledged_pct": 0.0,
        "read": False, "cards": None, "value_usd": None, "image_uri": None, "color": None,
        "have": None, "short": None, "status": None,
    }


def _ownership(built: int, loose: int) -> str:
    return "built" if built else "loose" if loose else "none"


def catalog() -> list[dict]:
    """Every recipe: your decks (precon copies grouped, as ``deck_summaries``)
    plus every catalog precon / Jumpstart pack you don't own. Newest first."""
    entries = catalog_entries()
    by_fn = {e["fileName"]: e for e in entries}
    all_fns = _decklist()
    legacy = _legacy_pack_slugs(entries)
    owned_kind = _owned_file_names()
    set_names = deck_view._sets_index()

    out: list[dict] = []
    owned_slugs: dict[str, dict] = {}
    for d in deck_view.deck_summaries():
        fn = d.get("file_name") or legacy.get(d["slug"])
        entry = all_fns.get(fn) if fn else None
        kind: Kind = kind_of(entry.get("type")) if entry else ("precon" if d["origin"] == "precon" else d["origin"])
        row = {
            **d, "key": d["slug"], "file_name": fn, "kind": kind,
            "product_type": (entry or {}).get("type"),
            "ownership": _ownership(d["built"], d["loose"]), "read": True, "color": None,
            "have": None, "short": None, "status": None,
        }
        out.append(row)
        owned_slugs[d["slug"]] = row
        if fn:
            owned_kind.setdefault(fn, "deck")

    # Catalog recipes you don't own (pools you track as pools stay out entirely).
    unowned = [_base(e, set_names) for fn, e in by_fn.items() if fn not in owned_kind]
    contents: dict[str, list[Entry]] = {}
    for r in unowned:
        es = cached_entries(r["file_name"])
        if es is not None:
            contents[r["file_name"]] = es
    unsynced = set(sets.unsynced_set_codes({e.set_code for es in contents.values() for e in es if e.set_code}))

    needs = _deck_needs(list(owned_slugs))
    ids = {sid for n in needs.values() for sid in n} | {e.scryfall_id for es in contents.values() for e in es}
    facts = _card_facts(ids)
    free = inventory.free_quantities(list(ids))

    for slug, row in owned_slugs.items():
        need = needs.get(slug) or {}
        row["color"] = _color(need, facts)
        if need:
            row["have"], row["short"] = coverage(need, free)
            row["status"] = status(row["short"])

    for r in unowned:
        es = contents.get(r["file_name"])
        if es is not None and _is_pool(by_fn[r["file_name"]], es):
            continue
        if es is not None and not ({e.set_code for e in es if e.set_code} & unsynced):
            _fill_read(r, es, facts, free)
        out.append(r)

    out.sort(key=lambda d: d["name"])
    out.sort(key=lambda d: d["released"] or "", reverse=True)
    out.sort(key=lambda d: d["released"] is None)
    return out


# ---------- one catalog recipe ----------

def recipe(file_name: str) -> dict:
    """One catalog recipe's summary row + its cards (exact printings, free copies).

    ``ready`` is False until :func:`ensure_read` has run for it; ``unknown`` names
    cards whose printing isn't in the local catalog. Raises ``LookupError`` for a
    fileName that isn't a catalog recipe."""
    entry = mtgjson._decklist_by_filename().get(file_name)  # a failure surfaces (the route maps it)
    types = mtgjson.PRECON_MODERN_TYPES | {JUMPSTART_TYPE}
    if entry is None or entry.get("type") not in types:
        raise LookupError(f"no deck recipe {file_name!r}")
    row = _base(entry, deck_view._sets_index())
    built, loose = decks.precon_unit_counts().get(file_name, (0, 0))
    row.update(built=built, loose=loose, ownership=_ownership(built, loose))
    with db.connect() as conn:
        slugs = [r["slug"] for r in conn.execute(
            "SELECT slug FROM decks WHERE source_precon_file_name = ? ORDER BY precon_state = 'built' DESC, slug",
            (file_name,))]
    row.update(slugs=slugs, slug=slugs[0] if slugs else None)
    es = cached_entries(file_name)
    if es is None:
        return {"recipe": row, "ready": False, "cards": [], "unknown": []}
    ready = not sets.unsynced_set_codes({e.set_code for e in es if e.set_code})
    facts = _card_facts(e.scryfall_id for e in es)
    free = inventory.free_quantities([e.scryfall_id for e in es])
    printings = addcards.printings_for_ids(e.scryfall_id for e in es)
    if ready:
        _fill_read(row, es, facts, free)
    cards, unknown = [], []
    for e in es:
        p = printings.get(e.scryfall_id)
        if p is None:
            unknown.append(e.name)
            continue
        f = facts.get(e.scryfall_id) or {}
        ci = f.get("color_identity")
        cards.append({
            "printing": p, "board": e.board, "finish": "foil" if e.foil else "nonfoil", "count": e.count,
            "type_line": f.get("type_line"), "cmc": f.get("cmc"),
            "color_identity": json.loads(ci) if isinstance(ci, str) and ci else (ci or []),
            "pledged_here": 0, "free": free.get(e.scryfall_id, 0),
        })
    return {"recipe": row, "ready": ready, "cards": cards, "unknown": unknown}


# ---------- reading (the one network step) ----------

def file_names_for_set(code: str) -> list[str]:
    """Every catalog recipe (precon + Jumpstart) published in set ``code``."""
    code = code.lower()
    return sorted(e["fileName"] for e in catalog_entries() if (e.get("code") or "").lower() == code)


def ensure_read(file_names: list[str], *, progress: Callable[[int, int, str], None] | None = None,
                refresh_stale: bool = False, log: Callable[[str], None] | None = None) -> int:
    """Fetch each recipe's deck file, sync card sets with no local rows, and (for
    Jumpstart sets) the packs' front cards. Returns the number of recipes read.

    Raises ``RuntimeError`` naming card sets still unsynced afterwards
    (``sets.ensure_priced`` swallows sync errors; a read must not look
    successful when it isn't)."""
    from . import front_cards  # local: front_cards → sets cycle

    lookup = mtgjson._decklist_by_filename()
    tick = progress or (lambda *_: None)
    total = len(file_names) + 1
    set_codes: set[str] = set()
    jumpstart_codes: set[str] = set()
    for i, fn in enumerate(file_names):
        entry = lookup.get(fn) or {}
        tick(i, total, entry.get("name") or fn)
        set_codes.update(e.set_code for e in entries_from(mtgjson.deck(fn)) if e.set_code)
        if entry.get("type") == JUMPSTART_TYPE and entry.get("code"):
            jumpstart_codes.add(entry["code"].lower())
    tick(len(file_names), total, "Matching cards to your collection")
    sets.ensure_priced(set_codes, refresh_stale=refresh_stale, log=log)
    missing = sets.unsynced_set_codes(set_codes)
    if missing:
        raise RuntimeError(f"Couldn't sync prices for card set(s): {', '.join(c.upper() for c in missing)}. Check the connection and read again.")
    for code in sorted(jumpstart_codes):
        try:
            front_cards.sync_front_cards(code)
        except Exception:  # noqa: BLE001 — front cards only add value; never block
            pass
    return len(file_names)

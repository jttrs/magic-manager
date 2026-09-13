"""Secret Lair Drop discovery + live-Scryfall valuation (shared engine).

Secret Lair is a single Scryfall set (`sld`) with hundreds of cards; a "drop" is
one MTGJSON DeckList entry of ``type == "Secret Lair Drop"`` — NOT a
``sealedProduct`` (MTGJSON models SLD drops only as deck compositions). So SLD
can't ride the normal `sealed.build_product_tree` path (which resolves products
from ``sealedProduct``); it needs this dedicated engine.

SLD pricing is also DISTINCT from the rest of sealed-value: prices are fetched
**live from Scryfall** (no local `cards` sync needed), and the drop carries two
extra "floor" figures — the CHEAPEST printing of each card anywhere on Scryfall
(matched by oracle id), i.e. the cheapest way to get the cards into a deck
regardless of the Secret Lair treatment. This module is the single source of
truth for that logic; both `scripts/secret_lair_value.py` (recent-N table) and
`scripts/sealed_value.py` (value one named drop) consume it.

A logical drop merges a base printing with any ``… Foil Edition`` sibling
(MTGJSON lists foil-edition-only Secret Lairs as separate deck entries).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from . import mtgjson, scryfall, util


# ---------- price extraction (live Scryfall) ----------

def price(card: dict, key: str) -> float | None:
    """Extract a nested Scryfall price. ``card["prices"][key]`` is a string or
    None; coerce to float or None."""
    prices = card.get("prices") or {}
    v = prices.get(key)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def card_floors(oracle_id: str) -> tuple[float | None, float | None]:
    """Cheapest ``(usd, usd_foil)`` across every printing of a card.

    Enumerates all printings via ``oracleid:<id> unique=prints`` and returns the
    min non-null price in each finish (None if no printing has that finish
    priced) — the "cheapest to buy for a deck" figure, ignoring which set the
    cheapest copy lives in. For MANY cards prefer :func:`card_floors_many`, which
    batches the searches (one query per chunk instead of one per id)."""
    return card_floors_many([oracle_id]).get(oracle_id, (None, None))


# Scryfall caps boolean clauses per query (fails >~20 with HTTP 400); stay under.
_FLOOR_CHUNK = 20


def card_floors_many(oracle_ids: list[str]) -> dict[str, tuple[float | None, float | None]]:
    """Batched :func:`card_floors` — ``{oracle_id: (min_usd, min_usd_foil)}``.

    ORs many oracle_ids into one ``(oracleid:a or oracleid:b …) unique=prints``
    search per chunk (≤ ``_FLOOR_CHUNK`` ids), then groups the printings back by
    each card's ``oracle_id`` and takes the per-finish min. Collapses N per-card
    searches into ⌈N/60⌉ — the difference between a 400-card display taking one
    call vs. hundreds. Oracle_ids with no priced printing map to ``(None, None)``."""
    ids = [o for o in dict.fromkeys(oracle_ids) if o]
    out: dict[str, tuple[float | None, float | None]] = {o: (None, None) for o in ids}
    nf: dict[str, list[float]] = {o: [] for o in ids}
    ff: dict[str, list[float]] = {o: [] for o in ids}
    for i in range(0, len(ids), _FLOOR_CHUNK):
        chunk = ids[i:i + _FLOOR_CHUNK]
        q = "(" + " or ".join(f"oracleid:{o}" for o in chunk) + ")"
        for p in scryfall.search(q, unique="prints"):
            oid = p.get("oracle_id")
            if oid not in nf:
                continue
            v = price(p, "usd")
            if v is not None:
                nf[oid].append(v)
            v = price(p, "usd_foil")
            if v is not None:
                ff[oid].append(v)
    for o in ids:
        out[o] = (min(nf[o]) if nf[o] else None, min(ff[o]) if ff[o] else None)
    return out


# ---------- drop discovery / identity ----------

def strip_foil_edition(name: str) -> str:
    """Drop the ``" Foil Edition"`` suffix (for merging base+foil siblings in the
    DeckList, where the foil variant is named exactly ``… Foil Edition``)."""
    suffix = " Foil Edition"
    return name[: -len(suffix)] if name.endswith(suffix) else name


def normalize_name(s: str) -> str:
    """Canonical match key for Secret Lair names across data sources.

    Store titles, MTGJSON DeckList names, and MTGJSON sealedProduct names spell
    the same drop differently (``"Far Out, Man"`` vs ``"Far Out Man"``;
    ``"Dungeons & Dragons"`` vs ``"Dungeons and Dragons"``; ``"Marvel's Storm"``
    vs ``"Marvels Storm"``). Normalize by mapping ``&`` → ``and``, DELETING
    apostrophes (so a possessive ``'s`` stays one token: ``marvels``, not
    ``marvel s``), then collapsing every run of non-alphanumerics to one space,
    lowercased. The single source of matching truth for ``identify_drop`` and the
    sealed-market resolver."""
    s = (s or "").lower().replace("&", " and ").replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# Finish markers a sealedProduct name may carry (the DeckList uses only "Foil
# Edition", but sealedProduct names use "Rainbow Foil", bare "Foil", etc.).
# Stripped ONLY when matching a sealedProduct to a drop (not in group_drops).
_FINISH_MARKERS = (
    "rainbow foil edition", "rainbow foil", "traditional foil edition",
    "traditional foil", "foil edition", "non foil edition", "non foil", "foil",
)


def edition_from_name(name: str) -> str:
    """Infer a Secret Lair listing's finish from its (raw, un-normalized) name.

    Store / MTGJSON ``sealedProduct`` names carry the finish (``… Rainbow Foil``,
    ``… Traditional Foil``, ``… Non-Foil Edition``); the bare DeckList drop name
    does not. Returns ``"foil"`` unless the name is an explicit non-foil (default
    ``"nonfoil"`` for an unmarked drop name). The single source of finish-sniffing
    truth for the earmark resolver + review."""
    n = (name or "").lower()
    if "foil" in n and "non foil" not in n and "non-foil" not in n:
        return "foil"
    return "nonfoil"


def strip_finish_marker(normalized: str) -> str:
    """From an already-``normalize_name``d string, drop a trailing finish marker
    (rainbow/traditional/plain foil, non-foil) so a foil sealedProduct's core
    name matches its base drop. Also drops a leading ``secret lair x`` /
    ``secret lair drop`` / ``secret lair promo x`` scaffold the sealedProduct
    names carry but the drop names don't."""
    s = normalized
    for prefix in ("secret lair drop secret lair x ", "secret lair drop secret lair promo x ",
                   "secret lair drop ", "secret lair x ", "secret lair promo x "):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    for m in _FINISH_MARKERS:
        if s.endswith(" " + m):
            s = s[: -len(m) - 1]
            break
    return s.strip()


def group_drops(entries: list[dict]) -> dict[str, dict]:
    """Merge base + Foil-Edition siblings into one logical drop per key.

    Key is the stripped name. A BASE entry (no ``" Foil Edition"`` suffix) always
    wins as canonical for display name + release date, regardless of encounter
    order."""
    groups: dict[str, dict] = {}
    for e in entries:
        raw_name = e.get("name") or ""
        key = strip_foil_edition(raw_name)
        is_base = raw_name == key
        if key not in groups:
            groups[key] = {
                "name": raw_name,
                "release_date": e.get("releaseDate"),
                "file_names": [e.get("fileName")],
            }
            continue
        groups[key]["file_names"].append(e.get("fileName"))
        if is_base:
            groups[key]["name"] = raw_name
            groups[key]["release_date"] = e.get("releaseDate")
    return groups


def all_drops() -> dict[str, dict]:
    """Every SLD drop, keyed by stripped name (base+foil merged). Raises
    ``mtgjson.MtgJsonError`` on lookup failure."""
    entries = [
        e for e in mtgjson.deck_list(set_code="SLD")
        if e.get("type") == "Secret Lair Drop"
    ]
    return group_drops(entries)


def recent_drops(n: int) -> tuple[list[dict], int]:
    """The ``n`` most recent drops (release desc, name asc tie-break) + the total
    count. Returns ``(chosen, total)``."""
    groups = all_drops()
    chosen = sorted(groups.values(), key=lambda g: g["name"])
    chosen.sort(key=lambda g: g["release_date"], reverse=True)
    return chosen[:n], len(groups)


def identify_drop(name_substr: str) -> dict:
    """Resolve a SLD drop by name (exact→unique-substring), mirroring
    ``sealed.identify_product``'s contract.

    Matching is PUNCTUATION-INSENSITIVE (store titles drop the comma in "Far Out,
    Man"): exact match on the normalized canonical name wins; else a unique
    normalized-substring match. When several names contain the query (e.g. the
    query "… Beholder I" is a substring of "… Beholder II"), a candidate whose
    name ENDS WITH the query — a suffix match, meaning the query is the full
    trailing title — wins if unique. Raises ``LookupError`` (with candidates) on
    no match or genuine ambiguity."""
    groups = all_drops()
    want = normalize_name(name_substr)
    exact = [g for g in groups.values() if normalize_name(g.get("name")) == want]
    if exact:
        return exact[0]
    subs = [g for g in groups.values() if want in normalize_name(g.get("name"))]
    if len(subs) == 1:
        return subs[0]
    # Disambiguate "X I" vs "X II": prefer a candidate ending exactly with the
    # query (so "… Beholder I" doesn't ambiguously match "… Beholder II").
    if len(subs) > 1:
        suffix = [g for g in subs if normalize_name(g.get("name")).endswith(want)]
        if len(suffix) == 1:
            return suffix[0]
    if not subs:
        raise LookupError(
            f"no Secret Lair drop matching {name_substr!r}. "
            f"({len(groups)} drops known; try a more distinctive substring.)"
        )
    names = ", ".join(sorted(g.get("name", "?") for g in subs)[:12])
    raise LookupError(
        f"{len(subs)} Secret Lair drops match {name_substr!r}; be more specific: {names}"
    )


def collect_drop_ids(file_names: list[str]) -> list[str]:
    """De-duplicated union of Scryfall IDs across a drop's sibling decks,
    preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for fn in file_names:
        deck = mtgjson.deck(fn)
        for sid in mtgjson.deck_card_scryfall_ids(deck):
            if sid not in seen:
                seen.add(sid)
                out.append(sid)
    return out


# ---------- formatting helpers (shared with the table renderers) ----------

def search_url(collector_numbers: list[str]) -> str:
    """A Scryfall search URL for a drop's exact collector numbers in ``sld``."""
    cns = sorted(
        {cn.strip().rstrip("★").strip() for cn in collector_numbers},
        key=util.cn_sort_key,
    )
    if not cns:
        return "https://scryfall.com/search?q=" + quote_plus("set:sld")
    terms = "set:sld (" + " or ".join(f"cn:{cn}" for cn in cns) + ")"
    return "https://scryfall.com/search?q=" + quote_plus(terms)


def cell(total: float, priced_ct: int, card_ct: int) -> str:
    """Render a price cell: ``$X.XX``, ``$X.XX (n)`` for partial coverage, or ``—``."""
    if priced_ct == 0:
        return "—"
    s = util.fmt_usd(total)
    return s if priced_ct == card_ct else f"{s} ({priced_ct})"


# ---------- valuation ----------

@dataclass
class DropValue:
    """The priced result of one Secret Lair drop."""
    name: str
    release_date: str | None
    card_count: int
    collector_numbers: list[str]
    nonfoil_total: float
    nonfoil_ct: int
    foil_total: float
    foil_ct: int
    nf_floor_total: float
    nf_floor_ct: int
    foil_floor_total: float
    foil_floor_ct: int
    search_url: str = ""
    ids: list[str] = field(default_factory=list)


def value_drop(drop: dict, *, floors: bool = True,
               _card_by_id: dict | None = None,
               _floors_cache: dict | None = None) -> DropValue:
    """Value one logical drop with live Scryfall prices (+ optional floors).

    Resolves the drop's cards (``collect_drop_ids`` → ``scryfall.collection``),
    sums the drop's own Secret Lair printings (nonfoil/foil), and — when
    ``floors`` — sums the cheapest printing of each card anywhere on Scryfall.

    ``_card_by_id`` / ``_floors_cache`` let a batch caller (e.g. the recent-N
    table) share one Scryfall fetch + per-oracle floor cache across many drops;
    when omitted, this fetches just this drop's cards. Raises
    ``mtgjson.MtgJsonError`` / ``scryfall.ScryfallError`` on lookup failure."""
    ids = drop.get("ids") or collect_drop_ids(drop["file_names"])

    if _card_by_id is None:
        found, _nf = scryfall.collection([{"id": i} for i in ids])
        _card_by_id = {c["id"]: c for c in found}
    if _floors_cache is None:
        _floors_cache = {}

    # Pre-warm ALL this drop's floors in ONE batched pass (chunked OR-search),
    # not one Scryfall call per card. Only the oracle_ids not already cached from
    # an earlier drop are fetched; the shared _floors_cache dedups across drops.
    if floors:
        need_oids = [
            oid for sid in ids
            if (card := _card_by_id.get(sid)) is not None
            and (oid := card.get("oracle_id")) and oid not in _floors_cache
        ]
        if need_oids:
            # A Scryfall failure degrades this drop's floor to unpriced — never
            # aborts a multi-drop batch mid-run.
            try:
                _floors_cache.update(card_floors_many(need_oids))
            except scryfall.ScryfallError:
                _floors_cache.update({o: (None, None) for o in need_oids})

    nf_total = foil_total = nf_floor_total = foil_floor_total = 0.0
    nf_ct = foil_ct = nf_floor_ct = foil_floor_ct = 0
    cns: list[str] = []
    for sid in ids:
        card = _card_by_id.get(sid)
        if card is None:
            continue
        cns.append(card.get("collector_number") or "")
        nf = price(card, "usd")
        if nf is not None:
            nf_total += nf
            nf_ct += 1
        ff = price(card, "usd_foil")
        if ff is not None:
            foil_total += ff
            foil_ct += 1
        if floors:
            oid = card.get("oracle_id")
            nf_floor, foil_floor = _floors_cache.get(oid, (None, None))
            if nf_floor is not None:
                nf_floor_total += nf_floor
                nf_floor_ct += 1
            if foil_floor is not None:
                foil_floor_total += foil_floor
                foil_floor_ct += 1

    return DropValue(
        name=drop["name"], release_date=drop.get("release_date"),
        card_count=len(ids), collector_numbers=cns,
        nonfoil_total=nf_total, nonfoil_ct=nf_ct,
        foil_total=foil_total, foil_ct=foil_ct,
        nf_floor_total=nf_floor_total, nf_floor_ct=nf_floor_ct,
        foil_floor_total=foil_floor_total, foil_floor_ct=foil_floor_ct,
        search_url=search_url(cns), ids=ids,
    )

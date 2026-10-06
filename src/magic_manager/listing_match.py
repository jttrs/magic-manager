"""Match a store listing (its title) to what it sells — deterministically.

A listing is one of:

* ``other_game`` — not Magic (Pokémon, One Piece, Riftbound, …);
* ``single``     — a card printing, TCGplayer-style ``Name (extras) (CN) (Set)``;
* ``sld``        — a Secret Lair drop (``Secret Lair Drop Series: <drop> | <finish>``);
* ``sealed``     — a sealed product in MTGJSON's ``sealedProduct`` catalog.

Sealed matching: find the LONGEST set name in the title (so *Secrets of
Strixhaven* beats *Strixhaven*, *Final Fantasy Commander* beats *Final Fantasy*),
expand to its set family (``fin`` ⇄ ``fic``), then score every product of the
family by token overlap. Title words no product in the family uses (store noise:
"presale", "expected release date", "MTG") are ignored, and synonyms are folded
("Display" = "Box", "Decks" = "Deck", "Collector's" = "Collector"). A clear winner
is ``matched``; close calls are ``ambiguous`` with candidates for you to confirm;
nothing close is ``unmatched`` (e.g. too new for MTGJSON). Commander decks whose
title lacks the set name fall back to MTGJSON's deck list.

Singles: the set + collector number identify the printing, but store metadata
can be wrong (docs/deals-scraping.md #9), so the card NAME must agree — else the
printings of that name are offered as candidates, never silently picked.
"""
from __future__ import annotations

import html as htmllib
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from . import db, mtgjson, scryfall, sets as sets_mod, sld

Kind = Literal["sealed", "sld", "single", "other_game", "unknown"]
Status = Literal["matched", "ambiguous", "unmatched", "skipped"]

_STOP = {"magic", "the", "gathering", "mtg", "tcg", "of", "and", "a", "an", "universes", "beyond", "edition"}
_SYN = {"display": "box", "decks": "deck", "boxes": "box", "boosters": "booster", "collectors": "collector",
        "packs": "pack", "bundles": "bundle", "kits": "kit"}
_OTHER_GAMES = re.compile(r"pok[eé]mon|one piece|riftbound|grand archive|lorcana|yu-?gi-?oh|flesh and blood|"
                          r"star wars unlimited|digimon|dragon ball|weiss schwarz|sorcery|altered tcg|union arena|gundam", re.I)
_SET_TYPES = {"core", "expansion", "masters", "draft_innovation", "commander", "starter", "box", "funny", "duel_deck",
              "planechase", "archenemy", "from_the_vault", "premium_deck", "spellbook", "arsenal"}
_CN = re.compile(r"^\d+[a-z]?$|^[a-z0-9]{2,5}-\d+[a-z]?$", re.I)
_SET_CN = re.compile(r"^([a-z0-9]{2,5})-(\d+[a-z]?)$", re.I)
_SET_ALIASES = {"secret lair drop series": "sld", "secret lair drop": "sld", "secret lair": "sld"}


@dataclass
class Candidate:
    set_code: str
    name: str
    score: float
    scryfall_id: str | None = None      # singles
    finish: str | None = None           # singles / sld edition
    price: float | None = None          # singles: market at that finish


@dataclass
class Match:
    kind: Kind
    status: Status
    match: Candidate | None = None
    candidates: list[Candidate] = field(default_factory=list)
    note: str = ""


def norm_tokens(s: str) -> list[str]:
    s = htmllib.unescape(s or "").lower().replace("&", " and ").replace("’", "").replace("'", "")
    s = s.replace("pokémon", "pokemon")
    s = re.sub(r"\bpre[\s-]+release\b", "prerelease", s)
    toks = [_SYN.get(t, t) for t in re.findall(r"[a-z0-9]+", s)]
    return [t for t in toks if t not in _STOP]


def _contains(hay: list[str], needle: list[str]) -> bool:
    n = len(needle)
    return n > 0 and any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


@lru_cache(maxsize=1)
def _set_names() -> tuple[tuple[tuple[str, ...], str], ...]:
    """(normalized name tokens, code) for physical sets, longest names first."""
    out = []
    for s in scryfall.all_sets():
        if s.get("digital") or s.get("set_type") not in _SET_TYPES:
            continue
        toks = tuple(norm_tokens(s.get("name", "")))
        if toks:
            out.append((toks, s["code"].lower()))
    return tuple(sorted(out, key=lambda x: -len(x[0])))


@lru_cache(maxsize=1)
def _set_tails() -> tuple[tuple[tuple[str, ...], str], ...]:
    """Set names without their first word ("Marvel's Spider-Man" → "Spider-Man"),
    2+ words only — stores often drop a possessive or franchise prefix."""
    out = [(toks[1:], code) for toks, code in _set_names() if len(toks) >= 3]
    return tuple(sorted(out, key=lambda x: -len(x[0])))


def detect_set(title: str) -> str | None:
    """The code of the longest set name in the title (full names first, then
    names without their leading word)."""
    toks = norm_tokens(title)
    for names in (_set_names(), _set_tails()):
        for name, code in names:
            if _contains(toks, list(name)):
                return code
    return None


def _family(code: str) -> list[str]:
    try:
        return sorted({c.lower() for c in sets_mod.resolve(code).all_codes})
    except LookupError:
        return [code]


def classify(title: str) -> Kind:
    t = title or ""
    if _OTHER_GAMES.search(t):
        return "other_game"
    if re.search(r"custom[\s-]+built|\bproxy\b|\bproxies\b|\bmystery\b|\brepack\b|uncut sheet|\bgraded\b|beckett|\bpsa \d|\bcgc\b|"
                 r"\bsupplies\b|sleeves|playmat|deck box|binder|\bpins?\b|pin set|token bundle|acrylic", t, re.I):
        return "unknown"
    groups = re.findall(r"\(([^()]*)\)", t)
    if any(_CN.match(g.strip()) for g in groups):
        return "single"
    if re.search(r"secret lair", t, re.I) and not re.search(r"commander deck|countdown kit|bundle", t, re.I):
        return "sld"
    return "sealed"


# ---------- sealed ----------

def _score_products(title: str, codes: list[str]) -> list[Candidate]:
    products = []
    for c in codes:
        try:
            products += [(c, p) for p in mtgjson.sealed_products(c)]
        except Exception:  # noqa: BLE001 — a family member without an MTGJSON file has no products
            continue
    if not products:
        return []
    vocab = {t for _, p in products for t in norm_tokens(p.get("name", ""))}
    title_toks = set(norm_tokens(title)) & vocab
    out = []
    for c, p in products:
        pt = set(norm_tokens(p.get("name", "")))
        if not pt:
            continue
        union = title_toks | pt
        out.append(Candidate(set_code=c, name=p["name"], score=len(title_toks & pt) / len(union) if union else 0.0))
    return sorted(out, key=lambda x: (-x.score, len(x.name)))


def _by_finish(title: str, scored: list[Candidate]) -> Candidate | None:
    """Foil / non-foil twins (Secret Lair products): the title's finish decides."""
    if len(scored) < 2 or scored[0].score < 0.6:
        return None
    base = lambda n: " ".join(t for t in norm_tokens(n) if t not in ("foil", "rainbow", "traditional", "non", "nonfoil"))  # noqa: E731
    twins = [c for c in scored[:4] if base(c.name) == base(scored[0].name)]
    if len(twins) < 2:
        return None
    want_foil = sld.edition_from_name(title) == "foil"
    pick = [c for c in twins if ("foil" in norm_tokens(c.name)) == want_foil]
    return pick[0] if len(pick) == 1 else None


def _deck_fallback_codes(title: str) -> list[str]:
    """Commander decks whose title lacks the set name: find an MTGJSON deck name in it."""
    toks = norm_tokens(title)
    best: tuple[int, str] | None = None
    for d in mtgjson.deck_list():
        dt = norm_tokens(d.get("name", ""))
        if len(dt) >= 2 and _contains(toks, dt) and (best is None or len(dt) > best[0]):
            best = (len(dt), (d.get("code") or "").lower())
    return _family(best[1]) if best and best[1] else []


MATCH_AT = 0.75
MARGIN = 0.08


_LANG = re.compile(r"\b(japanese|jp|jpn|korean|chinese|s-chinese|t-chinese|german|french|italian|spanish|portuguese|russian)\b", re.I)


def match_sealed(title: str) -> Match:
    lang = _LANG.search(title)
    m = _match_sealed(title)
    if lang and m.status == "matched":
        return Match("sealed", "ambiguous", None, m.candidates,
                     note=f"A {lang.group(1).title()}-language product — MTGJSON prices the English one. Confirm if you want it compared anyway.")
    return m


def _match_sealed(title: str) -> Match:
    code = detect_set(title)
    scored = _score_products(title, _family(code)) if code else []
    if not scored or scored[0].score < MATCH_AT:
        alt = _deck_fallback_codes(title)
        if alt:
            alt_scored = _score_products(title, alt)
            if alt_scored and (not scored or alt_scored[0].score > scored[0].score):
                scored = alt_scored
    if not scored:
        return Match("sealed", "unmatched", note="No set named in the title has sealed products in MTGJSON yet.")
    top = scored[0]
    if top.score >= MATCH_AT and (len(scored) == 1 or top.score - scored[1].score >= MARGIN or top.score == 1.0):
        return Match("sealed", "matched", top, scored[:3])
    pick = _by_finish(title, scored)
    if pick:
        return Match("sealed", "matched", pick, scored[:3])
    if top.score >= 0.5:
        return Match("sealed", "ambiguous", None, scored[:3], note="Several products fit — pick the right one.")
    return Match("sealed", "unmatched", None, scored[:3], note="No product in that set fits the title closely.")


# ---------- Secret Lair ----------

def match_sld(title: str) -> Match:
    edition = sld.edition_from_name(title)
    core = re.sub(r"(?i)^.*?secret lair(?: drop series| drop| artist series)?\s*[:|-]\s*", "", title)
    core = re.split(r"\s*\|\s*", core)[0]
    try:
        drop = sld.identify_drop(sld.strip_finish_marker(sld.normalize_name(core)))
    except LookupError as e:
        return Match("sld", "unmatched", note=str(e))
    return Match("sld", "matched", Candidate("sld", drop["name"], 1.0, finish=edition))


# ---------- singles ----------

def _front(name: str) -> str:
    return " ".join(norm_tokens((name or "").split(" // ")[0]))


def _single_parts(title: str) -> tuple[str, str | None, str | None, str]:
    """(card name, collector number, set name, finish) from a TCGplayer-style title."""
    name = re.split(r"\s+[(\[]", title, maxsplit=1)[0].strip(" -|")
    groups = [g.strip() for g in re.findall(r"\(([^()]*)\)", title)]
    cn = next((g for g in reversed(groups) if _CN.match(g)), None)
    rest = [g for g in groups if not _CN.match(g)]
    set_name = rest[-1] if rest else None
    sc = _SET_CN.match(cn or "")
    if sc:                                   # "(SLD-2296)": the set code rides with the number
        set_name, cn = sc.group(1), sc.group(2)
    elif set_name is None:                   # "Name (609) - Secret Lair Drop Series"
        tail = re.split(r"\)\s*-\s*", title)
        set_name = tail[-1].strip() if len(tail) > 1 else None
    if cn and cn[0] == "0" and cn.isdigit():
        cn = cn.lstrip("0") or "0"
    low = title.lower()
    finish = "foil" if (("foil" in low and "non-foil" not in low and "nonfoil" not in low) or "etched" in low) else "nonfoil"
    return name, cn, set_name, finish


def _set_code_for(set_name: str | None) -> str | None:
    if not set_name:
        return None
    if re.fullmatch(r"[A-Za-z0-9]{2,5}", set_name) and any(code == set_name.lower() for _, code in _set_names()):
        return set_name.lower()
    key = " ".join(norm_tokens(set_name))
    for alias, code in _SET_ALIASES.items():
        if key == " ".join(norm_tokens(alias)):
            return code
    for toks, code in _set_names():
        if " ".join(toks) == key:
            return code
    return detect_set(set_name)


def _price(row: dict, finish: str) -> float | None:
    v = row.get("prices_usd_foil" if finish == "foil" else "prices_usd")
    return float(v) if v not in (None, "") else None


def _rank(cands: list[Candidate], title: str, price: float | None) -> list[Candidate]:
    """Printings the title hints at first (a set code in its extras, e.g. "(FDN Bundle)"),
    then the closest price to the listing — same-name printings differ wildly."""
    hints = {t.lower() for g in re.findall(r"\(([^()]*)\)", title) for t in re.findall(r"[A-Za-z0-9]{3,5}", g)}

    def key(c: Candidate):
        hinted = c.set_code.lower() in hints or c.set_code.lower().lstrip("p") in hints
        gap = abs((c.price or 0) - price) if price is not None and c.price is not None else float("inf")
        return (not hinted, gap)
    return sorted(cands, key=key)


def match_single(title: str, price: float | None = None) -> Match:
    name, cn, set_name, finish = _single_parts(title)
    code = _set_code_for(set_name)
    want = _front(name)
    with db.connect() as conn:
        row = conn.execute("SELECT scryfall_id, name, flavor_name, set_code, collector_number, prices_usd, prices_usd_foil FROM cards "
                           "WHERE set_code = ? AND collector_number = ?", (code, cn)).fetchone() if code and cn else None
        row = dict(row) if row else None
        if (row is None or want not in {_front(row["name"]), _front(row.get("flavor_name") or "")}) and code and cn:
            # Not local, or the name disagrees: ask Scryfall, which also knows each
            # face's flavor name (Universes Beyond: "Hawkins National Laboratory" is
            # SLD 609 Havengul Laboratory).
            found, _ = scryfall.collection([{"set": code, "collector_number": cn}])
            if found:
                c = found[0]
                names = {_front(c.get("name", "")), _front(c.get("flavor_name") or "")} | {
                    _front(f.get(k) or "") for f in c.get("card_faces") or [] for k in ("name", "flavor_name")}
                prices = c.get("prices") or {}
                row = {"scryfall_id": c["id"], "name": c["name"], "set_code": c["set"], "collector_number": c["collector_number"],
                       "prices_usd": prices.get("usd"), "prices_usd_foil": prices.get("usd_foil"), "_names": names}
        if row and want in (row.get("_names") or {_front(row["name"]), _front(row.get("flavor_name") or "")}):
            return Match("single", "matched", Candidate(row["set_code"], row["name"], 1.0, row["scryfall_id"], finish, _price(row, finish)))
        same_name = [dict(r) for r in conn.execute(
            "SELECT scryfall_id, name, set_code, collector_number, prices_usd, prices_usd_foil FROM cards WHERE lower(name) = lower(?) "
            "OR lower(name) LIKE lower(?) OR lower(flavor_name) = lower(?) LIMIT 40", (name, name + " // %", name))]
    cands = _rank([Candidate(r["set_code"], f"{r['name']} ({r['set_code'].upper()} {r['collector_number']})", 0.5, r["scryfall_id"], finish, _price(r, finish))
                   for r in same_name], title, price)
    if not cands and row:
        # No card carries the store's name (e.g. an unlisted crossover name): offer
        # the printing its set + number point at, for you to confirm.
        cands = [Candidate(row["set_code"], f"{row['name']} ({row['set_code'].upper()} {row['collector_number']})", 0.5,
                           row["scryfall_id"], finish, _price(row, finish))]
    note = (f"The store says {set_name or '?'} #{cn or '?'}, but that printing is "
            f"{row['name'] if row else 'not found'} — pick the right printing of {name}.")
    return Match("single", "ambiguous" if cands else "unmatched", None, cands[:8], note=note)


# ---------- entry point ----------

def match(title: str, price: float | None = None) -> Match:
    """What ``title`` sells; ``price`` (the listing's) ranks candidate printings."""
    kind = classify(title)
    if kind == "other_game":
        return Match("other_game", "skipped", note="Not a Magic product.")
    if kind == "unknown":
        return Match("unknown", "skipped", note="Not something we value (custom, graded, uncut, supplies or mystery).")
    if kind == "single":
        return match_single(title, price)
    if kind == "sld":
        m = match_sld(title)
        return m if m.status == "matched" else match_sealed(title)
    return match_sealed(title)

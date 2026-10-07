"""Jumpstart engine: pack versions, what you can build from free cards, and the
two shopping lists (cards to make every theme buildable · whole packs you
don't own).

Single source of truth behind ``scripts/jumpstart_buildable.py``,
``scripts/jumpstart_reference.py``, ``mm query missing-jumpstart`` and the web
Collection → Jumpstart sheet (``api.jumpstart``).

Vocabulary. A *variant* (version) is one MTGJSON ``type: Jumpstart`` DeckList
entry (``Angels (1)``); its *theme* is the name minus a trailing version
suffix (``Angels``). Contents come from the per-deck MTGJSON file
(commander/main/side boards); every read here is LOCAL (the deck files'
on-disk cache + the local ``cards`` table). :func:`ensure_ready` is the one
network step (deck files, missing card sets, front cards) — run it as a job.

Free vs owned. *Buildable now* compares each pack to FREE copies (owned minus
pledged to built decks, finish-agnostic, :func:`inventory.free_quantities`),
each pack on its own — two packs sharing a card both count the same free
copy. The *buildable set* target counts OWNED copies including pledged ones
(you can break a built pack down to reuse them), as the CLI always has.
"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Iterable, Literal

from . import (
    db, decks, exports, front_cards, inventory, missing as missing_mod, mtgjson,
    ownership, selectors, sets, util,
)

# A pack this many cards short of free copies (or fewer) is "close".
CLOSE_SHORT = 3

_BOARDS = ("commander", "mainBoard", "sideBoard")

# A version suffix is a trailing integer, with or without parentheses:
#   'Angels (1)' → 'Angels' (J25/MSH naming), 'Corruption 1' → 'Corruption' (ONE).
# Anchored at `$`, so only a TRAILING version token is ever stripped.
_VERSION_SUFFIX = re.compile(r"\s*\(?(\d+)\)?\s*$")

# Colour-code sort: mono/colorless C<W<U<B<R<G, then every multicolour code as
# one trailing block ordered by its letter sequence.
_MONO_RANK = {"C": 0, "W": 1, "U": 2, "B": 3, "R": 4, "G": 5}

Shop = Literal["buildable", "packs"]


def theme_of(variant_name: str) -> str:
    """'Angels (1)' → 'Angels', 'Corruption 1' → 'Corruption'."""
    return _VERSION_SUFFIX.sub("", variant_name or "").strip()


def version_of(variant_name: str) -> int | None:
    """'Angels (1)' → 1; a single-version theme ('Aang') → None."""
    m = _VERSION_SUFFIX.search(variant_name or "")
    return int(m.group(1)) if m else None


def color_sort_key(code: str) -> tuple[int, str]:
    if code in _MONO_RANK:
        return (_MONO_RANK[code], "")
    return (6, code)


def build_target(variants_boards: dict[str, dict[str, int]]) -> dict[str, int]:
    """Pure "buildable set" target: Σ_themes max_versions(count) per scryfall_id.

    ``variants_boards`` maps a variant NAME to its ``{scryfall_id: count}``.
    Within a theme the MAX across versions (so any one version is buildable,
    reusing shared cards); across themes the SUM (all themes built at once).
    """
    by_theme: dict[str, list[dict[str, int]]] = defaultdict(list)
    for name, counts in variants_boards.items():
        by_theme[theme_of(name)].append(counts)
    target: dict[str, int] = defaultdict(int)
    for versions in by_theme.values():
        theme_max: dict[str, int] = defaultdict(int)
        for vc in versions:
            for sid, n in vc.items():
                theme_max[sid] = max(theme_max[sid], n)
        for sid, n in theme_max.items():
            target[sid] += n
    return dict(target)


def jumpstart_set_codes() -> list[str]:
    """Every set code publishing ``type: Jumpstart`` decks (lowercase, sorted)."""
    return sorted({
        (d.get("code") or "").lower()
        for d in mtgjson.deck_list()
        if d.get("type") == "Jumpstart" and d.get("code")
    })


def variants(code: str) -> list[dict]:
    """The set's Jumpstart DeckList entries, sorted by name."""
    return sorted(mtgjson.jumpstart_variants(code.lower()),
                  key=lambda v: v.get("name") or v.get("fileName") or "")


@dataclass(frozen=True)
class Entry:
    scryfall_id: str
    count: int
    foil: bool
    name: str
    set_code: str


def entries(file_name: str) -> list[Entry]:
    """One pack's gameplay cards in board order (commander → main → side)."""
    data = mtgjson.deck(file_name)
    out: list[Entry] = []
    for board in _BOARDS:
        for e in data.get(board) or []:
            sid = (e.get("identifiers") or {}).get("scryfallId")
            if sid:
                out.append(Entry(sid, int(e.get("count", 1) or 1), bool(e.get("isFoil")),
                                 e.get("name") or "", (e.get("setCode") or "").lower()))
    return out


def counts_by_id(es: Iterable[Entry]) -> dict[str, int]:
    """Copies per scryfall_id, finishes merged (a foil copy builds a pack too)."""
    out: dict[str, int] = defaultdict(int)
    for e in es:
        out[e.scryfall_id] += e.count
    return dict(out)


# ---------- readiness (the one network step) ----------

def _cache_dir() -> Path:
    return Path(os.environ.get("MTGJSON_CACHE_DIR") or Path(os.environ.get("TMPDIR") or "/tmp") / "mtgjson-cache")


def deck_cached(file_name: str) -> bool:
    """True when the MTGJSON deck file is already in the wrapper's disk cache."""
    return (_cache_dir() / "decks" / f"{file_name.removesuffix('.json')}.json").exists()


def is_ready(code: str) -> bool:
    """Every deck file cached and every card set they reference synced locally."""
    vs = variants(code)
    if not vs or not all(deck_cached(v["fileName"]) for v in vs):
        return False
    codes = {e.set_code for v in vs for e in entries(v["fileName"]) if e.set_code}
    return not sets.unsynced_set_codes(codes)


def ensure_ready(code: str, *, progress: Callable[[int, int, str], None] | None = None,
                 refresh_stale: bool = False, log: Callable[[str], None] | None = None) -> int:
    """Fetch every pack's deck file, sync card sets with no local rows, and pull
    the set's front cards (best-effort). Returns the number of packs.

    Price freshness is local-first (CLAUDE.md § Price freshness): stale sets are
    warned about through ``log`` and re-synced only with ``refresh_stale``.
    Raises ``RuntimeError`` naming any card set still unsynced afterwards —
    ``sets.ensure_priced`` swallows sync errors, and a read that leaves the set
    not ready must fail rather than look successful."""
    code = code.lower()
    vs = variants(code)
    tick = progress or (lambda *_: None)
    set_codes: set[str] = set()
    for i, v in enumerate(vs):
        tick(i, len(vs) + 1, v.get("name") or v["fileName"])
        set_codes.update(e.set_code for e in entries(v["fileName"]) if e.set_code)
    tick(len(vs), len(vs) + 1, "Matching cards to your collection")
    sets.ensure_priced(set_codes, refresh_stale=refresh_stale, log=log)
    missing = sets.unsynced_set_codes(set_codes)
    if missing:
        raise RuntimeError(f"Couldn't sync prices for card set(s): {', '.join(c.upper() for c in missing)}. Check the connection and read again.")
    try:
        front_cards.sync_front_cards(code)
    except Exception:  # noqa: BLE001 — front cards only add value; never block
        pass
    return len(vs)


# ---------- the set view ----------

@dataclass
class PackCard:
    scryfall_id: str
    name: str
    count: int
    foil: bool
    unit_usd: float | None
    rarity: str | None
    collector_number: str | None
    set_code: str
    color: str
    free: int
    known: bool = True  # False: printing not in the local cards table


@dataclass
class Pack:
    file_name: str
    name: str
    theme: str
    version: int | None
    color: str
    card_count: int
    usd_total: float | None
    top_card: str | None
    top_card_usd: float | None
    front_card: str | None
    built: int
    deconstructed: int
    deck_slug: str | None = None
    top_card_id: str | None = None
    have: int = 0
    short: int = 0
    cards: list[PackCard] = field(default_factory=list)

    @property
    def status(self) -> Literal["build", "close", "far"]:
        if self.short == 0:
            return "build"
        return "close" if self.short <= CLOSE_SHORT else "far"

    @property
    def owned(self) -> bool:
        return self.built + self.deconstructed > 0


def _card_rows(ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    out: dict[str, dict] = {}
    with db.connect() as conn:
        for i in range(0, len(ids), 500):
            part = ids[i:i + 500]
            ph = ",".join("?" * len(part))
            for r in conn.execute(
                f"SELECT scryfall_id, name, set_code, collector_number, rarity, prices_usd, "
                f"prices_usd_foil, color_identity FROM cards WHERE scryfall_id IN ({ph})", part,
            ):
                out[r["scryfall_id"]] = dict(r)
    return out


def _deck_slugs(file_names: list[str]) -> dict[str, str]:
    """A deck row per pack version you own (a built copy first)."""
    if not file_names:
        return {}
    ph = ",".join("?" * len(file_names))
    with db.connect() as conn:
        rows = conn.execute(
            f"SELECT source_precon_file_name AS fn, slug FROM decks WHERE source_precon_file_name IN ({ph}) "
            f"ORDER BY precon_state = 'built' DESC, slug", file_names).fetchall()
    out: dict[str, str] = {}
    for r in rows:
        out.setdefault(r["fn"], r["slug"])
    return out


def _owned_slugs(code: str) -> set[str]:
    with db.connect() as conn:
        return {r["slug"] for r in conn.execute("SELECT slug FROM decks WHERE slug LIKE ?", (f"pack:%-{code}",))}


def owned_file_names(code: str) -> set[str]:
    """fileNames of the set's pack versions you own at least one copy of (built
    or broken down) — deck rows keyed by ``source_precon_file_name`` plus
    pre-fileName ``pack:<theme>-<code>`` slug rows. The one ownership rule the
    set picker, the pack list and the whole-pack list share."""
    code = code.lower()
    units = decks.precon_unit_counts()
    slugs = _owned_slugs(code)
    return {v["fileName"] for v in variants(code)
            if sum(units.get(v["fileName"], (0, 0))) or sets._slug_theme(v.get("name") or v["fileName"], code) in slugs}


def set_packs(code: str) -> list[Pack]:
    """Every pack version of a Jumpstart set with its contents, your copies of
    the pack (built / broken down) and how much of it your free cards cover.
    Local reads only — call :func:`ensure_ready` first for a set never read."""
    code = code.lower()
    vs = variants(code)
    per = {v["fileName"]: entries(v["fileName"]) for v in vs}
    ids = list(dict.fromkeys(e.scryfall_id for es in per.values() for e in es))
    cards = _card_rows(ids)
    free = inventory.free_quantities(ids)
    units = decks.precon_unit_counts()
    slugs = _owned_slugs(code)
    deck_slugs = _deck_slugs([v["fileName"] for v in vs])

    packs: list[Pack] = []
    for v in vs:
        fn = v["fileName"]
        name = v.get("name") or fn
        s = sets._jumpstart_variant_summary(v, anchor=code)
        built, decon = units.get(fn, (0, 0))
        if not built + decon and sets._slug_theme(name, code) in slugs:
            built = 1  # a pre-fileName pack deck row: owned, state unknown → counted built
        fc = front_cards.front_card_for_theme(code, name)
        p = Pack(file_name=fn, name=name, theme=theme_of(name), version=version_of(name),
                 color=s["color"], card_count=s["card_count"], usd_total=s["usd_total"],
                 top_card=s["top_card"], top_card_usd=s["top_card_usd"],
                 front_card=fc["name"] if fc is not None else None,
                 built=built, deconstructed=decon,
                 deck_slug=deck_slugs.get(fn) or (sets._slug_theme(name, code) if built + decon else None))
        for e in per[fn]:
            c = cards.get(e.scryfall_id) or {}
            price = c.get("prices_usd_foil" if e.foil else "prices_usd")
            p.cards.append(PackCard(
                scryfall_id=e.scryfall_id, name=c.get("name") or e.name, count=e.count, foil=e.foil,
                unit_usd=float(price) if price is not None else None, rarity=c.get("rarity"),
                collector_number=c.get("collector_number"), set_code=(c.get("set_code") or e.set_code),
                color=util.format_color_identity(c.get("color_identity"), collapse_multicolor=False),
                free=free.get(e.scryfall_id, 0), known=bool(c),
            ))
        priced = [c for c in p.cards if c.unit_usd is not None]
        if priced:  # the priciest card, first on ties (as the summary's top_card)
            p.top_card_id = max(priced, key=lambda c: c.unit_usd).scryfall_id
        need = counts_by_id(per[fn])
        p.have = sum(min(n, free.get(sid, 0)) for sid, n in need.items())
        p.short = sum(n for n in need.values()) - p.have
        packs.append(p)
    packs.sort(key=lambda p: (color_sort_key(p.color), p.theme.lower(), p.version or 0))
    return packs


# ---------- the two shopping lists ----------

@dataclass
class BuildableMissing:
    themes: int
    variants: int
    target: dict[str, int]
    owned: dict[str, int]
    rows: list[selectors.MaterializedRow]
    filtered: int
    skipped: list[str]

    @property
    def copies(self) -> int:
        return sum(r.quantity for r in self.rows)

    @property
    def usd(self) -> float:
        return round(sum((r.card.get("prices_usd") or 0.0) * r.quantity for r in self.rows), 2)


def _card_dicts(ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    with db.connect() as conn:
        ph = ",".join("?" for _ in ids)
        return {
            r["scryfall_id"]: selectors._card_dict(r)
            for r in conn.execute(
                f"SELECT {selectors._CARD_COLS} FROM cards c WHERE c.scryfall_id IN ({ph})", ids)
        }


def buildable_missing(code: str, *, filter_buyable: bool = True) -> BuildableMissing:
    """Cards still missing to hold one built copy of every theme plus each
    theme's other-version extras (:func:`build_target` − owned incl. pledged),
    nonfoil, through the physical-buyable gate unless ``filter_buyable=False``."""
    code = code.lower()
    vs = variants(code)
    boards: dict[str, dict[str, int]] = {}
    names: dict[str, str] = {}
    for v in vs:
        es = entries(v["fileName"])
        boards[v.get("name") or v["fileName"]] = counts_by_id(es)
        for e in es:
            names.setdefault(e.scryfall_id, e.name)
    target = build_target(boards)
    owned = ownership.owned_counts(grain="scryfall_id", scryfall_ids=list(target))
    short = {sid: target[sid] - owned.get(sid, 0) for sid in target if target[sid] > owned.get(sid, 0)}
    cards = _card_dicts(list(short))
    rows: list[selectors.MaterializedRow] = []
    skipped: list[str] = []
    for sid, qty in short.items():
        if sid not in cards:
            skipped.append(names.get(sid, sid))
            continue
        rows.append(selectors.MaterializedRow(scryfall_id=sid, quantity=qty, finish="nonfoil", card=cards[sid]))
    n_before = len(rows)
    if filter_buyable:
        rows = missing_mod.physical_buyable(rows, code)
    rows.sort(key=lambda r: ((r.card.get("set") or ""), util.cn_sort_key(r.card.get("collector_number"))))
    return BuildableMissing(themes=len({theme_of(n) for n in boards}), variants=len(vs), target=target,
                            owned=owned, rows=rows, filtered=n_before - len(rows), skipped=skipped)


def pack_rows(code: str, variant: dict, *, include_front: bool = True) -> tuple[list[selectors.MaterializedRow], int]:
    """One pack as export-ready rows (shipped finish) + its front/title card.
    Returns ``(rows, n_skipped)`` — gameplay printings absent from ``cards``."""
    es = entries(variant["fileName"])
    cards = _card_dicts(list(dict.fromkeys(e.scryfall_id for e in es)))
    rows: list[selectors.MaterializedRow] = []
    skipped = 0
    for e in es:
        card = cards.get(e.scryfall_id)
        if card is None:
            skipped += 1
            continue
        rows.append(selectors.MaterializedRow(scryfall_id=e.scryfall_id, quantity=e.count,
                                              finish="foil" if e.foil else "nonfoil", card=card))
    if include_front:
        fc = front_cards.front_card_for_theme(code.lower(), variant.get("name") or "")
        if fc is not None:
            rows.append(front_cards.front_card_row(fc))
    return rows, skipped


def row_value(r: selectors.MaterializedRow) -> float | None:
    """Line value at the row's shipped finish (foil price for foil, else
    nonfoil; unpriced → None) — the same basis as the pack totals."""
    unit = r.card.get("prices_usd_foil" if r.finish == "foil" else "prices_usd")
    return float(unit) * r.quantity if unit is not None else None


@dataclass
class MissingPacks:
    total: int
    packs: list[tuple[dict, list[selectors.MaterializedRow]]]
    skipped: int

    @property
    def rows(self) -> list[selectors.MaterializedRow]:
        """Every pack's rows merged per (printing, finish), quantities summed."""
        merged: dict[tuple[str, str], selectors.MaterializedRow] = {}
        for _, rows in self.packs:
            for r in rows:
                k = (r.scryfall_id, r.finish)
                merged[k] = replace(merged[k], quantity=merged[k].quantity + r.quantity) if k in merged else r
        return sorted(merged.values(), key=lambda r: (r.card.get("set") or "", util.cn_sort_key(r.card.get("collector_number")), r.finish))

    @property
    def copies(self) -> int:
        return sum(r.quantity for _, rows in self.packs for r in rows)

    @property
    def usd(self) -> float:
        return round(sum(row_value(r) or 0.0 for _, rows in self.packs for r in rows), 2)


def missing_packs(code: str) -> MissingPacks:
    """Every pack version you own no copy of (built or broken down), each with
    its FULL contents + front card — not deduped across packs, not reduced by
    cards you already own (the whole-pack shopping list)."""
    code = code.lower()
    vs = variants(code)
    owned = owned_file_names(code)
    out: list[tuple[dict, list[selectors.MaterializedRow]]] = []
    skipped = 0
    for v in vs:
        if v["fileName"] in owned:
            continue
        rows, n = pack_rows(code, v)
        skipped += n
        out.append((v, rows))
    return MissingPacks(total=len(vs), packs=out, skipped=skipped)


def buy_text(code: str, shop: Shop, target: str) -> tuple[str, int]:
    """Paste-ready block for one shopping list through the ONE exports engine."""
    rows = buildable_missing(code).rows if shop == "buildable" else missing_packs(code).rows
    text = exports.build(target, rows)
    return text, len([ln for ln in text.splitlines() if ln.strip()])

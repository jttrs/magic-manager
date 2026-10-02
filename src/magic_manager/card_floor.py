"""Cheapest-printing "floor" lookups — the single home for "what's the cheapest
way to get this card's mechanics", batched and finish-aware.

Two notions of a card's floor, both oracle-grain (functional equivalence = same
``oracle_id``, since any printing of a card plays identically):

* **anywhere** — the cheapest printing of a card across EVERY set, from a LIVE
  Scryfall ``oracleid:`` search. :func:`anywhere_floors` batches many oracle_ids
  into a few ``(oracleid:a or oracleid:b …) unique=prints`` queries (⌈N/20⌉
  requests, not one per card) and is memoized per run.
* **local / in-family** — the cheapest printing among the locally-synced
  ``cards`` rows (optionally restricted to a set family), NO network. This is the
  oracle-grain sibling of :func:`sets.card_price_map`; :func:`sets.lowest_price_by_oracle`
  is the whole-DB flavor and :func:`local_floors` adds the family-scope filter +
  the cheapest-printing location (set/cn).

Both return either a per-finish :class:`FloorPair` (``finish_mode="preserve"`` —
keep nonfoil vs foil distinct, since a print may exist in only one finish) or a
single collapsed :class:`Floor` (``finish_mode="either"`` — the cheaper of the
two, preferring nonfoil on a tie).

This module is the DRY home for floor logic that was duplicated across
``missing._cheapest``, ``set_status._cheapest_pair`` / ``_anywhere_floor`` (a slow
per-id loop), and ``sld.card_floors_many``. The low-level price helpers
(:func:`price`, :func:`card_floors`, :func:`card_floors_many`) are re-exported by
``sld`` so its existing callers (``sld.value_drop``, ``valuation._floor_sum``)
keep working unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from . import db, scryfall

FinishMode = Literal["either", "preserve"]


# ---------- price extraction (live Scryfall rows) ----------

def price(card: dict, key: str) -> float | None:
    """Extract a nested Scryfall price. ``card["prices"][key]`` is a string or
    None; coerce to float, or None when absent/blank/unparseable."""
    prices = card.get("prices") or {}
    v = prices.get(key)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ---------- the ONE "cheaper of the two finishes" helper ----------

def cheapest_floor(
    nonfoil: float | None, foil: float | None, *, prefer: str = "nonfoil",
) -> tuple[float | None, str | None]:
    """Cheaper of ``(nonfoil, foil)`` as ``(price, finish)``.

    Prefers ``prefer`` (default ``"nonfoil"``) on a tie; falls back to the other
    finish when the preferred one is unpriced; ``(None, None)`` when neither is
    priced. This is the single lifted copy of what ``missing._cheapest`` and
    ``set_status._cheapest_pair`` each hand-rolled."""
    first, second = (nonfoil, foil) if prefer == "nonfoil" else (foil, nonfoil)
    first_fin, second_fin = (("nonfoil", "foil") if prefer == "nonfoil"
                             else ("foil", "nonfoil"))
    if first is not None and (second is None or first <= second):
        return first, first_fin
    if second is not None:
        return second, second_fin
    return None, None


# ---------- result shapes ----------

@dataclass
class Floor:
    """The cheapest printing of a card at one scope, one finish (or collapsed)."""
    usd: float | None = None
    finish: str | None = None
    set_code: str | None = None
    collector_number: str | None = None


@dataclass
class FloorPair:
    """Finish-preserving floor — the cheapest printing in EACH finish, kept
    distinct (a print may exist in only one finish, so these can differ in set)."""
    nonfoil: Floor | None = None
    foil: Floor | None = None

    def collapse(self, *, prefer: str = "nonfoil") -> Floor:
        """The cheaper of the two finishes as a single :class:`Floor`."""
        nf = self.nonfoil.usd if self.nonfoil else None
        ff = self.foil.usd if self.foil else None
        usd, finish = cheapest_floor(nf, ff, prefer=prefer)
        if finish == "nonfoil":
            return self.nonfoil or Floor()
        if finish == "foil":
            return self.foil or Floor()
        return Floor()


# ---------- live, batched, anywhere floor ----------

# Scryfall caps boolean clauses per query (fails >~20 with HTTP 400); stay under.
_FLOOR_CHUNK = 20


def _scan_anywhere(oracle_ids: list[str]) -> dict[str, FloorPair]:
    """Core batched scan: one ``(oracleid:a or …) unique=prints`` search per chunk
    of ≤ ``_FLOOR_CHUNK`` ids, tracking the CHEAPEST printing (price + set + cn)
    per finish for each oracle_id. The single source of truth both the price-only
    tuple API (:func:`card_floors_many`) and the enriched API
    (:func:`anywhere_floors`) project from, so there's one search pass either way.

    Raises ``scryfall.ScryfallError`` on a lookup failure (callers that must not
    abort a batch catch it and degrade the affected ids to unpriced)."""
    ids = [o for o in dict.fromkeys(oracle_ids) if o]
    out: dict[str, FloorPair] = {o: FloorPair() for o in ids}
    for i in range(0, len(ids), _FLOOR_CHUNK):
        chunk = ids[i:i + _FLOOR_CHUNK]
        q = "(" + " or ".join(f"oracleid:{o}" for o in chunk) + ")"
        for p in scryfall.search(q, unique="prints"):
            oid = p.get("oracle_id")
            pair = out.get(oid)
            if pair is None:
                continue
            set_code = p.get("set")
            cn = p.get("collector_number")
            nf = price(p, "usd")
            if nf is not None and (pair.nonfoil is None or nf < pair.nonfoil.usd):
                pair.nonfoil = Floor(nf, "nonfoil", set_code, cn)
            ff = price(p, "usd_foil")
            if ff is not None and (pair.foil is None or ff < pair.foil.usd):
                pair.foil = Floor(ff, "foil", set_code, cn)
    return out


def anywhere_floors(
    oracle_ids: Iterable[str], *, finish_mode: FinishMode = "either",
) -> dict[str, Floor | FloorPair]:
    """Cheapest printing of each card ANYWHERE (live, batched), keyed by oracle_id.

    ``finish_mode="preserve"`` → a :class:`FloorPair` per id (nonfoil + foil floors
    kept distinct, each carrying its own set/cn). ``finish_mode="either"`` → a
    single :class:`Floor` per id, the cheaper finish (nonfoil preferred on tie).
    Every requested id is present in the result (unpriced → an empty Floor /
    FloorPair with ``usd=None``). Raises ``scryfall.ScryfallError`` on lookup
    failure."""
    pairs = _scan_anywhere(list(oracle_ids))
    if finish_mode == "preserve":
        return dict(pairs)
    return {oid: pair.collapse() for oid, pair in pairs.items()}


# ---------- price-only compatibility API (re-exported by sld) ----------

def card_floors_many(oracle_ids: list[str]) -> dict[str, tuple[float | None, float | None]]:
    """Batched per-finish price floor — ``{oracle_id: (min_usd, min_usd_foil)}``.

    The price-only projection of :func:`anywhere_floors` (``finish_mode="preserve"``),
    kept at this name + shape because ``sld.value_drop`` and ``valuation._floor_sum``
    already consume it. Collapses N per-card searches into ⌈N/20⌉; ids with no
    priced printing map to ``(None, None)``."""
    pairs = _scan_anywhere(oracle_ids)
    return {
        o: (pair.nonfoil.usd if pair.nonfoil else None,
            pair.foil.usd if pair.foil else None)
        for o, pair in pairs.items()
    }


def card_floors(oracle_id: str) -> tuple[float | None, float | None]:
    """Single-card :func:`card_floors_many`. Prefer the batched form for many ids."""
    return card_floors_many([oracle_id]).get(oracle_id, (None, None))


# ---------- local / in-family floor (no network) ----------

def local_floors(
    oracle_ids: Iterable[str], *,
    family_codes: Iterable[str] | None = None,
    finish_mode: FinishMode = "either",
    conn=None,
) -> dict[str, Floor | FloorPair]:
    """Cheapest LOCALLY-synced printing of each card, keyed by oracle_id — NO
    network. The in-family / local analog of :func:`anywhere_floors`.

    ``family_codes`` (lowercased set codes) restricts the search to one set
    family (the "in-family floor"); ``None`` scans every local printing (the
    whole-DB "local anywhere" floor, matching ``sets.lowest_price_by_oracle``'s
    scope). ``finish_mode`` mirrors :func:`anywhere_floors`. Oracle_ids with no
    local printing are omitted (the caller treats them as unpriced)."""
    ids = list(dict.fromkeys(o for o in oracle_ids if o))
    if not ids:
        return {}

    def _q(c):
        oid_ph = ",".join("?" for _ in ids)
        params: list = list(ids)
        where = f"oracle_id IN ({oid_ph})"
        if family_codes is not None:
            fam = list(family_codes)
            if not fam:
                return {}
            fam_ph = ",".join("?" for _ in fam)
            where += f" AND LOWER(set_code) IN ({fam_ph})"
            params += fam
        rows = c.execute(
            f"SELECT oracle_id, set_code, collector_number, prices_usd, "
            f"prices_usd_foil FROM cards WHERE {where}",
            params,
        ).fetchall()
        pairs: dict[str, FloorPair] = {}
        for r in rows:
            pair = pairs.setdefault(r["oracle_id"], FloorPair())
            nf = r["prices_usd"]
            if nf is not None and (pair.nonfoil is None or nf < pair.nonfoil.usd):
                pair.nonfoil = Floor(nf, "nonfoil", r["set_code"], r["collector_number"])
            ff = r["prices_usd_foil"]
            if ff is not None and (pair.foil is None or ff < pair.foil.usd):
                pair.foil = Floor(ff, "foil", r["set_code"], r["collector_number"])
        if finish_mode == "preserve":
            return dict(pairs)
        return {oid: pair.collapse() for oid, pair in pairs.items()}

    if conn is not None:
        return _q(conn)
    with db.connect() as c:
        return _q(c)

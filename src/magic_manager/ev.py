"""Deterministic booster expected-value (EV) math from MTGJSON booster data.

The single hardest part of valuing a sealed *booster* product — how likely each
card is to appear — is **already published by MTGJSON**, per card, per booster
type. Every per-set file (``mtgjson.set_file``) carries a top-level ``booster``
dict keyed by booster type (``draft`` / ``set`` / ``play`` / ``play-arena`` /
``collector`` / ``beginner`` / ``prerelease`` / …). Each type looks like::

    booster[type] = {
      "boosters": [ {"contents": {sheetName: count, ...}, "weight": int}, ... ],
      "boostersTotalWeight": int,
      "sheets": { sheetName: {"foil": bool, "totalWeight": int,
                              "cards": {uuid: weight, ...}} },
    }

So a booster's EV is EXACT card-level math, not a rarity average::

    EV = Σ_layout (layout.weight / boostersTotalWeight)
             · Σ_sheet count · Σ_uuid (uuid.weight / sheet.totalWeight) · price(uuid)

using ``usd_foil`` when ``sheet.foil`` is true, else ``usd``. Different booster
types (draft vs set vs play vs collector) each own their ``sheets``/``boosters``
subtree, so overlapping/identical card pools are handled correctly — the caller
just picks the right ``booster_type`` (a sealed product's ``contents.pack[].code``
names it; see ``sealed.py``).

This module is pure arithmetic over data passed in; its only I/O is the local
``cards`` price join (``_local_prices``), mirroring ``sets._rollup_deck_prices``
(sets.py:1290-1301). That keeps it trivially unit-testable offline.

Missing prices never crash: an unpriced card is skipped in the numerator but its
weight stays in the sheet's ``totalWeight`` denominator (MTGJSON's published
total), so EV *under-reports* and the shortfall is surfaced as ``coverage`` +
``n_unpriced`` diagnostics rather than silently absorbed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import db


# ---------- local price join (mirrors sets._rollup_deck_prices) ----------

def _local_prices(scryfall_ids: list[str]) -> dict[str, tuple[float | None, float | None]]:
    """Map ``scryfall_id -> (prices_usd, prices_usd_foil)`` from the local cards
    table. IDs absent from the table are simply absent from the result (the
    caller treats them as unpriced). Empty input → empty dict."""
    if not scryfall_ids:
        return {}
    with db.connect() as conn:
        placeholders = ",".join("?" for _ in scryfall_ids)
        return {
            r["scryfall_id"]: (r["prices_usd"], r["prices_usd_foil"])
            for r in conn.execute(
                f"SELECT scryfall_id, prices_usd, prices_usd_foil "
                f"FROM cards WHERE scryfall_id IN ({placeholders})",
                scryfall_ids,
            ).fetchall()
        }


def build_uuid_price_map(set_data: dict) -> tuple[dict[str, dict], list[str]]:
    """Build ``{uuid: {"scryfall_id", "name", "usd", "usd_foil"}}`` for every
    printing in ``set_data['cards']``, joining local prices by scryfall_id.

    The booster ``sheets`` key cards by MTGJSON ``uuid``; the local cards table
    keys on ``scryfall_id``. The set file's ``cards[]`` carries both, so it is
    the bridge. Returns ``(uuid_price, no_local_row_uuids)`` where the second
    list is uuids whose scryfallId had NO row in the local cards table at all
    (a "sync the set first" signal). Per-finish ``None`` prices are left in the
    dict and resolved per-sheet later (a sheet's foil-ness decides which price
    matters, so finish-specific missingness is diagnosed in ``sheet_ev``)."""
    cards = set_data.get("cards") or []
    by_sid: dict[str, str] = {}     # scryfall_id -> uuid (for the price join)
    uuid_meta: dict[str, dict] = {}
    for c in cards:
        uuid = c.get("uuid")
        sid = (c.get("identifiers") or {}).get("scryfallId")
        if not uuid:
            continue
        uuid_meta[uuid] = {"scryfall_id": sid, "name": c.get("name"),
                           "usd": None, "usd_foil": None}
        if sid:
            by_sid[sid] = uuid
    prices = _local_prices(list(by_sid))
    no_row: list[str] = []
    for sid, uuid in by_sid.items():
        pr = prices.get(sid)
        if pr is None:
            no_row.append(uuid)
            continue
        uuid_meta[uuid]["usd"], uuid_meta[uuid]["usd_foil"] = pr
    # uuids with no scryfallId at all also can't be priced.
    no_row.extend(u for u, m in uuid_meta.items() if not m["scryfall_id"])
    return uuid_meta, no_row


# ---------- per-sheet expectation ----------

@dataclass
class SheetEV:
    """Expected value of ONE pull from a single booster sheet."""
    name: str
    foil: bool
    total_weight: int
    ev_per_pull: float      # Σ (weight/total_weight) · price, over priced cards
    n_cards: int
    n_unpriced: int         # cards on the sheet with no price in the chosen finish
    priced_weight: int      # Σ weight over priced cards (≤ total_weight)


def sheet_ev(sheet: dict, uuid_price: dict[str, dict]) -> SheetEV:
    """Expected USD of one pull from ``sheet``.

    ``sheet`` is a MTGJSON booster sheet: ``{foil: bool, totalWeight: int,
    cards: {uuid: weight}}``. Price basis follows ``sheet['foil']`` (foil sheets
    use ``usd_foil``, else ``usd``). Normalization divides by the sheet's OWN
    published ``totalWeight`` (trusted over Σ card weights). Cards missing the
    needed-finish price contribute 0 to the EV but are counted in ``n_unpriced``
    and excluded from ``priced_weight`` so ``coverage`` can be derived."""
    foil = bool(sheet.get("foil"))
    cards = sheet.get("cards") or {}
    total_weight = int(sheet.get("totalWeight") or sum(cards.values()) or 0)
    key = "usd_foil" if foil else "usd"
    ev = 0.0
    n_unpriced = 0
    priced_weight = 0
    for uuid, weight in cards.items():
        meta = uuid_price.get(uuid)
        price = meta.get(key) if meta else None
        if price is None:
            n_unpriced += 1
            continue
        w = int(weight)
        priced_weight += w
        if total_weight:
            ev += (w / total_weight) * float(price)
    return SheetEV(
        name=str(sheet.get("_name", "")),
        foil=foil,
        total_weight=total_weight,
        ev_per_pull=ev,
        n_cards=len(cards),
        n_unpriced=n_unpriced,
        priced_weight=priced_weight,
    )


# ---------- per-pack-layout ----------

def booster_config_ev(config: dict, sheet_evs: dict[str, SheetEV]) -> float:
    """EV of one pack layout = ``{contents: {sheetName: count}, weight}``.

    ``EV = Σ_sheet count · sheet_evs[sheet].ev_per_pull``. A layout referencing
    a sheet with no computed EV (shouldn't happen with well-formed data)
    contributes 0 for that sheet."""
    contents = config.get("contents") or {}
    total = 0.0
    for sheet_name, count in contents.items():
        se = sheet_evs.get(sheet_name)
        if se is not None:
            total += int(count) * se.ev_per_pull
    return total


# ---------- whole-booster ----------

@dataclass
class BoosterEV:
    """Whole-booster expected value for one booster type."""
    booster_type: str
    ev_usd: float
    boosters_total_weight: int
    n_configs: int
    sheets: dict[str, SheetEV] = field(default_factory=dict)
    n_unpriced: int = 0        # distinct unpriced cards across all sheets
    coverage: float = 1.0      # pull-weighted fraction of probability mass priced


def booster_ev(set_data: dict, booster_type: str,
               uuid_price: dict[str, dict] | None = None) -> BoosterEV:
    """Expected singles value of one sealed booster of ``booster_type``.

    Weighted mix over pack layouts::

        ev = Σ_config (config.weight / boostersTotalWeight) · booster_config_ev(config)

    ``uuid_price`` (from :func:`build_uuid_price_map`) is computed once if not
    supplied. ``coverage`` is the expected-pull-weighted average of each sheet's
    priced-weight fraction — i.e. how much of the booster's probability mass had
    a price — so a low value flags an EV that materially under-reports. Raises
    ``KeyError`` if ``booster_type`` isn't present in ``set_data['booster']``."""
    boosters = (set_data.get("booster") or {})
    if booster_type not in boosters:
        raise KeyError(
            f"booster type {booster_type!r} not in set "
            f"{set_data.get('code', '?')}; available: {sorted(boosters)}"
        )
    cfg = boosters[booster_type]
    if uuid_price is None:
        uuid_price, _ = build_uuid_price_map(set_data)

    # Compute each sheet's per-pull EV once (label it for diagnostics).
    sheet_evs: dict[str, SheetEV] = {}
    for name, sheet in (cfg.get("sheets") or {}).items():
        se = sheet_ev({**sheet, "_name": name}, uuid_price)
        sheet_evs[name] = se

    layouts = cfg.get("boosters") or []
    total_weight = int(cfg.get("boostersTotalWeight")
                       or sum(int(c.get("weight", 1)) for c in layouts) or 1)

    ev = 0.0
    # Expected pulls per sheet (pull-weighted, for the coverage metric).
    expected_pulls: dict[str, float] = {}
    for config in layouts:
        p = int(config.get("weight", 1)) / total_weight
        ev += p * booster_config_ev(config, sheet_evs)
        for sheet_name, count in (config.get("contents") or {}).items():
            expected_pulls[sheet_name] = expected_pulls.get(sheet_name, 0.0) + p * int(count)

    # Pull-weighted coverage: Σ pulls·(priced_weight/total_weight) / Σ pulls.
    num = den = 0.0
    for sheet_name, pulls in expected_pulls.items():
        se = sheet_evs.get(sheet_name)
        if se is None or not se.total_weight:
            continue
        num += pulls * (se.priced_weight / se.total_weight)
        den += pulls
    coverage = (num / den) if den else 1.0

    n_unpriced = sum(se.n_unpriced for se in sheet_evs.values())
    return BoosterEV(
        booster_type=booster_type,
        ev_usd=round(ev, 4),
        boosters_total_weight=total_weight,
        n_configs=len(layouts),
        sheets=sheet_evs,
        n_unpriced=n_unpriced,
        coverage=round(coverage, 4),
    )


def booster_types(set_data: dict) -> list[str]:
    """Sorted list of booster type keys available for a set (``[]`` if none).

    Used by ``sealed_value.py --list-boosters`` and by characterize-set to
    record which booster types a family exposes."""
    return sorted((set_data.get("booster") or {}).keys())

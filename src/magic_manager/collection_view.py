"""Collection view engine: a set family's ENTIRE printing universe joined to what
you own.

The missing-set pipeline (``missing.missing_printings``) answers "what should I
buy" over a curated universe (rares/mythics, chase uncommons, preferred
treatments). The Collection view answers a broader question: "show me the whole
family, my copies of each printing, and where the gaps are". So this module:

* enumerates every physical printing in the family's set_targets-authoritative
  code set (``family_status._family_code_set`` — the same scope card-diff and
  set-status use), in ONE cards query;
* keeps the printings a collector catalogs, reusing the master-list policy:
  set types in ``sets.DEFAULT_INVENTORY_SET_TYPES`` (no memorabilia/art-series,
  alchemy or token sets) and not ``sets.is_excluded_variant`` (prerelease,
  stamped, serialized, …); then drops tokens, digital-only
  (``selectors._is_digital_only``), the family's HARD-tier unobtainable rules,
  and meld-back faces (``missing._drop_meld_back_faces``). Every exclusion
  yields to ownership: a printing you own always shows (ground truth first);
* attaches owned and pledged quantities per finish (one inventory query, one
  deck_assignments query) and the classification flags the UI layers on:
  ``is_bulk`` (common/uncommon), ``is_chase`` (family chase-tier rules),
  ``standard_frame`` (``treatments.is_standard_frame``), ``treatment`` codes.

Pure engine: no rendering. ``api.collection`` adapts it for the web.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import db, exports, family_status, missing as missing_mod, scryfall, selectors as sel_mod, sets as sets_mod, treatments

BULK_RARITIES = frozenset({"common", "uncommon"})
_HARD_TIER = frozenset({"hard"})
_CHASE_TIER = frozenset({"chase"})


@dataclass
class CollectionCard:
    scryfall_id: str
    oracle_id: str | None
    name: str
    family: str
    set_code: str
    collector_number: str
    rarity: str
    type_line: str | None
    cmc: float | None
    color_identity: list[str]
    released_at: str | None
    finishes: list[str]                 # finishes this printing exists in
    owned: dict[str, int]               # finish -> owned copies
    pledged: dict[str, int]             # finish -> copies pledged to built decks
    price_usd: float | None
    price_usd_foil: float | None
    image_uri: str | None
    scryfall_uri: str | None
    treatment: str                      # treatments.compute_treatment codes ("" = plain)
    standard_frame: bool
    is_bulk: bool
    is_chase: bool
    is_token: bool

    @property
    def owned_total(self) -> int:
        return sum(self.owned.values())


@dataclass
class FamilySummary:
    code: str
    name: str
    printings: int
    owned_printings: int
    owned_copies: int
    owned_usd: float
    missing_printings: int
    missing_usd: float
    # Member sets that contribute printings, oldest release first: [{code, name}].
    sets: list[dict[str, str]] = field(default_factory=list)


@dataclass
class FamilyCollection:
    summary: FamilySummary
    cards: list[CollectionCard] = field(default_factory=list)


def _unit_price(card: CollectionCard, finish: str) -> float | None:
    return card.price_usd_foil if finish == "foil" else card.price_usd


def _cheapest_finish_price(card: CollectionCard) -> float | None:
    prices = [p for f in card.finishes if (p := _unit_price(card, f)) is not None]
    return min(prices) if prices else None


def family_cards(code: str) -> FamilyCollection:
    """The full printing universe of ``code``'s family with ownership attached.
    Raises ``LookupError`` for an unknown code."""
    parent_code, parent_name, related = family_status.resolve_family(code)
    codes = sorted(family_status._family_code_set(parent_code, related))
    ph = ",".join("?" for _ in codes)
    with db.connect() as conn:
        rows = conn.execute(
            f"""
            SELECT {sel_mod._CARD_COLS}, c.image_uri AS c_image_uri,
                   c.released_at AS c_released_at
            FROM cards c WHERE c.set_code IN ({ph})
            """,
            codes,
        ).fetchall()
        owned: dict[tuple[str, str], int] = {
            (r[0], r[1]): r[2] for r in conn.execute(
                f"""
                SELECT i.scryfall_id, i.finish, i.quantity FROM inventory i
                JOIN cards c ON c.scryfall_id = i.scryfall_id
                WHERE c.set_code IN ({ph}) AND i.quantity > 0
                """,
                codes,
            )
        }
        pledged: dict[tuple[str, str], int] = {
            (r[0], r[1]): r[2] for r in conn.execute(
                f"""
                SELECT da.scryfall_id, da.finish, SUM(da.count) FROM deck_assignments da
                JOIN cards c ON c.scryfall_id = da.scryfall_id
                WHERE c.set_code IN ({ph})
                GROUP BY da.scryfall_id, da.finish
                """,
                codes,
            )
        }

    owned_by: dict[str, dict[str, int]] = {}
    for (sid, fin), q in owned.items():
        owned_by.setdefault(sid, {})[fin] = q
    pledged_by: dict[str, dict[str, int]] = {}
    for (sid, fin), q in pledged.items():
        pledged_by.setdefault(sid, {})[fin] = q
    owned_ids = set(owned_by)
    all_sets = {s["code"].lower(): s for s in scryfall.all_sets()}
    set_types = {code: s.get("set_type") for code, s in all_sets.items()}
    candidates: list[sel_mod.MaterializedRow] = []
    extra: dict[str, tuple[str | None, str | None]] = {}
    for r in rows:
        card = sel_mod._card_dict(r)
        sid = card["scryfall_id"]
        if sid not in owned_ids and (
            set_types.get(card["set"]) not in sets_mod.DEFAULT_INVENTORY_SET_TYPES
            or sets_mod.is_excluded_variant(card)
            or card.get("is_token")
            or sel_mod._is_digital_only(card)
            or sel_mod._is_family_unobtainable(card, parent_code, _HARD_TIER)
        ):
            continue
        card["color_identity"] = r["color_identity"]
        card["finishes"] = r["finishes"]
        extra[sid] = (r["c_image_uri"], r["c_released_at"])
        candidates.append(sel_mod.MaterializedRow(scryfall_id=sid, quantity=0, finish="nonfoil", card=card))

    kept = {r.scryfall_id for r in missing_mod._drop_meld_back_faces(candidates, parent_code, family_codes=set(codes))}
    cards: list[CollectionCard] = []
    for r in candidates:
        sid, c = r.scryfall_id, r.card
        if sid not in kept and sid not in owned_ids:
            continue
        # Inventory records two finishes; etched is a foil finish there (Scryfall
        # lists it separately, e.g. etched-only commander printings).
        raw = ["foil" if f == "etched" else f for f in json.loads(c.get("finishes") or "[]")]
        finishes = list(dict.fromkeys(f for f in raw if f in sel_mod.VALID_FINISHES)) or ["nonfoil"]
        img, released = extra[sid]
        cards.append(CollectionCard(
            scryfall_id=sid, oracle_id=c.get("oracle_id"), name=c.get("name") or "",
            family=parent_code, set_code=(c.get("set") or "").lower(),
            collector_number=c.get("collector_number") or "", rarity=c.get("rarity") or "common",
            type_line=c.get("type_line"), cmc=c.get("cmc"),
            color_identity=json.loads(c.get("color_identity") or "[]"),
            released_at=released, finishes=finishes,
            owned=owned_by.get(sid, {}),
            pledged=pledged_by.get(sid, {}),
            price_usd=c.get("prices_usd"), price_usd_foil=c.get("prices_usd_foil"),
            image_uri=img, scryfall_uri=c.get("scryfall_uri"),
            treatment=treatments.compute_treatment(c, finish=None),
            standard_frame=treatments.is_standard_frame(c),
            is_bulk=(c.get("rarity") or "") in BULK_RARITIES,
            is_chase=sel_mod._is_family_unobtainable(c, parent_code, _CHASE_TIER),
            is_token=bool(c.get("is_token")),
        ))

    owned_cards = [c for c in cards if c.owned_total]
    missing_cards = [c for c in cards if not c.owned_total]
    summary = FamilySummary(
        code=parent_code, name=parent_name,
        printings=len(cards), owned_printings=len(owned_cards),
        owned_copies=sum(c.owned_total for c in owned_cards),
        owned_usd=round(sum((_unit_price(c, f) or 0.0) * q for c in owned_cards for f, q in c.owned.items()), 2),
        missing_printings=len(missing_cards),
        missing_usd=round(sum(_cheapest_finish_price(c) or 0.0 for c in missing_cards), 2),
        sets=[
            {"code": code, "name": (all_sets.get(code) or {}).get("name") or code.upper()}
            for code in sorted(
                {c.set_code for c in cards},
                key=lambda code: ((all_sets.get(code) or {}).get("released_at") or "9999", code),
            )
        ],
    )
    return FamilyCollection(summary=summary, cards=cards)


def buy_lines(items: list[tuple[str, str, int]], target: str) -> str:
    """Paste-ready buy-list block for explicit ``(scryfall_id, finish, qty)``
    picks, through the ONE exports engine (TCGplayer treatment suffixes etc.).
    ``target`` is an ``exports`` key (``manapool`` | ``tcgplayer`` | …)."""
    ids = list(dict.fromkeys(sid for sid, _, _ in items))
    if not ids:
        return ""
    ph = ",".join("?" for _ in ids)
    with db.connect() as conn:
        by_id = {
            r["scryfall_id"]: sel_mod._card_dict(r)
            for r in conn.execute(f"SELECT {sel_mod._CARD_COLS} FROM cards c WHERE c.scryfall_id IN ({ph})", ids)
        }
    rows = [
        sel_mod.MaterializedRow(scryfall_id=sid, quantity=max(1, qty), finish=finish, card=by_id[sid])
        for sid, finish, qty in items if sid in by_id
    ]
    return exports.build(target, rows)

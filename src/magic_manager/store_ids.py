"""Store product ids → exact printings (shared by the cart audit and purchases).

Stores name a printing by their OWN product id, not a Scryfall id:

* **TCGplayer** — a product id. Scryfall answers it exactly
  (``/cards/tcgplayer/<id>``, cached by the wrapper); the printing is upserted.
* **Card Kingdom** — a product id per finish (its nonfoil and foil copies are
  separate products). MTGJSON's set files carry it (``identifiers.cardKingdomId``
  / ``cardKingdomFoilId`` / ``cardKingdomEtchedId``), so the id is looked up in
  the set files of the card's printings — the sets whose names best match Card
  Kingdom's edition first (an edition like "Final Fantasy Variants Foil" or
  "3rd Edition" isn't a Scryfall set name). Exact when found; a line nothing
  matches stays unidentified (shown by name, never guessed).

Both are offline-safe: a network failure leaves the line unidentified.
"""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from typing import Iterable

from . import db

# Card Kingdom edition words that never appear in (or never distinguish) Scryfall set names.
_EDITION_NOISE = {"foil", "variants", "variant", "the", "of", "and", "decks", "deck", "edition", "set", "magic", "gathering"}
_ORDINALS = {"3rd": "revised", "4th": "fourth", "5th": "fifth", "6th": "sixth", "7th": "seventh",
             "8th": "eighth", "9th": "ninth", "10th": "tenth"}
# Most set files read per Card Kingdom card before giving up (each is cached on disk).
CK_SCAN_LIMIT = 12


# ---------- TCGplayer ----------

def tcgplayer_printings(product_ids: Iterable[int]) -> dict[int, dict]:
    """``{product_id: scryfall card}`` for the ids Scryfall knows (sealed
    products and other games aren't cards → absent). Found printings are upserted."""
    from . import scryfall, sets as sets_mod
    out: dict[int, dict] = {}
    for pid in sorted({int(p) for p in product_ids if p}):
        try:
            card = scryfall.by_tcgplayer_id(pid)
        except Exception:  # noqa: BLE001 — offline: the line stays unidentified, named
            continue
        if card and card.get("id"):
            out[pid] = card
    if out:
        with db.connect() as conn:
            sets_mod.upsert_lookup_cards(conn, list(out.values()))
    return out


# ---------- Card Kingdom ----------

@dataclass(frozen=True)
class CkLine:
    product_id: int
    name: str
    edition: str | None = None
    number: str | None = None     # collector number from Card Kingdom's variant title, when it shows one


@dataclass(frozen=True)
class CkPrinting:
    scryfall_id: str
    finish: str                   # nonfoil | foil | etched — which of Card Kingdom's products the id is


def _tokens(name: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    return {_ORDINALS.get(w, w) for w in words} - _EDITION_NOISE


@functools.lru_cache(maxsize=64)
def _ck_index_cached(set_code: str) -> dict[int, CkPrinting]:
    from . import mtgjson
    data = mtgjson.set_file(set_code.upper())
    data = data.get("data", data) if isinstance(data, dict) else {}
    out: dict[int, CkPrinting] = {}
    for card in (data.get("cards") or []) + (data.get("tokens") or []):
        ids = card.get("identifiers") or {}
        sid = ids.get("scryfallId")
        if not sid:
            continue
        for key, finish in (("cardKingdomId", "nonfoil"), ("cardKingdomFoilId", "foil"), ("cardKingdomEtchedId", "etched")):
            if str(ids.get(key) or "").isdigit():
                out[int(ids[key])] = CkPrinting(sid, finish)
    return out


def _ck_index(set_code: str) -> dict[int, CkPrinting]:
    """Card Kingdom product id → printing, from one MTGJSON set file. Successes are cached; failures are not."""
    try:
        return _ck_index_cached(set_code)
    except Exception:  # noqa: BLE001 — no MTGJSON file for this code / offline
        return {}


_ck_index.cache_clear = _ck_index_cached.cache_clear  # type: ignore[attr-defined]


def _local_candidates(conn, name: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT set_code, collector_number FROM cards WHERE name = ? OR name LIKE ? || ' // %'", (name, name))]


def _ranked_sets(rows: list[dict], line: CkLine) -> list[str]:
    """The card's sets, the likeliest home of Card Kingdom's edition first."""
    from . import scryfall
    try:
        names = {s["code"].lower(): (s.get("name") or "", s.get("set_type") or "") for s in scryfall.all_sets()}
    except Exception:  # noqa: BLE001 — offline: rank by name overlap only
        names = {}
    want = _tokens(line.edition or "")
    promo = "promotional" in want or "promo" in want
    count: dict[str, int] = {}
    cn: dict[str, bool] = {}
    for r in rows:
        code = r["set_code"].lower()
        count[code] = count.get(code, 0) + 1
        if line.number and (r.get("collector_number") or "").lstrip("0") == line.number.lstrip("0"):
            cn[code] = True

    def score(code: str) -> tuple:
        set_name, set_type = names.get(code, ("", ""))
        have = _tokens(set_name)
        jac = len(want & have) / len(want | have) if (want or have) else 0.0
        return (-jac, not cn.get(code, False), not (promo and set_type == "promo"), -count[code], code)

    return sorted(count, key=score)


def cardkingdom_printings(lines: Iterable[CkLine], *, remote: bool = True) -> dict[int, CkPrinting]:
    """``{product_id: CkPrinting}`` for the Card Kingdom lines found in MTGJSON.
    Candidate sets come from the local catalog by card name; when none match
    (or the card isn't local) Scryfall's printings of the name widen them once
    (``remote``), upserted so the printing resolves locally afterwards."""
    from . import scryfall, sets as sets_mod
    out: dict[int, CkPrinting] = {}
    pending = {ln.product_id: ln for ln in lines if ln.product_id and ln.name}
    for pid, ln in pending.items():
        with db.connect() as conn:
            rows = _local_candidates(conn, ln.name)
        tried: set[str] = set()
        for widen in (False, True):
            if widen:
                if not remote:
                    break
                try:
                    cards = list(scryfall.search(f'!"{ln.name}"', unique="prints", include_extras="true"))
                except Exception:  # noqa: BLE001 — offline / no such name
                    break
                if cards:
                    with db.connect() as conn:
                        sets_mod.upsert_lookup_cards(conn, cards)
                rows = [{"set_code": c.get("set") or "", "collector_number": c.get("collector_number")} for c in cards]
            for code in [c for c in _ranked_sets(rows, ln) if c not in tried][:CK_SCAN_LIMIT]:
                tried.add(code)
                hit = _ck_index(code).get(pid)
                if hit:
                    out[pid] = hit
                    break
            if pid in out:
                break
    if out and remote:
        from . import addcards
        addcards.ensure_printings({p.scryfall_id for p in out.values()})
    return out

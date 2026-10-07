"""On-theme art swaps for a decklist: pick a Scryfall Tagger ART tag (``cat``,
``moon``, …) and, for each card in the list, find printings of that card whose
artwork carries it — preferring one you own with free copies, else the cheapest.

Thin composition over :mod:`magic_manager.scryfall_art` (which printings carry
the tag, incl. descendant tags) and the deck editor's ownership rule
(:func:`deck_edit.most_free`); printing facts come from
:func:`addcards.printings_for_ids`. Read-only except :func:`lookup_scryfall`,
which adds on-theme printings missing from the local catalog (a card cache, not
your data). Swapping is the editor's job: the draft changes printing and the
normal save path writes a new version.
"""
from __future__ import annotations

import itertools
import math

from . import addcards, db, deck_edit, inventory, scryfall, scryfall_art

_FINISHES = ("nonfoil", "foil")
_ORACLE_CHUNK = 20   # oracleid terms per Scryfall query (keeps the URL short)


def tags_synced() -> bool:
    """True once the Scryfall art-tag cache has been loaded (``mm scryfall tags sync``)."""
    with db.connect() as conn:
        return conn.execute("SELECT 1 FROM illustration_art_tags LIMIT 1").fetchone() is not None


def search_tags(q: str, limit: int = 20) -> dict:
    return {"synced": tags_synced(), "tags": scryfall_art.art_tag_search(q, limit)}


def _price(p: dict) -> float | None:
    v = p.get("price_usd") if p.get("price_usd") is not None else p.get("price_usd_foil")
    return float(v) if v is not None else None


def _owned(p: dict) -> int:
    return sum((p.get("owned") or {}).values())


def rank(cands: list[dict]) -> list[dict]:
    """On-theme printings of ONE card, best first: your printing with the most
    free copies (the deck editor's rule), else the cheapest; the rest follow
    free → cheapest → owned."""
    if not cands:
        return []
    free = {c["scryfall_id"]: c.get("free") or 0 for c in cands}
    mine = [(c["scryfall_id"], _owned(c)) for c in cands if free[c["scryfall_id"]] > 0]
    order = sorted(cands, key=lambda c: (
        -(c.get("free") or 0), _price(c) if _price(c) is not None else math.inf,
        -_owned(c), c["set_code"], c["collector_number"]))
    if mine:
        best = deck_edit.most_free(mine, free)
        order.sort(key=lambda c: c["scryfall_id"] != best)
    return order


def swaps(tag_ref: str, scryfall_ids) -> dict:
    """For each printing in a decklist: is it already on theme, can it swap to
    an on-theme printing of the same card, or is there none locally? Returns
    ``{tag: {id, label}, rows: [{scryfall_id, oracle_id, status, pick,
    candidates}], printings: {sid: PrintingOut-dict}, matched: {sid: [labels]},
    free_by_finish: {sid: {nonfoil, foil}}}`` (free copies per finish for printings
    you own; the printing's ``free`` is the finish-agnostic total)
    where ``status`` ∈ on_theme | swap | none and ``candidates`` are ranked
    (:func:`rank`). Raises ``LookupError`` for an unknown tag."""
    sids = list(dict.fromkeys(s for s in scryfall_ids if s))
    tag = scryfall_art.resolve_tag(tag_ref)
    if tag is None:
        raise LookupError(f"no art tag matches {tag_ref!r}")
    current = addcards.printings_for_ids(sids)
    oids = {p["oracle_id"] for p in current.values() if p.get("oracle_id")}
    hits = scryfall_art.printings_with_art(tag[0], oracle_ids=oids) if oids else []
    matched = {h["scryfall_id"]: h["tags"] for h in hits}
    printings = {**addcards.printings_for_ids(matched), **current}
    by_oracle: dict[str, list[dict]] = {}
    for h in hits:
        if h["scryfall_id"] in printings:
            by_oracle.setdefault(h["oracle_id"], []).append(printings[h["scryfall_id"]])
    rows = []
    for sid in sids:
        p = current.get(sid)
        if p is None:
            continue
        ranked = rank(by_oracle.get(p.get("oracle_id") or "", []))
        if sid in matched:
            status, pick = "on_theme", sid
        elif ranked:
            status, pick = "swap", ranked[0]["scryfall_id"]
        else:
            status, pick = "none", None
        rows.append({"scryfall_id": sid, "oracle_id": p.get("oracle_id"), "status": status,
                     "pick": pick, "candidates": [c["scryfall_id"] for c in ranked]})
    with db.connect() as conn:
        free_by_finish = {
            sid: {fin: inventory.free_quantity(sid, fin, conn=conn) for fin in _FINISHES}
            for sid, p in printings.items() if p.get("owned")}
    return {"tag": {"id": tag[0], "label": tag[1]}, "rows": rows,
            "printings": printings, "matched": matched, "free_by_finish": free_by_finish}


def lookup_scryfall(tag_ref: str, scryfall_ids) -> dict:
    """Ask Scryfall for on-theme printings of the cards behind these printings
    (``art:<tag>``) and add any missing from the local catalog. Network; returns
    ``{searched, added}``; raises ``scryfall.ScryfallError`` on a real lookup failure (searched = cards, added = printings new to the catalog)."""
    tag = scryfall_art.resolve_tag(tag_ref)
    if tag is None:
        raise LookupError(f"no art tag matches {tag_ref!r}")
    with db.connect() as conn:
        slug = conn.execute("SELECT slug FROM scryfall_tags WHERE id = ?", (tag[0],)).fetchone()[0]
    oids = sorted({p["oracle_id"] for p in addcards.printings_for_ids(scryfall_ids).values() if p.get("oracle_id")})
    found: list[dict] = []
    for i in range(0, len(oids), _ORACLE_CHUNK):
        part = " or ".join(f"oracleid:{o}" for o in oids[i:i + _ORACLE_CHUNK])
        try:
            found += itertools.islice(scryfall.search(f"art:{slug} game:paper unique:prints ({part})"), 500)
        except scryfall.ScryfallError as e:
            if "HTTP 404" in str(e) or "didn't match any cards" in str(e):
                continue   # Scryfall answers "no cards" with an error object
            raise
    known = set(addcards.printings_for_ids(f["id"] for f in found if f.get("id")))
    new = [f for f in found if f.get("id") and f["id"] not in known]
    addcards._upsert(new)
    return {"searched": len(oids), "added": len(new)}

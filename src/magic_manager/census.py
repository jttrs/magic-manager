"""Census reconciliation — diff a physical count against owned inventory.

The user counts ALL their loose cards for a set family into an add-mode
master-list XLSX (sheet ``checklist``; only filled ``qty_normal`` / ``qty_foil``
cells count). Products kept OFF the sheet (built decks, set-aside decks, scene
boxes) are named by MTGJSON fileName. ``target = census + Σ product recipes + copies pledged to unnamed built decks``
(those are off the sheet too); the plan is the difference between that target
and OWNED inventory over the sheet's printings:

* **adds** — target above owned (written as one ``import-block`` event);
* **removals** — owned above target (written as one ``adhoc`` event), never
  below the copies pledged to built decks.

It is a diff, never an overwrite and never an ingest of the sheet itself.
Driven by ``scripts/census_reconcile.py`` (skill ``census-reconcile``).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import db, decks, ingest, inventory, mtgjson, parsers, util

Key = tuple[str, str]  # (scryfall_id, finish)

_SHEET = "checklist"
_FINISH_COLS = (("qty_normal", "nonfoil"), ("qty_foil", "foil"))


class CensusError(ValueError):
    """Bad input: unreadable sheet, unresolved rows, unknown product, …"""


class CensusRefused(CensusError):
    """The plan would remove copies pledged to built decks; nothing written."""

    def __init__(self, plan: "CensusPlan"):
        self.plan = plan
        super().__init__(
            f"{len(plan.below_pledged)} removal line(s) would drop below the copies "
            "pledged to built decks — nothing written"
        )


@dataclass
class CensusSheet:
    anchor: str
    universe: set[Key]
    census: Counter
    labels: dict[Key, tuple[str, str, str]]  # key -> (set, cn, name)
    include_tokens: bool = False  # the sheet's _meta says tokens are on it


@dataclass
class CensusLine:
    """One (printing, finish) row of the plan. ``change`` is the magnitude of the
    adjustment (copies to add on an add line, to remove on a removal line)."""

    scryfall_id: str
    finish: str
    set: str
    cn: str
    name: str
    census: int
    products: int
    in_decks: int  # copies pledged to built decks that were not named as products
    owned: int
    pledged: int
    target: int
    change: int


@dataclass
class CensusPlan:
    anchor: str
    products: list[str]
    census_copies: int
    product_copies: int
    deck_copies: int
    target_copies: int
    owned_copies: int
    adds: list[CensusLine] = field(default_factory=list)
    removals: list[CensusLine] = field(default_factory=list)
    below_pledged: list[CensusLine] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "anchor": self.anchor,
            "products": list(self.products),
            "totals": {
                "census_copies": self.census_copies,
                "product_copies": self.product_copies,
                "deck_copies": self.deck_copies,
                "target_copies": self.target_copies,
                "owned_copies": self.owned_copies,
                "add_rows": len(self.adds),
                "add_copies": sum(ln.change for ln in self.adds),
                "removal_rows": len(self.removals),
                "removal_copies": sum(ln.change for ln in self.removals),
                "below_pledged": len(self.below_pledged),
            },
            "adds": [asdict(ln) for ln in self.adds],
            "removals": [asdict(ln) for ln in self.removals],
            "below_pledged": [asdict(ln) for ln in self.below_pledged],
        }


# ---------- reading the sheet ----------


def _qty(value, where: str) -> int:
    """A filled cell as a non-negative int (floats like 3.0 from Excel are fine)."""
    if isinstance(value, bool):
        raise CensusError(f"{where}: not a non-negative whole number: {value!r}")
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if not isinstance(value, int) or value < 0:
        raise CensusError(f"{where}: not a non-negative whole number: {value!r}")
    return value


def read_census(path: str | Path, *, conn=None) -> CensusSheet:
    """Read a filled add-mode master-list XLSX into a :class:`CensusSheet`."""
    path = Path(path)
    if path.suffix.lower() != ".xlsx":
        raise CensusError("census needs the XLSX checklist")
    if not path.exists():
        raise CensusError(f"file not found: {path}")

    try:
        sheet = parsers.read_master_list_rows(path)
    except Exception as e:  # corrupt / not a workbook
        raise CensusError(f"cannot read {path.name}: {e}") from e
    if sheet.missing_columns:
        raise CensusError(f"{path.name}: missing column(s) {', '.join(sheet.missing_columns)}")
    meta = sheet.meta or {}
    kind = (meta.get("kind") or "inventory").lower()
    mode = (meta.get("mode") or "add").lower()
    if kind != "inventory" or mode != "add":
        raise CensusError(
            f"{path.name}: census needs an add-mode inventory checklist (this one is "
            f"kind={kind}, mode={mode}) — generate a fresh sheet with "
            "`uv run mm set master-list <set>`"
        )

    parsed: list[tuple[int, str, str, str, dict[str, object]]] = []
    for r in sheet.rows:
        cells = {"qty_normal": r.qty_normal_raw, "qty_foil": r.qty_foil_raw}
        if not r.set and not r.collector_number and all(v in (None, "") for v in cells.values()):
            continue  # blank spacer row
        cn = re.sub(r"^(\d+)\.0+$", r"\1", r.collector_number)  # Excel floats: 1.0 -> 1
        parsed.append((r.row_num, r.set, cn, r.name, cells))
    if not parsed:
        raise CensusError(f"{path.name}: no card rows")

    anchor = str(meta.get("anchor_code") or parsed[0][1]).lower()

    universe: set[Key] = set()
    census: Counter = Counter()
    labels: dict[Key, tuple[str, str, str]] = {}
    unresolved: list[tuple[int, str, str, str]] = []
    with db.transaction(conn) as c:
        for n, set_code, cn, name, cells in parsed:
            row = c.execute(
                "SELECT scryfall_id FROM cards WHERE set_code = ? AND collector_number = ?",
                (set_code, cn),
            ).fetchone()
            if row is None:
                unresolved.append((n, set_code, cn, name))
                continue
            sid = row["scryfall_id"]
            for col, finish in _FINISH_COLS:
                key = (sid, finish)
                universe.add(key)
                labels[key] = (set_code, cn, name)
                cell = cells[col]
                if cell not in (None, ""):
                    census[key] += _qty(cell, f"row {n} {set_code} {cn} {name} [{col}]")
    if unresolved:
        shown = [f"row {n}: {s} {cn} {name}".rstrip() for n, s, cn, name in unresolved[:25]]
        more = f"\n  …and {len(unresolved) - 25} more" if len(unresolved) > 25 else ""
        codes = sorted({s for _, s, _, _ in unresolved})
        raise CensusError(
            f"{len(unresolved)} row(s) not in the local catalog:\n  " + "\n  ".join(shown) + more
            + "\nsync the set(s) first: " + "; ".join(f"uv run mm set sync {c}" for c in codes)
        )
    return CensusSheet(anchor=anchor, universe=universe, census=census, labels=labels,
                       include_tokens=str(meta.get("include_tokens") or "0").strip() == "1")


# ---------- planning ----------


def _product_needs(products: list[str], *, include_tokens: bool = False) -> list[dict[Key, int]]:
    """One recipe per ``products`` occurrence, in order. ``include_tokens`` follows
    the sheet (a token-inclusive sheet counts the products' token board too)."""
    out: list[dict[Key, int]] = []
    for file_name in products:
        try:
            needs = decks.precon_recipe_needs(file_name, include_tokens=include_tokens)
        except mtgjson.MtgJsonError as e:
            raise CensusError(f"unknown or unreadable product {file_name!r}: {e}") from e
        if not needs:
            raise CensusError(f"product {file_name!r} has no recipe cards")
        out.append(needs)
    return out


def _read_owned(conn, sids: list[str]) -> Counter:
    owned: Counter = Counter()
    for part in util.chunks(sids):
        marks = ",".join("?" * len(part))
        for r in conn.execute(
            f"SELECT scryfall_id, finish, quantity FROM inventory WHERE scryfall_id IN ({marks})",
            part,
        ):
            owned[(r["scryfall_id"], r["finish"])] = r["quantity"]
    return owned


def _deck_products(conn, deck_ids: list[int]) -> dict[int, str | None]:
    out: dict[int, str | None] = {}
    for part in util.chunks(deck_ids):
        marks = ",".join("?" * len(part))
        for r in conn.execute(
            f"SELECT deck_id, source_precon_file_name FROM decks WHERE deck_id IN ({marks})", part
        ):
            out[r["deck_id"]] = r["source_precon_file_name"]
    return out


def _build(sheet: CensusSheet, products: list[str], needs: list[dict[Key, int]], conn) -> CensusPlan:
    outside = sorted({k for n in needs for k in n if k not in sheet.universe})
    if outside:
        raise CensusError(
            f"{len(outside)} product card(s) are not on the sheet (the products must "
            "be the same set family as the sheet): "
            + ", ".join(f"{sid} {fin}" for sid, fin in outside[:10])
            + (" …" if len(outside) > 10 else "")
        )
    sids = sorted({sid for sid, _ in sheet.universe})
    owned = _read_owned(conn, sids)
    by_deck = inventory.pledged_by_deck(conn, sids)
    pledged: Counter = Counter()
    for pl in by_deck.values():
        pledged.update(pl)
    deck_file = _deck_products(conn, list(by_deck))

    # Each named product occurrence claims one unclaimed deck of that product (the
    # one with the most pledges on the sheet, then the lowest id); it counts for
    # max(recipe, that deck's pledges). Everything else pledged is an unnamed deck.
    claimed: set[int] = set()
    off: Counter = Counter()
    for file_name, recipe in zip(products, needs):
        cands = [d for d, f in deck_file.items() if f == file_name and d not in claimed]
        if not cands:
            off.update(recipe)
            continue
        d = min(cands, key=lambda x: (-sum(by_deck[x].values()), x))
        claimed.add(d)
        for k in set(recipe) | {k for k in by_deck[d] if k in sheet.universe}:
            off[k] += max(recipe.get(k, 0), by_deck[d].get(k, 0))
    in_decks: Counter = Counter()
    for d, pl in by_deck.items():
        if d not in claimed:
            for k, n in pl.items():
                if k in sheet.universe:
                    in_decks[k] += n

    adds: list[CensusLine] = []
    removals: list[CensusLine] = []
    target_total = 0
    for key in sheet.universe:
        tgt = sheet.census[key] + off[key] + in_decks[key]
        inv = owned[key]
        target_total += tgt
        if tgt == inv:
            continue
        set_code, cn, name = sheet.labels[key]
        line = CensusLine(
            scryfall_id=key[0], finish=key[1], set=set_code, cn=cn, name=name,
            census=sheet.census[key], products=off[key], in_decks=in_decks[key], owned=inv,
            pledged=pledged[key], target=tgt, change=abs(tgt - inv),
        )
        (adds if tgt > inv else removals).append(line)

    def order(ln: CensusLine):
        return (ln.set, util.cn_sort_key(ln.cn), ln.finish)

    adds.sort(key=order)
    removals.sort(key=order)
    return CensusPlan(
        anchor=sheet.anchor,
        products=list(products),
        census_copies=sum(sheet.census.values()),
        product_copies=sum(off[k] for k in sheet.universe),
        deck_copies=sum(in_decks.values()),
        target_copies=target_total,
        owned_copies=sum(owned[k] for k in sheet.universe),
        adds=adds,
        removals=removals,
        below_pledged=[ln for ln in removals if ln.owned - ln.change < ln.pledged],
    )


def plan(path: str | Path, products: list[str] | None = None, *, conn=None) -> CensusPlan:
    """Diff ``census + Σ products`` against owned inventory (read-only).

    ``products`` are MTGJSON fileNames and may repeat (two copies = listed twice).
    """
    products = list(products or [])
    sheet = read_census(path, conn=conn)
    needs = _product_needs(products, include_tokens=sheet.include_tokens)
    with db.transaction(conn) as c:
        return _build(sheet, products, needs, c)


# ---------- applying ----------


def apply(path: str | Path, products: list[str] | None = None) -> dict:
    """Write the plan in ONE transaction: adds as an ``import-block`` event,
    removals as an ``adhoc`` event. Refuses (nothing written) if any removal would
    drop below the copies pledged to built decks."""
    products = list(products or [])
    sheet = read_census(path)
    # network/disk reads stay outside the write transaction
    needs = _product_needs(products, include_tokens=sheet.include_tokens)
    with db.transaction() as c:
        p = _build(sheet, products, needs, c)
        if p.below_pledged:
            raise CensusRefused(p)

        adds_event = removals_event = None
        touched: set[Key] = set()
        if p.adds:
            label = f"census:{p.anchor} loose cards"
            with ingest.open_ingest_event("import-block", label=label, conn=c) as rec:
                adds_event = rec.ingest_id
                for ln in p.adds:
                    inventory.inventory_add(ln.scryfall_id, ln.finish, ln.change,
                                            conn=c, ingest_id=rec.ingest_id)
                    # inventory_add already appended the ledger delta; only tally.
                    if ln.owned == 0:
                        rec.rows_added += 1
                    else:
                        rec.rows_updated += 1
                    touched.add((ln.scryfall_id, ln.finish))
        if p.removals:
            label = f"census:{p.anchor} over-count removal"
            with ingest.open_ingest_event("adhoc", label=label, conn=c) as rec:
                removals_event = rec.ingest_id
                for ln in p.removals:
                    inventory.inventory_remove(ln.scryfall_id, ln.finish, ln.change,
                                               conn=c, ingest_id=rec.ingest_id)
                    if ln.owned - ln.change == 0:
                        rec.rows_zeroed += 1
                    else:
                        rec.rows_updated += 1
                    touched.add((ln.scryfall_id, ln.finish))

        after = _build(sheet, products, needs, c)
        if after.adds or after.removals:
            raise RuntimeError(
                f"census apply did not converge: {len(after.adds)} add(s) and "
                f"{len(after.removals)} removal(s) remain"
            )
        drift = [d for d in ingest.reconcile_inventory_ledger(c)
                 if (d["scryfall_id"], d["finish"]) in touched]
        if drift:
            raise RuntimeError(f"inventory and ledger disagree after census apply: {drift[:5]}")
        return {
            "adds_event": adds_event,
            "removals_event": removals_event,
            "added_copies": sum(ln.change for ln in p.adds),
            "removed_copies": sum(ln.change for ln in p.removals),
        }

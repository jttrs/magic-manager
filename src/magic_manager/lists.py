"""Labeled lists: CRUD, import (text + XLSX), and the selector evaluator.

A "list" is just a label + rows of (scryfall_id, finish, quantity). Conventional
label prefixes — ``set:``, ``wishlist:``, ``deck:``, ``idea:``, ``buy:`` — carry
no enforced semantics; they're how the user organizes things, and ``export-list``
can pull "every row tagged label:X".
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import db, parsers, scryfall, sets as sets_mod


# ---------- list CRUD ----------

@dataclass
class ListRow:
    scryfall_id: str
    finish: str
    quantity: int
    name: str
    set_code: str
    collector_number: str
    rarity: str
    prices_usd: float | None
    prices_usd_foil: float | None
    cmc: float | None
    flavor_name: str | None = None

    @property
    def unit_price(self) -> float | None:
        return self.prices_usd_foil if self.finish == "foil" else self.prices_usd

    @property
    def line_value(self) -> float | None:
        p = self.unit_price
        return p * self.quantity if p is not None else None

    @property
    def display_name(self) -> str:
        """Render as ``<flavor_name> / <oracle_name>`` for reskin printings,
        otherwise just the oracle name. Matches the convention used by the
        master-list XLSX writer (sets.py:369) so users see consistent names
        across `mm list show`, intake REPL feedback, and inventory checklists.
        """
        return f"{self.flavor_name} / {self.name}" if self.flavor_name else self.name


def list_show(label: str) -> list[ListRow]:
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT lr.scryfall_id, lr.finish, lr.quantity,
                   c.name, c.set_code, c.collector_number, c.rarity,
                   c.prices_usd, c.prices_usd_foil, c.cmc, c.flavor_name
            FROM list_rows lr
            JOIN cards c ON c.scryfall_id = lr.scryfall_id
            WHERE lr.label = ?
            ORDER BY c.set_code, c.collector_number, lr.finish
            """,
            (label,),
        ).fetchall()
    return [ListRow(**dict(r)) for r in rows]


def list_value(label: str) -> dict:
    rows = list_show(label)
    total = 0.0
    missing_price = []
    for r in rows:
        if r.line_value is None and r.quantity > 0:
            # Use display_name so reskin printings show as "<flavor> / <oracle>".
            missing_price.append((r.display_name, r.set_code, r.collector_number, r.finish))
        else:
            total += r.line_value or 0.0
    return {"total": total, "rows": len(rows), "missing_price": missing_price}


def summarize_label(label: str, *, top_n: int = 5) -> dict:
    """Snapshot of a list for the collision readout.

    Returns ``{"distinct_rows": N, "total_qty": N, "total_value": $X.XX,
    "top_value": [ListRow, ...]}`` covering only rows with quantity > 0.
    """
    rows = [r for r in list_show(label) if r.quantity > 0]
    rows_by_value = sorted(
        rows, key=lambda r: (r.line_value or 0.0), reverse=True,
    )
    return {
        "distinct_rows": len(rows),
        "total_qty": sum(r.quantity for r in rows),
        "total_value": sum((r.line_value or 0.0) for r in rows),
        "top_value": rows_by_value[:top_n],
    }


def list_delete(label: str) -> int:
    with db.connect() as conn:
        n = conn.execute("DELETE FROM lists WHERE label = ?", (label,)).rowcount
    return n


def all_lists() -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT l.label, l.kind, l.source, l.created_at, l.updated_at,
                   COALESCE(SUM(lr.quantity), 0) AS total_qty,
                   COUNT(lr.scryfall_id) AS distinct_rows
            FROM lists l
            LEFT JOIN list_rows lr ON lr.label = l.label
            GROUP BY l.label
            ORDER BY l.label
            """
        ).fetchall()
    return [dict(r) for r in rows]


# ---------- import (text or XLSX → list) ----------

def list_import(label: str, *, text: str | None = None, path: Path | None = None,
                kind: str | None = None, mode: str = "replace") -> dict:
    """Parse a text block or an XLSX file and upsert into the labeled list.

    For ``set:*`` labels:

    - **replace mode** (default): every (card, finish) cell present in the
      input becomes the new DB qty for that row. Cells *inside the partition*
      that are missing from the input are zeroed out. Cells outside the
      partition are never touched. The partition is the union of (set_code,
      rarity) pairs the input file actually covers — derived from the XLSX
      ``_meta`` sheet when present, or inferred from the rows otherwise.
    - **additive mode**: every cell with qty>0 in the input adds to the
      existing DB qty for that row. Cells with 0/blank are no-ops. Out-of-
      partition cells are never touched. Useful for booster-by-booster intake.

    For non-``set:`` labels, ``mode`` is ignored and the historical "insert or
    sum" behavior is preserved.

    Returns ``{"updated": N, "added": M, "zeroed": N, "warnings": [...],
    "not_found": [...], "extras": [...]}``.
    """
    if (text is None) == (path is None):
        raise ValueError("provide exactly one of text= or path=")
    if mode not in ("replace", "additive"):
        raise ValueError(f"unknown mode {mode!r}; expected 'replace' or 'additive'")

    if path is not None:
        fmt = parsers.detect_format(path)
        if fmt == "xlsx":
            result = parsers.parse_master_list_xlsx(path)
        elif fmt == "md":
            result = parsers.parse_master_list_md(path)
        else:
            result = parsers.parse_text(path.read_text(encoding="utf-8"))
    else:
        result = parsers.parse_text(text)

    parsers.resolve(result)

    is_set_label = label.startswith("set:")
    inferred_kind = kind or _kind_from_label(label)
    added = 0
    updated = 0
    zeroed = 0
    extras: list[dict] = []

    with db.connect() as conn:
        # Ensure the list row exists (idempotent).
        db.upsert_list(conn, label, kind=inferred_kind, source="imported")

        if is_set_label:
            # Build the partition descriptor: which (set_code, rarity) pairs
            # are in scope. Prefer _meta; fall back to row-derivation.
            partition = _derive_partition(result, conn, label)
            seen_keys: set[tuple[str, str]] = set()  # (scryfall_id, finish) we touched

            for entry in result.entries:
                if entry.card is None:
                    continue
                db.upsert_card(conn, entry.card)
                scry_id = entry.card["id"]
                finish = "foil" if entry.foil else "nonfoil"

                # Verify the card is in the seeded set list (i.e. we know
                # about this printing).
                row = conn.execute(
                    "SELECT quantity FROM list_rows WHERE label = ? AND scryfall_id = ? AND finish = ?",
                    (label, scry_id, finish),
                ).fetchone()
                if row is None:
                    extras.append({
                        "raw": entry.raw,
                        "reason": (
                            f"card {entry.card['name']} ({entry.card['set']}) "
                            f"{entry.card['collector_number']} is not in {label}; "
                            "run `mm set master-list` for the relevant set first"
                        ),
                    })
                    continue

                seen_keys.add((scry_id, finish))
                current_qty = row["quantity"]

                if mode == "replace":
                    new_qty = entry.qty
                else:  # additive
                    if entry.qty <= 0:
                        continue  # no-op for blank/zero cells in additive mode
                    new_qty = current_qty + entry.qty

                if new_qty == current_qty:
                    continue
                if new_qty == 0:
                    conn.execute(
                        "UPDATE list_rows SET quantity = 0 WHERE label = ? AND scryfall_id = ? AND finish = ?",
                        (label, scry_id, finish),
                    )
                    if current_qty > 0:
                        zeroed += 1
                else:
                    conn.execute(
                        "UPDATE list_rows SET quantity = ? WHERE label = ? AND scryfall_id = ? AND finish = ?",
                        (new_qty, label, scry_id, finish),
                    )
                    updated += 1

            # Replace mode only: zero out in-partition rows not seen in the
            # input. Additive mode never zeroes out anything implicitly.
            if mode == "replace" and partition is not None:
                in_partition_rows = _list_in_partition_rows(conn, label, partition)
                for r in in_partition_rows:
                    key = (r["scryfall_id"], r["finish"])
                    if key in seen_keys:
                        continue
                    if r["quantity"] == 0:
                        continue  # already zero, no-op
                    conn.execute(
                        "UPDATE list_rows SET quantity = 0 "
                        "WHERE label = ? AND scryfall_id = ? AND finish = ?",
                        (label, r["scryfall_id"], r["finish"]),
                    )
                    zeroed += 1
        else:
            # Free-form list: insert or sum (mode is ignored for these).
            for entry in result.entries:
                if entry.card is None:
                    continue
                db.upsert_card(conn, entry.card)
                scry_id = entry.card["id"]
                finish = "foil" if entry.foil else "nonfoil"
                existing = conn.execute(
                    "SELECT quantity FROM list_rows WHERE label = ? AND scryfall_id = ? AND finish = ?",
                    (label, scry_id, finish),
                ).fetchone()
                if existing:
                    new_q = existing["quantity"] + entry.qty
                    conn.execute(
                        "UPDATE list_rows SET quantity = ? WHERE label = ? AND scryfall_id = ? AND finish = ?",
                        (new_q, label, scry_id, finish),
                    )
                    updated += 1
                else:
                    conn.execute(
                        "INSERT INTO list_rows (label, scryfall_id, finish, quantity) VALUES (?, ?, ?, ?)",
                        (label, scry_id, finish, entry.qty),
                    )
                    added += 1

        db.record_import(conn,
                         command=f"list_import {label} mode={mode}",
                         source_path=str(path) if path else None,
                         rows_changed=added + updated + zeroed)

    return {
        "label": label,
        "mode": mode,
        "added": added,
        "updated": updated,
        "zeroed": zeroed,
        "warnings": result.warnings,
        "not_found": result.not_found,
        "extras": extras,
    }


@dataclass
class Partition:
    """The (set_code, rarity) scope a master-list XLSX claims to cover.

    ``rarities`` is None if the file has no rarity restriction (e.g. a full
    master list). ``set_codes`` is always non-empty.
    """
    set_codes: list[str]
    rarities: list[str] | None


def _derive_partition(result: parsers.ParseResult, conn, label: str) -> Partition | None:
    """Return the partition the input file claims to cover.

    Priority:
    1. ``_meta`` sheet on the XLSX (definitive).
    2. Inferred from the rows present in the file (fallback).
    3. ``None`` — the input has no rows at all.
    """
    meta = result.meta or {}
    if meta:
        codes = [c.strip().lower() for c in (meta.get("set_codes") or "").split(",") if c.strip()]
        rar = [r.strip().lower() for r in (meta.get("rarity_filter") or "").split(",") if r.strip()]
        if codes:
            return Partition(set_codes=codes, rarities=(rar or None))

    # Fallback: look at the cards parsed and derive scope from them.
    seen_codes: set[str] = set()
    seen_rarities: set[str] = set()
    for entry in result.entries:
        if entry.card:
            seen_codes.add((entry.card.get("set") or "").lower())
            r = (entry.card.get("rarity") or "").lower()
            if r:
                seen_rarities.add(r)
    if not seen_codes:
        return None
    return Partition(
        set_codes=sorted(seen_codes),
        # If we saw multiple rarities, treat as no-rarity-filter (safer).
        rarities=sorted(seen_rarities) if len(seen_rarities) == 1 else None,
    )


def _list_in_partition_rows(conn, label: str, partition: Partition) -> list:
    """Return list_rows for ``label`` that fall inside ``partition``."""
    set_placeholders = ",".join("?" for _ in partition.set_codes)
    args: list = list(partition.set_codes)
    rarity_clause = ""
    if partition.rarities:
        rarity_placeholders = ",".join("?" for _ in partition.rarities)
        rarity_clause = f" AND LOWER(c.rarity) IN ({rarity_placeholders})"
        args.extend(partition.rarities)
    args.insert(0, label)
    return conn.execute(
        f"""
        SELECT lr.scryfall_id, lr.finish, lr.quantity
        FROM list_rows lr
        JOIN cards c ON c.scryfall_id = lr.scryfall_id
        WHERE lr.label = ?
          AND LOWER(c.set_code) IN ({set_placeholders})
          {rarity_clause}
        """,
        args,
    ).fetchall()


def summarize_xlsx_file(path: Path) -> dict:
    """Pre-ingest preview for the slash command.

    Despite the function name, this handles both XLSX and markdown intake
    docs — dispatch is based on ``parsers.detect_format``. The name stays
    for backwards compatibility; use ``summarize_intake_file`` in new code.

    Returns a dict with: ``path``, ``meta`` (or ``None``), ``anchor_code``,
    ``set_codes``, ``rarity_filter``, ``rows_total``, ``rows_with_qty``,
    ``total_qty``, ``estimated_value``, ``top_value`` (top 5 rows by line value),
    ``warnings`` (parser warnings).

    Doesn't hit the network beyond what the parser already does (the
    rate-limited /cards/collection lookup for resolution).
    """
    fmt = parsers.detect_format(path)
    if fmt == "md":
        result = parsers.parse_master_list_md(path)
    else:
        result = parsers.parse_master_list_xlsx(path)
    parsers.resolve(result)
    meta = result.meta
    rows_with_qty = 0
    total_qty = 0
    estimated_value = 0.0
    rows_for_top: list[tuple[float, dict]] = []
    for e in result.entries:
        if not e.card or e.qty <= 0:
            continue
        rows_with_qty += 1
        total_qty += e.qty
        prices = e.card.get("prices") or {}
        unit_str = prices.get("usd_foil") if e.foil else prices.get("usd")
        try:
            unit = float(unit_str) if unit_str is not None else None
        except (TypeError, ValueError):
            unit = None
        line_value = (unit or 0.0) * e.qty
        if unit is not None:
            estimated_value += line_value
        # Render top-value display name with the merged "<flavor>/<oracle>"
        # form when the printing has a flavor_name (matches list_show display).
        oracle_name = e.card.get("name") or ""
        flavor_name = e.card.get("flavor_name") or (
            ((e.card.get("card_faces") or [{}])[0] or {}).get("flavor_name")
        )
        display_name = f"{flavor_name} / {oracle_name}" if flavor_name else oracle_name
        rows_for_top.append((line_value, {
            "qty": e.qty,
            "name": display_name,
            "set": (e.card.get("set") or "").lower(),
            "collector_number": e.card.get("collector_number"),
            "finish": "foil" if e.foil else "nonfoil",
            "unit_usd": unit,
            "line_value": line_value if unit is not None else None,
        }))
    rows_for_top.sort(key=lambda x: x[0], reverse=True)
    top_value = [r[1] for r in rows_for_top[:5]]
    anchor = (meta or {}).get("anchor_code") or ""
    set_codes = (meta or {}).get("set_codes") or ""
    rarity_filter = (meta or {}).get("rarity_filter") or ""
    return {
        "path": str(path),
        "meta": meta,
        "anchor_code": anchor,
        "set_codes": [c for c in set_codes.split(",") if c],
        "rarity_filter": [r for r in rarity_filter.split(",") if r],
        "rows_total": len(result.entries),
        "rows_with_qty": rows_with_qty,
        "total_qty": total_qty,
        "estimated_value": estimated_value,
        "top_value": top_value,
        "warnings": result.warnings,
    }


# Forward-compatible alias — new code should call this.
summarize_intake_file = summarize_xlsx_file


def _kind_from_label(label: str) -> str:
    prefix = label.split(":", 1)[0] if ":" in label else "other"
    if prefix in ("set", "wishlist", "deck", "idea", "buy"):
        return prefix
    return "other"


# ---------- selector → (card, qty, finish) materialization ----------

@dataclass
class MaterializedRow:
    scryfall_id: str
    quantity: int
    finish: str  # "nonfoil" | "foil"
    card: dict   # full row from cards table, normalized to dict


SELECTOR_RE = re.compile(
    r"""
    ^\s*
    (?P<kind>label|set|scryfall)
    :
    (?P<arg>[^\s].*?)
    \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)


def materialize(selector: str) -> list[MaterializedRow]:
    """Evaluate a selector string and return materialized rows.

    Supported forms:
      label:<label>
      set:<code>[+related]
      set:<code>[+related] missing[:normal|foil|both]
      scryfall:<query>          (every printing matching the query, qty=1, nonfoil)
    """
    s = selector.strip()

    # set: forms (potentially with "missing"/treatment modifiers)
    m = re.match(r"^\s*set:([a-z0-9]+)(\+related)?(\s+.+)?\s*$", s, re.IGNORECASE)
    if m:
        return _materialize_set(m.group(1).lower(), bool(m.group(2)),
                                (m.group(3) or "").strip())

    m = re.match(r"^\s*label:(.+)$", s, re.IGNORECASE)
    if m:
        return _materialize_label(m.group(1).strip())

    m = re.match(r"^\s*scryfall:(.+)$", s, re.IGNORECASE)
    if m:
        return _materialize_scryfall(m.group(1).strip())

    raise ValueError(f"unrecognized selector: {selector!r}")


def _materialize_label(label: str) -> list[MaterializedRow]:
    out: list[MaterializedRow] = []
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT lr.scryfall_id, lr.finish, lr.quantity,
                   c.scryfall_id AS card_id, c.name, c.set_code, c.collector_number,
                   c.rarity, c.prices_usd, c.prices_usd_foil, c.cmc, c.frame_effects,
                   c.colors, c.color_identity, c.type_line, c.mana_cost, c.is_promo, c.is_token
            FROM list_rows lr
            JOIN cards c ON c.scryfall_id = lr.scryfall_id
            WHERE lr.label = ? AND lr.quantity > 0
            ORDER BY c.set_code, c.collector_number, lr.finish
            """,
            (label,),
        ).fetchall()
    for r in rows:
        out.append(MaterializedRow(
            scryfall_id=r["scryfall_id"], quantity=r["quantity"], finish=r["finish"],
            card=_card_dict(r),
        ))
    return out


def _materialize_set(code: str, include_related: bool, modifier: str) -> list[MaterializedRow]:
    codes = [code]
    if include_related:
        try:
            resolved = sets_mod.resolve(code)
            codes = resolved.all_codes
        except LookupError:
            # fall back to just the code
            pass

    placeholders = ",".join("?" for _ in codes)
    with db.connect() as conn:
        cards = conn.execute(
            f"""
            SELECT scryfall_id, name, set_code, collector_number, rarity,
                   prices_usd, prices_usd_foil, cmc, frame_effects,
                   colors, color_identity, type_line, mana_cost, is_promo, is_token, finishes
            FROM cards
            WHERE set_code IN ({placeholders})
            ORDER BY set_code, collector_number
            """,
            codes,
        ).fetchall()
        # Pull the corresponding set:* list rows so we know what's owned.
        labels = [f"set:{c}" for c in codes]
        owned_rows = conn.execute(
            f"""
            SELECT scryfall_id, finish, quantity
            FROM list_rows
            WHERE label IN ({",".join("?" for _ in labels)})
            """,
            labels,
        ).fetchall()

    owned: dict[tuple[str, str], int] = {}
    for r in owned_rows:
        owned[(r["scryfall_id"], r["finish"])] = r["quantity"]

    # Parse modifier.
    missing_mode = None
    treatment_filter = None
    if modifier:
        for tok in modifier.split():
            if tok.lower().startswith("missing"):
                _, _, side = tok.partition(":")
                missing_mode = (side or "normal").lower()
                if missing_mode not in ("normal", "foil", "both"):
                    raise ValueError(f"missing modifier must be normal|foil|both, got {side!r}")
            elif tok.lower().startswith("frame:"):
                treatment_filter = tok.split(":", 1)[1].lower()

    out: list[MaterializedRow] = []
    for c in cards:
        if treatment_filter:
            fx = json.loads(c["frame_effects"] or "[]")
            # treatment_filter == "borderless" matches via type_line / frame data
            # heuristic: borderless lives in frame_effects on most cards,
            # but Scryfall sometimes encodes via card_faces; this filters known cases.
            # We accept borderless if frame_effects contains "borderless" OR
            # the rarity == "bonus"/"special" with the keyword in the name.
            if treatment_filter not in fx:
                continue
        finishes = json.loads(c["finishes"] or "[]") or ["nonfoil"]
        for fin in finishes:
            if fin not in ("nonfoil", "foil"):
                continue
            have = owned.get((c["scryfall_id"], fin), 0)
            if missing_mode is None:
                # No "missing" modifier: emit every printing at qty=1
                out.append(MaterializedRow(c["scryfall_id"], 1, fin, _card_dict(c)))
            else:
                want_normal = missing_mode in ("normal", "both") and fin == "nonfoil"
                want_foil = missing_mode in ("foil", "both") and fin == "foil"
                if (want_normal or want_foil) and have < 1:
                    out.append(MaterializedRow(c["scryfall_id"], 1, fin, _card_dict(c)))
    return out


def _materialize_scryfall(query: str) -> list[MaterializedRow]:
    out: list[MaterializedRow] = []
    with db.connect() as conn:
        for card in scryfall.search(query, unique="prints"):
            db.upsert_card(conn, card)
            out.append(MaterializedRow(
                scryfall_id=card["id"], quantity=1, finish="nonfoil",
                card=_card_dict_from_scryfall(card),
            ))
    return out


def _card_dict(row: sqlite3.Row) -> dict:
    """Normalize a sqlite Row from the cards table into a plain dict."""
    return {
        "scryfall_id":      row["scryfall_id"] if "scryfall_id" in row.keys() else row["card_id"],
        "name":             row["name"],
        "set":              row["set_code"],
        "collector_number": row["collector_number"],
        "rarity":           row["rarity"],
        "prices_usd":       row["prices_usd"],
        "prices_usd_foil":  row["prices_usd_foil"],
        "cmc":              row["cmc"],
        "type_line":        row["type_line"] if "type_line" in row.keys() else None,
        "mana_cost":        row["mana_cost"] if "mana_cost" in row.keys() else None,
    }


def _card_dict_from_scryfall(c: dict) -> dict:
    return {
        "scryfall_id":      c.get("id"),
        "name":             c.get("name"),
        "set":              (c.get("set") or "").lower(),
        "collector_number": c.get("collector_number"),
        "rarity":           c.get("rarity"),
        "prices_usd":       _f(c.get("prices", {}).get("usd")),
        "prices_usd_foil":  _f(c.get("prices", {}).get("usd_foil")),
        "cmc":              c.get("cmc"),
        "type_line":        c.get("type_line"),
        "mana_cost":        c.get("mana_cost"),
    }


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None

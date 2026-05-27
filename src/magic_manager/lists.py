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

    @property
    def unit_price(self) -> float | None:
        return self.prices_usd_foil if self.finish == "foil" else self.prices_usd

    @property
    def line_value(self) -> float | None:
        p = self.unit_price
        return p * self.quantity if p is not None else None


def list_show(label: str) -> list[ListRow]:
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT lr.scryfall_id, lr.finish, lr.quantity,
                   c.name, c.set_code, c.collector_number, c.rarity,
                   c.prices_usd, c.prices_usd_foil, c.cmc
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
            missing_price.append((r.name, r.set_code, r.collector_number, r.finish))
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
                kind: str | None = None) -> dict:
    """Parse a text block or an XLSX file and upsert into the labeled list.

    For ``set:*`` labels, the import only updates rows that are already seeded
    in the list (use ``mm set master-list`` first to create the universe);
    extras get a warning. For other labels, every parsed entry becomes a row.

    Returns ``{"updated": N, "added": M, "warnings": [...], "not_found": [...]}``.
    """
    if (text is None) == (path is None):
        raise ValueError("provide exactly one of text= or path=")

    if path is not None:
        fmt = parsers.detect_format(path)
        if fmt == "xlsx":
            result = parsers.parse_master_list_xlsx(path)
        else:
            result = parsers.parse_text(path.read_text(encoding="utf-8"))
    else:
        result = parsers.parse_text(text)

    parsers.resolve(result)

    is_set_label = label.startswith("set:")
    inferred_kind = kind or _kind_from_label(label)
    added = 0
    updated = 0
    extras: list[dict] = []

    with db.connect() as conn:
        # Ensure the list row exists (idempotent).
        db.upsert_list(conn, label, kind=inferred_kind, source="imported")

        for entry in result.entries:
            if entry.card is None:
                continue
            # Make sure the resolved card is in our local cache before inserting
            # a list_row that references it (FK constraint).
            db.upsert_card(conn, entry.card)
            scry_id = entry.card["id"]
            finish = "foil" if entry.foil else "nonfoil"

            if is_set_label:
                # Only update; never insert new rows.
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
                conn.execute(
                    "UPDATE list_rows SET quantity = ? WHERE label = ? AND scryfall_id = ? AND finish = ?",
                    (entry.qty, label, scry_id, finish),
                )
                updated += 1
            else:
                # Free-form list: insert or sum.
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
                         command=f"list_import {label}",
                         source_path=str(path) if path else None,
                         rows_changed=added + updated)

    return {
        "label": label,
        "added": added,
        "updated": updated,
        "warnings": result.warnings,
        "not_found": result.not_found,
        "extras": extras,
    }


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

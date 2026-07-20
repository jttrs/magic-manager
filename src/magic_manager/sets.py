"""Set resolution, syncing, and the fillable master-list XLSX builder.

A "set" in Magic isn't always one Scryfall set code. "Final Fantasy" is the
parent expansion ``fin`` plus 8 sibling/child sets (commander, masterpiece,
promos, art series, etc.). The resolver returns the parent + every set whose
``parent_set_code`` traces back to it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import db, scryfall


RARITY_ORDER = {
    "mythic":   0,
    "rare":     1,
    "uncommon": 2,
    "common":   3,
    "bonus":    4,
    "special":  5,
}


# Set types that count as "things players actively collect" for the default
# inventory bundle. Tokens and memorabilia (art series, scene boxes) are off
# by default; explicitly opt them in via include_kinds.
DEFAULT_INVENTORY_SET_TYPES = frozenset({"expansion", "commander", "masterpiece", "promo"})


# Per V1.5 user direction: prerelease promos, store-stamped promos,
# japanshowcase variants, serialized cards, and weird-border variants are
# excluded from default master-list output so the user only sees printings
# they actually catalog. Toggled by --include-variants on master-list.
EXCLUDED_BORDERS = frozenset({"white", "yellow"})
EXCLUDED_PROMO_TYPES = frozenset({
    "prerelease", "datestamped", "stamped", "promopack",
    "japanshowcase", "serialized",
    # Arena/Alchemy rebalanced cards exist only as digital re-tunings — they
    # have no physical counterpart, no foil finish, no secondary-market price,
    # and a literal "arena" security_stamp. Always filtered from physical
    # collection workflows. Mirrors selectors.DIGITAL_ONLY_PROMO_TYPES on the
    # missing-set side; both signals are universal across MTG (not set-specific).
    "rebalanced", "alchemy",
})


def is_excluded_variant(card_row) -> bool:
    """Return True if a card row should be filtered from default master-list
    output. Operates on either a sqlite Row or a Scryfall API dict.

    The filter intentionally errs on the side of exclusion — if a card has
    ANY of the excluded promo_types or borders, it's out. The user-facing
    effect is "the master list shows the printings I'd want to catalog,
    nothing else."
    """
    bc = card_row["border_color"] if hasattr(card_row, "keys") else card_row.get("border_color")
    if bc and str(bc).lower() in EXCLUDED_BORDERS:
        return True
    raw_pt = card_row["promo_types"] if hasattr(card_row, "keys") else card_row.get("promo_types")
    if raw_pt is None:
        return False
    # promo_types is a JSON-encoded list in our DB rows but a real list in
    # the Scryfall response — handle both.
    if isinstance(raw_pt, str):
        import json as _json
        try:
            pts = _json.loads(raw_pt)
        except _json.JSONDecodeError:
            return False
    else:
        pts = raw_pt
    return any(p in EXCLUDED_PROMO_TYPES for p in (pts or []))


@dataclass
class ResolvedSet:
    code: str           # anchor set code, e.g. "fin"
    name: str           # display name, e.g. "Final Fantasy"
    related: list[dict] # all sets in the family, anchor first

    @property
    def all_codes(self) -> list[str]:
        return [s["code"] for s in self.related]

    def filtered_codes(self, *, include_kinds: Iterable[str] = ()) -> list[str]:
        """Codes in the family whose ``set_type`` is in the default inventory
        bundle (expansion / commander / masterpiece / promo), expanded by
        ``include_kinds`` (e.g. ``{"token", "memorabilia"}``).

        The anchor is always included regardless — naming a token set
        explicitly should still produce that set in the output.
        """
        allowed = set(DEFAULT_INVENTORY_SET_TYPES) | set(include_kinds)
        out: list[str] = []
        for s in self.related:
            if s["code"] == self.code or s.get("set_type") in allowed:
                out.append(s["code"])
        return out

    @property
    def filtered_related(self) -> list[dict]:
        codes = set(self.filtered_codes())
        return [s for s in self.related if s["code"] in codes]


# ---------- name resolution ----------

def resolve(name_or_code: str) -> ResolvedSet:
    """Resolve to a specific Scryfall set (the "anchor") plus everything in
    its family tree.

    If the user names a specific child set ("Final Fantasy: Through the Ages"
    or ``fca``), the anchor is that set — ``--include-related`` then expands
    to the parent + all siblings. If they name a parent ("Final Fantasy" or
    ``fin``), the anchor is the parent.
    """
    needle = name_or_code.strip().lower()
    all_sets = scryfall.all_sets()
    by_code = {s["code"].lower(): s for s in all_sets}

    if needle in by_code:
        anchor = by_code[needle]
    else:
        candidates = [s for s in all_sets if s["name"].lower() == needle]
        if not candidates:
            candidates = [s for s in all_sets if needle in s["name"].lower()]
        if not candidates:
            raise LookupError(f"no Scryfall set matches {name_or_code!r}")
        # Prefer parents when there's ambiguity, otherwise take the first hit.
        parents = [s for s in candidates if not s.get("parent_set_code")]
        anchor = parents[0] if parents else candidates[0]

    # The "family" is the parent + every set whose ancestry chains back to it.
    parent = _walk_to_parent(by_code, anchor)
    related = [parent] + _descendants_of(all_sets, parent["code"])
    # Move the anchor to the front so callers/UIs can show it first.
    related = [anchor] + [s for s in related if s["code"] != anchor["code"]]
    return ResolvedSet(code=anchor["code"], name=anchor["name"], related=related)


def _walk_to_parent(by_code: dict, start: dict) -> dict:
    cur = start
    while cur.get("parent_set_code"):
        nxt = by_code.get(cur["parent_set_code"])
        if not nxt or nxt["code"] == cur["code"]:
            break
        cur = nxt
    return cur


def _descendants_of(all_sets: list[dict], parent_code: str) -> list[dict]:
    """All sets whose parent_set_code chains back to ``parent_code``."""
    by_code = {s["code"]: s for s in all_sets}
    out: list[dict] = []
    for s in all_sets:
        if s["code"] == parent_code:
            continue
        cur = s
        while cur.get("parent_set_code"):
            if cur["parent_set_code"] == parent_code:
                out.append(s)
                break
            cur = by_code.get(cur["parent_set_code"])
            if not cur:
                break
    return out


# ---------- syncing ----------

def sync(set_codes: Iterable[str]) -> int:
    """Pull every printing in ``set_codes`` into the cards table. Returns rows synced.

    English-only: sets that ship only in non-English (e.g. ``rfin`` regional
    promos which are JP-only) will simply have zero rows imported. The user
    catalogs English copies; non-English-only prints don't belong in the checklist.
    """
    codes = [c.lower() for c in set_codes]
    if not codes:
        return 0
    # Build a single search query using `or` so we paginate once. ``lang:en``
    # filters out the Japanese-only rfin J1/J2 prints (and any future non-English
    # variants Scryfall adds to a release).
    query = "(" + " or ".join(f"e:{c}" for c in codes) + ") lang:en"
    n = 0
    with db.connect() as conn:
        for card in scryfall.search(query, unique="prints"):
            db.upsert_card(conn, card)
            n += 1
    return n


# ---------- master-list seeding + XLSX emit ----------

def register_set_target(anchor_code: str, related_codes: Iterable[str], *,
                        include_variants: bool = False,
                        rarity_filter: Iterable[str] | None = None) -> dict:
    """Insert (or update) a set_targets row recording user intent to track a set.

    The set's universe of printings lives in the cards table — set_targets
    just records "I'm tracking this anchor + family" for `set:CODE missing`
    queries. Replaces V1's seed-rows-at-qty-0 pattern.

    Returns ``{"action": "inserted"|"updated", "anchor_code": str,
    "related_codes": list[str]}``.
    """
    import json as _json
    anchor = anchor_code.lower()
    codes = sorted({c.lower() for c in related_codes})
    if not codes:
        codes = [anchor]
    rarities = sorted({r.lower() for r in (rarity_filter or []) if r}) or None
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.connect() as conn:
        existing = conn.execute(
            "SELECT 1 FROM set_targets WHERE anchor_code = ?", (anchor,)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE set_targets
                SET related_codes = ?, include_variants = ?, rarity_filter = ?, updated_at = ?
                WHERE anchor_code = ?
                """,
                (_json.dumps(codes), 1 if include_variants else 0,
                 _json.dumps(rarities) if rarities else None, now, anchor),
            )
            action = "updated"
        else:
            conn.execute(
                """
                INSERT INTO set_targets
                  (anchor_code, related_codes, include_variants, rarity_filter, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (anchor, _json.dumps(codes), 1 if include_variants else 0,
                 _json.dumps(rarities) if rarities else None, now, now),
            )
            action = "inserted"
    return {"action": action, "anchor_code": anchor, "related_codes": codes}


def write_master_list_xlsx(set_codes: Iterable[str], out_path: Path,
                           include_tokens: bool = False,
                           prepopulate_from_inventory: bool = True,
                           rarity_filter: Iterable[str] | None = None,
                           anchor_code: str | None = None,
                           slug: str | None = None,
                           include_variants: bool = False,
                           mode: str = "add") -> tuple[int, int]:
    """Emit a fillable XLSX of every printing in ``set_codes``.

    When ``prepopulate_from_inventory`` is True (default), qty cells are
    pre-filled from the ``inventory`` table for printings the user already
    owns, so resuming after an ingest doesn't lose visible progress.

    When ``rarity_filter`` is given (case-insensitive iterable of rarities),
    only printings with one of those rarities are emitted.

    A hidden ``_meta`` sheet is always written so ingest can recover scope
    later: ``anchor_code``, ``set_codes``, ``rarity_filter``, ``slug``,
    ``generated_at``, ``magic_manager_version``.

    Returns ``(rows_written, cells_prefilled)``.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    from . import __version__

    codes = [c.lower() for c in set_codes]
    if not codes:
        raise ValueError("no set codes provided")

    rarity_set: set[str] | None = None
    if rarity_filter is not None:
        rarity_set = {r.lower() for r in rarity_filter if r and str(r).strip()}
        if not rarity_set:
            rarity_set = None  # treat empty list as "no filter"

    placeholders = ",".join("?" for _ in codes)
    with db.connect() as conn:
        rows = conn.execute(
            f"""
            SELECT scryfall_id, set_code, collector_number, name, flavor_name,
                   rarity, cmc, prices_usd, prices_usd_foil, is_token, scryfall_uri,
                   frame_effects, promo_types, border_color, full_art
            FROM cards
            WHERE set_code IN ({placeholders})
            ORDER BY 1, 2
            """,
            codes,
        ).fetchall()

        # (scryfall_id, finish) -> quantity (from inventory; only printings
        # in this set's family will actually be looked up by the loop below).
        prepop: dict[tuple[str, str], int] = {}
        if prepopulate_from_inventory:
            for r in conn.execute(
                "SELECT scryfall_id, finish, quantity FROM inventory"
            ).fetchall():
                prepop[(r["scryfall_id"], r["finish"])] = r["quantity"]

    if not include_tokens:
        rows = [r for r in rows if not r["is_token"]]
    if not include_variants:
        rows = [r for r in rows if not is_excluded_variant(r)]
    if rarity_set is not None:
        rows = [r for r in rows if (r["rarity"] or "").lower() in rarity_set]

    # Sort: set code asc, then collector_number asc (numeric where possible).
    # Inventory checklists are *input* tools — the user fills them in while
    # holding a physically-sorted pile of cards. Set+CN matches how MTG
    # players sort cards on their desk; rarity grouping (the old order) made
    # it harder to find any specific card. Output artifacts (missing-set,
    # query reports) still sort rarity-first because they're for *reading*.
    def cn_sortkey(cn: str) -> tuple:
        m = re.match(r"^(\d+)(.*)$", cn or "")
        if m:
            return (int(m.group(1)), m.group(2))
        return (10**9, cn or "")

    rows = sorted(
        rows,
        key=lambda r: (
            r["set_code"],
            cn_sortkey(r["collector_number"]),
        ),
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "checklist"

    # Column order is fixed; treatment is V1.5 between rarity and mana_value.
    # If columns shift, update parse_master_list_xlsx, the qty-tint indices,
    # and the widths dict below.
    headers = ["set", "collector_number", "name", "rarity", "treatment",
               "mana_value", "usd", "usd_foil", "qty_normal", "qty_foil"]
    ws.append(headers)
    for col, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="left")

    qty_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    int_validator = DataValidation(type="whole", operator="greaterThanOrEqual",
                                   formula1=0, allow_blank=True)
    int_validator.error = "Enter a non-negative integer (or leave blank for 0)."
    int_validator.errorTitle = "Invalid quantity"
    ws.add_data_validation(int_validator)

    cells_prefilled = 0
    # Hyperlink-styled font for the name cell — blue + underline mimics how
    # most apps render web links. The cell's value is unchanged (just the
    # displayed name); the hyperlink is a separate property openpyxl supports.
    link_font = Font(color="0563C1", underline="single")
    from .treatments import compute_treatment
    for r in rows:
        qn = prepop.get((r["scryfall_id"], "nonfoil"))
        qf = prepop.get((r["scryfall_id"], "foil"))
        if qn is not None:
            cells_prefilled += 1
        if qf is not None:
            cells_prefilled += 1
        # Render the displayed name as "<flavor_name> / <oracle_name>" when the
        # printing has a Universes Beyond reskin name (e.g. FCA Counterspell →
        # "Wild Rose Rebellion / Counterspell"); otherwise just the oracle name.
        # Round-trip-safe: parse_master_list_xlsx() keys on (set_code, cn).
        flavor = r["flavor_name"]
        display_name = f"{flavor} / {r['name']}" if flavor else r["name"]
        treatment = compute_treatment(r)
        ws.append([
            r["set_code"],
            r["collector_number"],
            display_name,
            r["rarity"],
            treatment,
            r["cmc"],
            r["prices_usd"],
            r["prices_usd_foil"],
            qn,
            qf,
        ])
        # Force collector_number to render as text. Many CNs are pure
        # digits ('4', '210') and Excel auto-coerces them to numbers,
        # then complains with the green-triangle "Number Stored as Text"
        # warning when other CNs in the same column have letter suffixes
        # (like '212s' or '551f'). Setting the cell's number_format to '@'
        # tells Excel "this is intentional text" and the warning disappears.
        cn_cell = ws.cell(row=ws.max_row, column=2)
        cn_cell.number_format = "@"
        # Attach a clickable hyperlink to the name cell, pointing at the card's
        # Scryfall page. Falls through silently if scryfall_uri is missing for
        # this row (older DB rows from V1.2 might not have one — re-sync fixes).
        uri = r["scryfall_uri"]
        if uri:
            name_cell = ws.cell(row=ws.max_row, column=3)
            name_cell.hyperlink = uri
            name_cell.font = link_font
    last_row = ws.max_row

    # Tint qty columns and apply integer validation. With treatment inserted
    # at column 5, qty_normal/qty_foil are now columns 9/10.
    for col_idx in (9, 10):
        col_letter = get_column_letter(col_idx)
        rng = f"{col_letter}2:{col_letter}{last_row}"
        int_validator.add(rng)
        for r in range(2, last_row + 1):
            ws.cell(row=r, column=col_idx).fill = qty_fill

    # Sensible widths. Column 5 is treatment — sized for "b|shw|ext|sm|ff"
    # worst case. Column 3 (name) holds long reskin pairs like
    # "Knights of San d'Oria / Ranger-Captain of Eos" so it gets generous
    # room.
    widths = {1: 6, 2: 8, 3: 48, 4: 10, 5: 14, 6: 6, 7: 9, 8: 9, 9: 11, 10: 9}
    for col_idx, w in widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = w

    # Format USD columns as currency with two decimals so prices line up
    # ($3.00 / $0.43 instead of $3.0 / $0.43).
    for col_idx in (7, 8):
        for row_idx in range(2, last_row + 1):
            ws.cell(row=row_idx, column=col_idx).number_format = '"$"#,##0.00'

    ws.freeze_panes = "A2"

    # Hidden _meta sheet: lets `mm set ingest` recover scope without trusting
    # the filename. Two columns (key, value) so the format stays human-readable
    # in case someone unhides the sheet for debugging.
    meta_ws = wb.create_sheet("_meta")
    meta_ws.sheet_state = "hidden"
    meta_ws.append(["key", "value"])
    meta_ws["A1"].font = Font(bold=True)
    meta_ws["B1"].font = Font(bold=True)

    rarity_value = ",".join(sorted(rarity_set)) if rarity_set else ""
    meta = {
        # `kind` distinguishes this artifact from `mm query missing-set`'s output
        # (which writes `kind: "missing"` to its own _meta sheet). Inventory
        # checklists round-trip through `mm set ingest`; missing checklists
        # never do. See feedback_checklist_artifacts memory for the full split.
        "kind": "inventory",
        # `mode` declares the intended ingest semantics — read by `mm set
        # ingest` and applied automatically. 'modify' → replace ingest
        # (in-partition cells overwrite, missing rows zero out); 'add' →
        # additive ingest (qty>0 cells sum into existing inventory). The
        # mode is also encoded in the filename slug for visibility on disk.
        "mode": mode,
        "anchor_code": (anchor_code or codes[0]).lower(),
        "set_codes": ",".join(codes),
        "rarity_filter": rarity_value,
        "slug": slug or out_path.stem,
        "include_tokens": "1" if include_tokens else "0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "magic_manager_version": __version__,
    }
    for k, v in meta.items():
        meta_ws.append([k, v])

    # Hidden _legend sheet: documents the treatment-column keyword space so
    # users can unhide it for reference without leaving the workbook.
    from .treatments import LEGEND
    legend_ws = wb.create_sheet("_legend")
    legend_ws.sheet_state = "hidden"
    legend_ws.append(["code", "meaning"])
    legend_ws["A1"].font = Font(bold=True)
    legend_ws["B1"].font = Font(bold=True)
    for code, meaning in LEGEND:
        legend_ws.append([code, meaning])
    legend_ws.column_dimensions["A"].width = 6
    legend_ws.column_dimensions["B"].width = 90

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return (last_row - 1, cells_prefilled)


def read_master_list_meta(path: Path) -> dict | None:
    """Read the ``_meta`` sheet (XLSX) or YAML frontmatter (MD) from a
    checklist file. Returns the dict of key/value strings, or ``None`` if no
    metadata is present.

    Works for both inventory checklists and Jumpstart checklists — the meta
    shape differs but the read is the same.
    """
    suffix = path.suffix.lower()
    if suffix == ".md":
        text = path.read_text(encoding="utf-8")
        if not (text.startswith("---\n") or text.startswith("---\r\n")):
            return None
        end = text.find("\n---\n", 4)
        if end == -1:
            end = text.find("\n---\r\n", 4)
        if end == -1:
            return None
        out: dict[str, str] = {}
        for line in text[4:end].splitlines():
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
        return out or None

    from openpyxl import load_workbook

    wb = load_workbook(filename=str(path), data_only=True)
    if "_meta" not in wb.sheetnames:
        return None
    ws = wb["_meta"]
    out: dict[str, str] = {}
    rows = ws.iter_rows(values_only=True)
    next(rows, None)  # skip header
    for row in rows:
        if not row or row[0] is None:
            continue
        key = str(row[0]).strip()
        val = "" if (len(row) < 2 or row[1] is None) else str(row[1]).strip()
        out[key] = val
    return out


# ---------- V2 inventory ingest ----------

def ingest_inventory_from_xlsx(path: Path, *, mode: str = "replace") -> dict:
    """Parse a filled-in master-list XLSX/MD and write qty cells to inventory.

    Partition-aware: in 'replace' mode, in-partition rows missing from the
    input are zeroed out (deleted from inventory); out-of-partition cells
    are never touched. In 'additive' mode, only cells with qty>0 add to
    existing inventory rows; nothing is zeroed.

    Partition is derived from the file's _meta sheet (definitive) or
    inferred from the rows present (fallback). Cards in the file that
    aren't in the partition's set codes are flagged as 'extras' (the user
    pasted unrelated cards into a set's checklist).

    Returns ``{"added": N, "updated": N, "zeroed": N, "warnings": [...],
    "not_found": [...], "extras": [...]}``.
    """
    from . import db, parsers
    if mode not in ("replace", "additive"):
        raise ValueError(f"unknown mode {mode!r}; expected 'replace' or 'additive'")

    fmt = parsers.detect_format(path)
    if fmt == "xlsx":
        result = parsers.parse_master_list_xlsx(path)
    elif fmt == "md":
        result = parsers.parse_master_list_md(path)
    else:
        result = parsers.parse_text(path.read_text(encoding="utf-8"))
    parsers.resolve(result)

    partition = _derive_inventory_partition(result)
    added = 0
    updated = 0
    zeroed = 0
    extras: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with db.connect() as conn:
        for entry in result.entries:
            if entry.card is None:
                continue
            db.upsert_card(conn, entry.card)
            scry_id = entry.card["id"]
            finish = "foil" if entry.foil else "nonfoil"
            card_set = (entry.card.get("set") or "").lower()

            # Out-of-partition cards are 'extras' (file tried to set qty for
            # a card outside the file's declared scope).
            if partition and card_set not in partition.set_codes:
                extras.append({
                    "raw": entry.raw,
                    "reason": (
                        f"card {entry.card['name']} ({card_set}) "
                        f"{entry.card.get('collector_number')} is outside the "
                        f"file's partition (set codes: {partition.set_codes})"
                    ),
                })
                continue

            seen_keys.add((scry_id, finish))

            row = conn.execute(
                "SELECT quantity FROM inventory WHERE scryfall_id = ? AND finish = ?",
                (scry_id, finish),
            ).fetchone()
            current_qty = row["quantity"] if row else 0

            if mode == "replace":
                new_qty = entry.qty
            else:
                if entry.qty <= 0:
                    continue
                new_qty = current_qty + entry.qty

            if new_qty == current_qty:
                continue
            if new_qty == 0:
                if current_qty > 0:
                    conn.execute(
                        "DELETE FROM inventory WHERE scryfall_id = ? AND finish = ?",
                        (scry_id, finish),
                    )
                    zeroed += 1
            elif row:
                conn.execute(
                    "UPDATE inventory SET quantity = ? WHERE scryfall_id = ? AND finish = ?",
                    (new_qty, scry_id, finish),
                )
                updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO inventory (scryfall_id, finish, quantity, acquired_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (scry_id, finish, new_qty, now),
                )
                added += 1

        # Replace mode: zero out in-partition inventory rows not seen.
        if mode == "replace" and partition is not None:
            in_partition_rows = conn.execute(
                f"""
                SELECT inv.scryfall_id, inv.finish, inv.quantity
                FROM inventory inv
                JOIN cards c ON c.scryfall_id = inv.scryfall_id
                WHERE LOWER(c.set_code) IN ({",".join("?" for _ in partition.set_codes)})
                """ + (
                    f" AND LOWER(c.rarity) IN ({','.join('?' for _ in partition.rarities)})"
                    if partition.rarities else ""
                ),
                partition.set_codes + (partition.rarities or []),
            ).fetchall()
            for r in in_partition_rows:
                key = (r["scryfall_id"], r["finish"])
                if key in seen_keys:
                    continue
                conn.execute(
                    "DELETE FROM inventory WHERE scryfall_id = ? AND finish = ?",
                    (r["scryfall_id"], r["finish"]),
                )
                zeroed += 1

        db.record_import(conn,
                         command=f"ingest_inventory_from_xlsx mode={mode}",
                         source_path=str(path),
                         rows_changed=added + updated + zeroed)

    return {
        "added": added,
        "updated": updated,
        "zeroed": zeroed,
        "warnings": result.warnings,
        "not_found": result.not_found,
        "extras": extras,
    }


@dataclass
class _InventoryPartition:
    set_codes: list[str]
    rarities: list[str] | None


def _derive_inventory_partition(result) -> "_InventoryPartition | None":
    """Same partition logic as lists._derive_partition but parameterized
    against the inventory table (no label scoping)."""
    meta = result.meta or {}
    if meta:
        codes = [c.strip().lower() for c in (meta.get("set_codes") or "").split(",") if c.strip()]
        rar = [r.strip().lower() for r in (meta.get("rarity_filter") or "").split(",") if r.strip()]
        if codes:
            return _InventoryPartition(set_codes=codes, rarities=(rar or None))

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
    return _InventoryPartition(
        set_codes=sorted(seen_codes),
        rarities=sorted(seen_rarities) if len(seen_rarities) == 1 else None,
    )


def summarize_intake_file(path: Path) -> dict:
    """Pre-ingest preview for the slash command. Handles both XLSX and md.

    Returns a dict with: ``path``, ``meta`` (or ``None``), ``anchor_code``,
    ``set_codes``, ``rarity_filter``, ``rows_total``, ``rows_with_qty``,
    ``total_qty``, ``estimated_value``, ``top_value`` (top 5 rows by line
    value), ``warnings`` (parser warnings).

    Doesn't hit the network beyond what the parser already does (the
    rate-limited /cards/collection lookup for resolution).
    """
    from . import parsers
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


# ---------- markdown intake format ----------

def write_master_list_md(set_codes: Iterable[str], out_path: Path,
                         include_tokens: bool = False,
                         prepopulate_from_inventory: bool = True,
                         rarity_filter: Iterable[str] | None = None,
                         anchor_code: str | None = None,
                         slug: str | None = None,
                         include_variants: bool = False,
                         mode: str = "add") -> tuple[int, int]:
    """Markdown twin of ``write_master_list_xlsx()``.

    File shape:

        ---
        anchor_code: fca
        set_codes: fin,fic,...
        rarity_filter: rare        # blank when no rarity slice
        slug: final-fantasy-...
        include_tokens: 0
        generated_at: 2026-...
        magic_manager_version: 0.1.0
        ---

        # <set name> — <slice description>

        ## Mythic (15 cards)

        - (FCA) 2 [N:0 F:0] — [<displayed name>](<scryfall_uri>) — $4.66 / $164.18
        - (FCA) 5 [N:0 F:0] — ...

    Returns ``(rows_written, cells_prefilled)`` to mirror the XLSX writer.
    The user edits the ``[N:k F:k]`` brackets to record their inventory; the
    parser keys on ``(SET) CN`` so display changes don't affect ingest.
    """
    codes = [c.lower() for c in set_codes]
    if not codes:
        raise ValueError("no set codes provided")

    rarity_set: set[str] | None = None
    if rarity_filter is not None:
        rarity_set = {r.lower() for r in rarity_filter if r and str(r).strip()}
        if not rarity_set:
            rarity_set = None

    placeholders = ",".join("?" for _ in codes)
    with db.connect() as conn:
        rows = conn.execute(
            f"""
            SELECT scryfall_id, set_code, collector_number, name, flavor_name,
                   rarity, prices_usd, prices_usd_foil, is_token, scryfall_uri,
                   frame_effects, promo_types, border_color, full_art
            FROM cards
            WHERE set_code IN ({placeholders})
            ORDER BY 1, 2
            """,
            codes,
        ).fetchall()

        prepop: dict[tuple[str, str], int] = {}
        if prepopulate_from_inventory:
            for r in conn.execute(
                "SELECT scryfall_id, finish, quantity FROM inventory"
            ).fetchall():
                prepop[(r["scryfall_id"], r["finish"])] = r["quantity"]

    if not include_tokens:
        rows = [r for r in rows if not r["is_token"]]
    if not include_variants:
        rows = [r for r in rows if not is_excluded_variant(r)]
    if rarity_set is not None:
        rows = [r for r in rows if (r["rarity"] or "").lower() in rarity_set]

    # Sort: set code asc, then collector_number asc. See the XLSX writer for
    # why inventory checklists sort this way (input tool, not a report).
    def cn_sortkey(cn: str) -> tuple:
        m = re.match(r"^(\d+)(.*)$", cn or "")
        if m:
            return (int(m.group(1)), m.group(2))
        return (10**9, cn or "")

    rows = sorted(
        rows,
        key=lambda r: (
            r["set_code"],
            cn_sortkey(r["collector_number"]),
        ),
    )

    rarity_value = ",".join(sorted(rarity_set)) if rarity_set else ""
    from . import __version__
    meta = {
        # `kind` distinguishes inventory checklists (this writer) from missing
        # checklists (`mm query missing-set`). See feedback_checklist_artifacts.
        "kind": "inventory",
        # `mode` declares ingest semantics. See the XLSX writer for the full
        # rationale; same field, same semantics in markdown form.
        "mode": mode,
        "anchor_code": (anchor_code or codes[0]).lower(),
        "set_codes": ",".join(codes),
        "rarity_filter": rarity_value,
        "slug": slug or out_path.stem,
        "include_tokens": "1" if include_tokens else "0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "magic_manager_version": __version__,
    }

    out_lines: list[str] = []
    out_lines.append("---")
    for k, v in meta.items():
        out_lines.append(f"{k}: {v}")
    out_lines.append("---")
    out_lines.append("")

    title = anchor_code.upper() if anchor_code else codes[0].upper()
    if rarity_value:
        title += f" — {rarity_value}"
    out_lines.append(f"# {title}")
    out_lines.append("")
    out_lines.append(
        "Edit the `[N:k F:k]` brackets to record quantities. Save, then run "
        "`/ingest-new-inventory-list` (or `mm set ingest`) to apply."
    )
    out_lines.append("")

    cells_prefilled = 0
    current_set = None
    set_counts: dict[str, int] = {}
    for r in rows:
        set_counts[r["set_code"]] = set_counts.get(r["set_code"], 0) + 1

    from .treatments import compute_treatment, LEGEND
    for r in rows:
        set_code = r["set_code"]
        if set_code != current_set:
            current_set = set_code
            out_lines.append("")
            out_lines.append(f"## {set_code.upper()} ({set_counts[set_code]} cards)")
            out_lines.append("")

        flavor = r["flavor_name"]
        display_name = f"{flavor} / {r['name']}" if flavor else r["name"]
        # Escape pipes / brackets that would otherwise interfere with markdown
        # link/table syntax. ``[`` and ``]`` in a link's display text need to
        # be escaped; flavor and oracle names rarely contain them but a few
        # split-card names do (e.g. "Fire // Ice" wouldn't, but
        # "[Battlefield Forge]" hypothetically would).
        safe_name = display_name.replace("[", "\\[").replace("]", "\\]")
        uri = r["scryfall_uri"] or ""
        link = f"[{safe_name}]({uri})" if uri else safe_name

        qn = prepop.get((r["scryfall_id"], "nonfoil"), 0)
        qf = prepop.get((r["scryfall_id"], "foil"), 0)
        if qn > 0:
            cells_prefilled += 1
        if qf > 0:
            cells_prefilled += 1

        usd = r["prices_usd"]
        usd_foil = r["prices_usd_foil"]
        price_segment = f"${usd if usd is not None else '—'} / ${usd_foil if usd_foil is not None else '—'}"

        treatment = compute_treatment(r)
        # Treatment is rendered in `[...]` after the qty bracket; empty for
        # standard prints. Parser keys on `(SET) CN` so the position doesn't
        # affect ingest.
        treatment_seg = f" [{treatment}]" if treatment else ""

        out_lines.append(
            f"- ({r['set_code'].upper()}) {r['collector_number']} "
            f"[N:{qn} F:{qf}]{treatment_seg} — {link} — {price_segment}"
        )

    # Legend at the bottom — informational, ignored by the parser.
    out_lines.append("")
    out_lines.append("## Treatment legend")
    out_lines.append("")
    for code, meaning in LEGEND:
        out_lines.append(f"- `{code}` — {meaning}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return (len(rows), cells_prefilled)


# ---------- Jumpstart pack-level checklist (kind=jumpstart) ----------

# A "jumpstart variant" is one MTGJSON deck file describing a sealed pack's
# 15-card content list (e.g. ``Toph_TLE``). Sets like TLE/J25/JMP/J22 publish
# 50+ variants. The user fills in one qty column + a deconstruct flag per row:
#   - ``qty``         → how many copies of this pack were opened
#   - ``deconstruct`` → bool; if False (default) one `pack:*` recipe is created
#                       and qty copies' worth of cards land in inventory. If
#                       True, NO recipe is created and all qty copies go to
#                       loose inventory.
#
# There is no per-copy kept/deconstructed split. V5 semantics write a pack's
# recipe exactly once regardless of copies (import_precon copies= only scales
# the inventory add, not the deck composition), so "kept 2, deconstructed 1"
# was indistinguishable in the DB from "kept 3": the recipe exists either way
# and 3 copies' cards are in inventory either way. The only representable
# distinction is "does a recipe exist for this pack" — hence a boolean, not a
# second qty column. (This is also why keeping qty>=2 leaves the extra copies
# as `available` in `mm deck find`: one pack's worth is pledged to the recipe,
# the rest are loose. That's expected, not a bug.)

def _jumpstart_variant_summary(variant_meta: dict) -> dict:
    """Fetch one variant's MTGJSON deck file and roll up displayable stats.

    Returns ``{"file_name", "theme", "card_count", "usd_total"}``. Pulls
    Scryfall USD per scryfall_id from the local cards table to compute
    ``usd_total`` (nonfoil price × count); printings missing from cards are
    skipped silently — user can still ingest, the totals just under-report.
    """
    from . import mtgjson as mtgjson_mod
    file_name = variant_meta["fileName"]
    deck_data = mtgjson_mod.deck(file_name)
    sids: list[tuple[str, int, bool]] = []  # (scryfall_id, count, is_foil)
    total_count = 0
    for board_key in ("commander", "mainBoard", "sideBoard"):
        for entry in deck_data.get(board_key) or []:
            sid = (entry.get("identifiers") or {}).get("scryfallId")
            count = int(entry.get("count", 1) or 1)
            total_count += count
            if sid:
                sids.append((sid, count, bool(entry.get("isFoil"))))

    usd_total = 0.0
    if sids:
        with db.connect() as conn:
            placeholders = ",".join("?" for _ in sids)
            rows = {
                r["scryfall_id"]: (r["prices_usd"], r["prices_usd_foil"])
                for r in conn.execute(
                    f"SELECT scryfall_id, prices_usd, prices_usd_foil "
                    f"FROM cards WHERE scryfall_id IN ({placeholders})",
                    [s[0] for s in sids],
                ).fetchall()
            }
        for sid, count, is_foil in sids:
            prices = rows.get(sid)
            if not prices:
                continue
            price = prices[1] if is_foil else prices[0]
            if price is not None:
                usd_total += float(price) * count
    return {
        "file_name": file_name,
        "theme": variant_meta.get("name") or file_name,
        "card_count": total_count,
        "usd_total": round(usd_total, 2) if usd_total else None,
    }


def _build_jumpstart_rows(set_code: str) -> list[dict]:
    """Enumerate Jumpstart variants for ``set_code`` and roll each one up."""
    from . import mtgjson as mtgjson_mod
    variants = mtgjson_mod.jumpstart_variants(set_code)
    if not variants:
        return []
    return [_jumpstart_variant_summary(v) for v in
            sorted(variants, key=lambda d: d.get("name") or d.get("fileName") or "")]


def write_jumpstart_list_xlsx(set_code: str, out_path: Path,
                              *, slug: str | None = None) -> int:
    """Emit a fillable XLSX of every Jumpstart pack variant for ``set_code``.

    Row schema: file_name | theme | card_count | usd_total | qty | deconstruct

    ``qty`` is how many copies of the pack were opened; ``deconstruct`` is a
    boolean (0/1, or blank=0) — set it to 1 to skip creating a recipe and dump
    all copies to loose inventory. Hidden ``_meta`` sheet declares
    ``kind=jumpstart`` so ingest can dispatch the correct branch. Returns
    ``rows_written``.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    from . import __version__

    rows = _build_jumpstart_rows(set_code)
    if not rows:
        raise ValueError(
            f"no Jumpstart variants found for set {set_code!r}. "
            f"Check `mm mtgjson decks --set {set_code}` for available decks."
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "checklist"

    headers = ["file_name", "theme", "card_count", "usd_total",
               "qty", "deconstruct"]
    ws.append(headers)
    for col, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="left")

    qty_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    int_validator = DataValidation(type="whole", operator="greaterThanOrEqual",
                                   formula1=0, allow_blank=True)
    int_validator.error = "Enter a non-negative integer (or leave blank for 0)."
    int_validator.errorTitle = "Invalid quantity"
    ws.add_data_validation(int_validator)

    # deconstruct is a 0/1 flag: constrain to those two values (blank = 0).
    bool_validator = DataValidation(type="whole", operator="between",
                                    formula1=0, formula2=1, allow_blank=True)
    bool_validator.error = "Enter 0 (keep a recipe) or 1 (deconstruct all copies)."
    bool_validator.errorTitle = "Invalid flag"
    ws.add_data_validation(bool_validator)

    for r in rows:
        ws.append([
            r["file_name"],
            r["theme"],
            r["card_count"],
            r["usd_total"],
            None,
            None,
        ])
    last_row = ws.max_row

    # col 5 = qty (non-negative int), col 6 = deconstruct (0/1)
    qty_letter = get_column_letter(5)
    int_validator.add(f"{qty_letter}2:{qty_letter}{last_row}")
    bool_letter = get_column_letter(6)
    bool_validator.add(f"{bool_letter}2:{bool_letter}{last_row}")
    for col_idx in (5, 6):
        for r in range(2, last_row + 1):
            ws.cell(row=r, column=col_idx).fill = qty_fill

    for row_idx in range(2, last_row + 1):
        ws.cell(row=row_idx, column=4).number_format = '"$"#,##0.00'

    widths = {1: 22, 2: 24, 3: 11, 4: 11, 5: 8, 6: 12}
    for col_idx, w in widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = w

    ws.freeze_panes = "A2"

    meta_ws = wb.create_sheet("_meta")
    meta_ws.sheet_state = "hidden"
    meta_ws.append(["key", "value"])
    meta_ws["A1"].font = Font(bold=True)
    meta_ws["B1"].font = Font(bold=True)

    code = set_code.lower()
    meta = {
        # `kind` is the dispatch key for `mm set ingest`. New value 'jumpstart'
        # routes to the Jumpstart importer; existing values 'inventory' and
        # 'missing' route to their own paths.
        "kind": "jumpstart",
        "anchor_code": code,
        "set_codes": code,
        "slug": slug or out_path.stem,
        "mode": "add",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "magic_manager_version": __version__,
    }
    for k, v in meta.items():
        meta_ws.append([k, v])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return last_row - 1


def write_jumpstart_list_md(set_code: str, out_path: Path,
                            *, slug: str | None = None) -> int:
    """Markdown twin of ``write_jumpstart_list_xlsx``.

    Line shape (after YAML frontmatter):

        - Toph_TLE — Toph — 15 cards — $4.20 [Q:0 X:0]

    Parser keys on the leading file_name token, so prose changes don't break
    ingest. The ``[Q:k X:b]`` bracket holds qty (copies opened) and the
    deconstruct-all flag (0/1).
    """
    from . import __version__

    rows = _build_jumpstart_rows(set_code)
    if not rows:
        raise ValueError(
            f"no Jumpstart variants found for set {set_code!r}. "
            f"Check `mm mtgjson decks --set {set_code}` for available decks."
        )

    code = set_code.lower()
    meta = {
        "kind": "jumpstart",
        "anchor_code": code,
        "set_codes": code,
        "slug": slug or out_path.stem,
        "mode": "add",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "magic_manager_version": __version__,
    }

    out_lines: list[str] = ["---"]
    for k, v in meta.items():
        out_lines.append(f"{k}: {v}")
    out_lines.append("---")
    out_lines.append("")
    out_lines.append(f"# {code.upper()} Jumpstart variants ({len(rows)} packs)")
    out_lines.append("")
    out_lines.append(
        "Edit the `[Q:k X:b]` bracket per row: `Q` = copies of the pack you "
        "opened, `X` = deconstruct-all flag (0 = keep a `pack:*` recipe, "
        "1 = dump all copies to loose inventory, no recipe). Save, then run "
        "`mm set ingest` to apply."
    )
    out_lines.append("")
    for r in rows:
        usd = r["usd_total"]
        usd_seg = f"${usd:.2f}" if usd is not None else "—"
        out_lines.append(
            f"- {r['file_name']} — {r['theme']} — {r['card_count']} cards — "
            f"{usd_seg} [Q:0 X:0]"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return len(rows)


def _slug_theme(theme: str, set_code: str) -> str:
    """Build a deck slug for a Jumpstart pack: ``pack:<theme>-<setcode>``."""
    raw_theme = "".join(c if c.isalnum() else "-" for c in theme.lower())
    while "--" in raw_theme:
        raw_theme = raw_theme.replace("--", "-")
    raw_theme = raw_theme.strip("-")
    return f"pack:{raw_theme}-{set_code.lower()}"


def ingest_jumpstart_from_path(path: Path) -> dict:
    """Apply a filled-in Jumpstart checklist to the local DB.

    For each row with ``qty > 0``:
      - ``deconstruct=False`` (default): creates one ``pack:*`` recipe
        (format='jumpstart') and adds ``qty`` copies' worth of cards to
        inventory via ``import_precon(copies=qty)``.
      - ``deconstruct=True``: runs ``import_precon(deconstruct=True,
        copies=qty)`` so all ``qty`` copies' cards land in inventory with no
        recipe created.

    Returns a summary:
      - ``rows_total`` (int): rows present in the file
      - ``rows_acted`` (int): rows with qty > 0
      - ``packs_created`` (int): total ``pack:*`` deck rows created
      - ``packs_deconstructed`` (int): total pack-copies dumped to loose
        inventory (deconstruct rows)
      - ``inv_qty_total`` (int): cumulative card-qty added to inventory
      - ``per_row``: list of ``{"file_name", "theme", "qty", "deconstruct",
        "slugs": [...], "missing_sids": [...], "error": str|None}``
      - ``warnings`` (list[str]): non-fatal parse/lookup warnings
    """
    from . import decks as decks_mod, mtgjson as mtgjson_mod
    from . import parsers
    from pathlib import Path as _Path

    path = _Path(path)
    suffix = path.suffix.lower()
    if suffix in (".xlsx",):
        parsed = parsers.parse_jumpstart_list_xlsx(path)
    elif suffix in (".md",):
        parsed = parsers.parse_jumpstart_list_md(path)
    else:
        raise ValueError(f"unsupported jumpstart-list extension: {suffix!r}")

    meta = parsed.meta or {}
    set_code = (meta.get("set_codes") or meta.get("anchor_code") or "").lower()
    if not set_code:
        # Fall back to inferring from a fileName like ``Toph_TLE`` if _meta is
        # missing. Unlikely but cheap to support.
        for r in parsed.rows:
            if "_" in r.file_name:
                set_code = r.file_name.rsplit("_", 1)[1].lower()
                break
    if not set_code:
        raise ValueError("could not determine set_code from checklist _meta or rows")

    summary: dict = {
        "rows_total": len(parsed.rows),
        "rows_acted": 0,
        "packs_created": 0,
        "packs_deconstructed": 0,
        "inv_qty_total": 0,
        "per_row": [],
        "warnings": list(parsed.warnings),
    }

    for row in parsed.rows:
        if row.qty <= 0:
            continue
        summary["rows_acted"] += 1
        per_row: dict = {
            "file_name": row.file_name,
            "theme": row.theme,
            "qty": row.qty,
            "deconstruct": row.deconstruct,
            "slugs": [],
            "missing_sids": [],
            "error": None,
        }

        # Resolve theme from MTGJSON when the parser couldn't capture it (md path).
        theme_for_slug = row.theme
        if not theme_for_slug:
            try:
                deck_data = mtgjson_mod.deck(row.file_name)
                theme_for_slug = deck_data.get("name") or row.file_name
            except mtgjson_mod.MtgJsonError as e:
                per_row["error"] = f"could not fetch deck JSON: {e}"
                summary["per_row"].append(per_row)
                continue

        base_slug = _slug_theme(theme_for_slug, set_code)

        try:
            if row.deconstruct:
                r = decks_mod.import_precon(
                    row.file_name,
                    slug=base_slug,  # not used in deconstruct path
                    format="jumpstart",
                    copies=row.qty,
                    add_inventory=True,
                    deconstruct=True,
                )
                per_row["missing_sids"].extend(r["missing_sids"])
                summary["packs_deconstructed"] += row.qty
                summary["inv_qty_total"] += r["inv_qty_total"]
            else:
                r = decks_mod.import_precon(
                    row.file_name,
                    slug=base_slug,
                    format="jumpstart",
                    copies=row.qty,
                    add_inventory=True,
                    deconstruct=False,
                )
                per_row["slugs"].extend(r["effective_slugs"])
                per_row["missing_sids"].extend(r["missing_sids"])
                summary["packs_created"] += len(r["effective_slugs"])
                summary["inv_qty_total"] += r["inv_qty_total"]
        except (mtgjson_mod.MtgJsonError, ValueError) as e:
            per_row["error"] = str(e)

        summary["per_row"].append(per_row)

    return summary

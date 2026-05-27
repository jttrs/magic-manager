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
    """Pull every printing in ``set_codes`` into the cards table. Returns rows synced."""
    codes = [c.lower() for c in set_codes]
    if not codes:
        return 0
    # Build a single search query using `or` so we paginate once.
    query = " or ".join(f"e:{c}" for c in codes)
    n = 0
    with db.connect() as conn:
        for card in scryfall.search(query, unique="prints"):
            db.upsert_card(conn, card)
            n += 1
    return n


# ---------- master-list seeding + XLSX emit ----------

def seed_set_list(label: str, set_codes: Iterable[str],
                  include_variants: bool = False) -> int:
    """Create (or update) a list with every printing in ``set_codes`` seeded at qty=0.

    Existing rows are preserved (so re-running this after the user has filled in
    quantities is safe). Only missing ``(card, finish)`` pairs get a 0 row.

    By default, prerelease/stamped/japanshowcase/serialized/white-bordered
    variants are NOT seeded so that ``set:<code> missing`` math doesn't count
    them. Pass ``include_variants=True`` to opt them back in.
    """
    codes = [c.lower() for c in set_codes]
    if not codes:
        return 0
    with db.connect() as conn:
        db.upsert_list(conn, label, kind="set", source="set-master")
        placeholders = ",".join("?" for _ in codes)
        rows = conn.execute(
            f"""
            SELECT scryfall_id, finishes, border_color, promo_types
            FROM cards
            WHERE set_code IN ({placeholders})
            """,
            codes,
        ).fetchall()
        seeded = 0
        for r in rows:
            if not include_variants and is_excluded_variant(r):
                continue
            import json
            finishes = json.loads(r["finishes"] or "[]") or ["nonfoil"]
            for fin in finishes:
                if fin not in ("nonfoil", "foil"):
                    continue
                # only insert if absent — don't clobber existing user qty
                existing = conn.execute(
                    "SELECT 1 FROM list_rows WHERE label = ? AND scryfall_id = ? AND finish = ?",
                    (label, r["scryfall_id"], fin),
                ).fetchone()
                if existing:
                    continue
                conn.execute(
                    "INSERT INTO list_rows (label, scryfall_id, finish, quantity) VALUES (?, ?, ?, 0)",
                    (label, r["scryfall_id"], fin),
                )
                seeded += 1
        return seeded


def write_master_list_xlsx(set_codes: Iterable[str], out_path: Path,
                           include_tokens: bool = False,
                           prepopulate_from_label: str | None = None,
                           rarity_filter: Iterable[str] | None = None,
                           anchor_code: str | None = None,
                           slug: str | None = None,
                           include_variants: bool = False) -> tuple[int, int]:
    """Emit a fillable XLSX of every printing in ``set_codes``.

    When ``prepopulate_from_label`` is set, qty cells are pre-filled from
    that label's existing rows so resuming after an ingest doesn't lose
    visible progress.

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

        # (scryfall_id, finish) -> quantity
        prepop: dict[tuple[str, str], int] = {}
        if prepopulate_from_label:
            for r in conn.execute(
                "SELECT scryfall_id, finish, quantity FROM list_rows WHERE label = ? AND quantity > 0",
                (prepopulate_from_label,),
            ).fetchall():
                prepop[(r["scryfall_id"], r["finish"])] = r["quantity"]

    if not include_tokens:
        rows = [r for r in rows if not r["is_token"]]
    if not include_variants:
        rows = [r for r in rows if not is_excluded_variant(r)]
    if rarity_set is not None:
        rows = [r for r in rows if (r["rarity"] or "").lower() in rarity_set]

    # Sort: rarity bucket, then collector_number (numeric where possible).
    def cn_sortkey(cn: str) -> tuple:
        m = re.match(r"^(\d+)(.*)$", cn or "")
        if m:
            return (int(m.group(1)), m.group(2))
        return (10**9, cn or "")

    rows = sorted(
        rows,
        key=lambda r: (
            RARITY_ORDER.get((r["rarity"] or "").lower(), 9),
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
    """Read the ``_meta`` sheet from a master-list XLSX. Returns the dict
    of key/value strings, or ``None`` if the sheet is absent.
    """
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


# ---------- markdown intake format ----------

def write_master_list_md(set_codes: Iterable[str], out_path: Path,
                         include_tokens: bool = False,
                         prepopulate_from_label: str | None = None,
                         rarity_filter: Iterable[str] | None = None,
                         anchor_code: str | None = None,
                         slug: str | None = None,
                         include_variants: bool = False) -> tuple[int, int]:
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
        if prepopulate_from_label:
            for r in conn.execute(
                "SELECT scryfall_id, finish, quantity FROM list_rows "
                "WHERE label = ? AND quantity > 0",
                (prepopulate_from_label,),
            ).fetchall():
                prepop[(r["scryfall_id"], r["finish"])] = r["quantity"]

    if not include_tokens:
        rows = [r for r in rows if not r["is_token"]]
    if not include_variants:
        rows = [r for r in rows if not is_excluded_variant(r)]
    if rarity_set is not None:
        rows = [r for r in rows if (r["rarity"] or "").lower() in rarity_set]

    def cn_sortkey(cn: str) -> tuple:
        m = re.match(r"^(\d+)(.*)$", cn or "")
        if m:
            return (int(m.group(1)), m.group(2))
        return (10**9, cn or "")

    rows = sorted(
        rows,
        key=lambda r: (
            RARITY_ORDER.get((r["rarity"] or "").lower(), 9),
            r["set_code"],
            cn_sortkey(r["collector_number"]),
        ),
    )

    rarity_value = ",".join(sorted(rarity_set)) if rarity_set else ""
    from . import __version__
    meta = {
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
    current_rarity = None
    rarity_counts: dict[str, int] = {}
    for r in rows:
        rarity_counts[r["rarity"] or "?"] = rarity_counts.get(r["rarity"] or "?", 0) + 1

    from .treatments import compute_treatment, LEGEND
    for r in rows:
        rarity = r["rarity"] or "?"
        if rarity != current_rarity:
            current_rarity = rarity
            out_lines.append("")
            out_lines.append(f"## {rarity.title()} ({rarity_counts[rarity]} cards)")
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

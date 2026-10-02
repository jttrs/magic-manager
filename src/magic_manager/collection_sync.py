"""Collection (inventory) import/export over per-service CSV — the offline core.

This mirrors ``decksource.py`` but for the INVENTORY table instead of decks: a
normalized row carrier (:class:`CollectionRow`), a config-driven CSV adapter
(:func:`read_csv` / :func:`write_csv`), a Scryfall resolve+upsert pass
(:func:`resolve_rows`), a direction-agnostic diff (:func:`diff_collections`,
generalized from ``decks.version_diff``), and the three apply-modes
(:func:`apply_import`) that map 1:1 onto the inventory-checklist semantics at
``sets.py`` and route through the ONE V19 ledger seam
(``ingest.open_ingest_event`` + ``inventory.inventory_add``/``inventory_set``),
so ``inventory.quantity == SUM(inventory_events.delta)`` is preserved for free.

**No network fetch happens for the CSV read itself** — the file is read offline;
only :func:`resolve_rows` goes out, and only through the rate-limited
``scryfall.collection`` wrapper (the same seam ``parsers.resolve`` and
``decksource._resolve_cards`` use). ``parsers.Entry`` is deliberately NOT the
carrier: it has no ``scryfall_id`` slot, and ManaBox CSVs carry the id directly
(the exact reason ``decksource`` documents for its own dict carrier).

Services are declared in ``config/collection_formats.toml`` (column map, finish/
condition maps, write order, ``has_scryfall_id``, ``confidence``) — adding a
service is config, not code. Condition / purchase_price are PASSTHROUGH-ONLY in
v1: carried on the row (the future-dimension hook) but never written to the DB,
whose inventory key is ``(scryfall_id, finish)`` only.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal

from . import config as config_mod
from . import db, scryfall
from . import ingest as ingest_mod
from . import inventory as inv_mod
from . import selectors as sel_mod
from . import util

Direction = Literal["import", "export"]
ApplyMode = Literal["add", "modify", "overwrite"]

_VALID_FINISHES = ("nonfoil", "foil")


# ---------------------------------------------------------------------------
# Normalized row — the decksource._norm shape minus `board`, plus the
# passthrough collection dimensions (condition / purchase_price).
# ---------------------------------------------------------------------------

@dataclass
class CollectionRow:
    """One normalized collection line. ``qty`` + ``finish`` + an identity
    (``scryfall_id`` OR ``set``+``collector_number``) are the load-bearing
    fields; ``name`` is diagnostic; ``condition``/``purchase_price`` are
    passthrough-only (carried through read→write but never entering the DB)."""
    qty: int
    finish: str  # 'nonfoil' | 'foil'
    scryfall_id: str | None = None
    set: str | None = None
    collector_number: str | None = None
    name: str | None = None
    condition: str | None = None
    purchase_price: str | None = None

    def identity(self, *, prefer_id: bool = True) -> tuple:
        """The (identity, finish) diff key. ``(scryfall_id, finish)`` when an id
        is present and ``prefer_id``; else ``(set, cn, finish)`` lowercased."""
        if prefer_id and self.scryfall_id:
            return (self.scryfall_id, self.finish)
        return ((self.set or "").lower(), str(self.collector_number or ""), self.finish)


# ---------------------------------------------------------------------------
# Config access
# ---------------------------------------------------------------------------

def service_format(service: str) -> dict:
    """The ``config/collection_formats.toml`` block for ``service`` (lowercased).

    Raises ``LookupError`` naming the known services if absent — a clean exit
    for a typo'd service, mirroring the selector-engine error contract."""
    fmts = config_mod.collection_formats()
    key = service.lower()
    if key not in fmts:
        raise LookupError(
            f"unknown collection service {service!r}; configured services: "
            f"{sorted(fmts)}"
        )
    return fmts[key]


def _finish_from(fmt: dict, raw: str | None) -> str:
    """Map a service finish token → our vocabulary. Unknown/blank → 'nonfoil'
    (the ManaBox 'Foil' column is literally 'normal'/'foil'/'etched')."""
    fmap = {str(k).lower(): str(v).lower() for k, v in (fmt.get("finish_map") or {}).items()}
    token = (raw or "").strip().lower()
    return fmap.get(token, "nonfoil")


def _condition_from(fmt: dict, raw: str | None) -> str | None:
    """Map a service condition token → our canonical condition (passthrough)."""
    cmap = {str(k).lower(): str(v).lower() for k, v in (fmt.get("condition_map") or {}).items()}
    token = (raw or "").strip().lower()
    if not token:
        return None
    return cmap.get(token, token)


# ---------------------------------------------------------------------------
# read_csv — service CSV → list[CollectionRow]  (offline, no network)
# ---------------------------------------------------------------------------

def read_csv(path: str | Path, service: str) -> list[CollectionRow]:
    """Parse a service's collection CSV into normalized rows.

    ``csv.DictReader`` over the service's declared column map; applies the
    finish and condition maps. A row missing BOTH an identity (no scryfall_id,
    no set+cn) and a positive quantity is skipped. Multiple CSV rows for the
    same printing+finish (e.g. one per condition) are kept SEPARATE here —
    :func:`diff_collections` and :func:`apply_import` aggregate by key.
    """
    fmt = service_format(service)
    cols = fmt.get("columns") or {}
    # MTGGoldfish-style set-code remap (service → Scryfall code), lowercased.
    remap = {str(k).lower(): str(v).lower()
             for k, v in (fmt.get("set_remap") or {}).items()}
    text = Path(path).read_text(encoding="utf-8-sig")  # tolerate a BOM
    reader = csv.DictReader(io.StringIO(text))

    def cell(row: dict, field_name: str) -> str | None:
        header = cols.get(field_name)
        if not header:
            return None
        v = row.get(header)
        return v.strip() if isinstance(v, str) else v

    out: list[CollectionRow] = []
    for raw in reader:
        qty_s = cell(raw, "quantity")
        try:
            qty = int(float(qty_s)) if qty_s not in (None, "") else 0
        except (TypeError, ValueError):
            qty = 0
        sid = cell(raw, "scryfall_id") or None
        setc = (cell(raw, "set") or None)
        set_lc = setc.lower() if setc else None
        if set_lc:
            set_lc = remap.get(set_lc, set_lc)  # apply the remap, if any
        cn = cell(raw, "collector_number") or None
        if qty <= 0 or not (sid or (set_lc and cn)):
            continue
        out.append(CollectionRow(
            qty=qty,
            finish=_finish_from(fmt, cell(raw, "finish")),
            scryfall_id=sid,
            set=set_lc,
            collector_number=cn,
            name=cell(raw, "name") or None,
            condition=_condition_from(fmt, cell(raw, "condition")),
            purchase_price=cell(raw, "purchase_price") or None,
        ))
    return out


# ---------------------------------------------------------------------------
# resolve_rows — fill scryfall_id + upsert cards (the one network pass)
# ---------------------------------------------------------------------------

@dataclass
class ResolveResult:
    resolved: list[CollectionRow] = field(default_factory=list)
    not_found: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def resolve_rows(rows: list[CollectionRow], *, conn=None) -> ResolveResult:
    """Resolve rows against Scryfall and UPSERT each matched card into ``cards``.

    Every row needs its card present in ``cards`` before apply (the ledger's
    ``inventory_events.scryfall_id`` FKs there), so this pass runs even for
    ManaBox rows that already carry a ``scryfall_id`` — the id tier just makes
    the lookup exact. The tiered batch-resolve + index-build is the shared
    ``scryfall.resolve_identifiers`` seam (which also owns the 400-bisection via
    ``scryfall.collection`` — a MTGGoldfish ``prm-*`` pseudo-set that Scryfall
    rejects degrades to not_found instead of sinking the batch). Resolution key
    per row, in priority order:

      1. ``scryfall_id`` — ManaBox/Archidekt/MTGGoldfish carry it (exact printing).
      2. ``(set, collector_number)`` — exact printing. An id-bearing row ALSO
         contributes a (set, cn) identifier so a STALE/merged id (present but
         unresolvable) falls back to set+cn instead of being dropped.

    A resolved row gets its ``scryfall_id`` filled from the matched card; an
    unresolved row lands in ``not_found`` (reported, never silently dropped).
    Name-only resolution is intentionally NOT offered — a collection write must
    land on an EXACT printing, so a row with neither an id nor set+cn is a hard
    not_found rather than a fuzzy name guess (the one tier decksource adds but
    this does not).
    """
    res = ResolveResult()
    id_idents: list[dict] = []
    setcn_idents: list[dict] = []
    seen_ids: set[str] = set()
    seen_setcn: set[tuple] = set()
    for r in rows:
        if r.scryfall_id and r.scryfall_id not in seen_ids:
            seen_ids.add(r.scryfall_id)
            id_idents.append({"id": r.scryfall_id})
        # NOT an elif: an id-bearing row with set+cn also enqueues the (set, cn)
        # identifier, so a stale/unresolvable id can fall back to set+cn below.
        if r.set and r.collector_number:
            key = (r.set.lower(), str(r.collector_number))
            if key not in seen_setcn:
                seen_setcn.add(key)
                setcn_idents.append({"set": r.set.lower(), "collector_number": str(r.collector_number)})

    by_id, by_setcn, _by_name, warnings = scryfall.resolve_identifiers(
        id_idents, setcn_idents
    )
    res.warnings.extend(warnings)

    # Upsert every matched card so the ledger FK target exists.
    with db.transaction(conn) as c:
        for card in list(by_id.values()):
            db.upsert_card(c, card)

    for r in rows:
        card = None
        if r.scryfall_id and r.scryfall_id in by_id:
            card = by_id[r.scryfall_id]
        elif r.set and r.collector_number:
            card = by_setcn.get((r.set.lower(), str(r.collector_number)))
        if card is None:
            res.not_found.append({
                "qty": r.qty, "name": r.name, "set": r.set,
                "collector_number": r.collector_number,
                "finish": r.finish,
                "reason": "unresolved against Scryfall",
            })
            continue
        r.scryfall_id = card["id"]
        res.resolved.append(r)
    return res


# ---------------------------------------------------------------------------
# write_csv — list[CollectionRow] → service CSV string
# ---------------------------------------------------------------------------

def _finish_to(fmt: dict, finish: str) -> str:
    """Invert finish_map: our vocabulary → the service's token (first match)."""
    fmap = fmt.get("finish_map") or {}
    for token, mapped in fmap.items():
        if str(mapped).lower() == finish:
            return str(token)
    return finish


def write_csv(rows: Iterable[CollectionRow], service: str) -> str:
    """Emit rows as a service CSV string (header + data), using the service's
    declared ``[write].order`` and column headers. Inverts the finish map and
    defaults a missing condition to ``[write].condition_default``.

    Returns a string (the driver owns the file write via ``util.output_dir``),
    mirroring the ``exports.build`` convention. ``purchase_price`` is emitted
    verbatim when present (passthrough)."""
    fmt = service_format(service)
    cols = fmt.get("columns") or {}
    write = fmt.get("write") or {}
    order = write.get("order") or list(cols.keys())
    cond_default = write.get("condition_default")

    headers = [cols.get(f, f) for f in order]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for r in rows:
        line: list = []
        for f in order:
            if f == "finish":
                line.append(_finish_to(fmt, r.finish))
            elif f == "condition":
                line.append(r.condition or cond_default or "")
            elif f == "quantity":
                line.append(r.qty)
            else:
                line.append(getattr(r, f, None) or "")
        writer.writerow(line)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# diff_collections — direction-agnostic (generalized from decks.version_diff)
# ---------------------------------------------------------------------------

def _aggregate(rows: Iterable[CollectionRow], *, prefer_id: bool) -> dict[tuple, dict]:
    """Collapse rows to ``{key: {qty, name, set, cn, finish, scryfall_id}}``,
    summing quantities for the same ``(identity, finish)`` key."""
    agg: dict[tuple, dict] = {}
    for r in rows:
        key = r.identity(prefer_id=prefer_id)
        slot = agg.get(key)
        if slot is None:
            agg[key] = {
                "qty": r.qty, "name": r.name, "set": r.set,
                "collector_number": r.collector_number, "finish": r.finish,
                "scryfall_id": r.scryfall_id,
            }
        else:
            slot["qty"] += r.qty
            slot["scryfall_id"] = slot["scryfall_id"] or r.scryfall_id
            slot["name"] = slot["name"] or r.name
    return agg


def _landing_from_inventory() -> list[CollectionRow]:
    """Materialize the local inventory as CollectionRows (the default landing
    state for an import diff). Reuses ``selectors.materialize('inventory')``."""
    out: list[CollectionRow] = []
    for mr in sel_mod.materialize("inventory"):
        card = mr.card
        out.append(CollectionRow(
            qty=mr.quantity, finish=mr.finish, scryfall_id=mr.scryfall_id,
            set=card.get("set"), collector_number=card.get("collector_number"),
            name=card.get("name"),
        ))
    return out


DiffKey = Literal["scryfall_id", "set_cn", "auto"]


def resolve_diff_key(
    incoming: list[CollectionRow], landing: list[CollectionRow]
) -> Literal["scryfall_id", "set_cn"]:
    """Pick the diff key that both sides can actually match on.

    ``scryfall_id`` is exact but only works when EVERY row on BOTH sides carries
    one; a single id-less row (an un-resolved moxfield export) keys as a
    ``(set, cn, finish)`` tuple that can never equal an id-keyed ``(sid, finish)``
    tuple, so a mixed diff would report everything as added+removed. The common
    denominator — set+cn, which inventory rows and service CSVs both carry — is
    the safe fallback. Used so callers don't have to know a service's id-fulness."""
    both = list(incoming) + list(landing)
    return "scryfall_id" if both and all(r.scryfall_id for r in both) else "set_cn"


def diff_collections(
    incoming: list[CollectionRow],
    landing: list[CollectionRow] | None = None,
    *,
    key: DiffKey = "auto",
) -> dict:
    """Diff ``incoming`` against ``landing`` (direction-agnostic).

    - import: ``incoming``=CSV rows, ``landing``=local inventory (the default
      when ``landing is None`` → ``selectors.materialize('inventory')``).
    - export: ``incoming``=local inventory rows, ``landing``=service CSV rows.

    Keyed on ``(scryfall_id, finish)`` (``key='scryfall_id'``) or
    ``(set, cn, finish)`` (``key='set_cn'``). ``key='auto'`` (the default) picks
    via :func:`resolve_diff_key` — ``scryfall_id`` only when BOTH sides are fully
    id-ful, else ``set_cn``. This is what makes export/diff against an id-less
    service (moxfield) correct: without it, id-ful inventory and an id-less CSV
    key into disjoint tuple arities and every row falsely reads added+removed.
    "added" = present in incoming but not landing; "removed" = present in landing
    but not incoming; "changed" = present on both with a different quantity. Each
    entry carries name/set/cn + both quantities. Mirrors ``decks.version_diff``.
    """
    if landing is None:
        landing = _landing_from_inventory()
    if key == "auto":
        key = resolve_diff_key(incoming, landing)
    prefer_id = key == "scryfall_id"
    inc = _aggregate(incoming, prefer_id=prefer_id)
    land = _aggregate(landing, prefer_id=prefer_id)

    added: list[dict] = []
    removed: list[dict] = []
    changed: list[dict] = []
    unchanged = 0
    for k, row in inc.items():
        if k not in land:
            added.append({**row, "qty_incoming": row["qty"], "qty_landing": 0})
        elif land[k]["qty"] != row["qty"]:
            changed.append({
                **row, "qty_incoming": row["qty"], "qty_landing": land[k]["qty"],
            })
        else:
            unchanged += 1
    for k, row in land.items():
        if k not in inc:
            removed.append({**row, "qty_incoming": 0, "qty_landing": row["qty"]})
    return {
        "added": added, "removed": removed, "changed": changed,
        "unchanged_count": unchanged,
        # The resolved key, so select_export_rows selects on the SAME basis the
        # diff was computed with (no second, independently-defaulted choice).
        "key": key,
    }


# Public alias — the driver (and tests) materialize the inventory-as-rows seam.
def inventory_rows() -> list[CollectionRow]:
    """Local inventory as :class:`CollectionRow`s — the export's ``incoming``
    side and an import diff's default ``landing`` side. Thin public wrapper over
    the shared materializer."""
    return _landing_from_inventory()


ExportMode = Literal["full", "delta"]


def select_export_rows(
    incoming: list[CollectionRow],
    diff: dict,
    *,
    mode: ExportMode,
    key: str | None = None,
) -> list[CollectionRow]:
    """Pick which inventory rows the reconciled export CSV should carry.

    - ``full`` (default): the entire ``incoming`` inventory, rendered in the
      service's format. The service's importer then reconciles however it does.
    - ``delta``: only the rows that DIFFER from the landing state — i.e. the
      diff's ``added`` + ``changed`` keys (cards the service is missing or has at
      the wrong count). This is the "just what to add/fix at the service" CSV.
      ``removed`` rows are NOT emitted (an export CSV can't express a deletion —
      that's a service-side manual action), but they ARE surfaced in the diff
      review so the user sees them.

    Keyed the SAME way the diff was computed: ``key`` defaults to ``diff['key']``
    (the key :func:`diff_collections` resolved), so the row selection can't
    diverge from the diff it's built against. Returns a subset of ``incoming``
    (same row objects), preserving per-row condition/price passthrough.
    """
    if mode == "full":
        return list(incoming)
    if mode != "delta":
        raise ValueError(f"unknown export mode {mode!r}")
    if key is None:
        key = diff.get("key", "scryfall_id")
    prefer_id = key == "scryfall_id"
    delta_keys = {
        (r.get("scryfall_id"), r["finish"]) if prefer_id
        else ((r.get("set") or "").lower(), str(r.get("collector_number") or ""), r["finish"])
        for r in (diff.get("added", []) + diff.get("changed", []))
    }
    out = []
    for r in incoming:
        rk = (r.scryfall_id, r.finish) if prefer_id else \
             ((r.set or "").lower(), str(r.collector_number or ""), r.finish)
        if rk in delta_keys:
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# apply_import — the three modes, through the V19 ledger seam
# ---------------------------------------------------------------------------

def apply_import(
    rows: list[CollectionRow],
    *,
    mode: ApplyMode,
    diff: dict | None = None,
    label: str | None = None,
    source_path: str | None = None,
    source_sha256: str | None = None,
    conn=None,
) -> dict:
    """Apply resolved ``rows`` to local inventory under one of three modes.

    All three open ONE ``collection-import`` ingest event and thread its
    ``ingest_id`` through every write (exactly like ``inventory_import_cmd``), so
    the ledger append and the inventory mutation commit together and
    ``inventory.quantity == SUM(delta)`` holds. Rows are aggregated by
    ``(scryfall_id, finish)`` first (a CSV may carry several lines per printing).
    The modes map 1:1 onto the checklist semantics (``sets.py``):

    - ``add``       → ``inventory_add(replace=False)`` — ADDITIVE: qty summed
                      onto any existing row. (qty≤0 can't occur; read_csv drops them.)
    - ``modify``    → ``inventory_set(qty)`` — REPLACE each incoming row to its
                      value; rows ABSENT from the CSV are left untouched.
    - ``overwrite`` → ``modify`` PLUS zero every landing row in ``diff['removed']``
                      (full audit: the CSV is authoritative). Requires ``diff``.

    ``rows`` must be resolved (every row has a ``scryfall_id`` and its card is
    upserted). Returns ``{"added", "updated", "zeroed", "ingest_id", "mode"}``.
    """
    if mode not in ("add", "modify", "overwrite"):
        raise ValueError(f"unknown apply mode {mode!r}")
    if mode == "overwrite" and diff is None:
        raise ValueError("overwrite mode requires the precomputed diff (for removed rows)")

    # Aggregate by (sid, finish) — one write per printing+finish.
    agg: dict[tuple[str, str], int] = {}
    for r in rows:
        if not r.scryfall_id:
            raise ValueError(f"apply_import got an unresolved row: {r!r}")
        if r.finish not in _VALID_FINISHES:
            raise ValueError(f"invalid finish {r.finish!r}")
        agg[(r.scryfall_id, r.finish)] = agg.get((r.scryfall_id, r.finish), 0) + r.qty

    added = updated = zeroed = 0
    with db.transaction(conn) as c:
        with ingest_mod.open_ingest_event(
            "collection-import",
            label=label or "collection import",
            source_path=source_path,
            source_sha256=source_sha256,
            mode=("additive" if mode == "add" else "replace"),
            conn=c,
        ) as rec:
            for (sid, finish), qty in agg.items():
                if mode == "add":
                    r = inv_mod.inventory_add(sid, finish, qty, conn=c,
                                              ingest_id=rec.ingest_id)
                else:  # modify / overwrite share the replace semantic
                    r = inv_mod.inventory_set(sid, finish, qty, conn=c,
                                              ingest_id=rec.ingest_id)
                action = r["action"]
                if action == "inserted":
                    added += 1
                elif action == "deleted":
                    zeroed += 1
                elif action in ("updated", "decremented") and r["old_qty"] != r["new_qty"]:
                    # Honest count: a modify to the SAME qty is a no-op (no delta
                    # recorded) and must not inflate the "updated" tally.
                    updated += 1

            if mode == "overwrite":
                for row in diff.get("removed", []):
                    sid = row.get("scryfall_id")
                    if not sid:
                        continue  # can't zero a landing row with no id
                    r = inv_mod.inventory_set(sid, row["finish"], 0, conn=c,
                                              ingest_id=rec.ingest_id)
                    if r["action"] == "deleted":
                        zeroed += 1
            ingest_id = rec.ingest_id

    return {"added": added, "updated": updated, "zeroed": zeroed,
            "ingest_id": ingest_id, "mode": mode}


# ---------------------------------------------------------------------------
# Review artifacts (reuse util.output_dir + exports.xlsx)
# ---------------------------------------------------------------------------

def _diff_rows_for_artifact(diff: dict) -> list[dict]:
    """Flatten a diff into one list of change rows, tagged with a change type,
    sorted by type then set/cn — the shared body for md/json/xlsx artifacts."""
    out: list[dict] = []
    for kind in ("added", "changed", "removed"):
        for row in diff.get(kind, []):
            out.append({"change": kind, **row})
    out.sort(key=lambda r: (r["change"], (r.get("set") or ""),
                            util.cn_sort_key(r.get("collector_number") or "")))
    return out


def diff_summary_line(diff: dict) -> str:
    """One-line counts summary for the CLI/skill readout."""
    return (f"{len(diff['added'])} added, {len(diff['changed'])} changed, "
            f"{len(diff['removed'])} removed, {diff['unchanged_count']} unchanged")


def diff_markdown(diff: dict, *, direction: Direction, service: str,
                  mode: ApplyMode | None = None, cap: int = 60) -> str:
    """A capped markdown review table for chat. ``added``/``changed``/``removed``
    rows, each showing landing→incoming quantities so the user can eyeball the
    net effect before approving. Capped to ``cap`` rows (the full set is in the
    JSON/XLSX artifacts)."""
    rows = _diff_rows_for_artifact(diff)
    header = (f"**Collection {direction}** — service `{service}`"
              + (f", mode `{mode}`" if mode else "")
              + f"\n\n{diff_summary_line(diff)}\n")
    if not rows:
        return header + "\n_(no differences)_"
    lines = [header, "", "| change | set | cn | name | finish | landing | incoming |",
             "| --- | --- | --- | --- | --- | ---: | ---: |"]
    for r in rows[:cap]:
        lines.append(
            f"| {r['change']} | {r.get('set') or '—'} | {r.get('collector_number') or '—'} "
            f"| {r.get('name') or '—'} | {r['finish']} | {r['qty_landing']} | {r['qty_incoming']} |"
        )
    if len(rows) > cap:
        lines.append(f"\n_…and {len(rows) - cap} more (see the XLSX/JSON artifact)._")
    return "\n".join(lines)


def write_diff_artifacts(diff: dict, *, direction: Direction, service: str,
                         stamp: str, mode: ApplyMode | None = None) -> dict:
    """Write the full diff to JSON + XLSX under ``output/collection-sync/diffs/``.

    ``stamp`` is a caller-supplied timestamp token (scripts stamp the time; the
    module stays clock-free so it's deterministic in tests). Returns
    ``{"json": Path, "xlsx": Path}``. Reuses ``util.output_dir`` + ``exports.xlsx``.
    """
    import json as _json
    from .exports import xlsx as xlsx_mod

    out_dir = util.output_dir("collection-sync", "diffs")
    base = f"{service}-{direction}-{stamp}"
    rows = _diff_rows_for_artifact(diff)

    json_path = out_dir / f"{base}.json"
    json_path.write_text(
        _json.dumps({"direction": direction, "service": service, "mode": mode,
                     "summary": {k: len(diff[k]) for k in ("added", "changed", "removed")}
                                | {"unchanged": diff["unchanged_count"]},
                     "rows": rows}, indent=2),
        encoding="utf-8",
    )

    headers = ["change", "set", "cn", "name", "finish", "landing", "incoming", "scryfall_id"]
    cell_rows = [[r["change"], r.get("set") or "", r.get("collector_number") or "",
                  r.get("name") or "", r["finish"], r["qty_landing"], r["qty_incoming"],
                  r.get("scryfall_id") or ""] for r in rows]
    sheets = [
        # text_cols=[3] forces the collector-number column to text (dodges
        # Excel's "number stored as text" coercion of CNs like "001"/"★").
        xlsx_mod.SheetSpec(title="diff", headers=headers, rows=cell_rows,
                           text_cols=[3], widths={4: 36, 8: 38}),
        xlsx_mod.meta_sheet([("direction", direction), ("service", service),
                             ("mode", mode or ""), ("stamp", stamp),
                             ("summary", diff_summary_line(diff))]),
    ]
    xlsx_path = out_dir / f"{base}.xlsx"
    xlsx_mod.write_workbook(xlsx_path, sheets)
    return {"json": json_path, "xlsx": xlsx_path}

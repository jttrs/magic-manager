"""``mm`` CLI: orchestrates set syncing, master-list generation, list import,
and exports.

Run via ``uv run mm …`` from the repo root.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import typer

from . import (
    db,
    decks as decks_mod,
    exports,
    intake as intake_mod,
    inventory as inv_mod,
    mtgjson as mtgjson_mod,
    selectors as sel_mod,
    sets as sets_mod,
    wishlist as wishlist_mod,
)

CHECKLISTS_DIR = Path("checklists")
PROCESSED_DIR = CHECKLISTS_DIR / "processed"
# Backwards-compat alias — older code paths and migration helpers reference
# INPUT_DIR. Both names point at the same Path; the directory itself was
# renamed from ``input/`` → ``checklists/`` in V1.6.
INPUT_DIR = CHECKLISTS_DIR

# Exit codes used by master-list collision detection. The `generate-set-list`
# skill reads these to decide whether to prompt for ingest-or-force.
EXIT_UNPROCESSED_INTAKE = 3
# Ingest collision: file SHA matches a prior successful ingest_log row.
EXIT_DUPLICATE_INGEST = 4

VALID_RARITIES = ("mythic", "rare", "uncommon", "common", "bonus", "special")

app = typer.Typer(no_args_is_help=True, add_completion=False,
                  help="Local-first MTG collection / set / wishlist manager.")
set_app = typer.Typer(no_args_is_help=True, help="Set sync and master-list generation.")
inventory_app = typer.Typer(no_args_is_help=True, help="Cards I physically own (V2 fact table).")
wishlist_app = typer.Typer(no_args_is_help=True, help="Cards I want, organized by free-text category.")
deck_app = typer.Typer(no_args_is_help=True, help="Decks: compositions independent of ownership.")
query_app = typer.Typer(no_args_is_help=True,
                        help="Run V2 selector queries against the local DB (show/value/xlsx/url/top/total/multiples/stats).")

checklists_app = typer.Typer(no_args_is_help=True,
                             help="Inspect inventory checklists in checklists/.")
mtgjson_app = typer.Typer(no_args_is_help=True,
                          help="Read MTGJSON.com data (precon decks, set files, etc.).")
db_app = typer.Typer(no_args_is_help=True,
                     help="Manage the local SQLite DB: snapshots, restore, integrity.")

app.add_typer(set_app, name="set")
app.add_typer(inventory_app, name="inventory")
app.add_typer(wishlist_app, name="wishlist")
app.add_typer(deck_app, name="deck")
app.add_typer(query_app, name="query")
app.add_typer(checklists_app, name="checklists")
# Back-compat alias for muscle memory: ``mm input list`` still works.
app.add_typer(checklists_app, name="input")
app.add_typer(mtgjson_app, name="mtgjson")
app.add_typer(db_app, name="db")


def _slug(s: str) -> str:
    raw = "".join(c if c.isalnum() else "-" for c in s.lower())
    # Collapse runs of hyphens so "Final Fantasy: Through the Ages" → "final-fantasy-through-the-ages"
    # rather than "final-fantasy--through-the-ages".
    while "--" in raw:
        raw = raw.replace("--", "-")
    return raw.strip("-")


# ---------- set ----------

@set_app.command("list-related")
def set_list_related(name_or_code: str = typer.Argument(...)):
    """Show parent + sibling/child sets for the user's confirmation step."""
    try:
        r = sets_mod.resolve(name_or_code)
    except LookupError as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
    typer.echo(f"Parent: {r.code} ({r.name})")
    typer.echo("Related sets:")
    for s in r.related:
        marker = "  *" if s["code"] == r.code else "   "
        typer.echo(f"{marker} {s['code']:6}  {s.get('set_type','?'):14}  "
                   f"{s.get('card_count','?'):>5} cards  {s['name']}")


@set_app.command("sync")
def set_sync(
    name_or_code: str = typer.Argument(...),
    include_related: bool = typer.Option(False, "--include-related",
                                         help="Sync parent + every sibling/child set."),
    only: list[str] = typer.Option(None, "--only", help="Restrict to these set codes (comma-separated)."),
):
    """Resolve and sync set(s) into the local cards table."""
    try:
        r = sets_mod.resolve(name_or_code)
    except LookupError as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)

    codes = r.all_codes if include_related else [r.code]
    if only:
        wanted = {c.strip().lower() for raw in only for c in raw.split(",")}
        codes = [c for c in codes if c in wanted]
        if not codes:
            typer.echo("error: --only filtered out all sets", err=True); raise typer.Exit(2)

    typer.echo(f"Syncing {len(codes)} set(s): {' '.join(codes)}")
    n = sets_mod.sync(codes)
    typer.echo(f"  → {n} cards upserted")


def _slice_suffix(*, only_codes: list[str], rarities: list[str]) -> str:
    """Build the filename slice suffix from optional set-code and rarity slices.

    No slice → ``""`` (empty — the unsliced default; filename has no slice token).
    Codes only → ``codes-joined-by-plus``.
    Rarities only → ``rarities-joined-by-plus``.
    Both → ``codes-rarities``.
    """
    parts: list[str] = []
    if only_codes:
        parts.append("+".join(only_codes))
    if rarities:
        parts.append("+".join(rarities))
    return "-".join(parts)


def _intake_path(slug: str, slice_suffix: str = "", ext: str = "xlsx", mode: str = "add") -> Path:
    # Filename shape: ``<slug>[-<slice>]-<mode>-checklist.<ext>``.
    # ``mode`` is ``add`` (default; blank-qty checklist for additive ingest)
    # or ``modify`` (prefilled-qty checklist for replace ingest). The mode
    # token in the filename is critical because cmux/Finder show filenames
    # without exposing _meta — surface intent on disk. Slice suffix encodes
    # the optional ``--only`` and ``--rarity`` filters; pre-V1.6 used an
    # explicit ``master`` token instead of an empty slice.
    middle = f"-{slice_suffix}" if slice_suffix else ""
    return CHECKLISTS_DIR / f"{slug}{middle}-{mode}-checklist.{ext}"


def _processed_path(slug: str, slice_suffix: str = "",
                    when: datetime | None = None, ext: str = "xlsx") -> Path:
    when = when or datetime.now()
    middle = f"-{slice_suffix}" if slice_suffix else ""
    return PROCESSED_DIR / f"{slug}{middle}-checklist-{when:%Y-%m-%d-%H%M%S}.{ext}"


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _split_csv(values: list[str] | None) -> list[str]:
    """Flatten a list of strings (each potentially comma-separated) into a
    deduplicated, lowercased list. Lets ``--include token,memorabilia`` and
    ``--include token --include memorabilia`` mean the same thing."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        for part in raw.split(","):
            v = part.strip().lower()
            if v and v not in seen:
                seen.add(v)
                out.append(v)
    return out


def _resolve_codes(name_or_code: str, *, include_kinds: list[str], only: list[str]
                   ) -> tuple[sets_mod.ResolvedSet, list[str]]:
    r = sets_mod.resolve(name_or_code)
    only_codes = _split_csv(only)
    kinds = _split_csv(include_kinds)
    if only_codes:
        wanted = set(only_codes)
        codes = [c for c in r.all_codes if c in wanted]
    else:
        codes = r.filtered_codes(include_kinds=kinds)
    if not codes:
        raise typer.BadParameter("set selection produced 0 codes")
    return r, codes


@set_app.command("master-list")
def set_master_list(
    name_or_code: str = typer.Argument(...),
    only: list[str] = typer.Option(
        None, "--only",
        help="Hard subset of codes (comma-separated). Bypasses the default set-type filter.",
    ),
    include: list[str] = typer.Option(
        None, "--include",
        help="Opt extra set_types into the family beyond the default "
             "(expansion/commander/masterpiece/promo). E.g. --include token,memorabilia.",
    ),
    rarity: list[str] = typer.Option(
        None, "--rarity",
        help="Slice by rarity (repeatable, comma-OK). Values: "
             "mythic|rare|uncommon|common|bonus|special. Output filename gets a "
             "rarity suffix and ingest of this file only touches rows of the "
             "given rarity.",
    ),
    out: Path = typer.Option(
        None, "--out",
        help="Override output path. When set, collision detection is skipped.",
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Overwrite an existing inventory checklist without prompting.",
    ),
    fmt: str = typer.Option(
        "xlsx", "--format",
        help="Output format: 'xlsx' (default; clickable Scryfall hyperlinks) "
             "or 'md' (markdown checklist editable in any text editor).",
    ),
    include_variants: bool = typer.Option(
        False, "--include-variants",
        help="Include prerelease, store-stamped, japanshowcase, serialized, "
             "and white/yellow-bordered variants. Off by default — these are "
             "filtered out of the inventory checklist AND the seeded set:<anchor> list "
             "so set-missing math doesn't count them.",
    ),
    mode: str = typer.Option(
        "add", "--mode",
        help="'add' (default): blank checklist for additive ingest — qty>0 "
             "cells sum into existing inventory; safe (cannot zero rows). Use "
             "for new acquisitions (booster packs, precons, trade-ins). "
             "'modify': prefilled checklist for replace ingest — in-partition "
             "cells overwrite DB qty AND missing in-partition rows zero out. "
             "Use to correct existing records (sold cards, miscounts, audits).",
    ),
):
    """Build the inventory checklist for a release family or a slice of it.

    The default family is the anchor set + every related set whose set_type
    is in {expansion, commander, masterpiece, promo}. Tokens, memorabilia
    (art series, scene boxes), and other set_types are excluded by default;
    opt them in with ``--include token,memorabilia``.

    The checklist lands at ``input/<slug>-<slice>.<ext>`` where ``<slice>``
    encodes the optional ``--only`` and ``--rarity`` filters (or ``master``
    if neither is given) and ``<ext>`` is ``xlsx`` (default) or ``md``.
    There can be at most one active inventory checklist per slice + format
    at a time; if one exists, the command refuses with exit
    ``EXIT_UNPROCESSED_INTAKE`` (3). Either ingest that file first via
    ``mm set ingest`` or pass ``--force``.
    """
    fmt = fmt.lower()
    if fmt not in ("xlsx", "md"):
        typer.echo(f"error: --format must be 'xlsx' or 'md', got {fmt!r}", err=True)
        raise typer.Exit(2)
    mode = mode.lower()
    if mode not in ("add", "modify"):
        typer.echo(f"error: --mode must be 'add' or 'modify', got {mode!r}", err=True)
        raise typer.Exit(2)
    try:
        r, codes = _resolve_codes(name_or_code, include_kinds=list(include or []), only=list(only or []))
    except (LookupError, typer.BadParameter) as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)

    only_codes = _split_csv(only)
    rarities = _split_csv(rarity)
    bad = [rr for rr in rarities if rr not in VALID_RARITIES]
    if bad:
        typer.echo(f"error: invalid --rarity value(s): {bad}; expected one of {VALID_RARITIES}", err=True)
        raise typer.Exit(2)

    slug = _slug(r.name)
    slice_suffix = _slice_suffix(only_codes=only_codes, rarities=rarities)
    out_path = out or _intake_path(slug, slice_suffix, ext=fmt, mode=mode)

    # Collision detection: only when the user is using the default path.
    if out is None and out_path.exists() and not force:
        typer.echo(f"refusing to overwrite existing inventory checklist: {out_path}", err=True)
        # Snapshot the current inventory rows that fall in this set's family.
        inv_rows = [r for r in inv_mod.inventory_show() if r.set_code in codes]
        if inv_rows:
            total_qty = sum(r.quantity for r in inv_rows)
            total_value = sum((r.line_value or 0.0) for r in inv_rows)
            typer.echo(
                f"  {len(inv_rows)} (card,finish) row(s) currently owned in this family, "
                f"qty {total_qty}, value ${total_value:.2f}",
                err=True,
            )
            top = sorted(inv_rows, key=lambda x: (x.line_value or 0.0), reverse=True)[:5]
            if top:
                typer.echo("  top by value:", err=True)
                for row in top:
                    price = f"${row.unit_price:.2f}" if row.unit_price is not None else "—"
                    typer.echo(
                        f"    {row.quantity}x {row.display_name} ({row.set_code.upper()}) "
                        f"{row.collector_number} [{row.finish}] @ {price}",
                        err=True,
                    )
        else:
            typer.echo(f"  no inventory rows yet in family {codes}", err=True)
        typer.echo("", err=True)
        typer.echo("To proceed, either:", err=True)
        typer.echo(f"  - Finish editing the existing XLSX, then: mm set ingest {name_or_code!r}", err=True)
        typer.echo(f"  - Discard partial edits and regenerate: mm set master-list {name_or_code!r} --force", err=True)
        raise typer.Exit(EXIT_UNPROCESSED_INTAKE)

    typer.echo(f"Syncing {len(codes)} set(s): {' '.join(codes)}")
    n_synced = sets_mod.sync(codes)
    typer.echo(f"  → {n_synced} cards upserted")

    target_result = sets_mod.register_set_target(
        r.code, codes, include_variants=include_variants, rarity_filter=rarities or None,
    )
    typer.echo(f"Registered set_target {r.code!r} ({target_result['action']}, "
               f"{len(target_result['related_codes'])} related code(s))")

    if force and out_path.exists():
        typer.echo(f"  ! --force: overwriting {out_path}", err=True)

    writer = (
        sets_mod.write_master_list_md if fmt == "md"
        else sets_mod.write_master_list_xlsx
    )
    n_rows, prefilled = writer(
        codes, out_path,
        # Tokens and memorabilia are governed by the family filter, not by a
        # second flag. If the user --included them they're in `codes` already.
        include_tokens=True,
        # mode='modify' prefills qty cells from current inventory (intended
        # for replace-style ingest). mode='add' leaves them blank (intended
        # for additive ingest of new acquisitions).
        prepopulate_from_inventory=(mode == "modify"),
        rarity_filter=rarities or None,
        anchor_code=r.code,
        slug=slug,
        include_variants=include_variants,
        mode=mode,
    )
    typer.echo(f"Wrote {n_rows} rows to {out_path} (mode={mode})")
    if prefilled:
        typer.echo(f"  → {prefilled} qty cell(s) pre-filled from inventory")
    typer.echo()
    typer.echo("Next steps:")
    if mode == "add":
        verb = "fill in qty_normal / qty_foil for the cards you're ADDING (cells start blank)"
    else:
        verb = "edit qty_normal / qty_foil to MODIFY existing inventory (prefilled values shown)"
    if fmt == "md":
        typer.echo(f"  1. Open {out_path} in any text editor and edit `[N:k F:k]` quantities ({verb}).")
    else:
        typer.echo(f"  1. Open {out_path} in Excel/Numbers — {verb}.")
    typer.echo(f"  2. When done: mm set ingest {name_or_code!r}  (auto-detects mode={mode} from _meta)")


@set_app.command("ingest")
def set_ingest(
    name_or_code: str = typer.Argument(
        None,
        help="Set name or code. Optional when --path is given AND the file has a _meta sheet.",
    ),
    path: Path = typer.Option(
        None, "--path",
        help="Override path to the inventory checklist. Default: input/<slug>-master.xlsx.",
    ),
    mode: str = typer.Option(
        None, "--mode",
        help="OPTIONAL OVERRIDE. 'replace' (in-partition cells overwrite DB qty; "
             "missing in-partition rows zero out) or 'additive' (only qty>0 cells "
             "add to existing). Default: auto-detect from the checklist's _meta.mode "
             "('modify' → replace, 'add' → additive). Pass --mode explicitly only to "
             "override the file's declared intent (logs a stderr warning) OR for "
             "legacy files with no _meta.mode.",
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Re-ingest even if this exact file (by SHA-256) succeeded previously.",
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit a single JSON document on stdout summarizing the run "
             "(for the /ingest-new-inventory-list slash command).",
    ),
):
    """Ingest a filled-in inventory checklist, then archive it under input/processed/.

    Imports the qty_normal / qty_foil cells into ``set:<anchor>`` honoring
    the file's partition (set codes + rarity from ``_meta`` or inferred from
    rows), then atomically renames the file with a timestamp so the next
    ``mm set master-list`` run will produce a fresh inventory checklist
    pre-populated from the now-saved DB state.

    The ingest mode is read from the checklist's _meta sheet by default
    (``modify`` checklists → replace semantics, ``add`` checklists → additive
    semantics). Pass ``--mode`` explicitly to override; the override is honored
    with a stderr warning when it disagrees with the file's declared mode.
    """
    if mode is not None and mode not in ("replace", "additive"):
        typer.echo(f"error: --mode must be 'replace' or 'additive', got {mode!r}", err=True)
        raise typer.Exit(2)

    # Resolve path + anchor. Either name_or_code or --path must give us enough.
    if path is not None:
        src = path
        if not src.exists():
            typer.echo(f"error: no inventory checklist found at {src}", err=True)
            raise typer.Exit(2)
        # Try the file's _meta first; fall back to name_or_code arg.
        meta = sets_mod.read_master_list_meta(src)
        if meta and meta.get("anchor_code"):
            anchor = meta["anchor_code"]
            slug = meta.get("slug") or _slug(anchor)
        elif name_or_code:
            try:
                r = sets_mod.resolve(name_or_code)
            except LookupError as e:
                typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
            anchor = r.code
            slug = _slug(r.name)
        else:
            typer.echo(
                "error: --path file has no _meta sheet; pass NAME_OR_CODE to disambiguate",
                err=True,
            )
            raise typer.Exit(2)
    else:
        if not name_or_code:
            typer.echo("error: provide either NAME_OR_CODE or --path", err=True)
            raise typer.Exit(2)
        try:
            r = sets_mod.resolve(name_or_code)
        except LookupError as e:
            typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
        anchor = r.code
        slug = _slug(r.name)
        # Look for intake docs matching this family's slug, in either format.
        # There can be more than one (master + rarity slices, or both xlsx and
        # md side-by-side); if exactly one matches use it, otherwise force the
        # user to disambiguate via --path.
        candidates = []
        if INPUT_DIR.exists():
            for ext in ("xlsx", "md"):
                candidates.extend(INPUT_DIR.glob(f"{slug}-*.{ext}"))
            candidates = sorted(candidates)
        if not candidates:
            typer.echo(f"error: no inventory checklist (.xlsx/.md) found in {INPUT_DIR}/ for slug {slug!r}", err=True)
            typer.echo(f"  run `mm set master-list {name_or_code!r}` first", err=True)
            raise typer.Exit(2)
        if len(candidates) > 1:
            typer.echo(
                f"error: multiple inventory checklists match slug {slug!r}; "
                "pass --path to choose:",
                err=True,
            )
            for c in candidates:
                typer.echo(f"  - {c}", err=True)
            raise typer.Exit(2)
        src = candidates[0]

    # ---- Mode resolution: auto-detect from _meta.mode, reconcile with --mode ----
    # Read _meta unconditionally now (the path-resolution branches above may
    # or may not have already done so). Source of truth is the file we're
    # about to ingest, regardless of how we found it.
    file_meta = sets_mod.read_master_list_meta(src) or {}
    declared_meta_mode = file_meta.get("mode")  # 'modify', 'add', or None (legacy)
    declared_to_op = {"modify": "replace", "add": "additive"}
    declared_op = declared_to_op.get(declared_meta_mode)  # 'replace', 'additive', or None
    if mode is None:
        # No explicit override → use the file's declared mode.
        if declared_op is None:
            typer.echo(
                f"error: this checklist has no _meta.mode (likely generated before "
                f"mode-aware tagging). Pass --mode replace or --mode additive "
                f"explicitly to ingest it.",
                err=True,
            )
            raise typer.Exit(2)
        mode = declared_op
    elif declared_op is not None and declared_op != mode:
        # User passed --mode AND it disagrees with the file's declaration.
        # Honor the override but warn loudly — getting this wrong on a
        # 'modify' checklist run as 'additive' (or vice versa) silently
        # corrupts the inventory state.
        typer.echo(
            f"warning: file's _meta.mode is {declared_meta_mode!r} (would ingest "
            f"as {declared_op!r}); --mode override is {mode!r} — applying "
            f"{mode!r} as requested. If this is wrong, ctrl-C now.",
            err=True,
        )
    # else: --mode passed and either agrees with declared OR file is legacy
    # (declared_op is None and user provided explicit --mode, which is fine).

    # Hash + duplicate check.
    sha = _file_sha256(src)
    with db.connect() as conn:
        prior = db.find_ingest_log_by_hash(conn, sha)
    prior_success = next((p for p in prior if p["status"] == "success"), None)
    if prior_success and not force:
        msg = (
            f"this file's SHA-256 matches a previous successful ingest "
            f"(log id {prior_success['id']}, "
            f"mode {prior_success['mode']}, at {prior_success['at']})."
        )
        if json_out:
            json.dump({
                "status": "duplicate",
                "file": str(src),
                "sha256": sha,
                "prior_log": prior_success,
                "message": msg,
            }, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            typer.echo(f"refusing to re-ingest: {msg}", err=True)
            typer.echo("  pass --force to proceed (the file will be re-applied "
                       "in the chosen --mode and a new log row will be added).", err=True)
        raise typer.Exit(EXIT_DUPLICATE_INGEST)

    # Run the actual import — V2 path writes directly to the inventory table,
    # honoring the file's partition (set codes + rarity from _meta or rows).
    error: str | None = None
    result: dict | None = None
    try:
        result = sets_mod.ingest_inventory_from_xlsx(src, mode=mode)
    except Exception as e:
        error = repr(e)

    archived: Path | None = None
    if result is not None:
        # Compute slice suffix from the file's stem for the archive name.
        # Possible stems:
        #   <slug>-checklist           → unsliced (V1.6+)
        #   <slug>-<slice>-checklist   → sliced (V1.6+)
        #   <slug>-<slice>             → pre-V1.6 file the user hand-renamed
        #   <slug>                     → pre-V1.6 unsliced (rare)
        # Strip ``-checklist`` first so the rest is just ``<slug>[-<slice>]``.
        stem = src.stem
        if stem.endswith("-checklist"):
            stem = stem[: -len("-checklist")]
        if stem == slug:
            slice_suffix = ""
        elif stem.startswith(f"{slug}-"):
            slice_suffix = stem[len(slug) + 1:]
        else:
            slice_suffix = stem
        ext = src.suffix.lstrip(".") or "xlsx"
        archived = _processed_path(slug, slice_suffix, ext=ext)
        archived.parent.mkdir(parents=True, exist_ok=True)
        src.rename(archived)

    # Persist the log entry. The label column now records the set anchor as
    # a 'set:<code>' string for backwards compatibility with the ingest_log
    # schema; the row no longer means a list_rows row exists.
    log_label = f"set:{anchor}"
    with db.connect() as conn:
        db.record_ingest_log(
            conn,
            label=log_label,
            mode=mode,
            source_path=str(src),
            archived_path=str(archived) if archived else None,
            file_sha256=sha,
            rows_added=(result or {}).get("added", 0),
            rows_updated=(result or {}).get("updated", 0),
            rows_zeroed=(result or {}).get("zeroed", 0),
            status="success" if error is None else "failed",
            error=error,
        )

    # Snapshot inventory in this set's family post-ingest.
    inv_summary = None
    if error is None:
        try:
            family_codes = set(sets_mod.resolve(anchor).all_codes)
        except LookupError:
            family_codes = {anchor}
        inv_rows = [r for r in inv_mod.inventory_show() if r.set_code in family_codes]
        inv_summary = {
            "distinct_rows": len(inv_rows),
            "total_qty": sum(r.quantity for r in inv_rows),
            "total_value": sum((r.line_value or 0.0) for r in inv_rows),
        }

    if json_out:
        out = {
            "status": "success" if error is None else "failed",
            "file": str(src),
            "archived_path": str(archived) if archived else None,
            "anchor_code": anchor,
            "mode": mode,
            "sha256": sha,
            "rows_added": (result or {}).get("added", 0),
            "rows_updated": (result or {}).get("updated", 0),
            "rows_zeroed": (result or {}).get("zeroed", 0),
            "warnings": (result or {}).get("warnings", []),
            "not_found": (result or {}).get("not_found", []),
            "extras": (result or {}).get("extras", []),
            "inventory_summary": inv_summary,
            "error": error,
        }
        json.dump(out, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        if error is not None:
            raise typer.Exit(2)
        return

    if error is not None:
        typer.echo(f"error: ingest failed: {error}", err=True)
        raise typer.Exit(2)

    typer.echo(
        f"Inventory ({anchor}): {result['updated']} updated, "
        f"{result['added']} added, {result['zeroed']} zeroed (mode={mode})"
    )
    for w in result["warnings"]:
        typer.echo(f"  warning: {w}", err=True)
    for nf in result["not_found"]:
        if "raw" in nf:
            typer.echo(f"  not found: {nf['raw']} ({nf.get('reason','')})", err=True)
        else:
            typer.echo(f"  not found: {nf}", err=True)
    for ex in result["extras"]:
        typer.echo(f"  extra (outside file's partition): {ex['raw']}", err=True)
    typer.echo(f"Archived inventory checklist → {archived}")
    if inv_summary:
        typer.echo(
            f"Inventory in {anchor} family: {inv_summary['distinct_rows']} rows, "
            f"qty {inv_summary['total_qty']}, value ${inv_summary['total_value']:.2f}"
        )


# ---------- inventory (V2) ----------

def _read_text_or_path(source: str | None) -> tuple[str | None, Path | None]:
    """Resolve the (text, path) tuple for an import source argument.

    None or '-' means stdin. A non-existent path errors out.
    """
    if source is None or source == "-":
        return sys.stdin.read(), None
    p = Path(source)
    if not p.exists():
        typer.echo(f"error: file not found: {p}", err=True); raise typer.Exit(2)
    return None, p


def _resolve_block(text: str | None, path: Path | None):
    """Parse a text block / file with parsers.parse_text + resolve.

    Returns the ParseResult. Caller decides how to route entries into the
    target table (inventory / wishlist / deck_cards).
    """
    from . import parsers as _parsers
    if path is not None:
        fmt = _parsers.detect_format(path)
        if fmt == "xlsx":
            result = _parsers.parse_master_list_xlsx(path)
        elif fmt == "md":
            result = _parsers.parse_master_list_md(path)
        else:
            result = _parsers.parse_text(path.read_text(encoding="utf-8"))
    else:
        result = _parsers.parse_text(text)
    _parsers.resolve(result)
    return result


@inventory_app.command("show")
def inventory_show_cmd():
    """Show every printing in inventory with quantities and current value."""
    rows = inv_mod.inventory_show()
    if not rows:
        typer.echo("(inventory empty)"); return
    typer.echo(f"{'qty':>4} {'finish':>7} {'set':>6} {'cn':>6}  name (rarity, usd)")
    for r in rows:
        usd = f"${r.unit_price:.2f}" if r.unit_price is not None else "—"
        typer.echo(f"{r.quantity:>4} {r.finish:>7} {r.set_code:>6} "
                   f"{r.collector_number:>6}  {r.display_name} ({r.rarity}, {usd})")


@inventory_app.command("value")
def inventory_value_cmd():
    """Total inventory value in USD."""
    v = inv_mod.inventory_value()
    typer.echo(f"Inventory: ${v['total']:.2f} across {v['rows']} rows")
    if v["missing_price"]:
        typer.echo(f"Cards without USD price ({len(v['missing_price'])}):")
        for name, set_code, cn, finish in v["missing_price"]:
            typer.echo(f"  {name} ({set_code.upper()}) {cn} [{finish}]")


@inventory_app.command("add")
def inventory_add_cmd(
    scryfall_id: str = typer.Argument(...),
    finish: str = typer.Argument(..., help="nonfoil | foil"),
    qty: int = typer.Argument(1),
    replace: bool = typer.Option(False, "--replace", help="Set quantity outright instead of summing."),
):
    """Add (or replace) a single printing in inventory."""
    try:
        result = inv_mod.inventory_add(scryfall_id, finish, qty, replace=replace)
    except ValueError as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
    typer.echo(f"{result['action']}: {scryfall_id} {finish} qty={result['new_qty']}")


@inventory_app.command("remove")
def inventory_remove_cmd(
    scryfall_id: str = typer.Argument(...),
    finish: str = typer.Argument(..., help="nonfoil | foil"),
    qty: int = typer.Option(None, "--qty", help="Subtract this many (omit to delete the row)."),
):
    """Remove (or decrement) a single printing in inventory."""
    result = inv_mod.inventory_remove(scryfall_id, finish, qty)
    typer.echo(f"{result['action']}: {scryfall_id} {finish} new_qty={result['new_qty']}")


@inventory_app.command("import")
def inventory_import_cmd(
    source: str = typer.Argument(None, help="Path to file (XLSX/text) or '-' for stdin."),
):
    """Read a Moxfield-style block (stdin or file) and add to inventory.

    Insert-or-sum semantics: re-importing the same block doubles the qty.
    Use ``mm inventory remove`` or ``mm inventory add --replace`` to undo.
    """
    text, path = _read_text_or_path(source)
    result = _resolve_block(text, path)
    added = updated = 0
    with db.connect() as conn:
        for entry in result.entries:
            if entry.card is None:
                continue
            db.upsert_card(conn, entry.card)
    for entry in result.entries:
        if entry.card is None:
            continue
        finish = "foil" if entry.foil else "nonfoil"
        r = inv_mod.inventory_add(entry.card["id"], finish, entry.qty)
        if r["action"] == "inserted":
            added += 1
        else:
            updated += 1
    typer.echo(f"Inventory: {added} added, {updated} updated")
    for w in result.warnings:
        typer.echo(f"  warning: {w}", err=True)
    for nf in result.not_found:
        if isinstance(nf, dict) and "raw" in nf:
            typer.echo(f"  not found: {nf['raw']} ({nf.get('reason','')})", err=True)
        else:
            typer.echo(f"  not found: {nf}", err=True)


# ---------- wishlist (V2) ----------

@wishlist_app.command("show")
def wishlist_show_cmd(
    category: str = typer.Option(None, "--category", "-c", help="Filter to one category."),
):
    """Show wishlist entries (optionally filtered to one category)."""
    rows = wishlist_mod.wishlist_show(category=category)
    if not rows:
        scope = f"category={category!r}" if category else "all categories"
        typer.echo(f"(wishlist empty for {scope})"); return
    typer.echo(f"{'qty':>4} {'finish':>7} {'set':>6} {'cn':>6}  category   name (rarity, usd)")
    for r in rows:
        usd = f"${r.unit_price:.2f}" if r.unit_price is not None else "—"
        typer.echo(f"{r.qty_wanted:>4} {r.finish:>7} {r.set_code:>6} "
                   f"{r.collector_number:>6}  {r.category:10} {r.display_name} ({r.rarity}, {usd})")


@wishlist_app.command("categories")
def wishlist_categories_cmd():
    """List distinct wishlist categories with row/qty counts."""
    cats = wishlist_mod.wishlist_categories()
    if not cats:
        typer.echo("(no wishlist entries)"); return
    typer.echo(f"{'category':30} {'rows':>6} {'qty':>6}")
    for c in cats:
        typer.echo(f"{c['category']:30} {c['rows']:>6} {c['total_qty']:>6}")


@wishlist_app.command("value")
def wishlist_value_cmd(
    category: str = typer.Option(None, "--category", "-c"),
):
    """Total wishlist value in USD (acquisition floor)."""
    v = wishlist_mod.wishlist_value(category=category)
    scope = f"({category})" if category else "(all)"
    typer.echo(f"Wishlist {scope}: ${v['total']:.2f} across {v['rows']} rows")
    if v["missing_price"]:
        typer.echo(f"Cards without USD price ({len(v['missing_price'])}):")
        for name, set_code, cn, finish in v["missing_price"]:
            typer.echo(f"  {name} ({set_code.upper()}) {cn} [{finish}]")


@wishlist_app.command("add")
def wishlist_add_cmd(
    scryfall_id: str = typer.Argument(...),
    finish: str = typer.Argument(..., help="nonfoil | foil | either"),
    category: str = typer.Argument("default"),
    qty: int = typer.Argument(1),
    priority: int = typer.Option(None, "--priority"),
    notes: str = typer.Option(None, "--notes"),
):
    """Add a single printing to a wishlist category."""
    try:
        result = wishlist_mod.wishlist_add(scryfall_id, finish, category, qty,
                                           priority=priority, notes=notes)
    except ValueError as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
    typer.echo(f"{result['action']}: {scryfall_id} {finish} {category} qty={result['new_qty']}")


@wishlist_app.command("remove")
def wishlist_remove_cmd(
    scryfall_id: str = typer.Argument(...),
    finish: str = typer.Argument(..., help="nonfoil | foil | either"),
    category: str = typer.Argument("default"),
    qty: int = typer.Option(None, "--qty"),
):
    """Remove a wishlist entry (or decrement its qty)."""
    result = wishlist_mod.wishlist_remove(scryfall_id, finish, category, qty)
    typer.echo(f"{result['action']}: {scryfall_id} {finish} {category} new_qty={result['new_qty']}")


@wishlist_app.command("import")
def wishlist_import_cmd(
    category: str = typer.Argument(...),
    source: str = typer.Argument(None, help="Path to file or '-' for stdin."),
    finish: str = typer.Option("either", "--finish", help="Default finish for imported lines."),
):
    """Read a Moxfield-style block and add to a wishlist category."""
    if finish not in ("nonfoil", "foil", "either"):
        typer.echo(f"error: --finish must be nonfoil|foil|either, got {finish!r}", err=True)
        raise typer.Exit(2)
    text, path = _read_text_or_path(source)
    result = _resolve_block(text, path)
    added = updated = 0
    with db.connect() as conn:
        for entry in result.entries:
            if entry.card is None:
                continue
            db.upsert_card(conn, entry.card)
    for entry in result.entries:
        if entry.card is None:
            continue
        # If the entry's parsed finish is foil, use that; otherwise the --finish default.
        eff_finish = "foil" if entry.foil else finish
        r = wishlist_mod.wishlist_add(entry.card["id"], eff_finish, category, entry.qty)
        if r["action"] == "inserted":
            added += 1
        else:
            updated += 1
    typer.echo(f"Wishlist {category!r}: {added} added, {updated} updated")
    for w in result.warnings:
        typer.echo(f"  warning: {w}", err=True)
    for nf in result.not_found:
        if isinstance(nf, dict) and "raw" in nf:
            typer.echo(f"  not found: {nf['raw']} ({nf.get('reason','')})", err=True)
        else:
            typer.echo(f"  not found: {nf}", err=True)


# ---------- deck (V2) ----------

@deck_app.command("ls")
def deck_ls_cmd():
    """List every deck."""
    ds = decks_mod.deck_list()
    if not ds:
        typer.echo("(no decks)"); return
    typer.echo(f"{'slug':30} {'name':40} {'format':12} {'updated_at'}")
    for d in ds:
        typer.echo(f"{d.slug:30} {d.name:40} {(d.format or '—'):12} {d.updated_at}")


@deck_app.command("show")
def deck_show_cmd(slug: str = typer.Argument(...)):
    """Show every card in a deck (all boards)."""
    try:
        rows = decks_mod.deck_show(slug)
    except LookupError as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
    if not rows:
        typer.echo(f"(deck {slug!r} is empty)"); return
    typer.echo(f"{'cnt':>4} {'finish':>7} {'board':>10} {'set':>6} {'cn':>6}  name (rarity, usd)")
    for r in rows:
        usd = f"${r.unit_price:.2f}" if r.unit_price is not None else "—"
        typer.echo(f"{r.count:>4} {r.finish:>7} {r.board:>10} {r.set_code:>6} "
                   f"{r.collector_number:>6}  {r.display_name} ({r.rarity}, {usd})")


@deck_app.command("create")
def deck_create_cmd(
    slug: str = typer.Argument(...),
    name: str = typer.Option(..., "--name"),
    format: str = typer.Option(None, "--format"),
    archetype: str = typer.Option(None, "--archetype"),
    notes: str = typer.Option(None, "--notes"),
):
    """Create a new (empty) deck."""
    try:
        d = decks_mod.deck_create(slug, name, format=format, archetype=archetype, notes=notes)
    except ValueError as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
    typer.echo(f"Created deck #{d.deck_id}: {d.slug} ({d.name})")


@deck_app.command("delete")
def deck_delete_cmd(
    slug: str = typer.Argument(...),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Delete a deck (cascades to deck_cards)."""
    if not yes:
        typer.echo("refusing without --yes; this deletes the deck and all its cards.", err=True)
        raise typer.Exit(2)
    n = decks_mod.deck_delete(slug)
    typer.echo(f"Deleted {n} deck(s)")


@deck_app.command("find")
def deck_find_cmd(
    query: str = typer.Argument(
        ...,
        help="A scryfall_id, a 'set cn' pair (QUOTED, e.g. 'fin 248'), or an exact card name (QUOTED if it has spaces). Tries each form in order.",
    ),
    json_out: bool = typer.Option(False, "--json"),
):
    """List every deck that contains a given printing.

    Resolution order: scryfall_id (UUID-shaped) → 'set cn' pair (two
    whitespace-separated tokens) → exact case-insensitive name match against
    cards.name OR cards.flavor_name. Reports per-deck commitments plus the
    inventory↔committed↔available math for the resolved scryfall_id.
    """
    import re as _re

    q = query.strip()
    candidates: list[str] = []  # scryfall_ids matching the query
    with db.connect() as conn:
        # Form 1: UUID-shaped → exact scryfall_id lookup.
        if _re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", q.lower()):
            r = conn.execute("SELECT scryfall_id FROM cards WHERE scryfall_id = ?", (q.lower(),)).fetchone()
            if r is not None:
                candidates.append(r["scryfall_id"])

        # Form 2: 'set cn' two-token form.
        if not candidates:
            parts = q.split()
            if len(parts) == 2:
                setc, cn = parts[0].lower(), parts[1]
                rows = conn.execute(
                    "SELECT scryfall_id FROM cards WHERE set_code = ? AND collector_number = ?",
                    (setc, cn),
                ).fetchall()
                candidates.extend(r["scryfall_id"] for r in rows)

        # Form 3: exact name (or flavor_name) match, case-insensitive.
        if not candidates:
            rows = conn.execute(
                "SELECT scryfall_id FROM cards "
                "WHERE LOWER(name) = ? OR LOWER(flavor_name) = ? "
                "ORDER BY set_code, collector_number",
                (q.lower(), q.lower()),
            ).fetchall()
            candidates.extend(r["scryfall_id"] for r in rows)

    if not candidates:
        typer.echo(f"no card found matching {query!r} (tried scryfall_id, 'set cn', and exact name)", err=True)
        raise typer.Exit(1)

    # For each candidate scryfall_id, gather (deck slug, board, finish, count)
    # plus inventory and computed available.
    results: list[dict] = []
    with db.connect() as conn:
        for sid in candidates:
            card = conn.execute(
                "SELECT name, flavor_name, set_code, collector_number, rarity FROM cards WHERE scryfall_id=?",
                (sid,),
            ).fetchone()
            deck_rows = conn.execute(
                "SELECT d.slug, dc.board, dc.finish, dc.count "
                "FROM deck_cards dc JOIN decks d ON d.deck_id = dc.deck_id "
                "WHERE dc.scryfall_id = ? "
                "ORDER BY d.slug, dc.board, dc.finish",
                (sid,),
            ).fetchall()
            inv_rows = conn.execute(
                "SELECT finish, quantity FROM inventory WHERE scryfall_id = ?",
                (sid,),
            ).fetchall()
            committed_by_finish: dict[str, int] = {}
            for r in deck_rows:
                committed_by_finish[r["finish"]] = committed_by_finish.get(r["finish"], 0) + r["count"]
            owned_by_finish = {r["finish"]: r["quantity"] for r in inv_rows}
            available_by_finish = {
                fin: max(0, owned_by_finish.get(fin, 0) - committed_by_finish.get(fin, 0))
                for fin in set(owned_by_finish) | set(committed_by_finish)
            }
            results.append({
                "scryfall_id": sid,
                "name": card["name"],
                "flavor_name": card["flavor_name"],
                "set": card["set_code"],
                "collector_number": card["collector_number"],
                "rarity": card["rarity"],
                "decks": [
                    {"slug": r["slug"], "board": r["board"], "finish": r["finish"], "count": r["count"]}
                    for r in deck_rows
                ],
                "owned": owned_by_finish,
                "committed": committed_by_finish,
                "available": available_by_finish,
            })

    if json_out:
        json.dump(results, sys.stdout, indent=2); sys.stdout.write("\n")
        return

    for res in results:
        flavor = res["flavor_name"]
        display = f"{flavor} / {res['name']}" if flavor else res["name"]
        setc = (res["set"] or "?").upper()
        cn = res["collector_number"] or "?"
        typer.echo(f"\n{display} ({setc} {cn}, {res['rarity']})  scryfall_id={res['scryfall_id']}")
        if not res["decks"]:
            typer.echo("  (not in any deck)")
        else:
            for dk in res["decks"]:
                typer.echo(f"  deck={dk['slug']:<30} board={dk['board']:<10} finish={dk['finish']:<8} count={dk['count']}")
        # Math line
        finish_keys = sorted(set(res["owned"]) | set(res["committed"]))
        for fin in finish_keys:
            o = res["owned"].get(fin, 0)
            c = res["committed"].get(fin, 0)
            a = res["available"].get(fin, 0)
            typer.echo(f"  {fin:>7}: owned={o}  committed={c}  available={a}")


@deck_app.command("value")
def deck_value_cmd(slug: str = typer.Argument(...)):
    """Total deck value in USD."""
    try:
        v = decks_mod.deck_value(slug)
    except LookupError as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
    typer.echo(f"Deck {slug!r}: ${v['total']:.2f} across {v['rows']} rows")
    if v["missing_price"]:
        typer.echo(f"Cards without USD price ({len(v['missing_price'])}):")
        for name, set_code, cn, finish in v["missing_price"]:
            typer.echo(f"  {name} ({set_code.upper()}) {cn} [{finish}]")


_BOARD_KEY_TO_NAME = (
    ("commander", "commander"),
    ("mainBoard", "main"),
    ("sideBoard", "side"),
)


@deck_app.command("import-precon")
def deck_import_precon_cmd(
    file_name: str = typer.Argument(
        ...,
        help="MTGJSON deck fileName (e.g. CounterBlitzFinalFantasyX_FIC). See `mm mtgjson decks` to list available precons.",
    ),
    slug: str = typer.Option(
        None, "--slug",
        help="Override the auto-derived slug. Defaults to slugified MTGJSON deck name; --copies>1 appends -2/-3/...",
    ),
    name: str = typer.Option(
        None, "--name",
        help="Override the deck's display name. Defaults to MTGJSON 'name' field.",
    ),
    copies: int = typer.Option(
        1, "--copies", min=1,
        help="Create N independent decks from this precon. First gets the bare slug; copies 2..N get -2, -3, ... suffixes.",
    ),
    add_inventory: bool = typer.Option(
        True, "--add-inventory/--no-add-inventory",
        help="Also add the precon's cards to inventory (default: yes). --no-add-inventory builds the deck composition without claiming physical ownership.",
    ),
    deconstruct: bool = typer.Option(
        False, "--deconstruct",
        help="Skip deck creation; only add cards to inventory. Use when opening a precon to break it down for parts.",
    ),
):
    """Import an MTGJSON precon into the local DB.

    By default: creates one or more named decks AND adds the cards to inventory.
    The two effects are independent — see --no-add-inventory and --deconstruct.

    The MTGJSON Card(Deck) entries carry `identifiers.scryfallId` which maps
    directly to our cards table. No Scryfall API calls; the precon JSON is
    cached after first fetch.
    """
    try:
        deck_data = mtgjson_mod.deck(file_name)
    except mtgjson_mod.MtgJsonError as e:
        typer.echo(f"error: could not fetch MTGJSON precon {file_name!r}: {e}", err=True)
        raise typer.Exit(2)

    deck_name = name or deck_data.get("name") or file_name
    base_slug = slug or _slug(deck_name)
    if not base_slug:
        typer.echo(f"error: could not derive slug from name {deck_name!r}; pass --slug", err=True)
        raise typer.Exit(2)

    # --- 1. Decide effective slugs (one per copy), checking collisions up-front. ---
    effective_slugs: list[str] = []
    if not deconstruct:
        for i in range(copies):
            s = base_slug if i == 0 else f"{base_slug}-{i+1}"
            if decks_mod.deck_get(s) is not None:
                typer.echo(
                    f"error: deck slug {s!r} already exists. Pass --slug to override "
                    f"or `mm deck delete {s}` to remove the existing deck first.",
                    err=True,
                )
                raise typer.Exit(2)
            effective_slugs.append(s)

    # --- 2. Create deck rows (skipped under --deconstruct). ---
    fmt = "commander" if deck_data.get("type", "").lower().startswith("commander") else None
    for s in effective_slugs:
        decks_mod.deck_create(s, deck_name, format=fmt)

    # --- 3. Walk boards, write deck_cards rows + accumulate inventory aggregates. ---
    deck_added = deck_updated = 0
    deck_card_qty = 0
    inv_aggregate: dict[tuple[str, str], int] = {}  # (scryfall_id, finish) → qty across all boards × copies
    missing_sids: list[dict] = []  # mtgjson entries with no scryfallId
    for mj_key, board_name in _BOARD_KEY_TO_NAME:
        for entry in deck_data.get(mj_key, []) or []:
            sid = (entry.get("identifiers") or {}).get("scryfallId")
            if not sid:
                missing_sids.append({
                    "name": entry.get("name"),
                    "set": entry.get("setCode"),
                    "cn": entry.get("number"),
                    "board": board_name,
                })
                continue
            count = int(entry.get("count", 1) or 1)
            finish = "foil" if entry.get("isFoil") else "nonfoil"
            for s in effective_slugs:
                r = decks_mod.deck_add_card(s, sid, board_name, finish, count)
                deck_card_qty += count
                if r["action"] == "inserted":
                    deck_added += 1
                else:
                    deck_updated += 1
            inv_aggregate[(sid, finish)] = inv_aggregate.get((sid, finish), 0) + count * copies

    # --- 4. Inventory aggregates (suppressed by --no-add-inventory or --deconstruct override). ---
    inv_added = inv_updated = 0
    inv_qty_total = 0
    if add_inventory:
        for (sid, finish), qty in inv_aggregate.items():
            r = inv_mod.inventory_add(sid, finish, qty)
            inv_qty_total += qty
            if r["action"] == "inserted":
                inv_added += 1
            else:
                inv_updated += 1

    # --- 5. Summary. ---
    if deconstruct:
        typer.echo(
            f"Imported precon {deck_name!r} as INVENTORY ONLY (--deconstruct): "
            f"{inv_added} new rows, {inv_updated} bumped, {inv_qty_total} total card-qty across "
            f"{len(inv_aggregate)} distinct (printing, finish) entries × {copies} copies."
        )
    else:
        slug_list = ", ".join(effective_slugs)
        typer.echo(
            f"Imported precon {deck_name!r} as {len(effective_slugs)} deck(s): {slug_list}. "
            f"Deck rows: {deck_added} added, {deck_updated} updated ({deck_card_qty} total card-qty)."
        )
        if add_inventory:
            typer.echo(
                f"Inventory: {inv_added} new rows, {inv_updated} bumped "
                f"({inv_qty_total} total card-qty)."
            )
        else:
            typer.echo("Inventory: skipped (--no-add-inventory).")

    if missing_sids:
        typer.echo(
            f"warning: {len(missing_sids)} entries had no scryfallId and were skipped:",
            err=True,
        )
        for m in missing_sids[:5]:
            typer.echo(f"  - {m['name']} ({m['set']} {m['cn']}, board={m['board']})", err=True)
        if len(missing_sids) > 5:
            typer.echo(f"  ...and {len(missing_sids) - 5} more", err=True)


@deck_app.command("import")
def deck_import_cmd(
    slug: str = typer.Argument(...),
    source: str = typer.Argument(None, help="Path to file or '-' for stdin."),
    board: str = typer.Option("main", "--board", help="main | side | commander | companion | maybe"),
):
    """Import a Moxfield-style block into a deck/board.

    The deck must already exist (use ``mm deck create``). All entries land
    on the given --board; for sideboards, run a second import with
    --board side.
    """
    if board not in ("main", "side", "commander", "companion", "maybe"):
        typer.echo(f"error: --board must be one of main/side/commander/companion/maybe, got {board!r}", err=True)
        raise typer.Exit(2)
    if decks_mod.deck_get(slug) is None:
        typer.echo(f"error: no deck {slug!r}; create with `mm deck create`", err=True)
        raise typer.Exit(2)
    text, path = _read_text_or_path(source)
    result = _resolve_block(text, path)
    with db.connect() as conn:
        for entry in result.entries:
            if entry.card is None:
                continue
            db.upsert_card(conn, entry.card)
    added = updated = 0
    for entry in result.entries:
        if entry.card is None:
            continue
        finish = "foil" if entry.foil else "nonfoil"
        r = decks_mod.deck_add_card(slug, entry.card["id"], board, finish, entry.qty)
        if r["action"] == "inserted":
            added += 1
        else:
            updated += 1
    typer.echo(f"Deck {slug!r} (board={board}): {added} added, {updated} updated")
    for w in result.warnings:
        typer.echo(f"  warning: {w}", err=True)
    for nf in result.not_found:
        if isinstance(nf, dict) and "raw" in nf:
            typer.echo(f"  not found: {nf['raw']} ({nf.get('reason','')})", err=True)
        else:
            typer.echo(f"  not found: {nf}", err=True)


# ---------- query (V2 selectors) ----------

QUERIES_DIR = Path("queries")


def _selector_slug(selector: str) -> str:
    """Slugify a selector string for use in artifact filenames.

    Deterministic: same selector always produces the same slug. Lowercases,
    keeps alphanumerics, collapses everything else to a single hyphen,
    trims leading/trailing hyphens.
    """
    raw = "".join(c if c.isalnum() else "-" for c in selector.lower())
    while "--" in raw:
        raw = raw.replace("--", "-")
    return raw.strip("-")


def _materialize_or_die(selector: str):
    try:
        return sel_mod.materialize(selector)
    except sel_mod.SelectorParseError as e:
        typer.echo(f"error: invalid selector: {e}", err=True); raise typer.Exit(2)
    except LookupError as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)


def _row_unit_price(r: sel_mod.MaterializedRow) -> float | None:
    if r.finish == "foil":
        return r.card.get("prices_usd_foil")
    return r.card.get("prices_usd")


def _row_line_value(r: sel_mod.MaterializedRow) -> float | None:
    p = _row_unit_price(r)
    return p * r.quantity if p is not None else None


def _row_display_name(r: sel_mod.MaterializedRow) -> str:
    flavor = r.card.get("flavor_name")
    name = r.card.get("name") or ""
    return f"{flavor} / {name}" if flavor else name


_RARITY_RANK = {"mythic": 0, "rare": 1, "uncommon": 2, "common": 3,
                "special": 4, "bonus": 5}
_VALID_SORTS = ("default", "value-desc", "value-asc", "rarity")


def _apply_sort(rows: list[sel_mod.MaterializedRow], sort_key: str) -> list[sel_mod.MaterializedRow]:
    """Apply a named sort to materialized rows, with deterministic tie-breaking.

    'default' is a no-op — the materializer already sorts by (set, cn, finish).
    'value-desc' / 'value-asc' use line value. Unpriced rows always sink to
    the BOTTOM (regardless of direction) — None is informationally similar to
    'unknown' rather than 'cheapest', so surfacing it at the top of value-asc
    would mislead someone scanning for low-hanging fruit. 'rarity' orders
    mythic > rare > uncommon > common > special > bonus. All sorts break ties
    on (set, cn, finish).
    """
    if sort_key == "default":
        return rows
    if sort_key not in _VALID_SORTS:
        typer.echo(f"error: --sort must be one of {_VALID_SORTS}, got {sort_key!r}", err=True)
        raise typer.Exit(2)

    def tie(r: sel_mod.MaterializedRow):
        return (r.card.get("set") or "", r.card.get("collector_number") or "", r.finish)

    if sort_key == "value-desc":
        # Unpriced rows go to the bottom: priority bit 1 for unpriced, 0 for priced.
        return sorted(rows, key=lambda r: (
            0 if _row_line_value(r) is not None else 1,
            -(_row_line_value(r) or 0.0),
            tie(r),
        ))
    if sort_key == "value-asc":
        # Same priority bit so unpriced rows stay at the bottom in asc too.
        return sorted(rows, key=lambda r: (
            0 if _row_line_value(r) is not None else 1,
            _row_line_value(r) if _row_line_value(r) is not None else 0.0,
            tie(r),
        ))
    if sort_key == "rarity":
        return sorted(rows, key=lambda r: (_RARITY_RANK.get((r.card.get("rarity") or "").lower(), 99), tie(r)))
    return rows


@query_app.command("show")
def query_show_cmd(
    selector: str = typer.Argument(..., help="V2 selector, e.g. 'inventory' or 'set:sld missing rarity=mythic'"),
    first: int = typer.Option(None, "--first", help="Cap displayed rows (total count still printed)."),
    sort: str = typer.Option("default", "--sort",
        help="Sort order: default (set,cn,finish) | value-desc | value-asc | rarity."),
    json_out: bool = typer.Option(False, "--json"),
):
    """Show rows matching a selector."""
    rows = _materialize_or_die(selector)
    rows = _apply_sort(rows, sort)
    if json_out:
        out = [
            {
                "scryfall_id": r.scryfall_id,
                "set": r.card.get("set"),
                "collector_number": r.card.get("collector_number"),
                "name": r.card.get("name"),
                "flavor_name": r.card.get("flavor_name"),
                "rarity": r.card.get("rarity"),
                "finish": r.finish,
                "quantity": r.quantity,
                "unit_price": _row_unit_price(r),
                "line_value": _row_line_value(r),
            }
            for r in rows
        ]
        json.dump(out, sys.stdout, indent=2); sys.stdout.write("\n")
        return
    typer.echo(f"# selector: {selector}", err=True)
    typer.echo(f"# rows: {len(rows)}", err=True)
    if not rows:
        raise typer.Exit(1)
    capped = rows[:first] if first else rows
    typer.echo(f"{'qty':>4} {'finish':>7} {'set':>6} {'cn':>6} {'rarity':>9}  name (usd / line)")
    for r in capped:
        unit = _row_unit_price(r); line = _row_line_value(r)
        usd = f"${unit:.2f}" if unit is not None else "—"
        line_s = f"${line:.2f}" if line is not None else "—"
        typer.echo(f"{r.quantity:>4} {r.finish:>7} {r.card.get('set',''):>6} "
                   f"{r.card.get('collector_number',''):>6} {(r.card.get('rarity') or ''):>9}  "
                   f"{_row_display_name(r)} ({usd} / {line_s})")
    if first and len(rows) > first:
        typer.echo(f"# truncated to first {first}; total {len(rows)}", err=True)


@query_app.command("value")
def query_value_cmd(
    selector: str = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
):
    """Total USD value of a selector's rows."""
    rows = _materialize_or_die(selector)
    total = 0.0
    missing = []
    priced_rows: list[tuple[float, sel_mod.MaterializedRow]] = []
    for r in rows:
        line = _row_line_value(r)
        if line is None and r.quantity > 0:
            missing.append((_row_display_name(r), r.card.get("set"), r.card.get("collector_number"), r.finish))
        else:
            total += line or 0.0
            if line is not None:
                priced_rows.append((line, r))
    priced_rows.sort(key=lambda t: t[0], reverse=True)
    top_5 = [
        {"name": _row_display_name(r), "set": r.card.get("set"),
         "cn": r.card.get("collector_number"), "finish": r.finish, "line_value": v}
        for v, r in priced_rows[:5]
    ]
    if json_out:
        json.dump({"selector": selector, "total": total, "rows": len(rows),
                   "missing_price": [{"name": n, "set": s, "cn": c, "finish": f}
                                     for n, s, c, f in missing],
                   "top_5": top_5}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    typer.echo(f"Selector {selector!r}: ${total:.2f} across {len(rows)} rows")
    if missing:
        typer.echo(f"  ({len(missing)} rows have no USD price)")
    if top_5:
        typer.echo("Top 5 by line value:")
        for t in top_5:
            typer.echo(f"  ${t['line_value']:.2f}  {t['name']} ({(t['set'] or '').upper()}) {t['cn']} [{t['finish']}]")


@query_app.command("top")
def query_top_cmd(
    n: int = typer.Argument(10, help="Show top-N rows by line value."),
):
    """Top-N inventory rows by line value (shorthand for `mm query show inventory` sorted)."""
    rows = _materialize_or_die("inventory")
    priced = [(r, _row_line_value(r)) for r in rows]
    priced = [(r, v) for r, v in priced if v is not None]
    priced.sort(key=lambda t: t[1], reverse=True)
    capped = priced[:n]
    typer.echo(f"Top {len(capped)} inventory rows by line value:")
    for r, line in capped:
        typer.echo(f"  ${line:.2f}  {_row_display_name(r)} "
                   f"({(r.card.get('set') or '').upper()}) {r.card.get('collector_number')} "
                   f"[{r.finish}] qty={r.quantity}")


@query_app.command("total")
def query_total_cmd():
    """Shorthand for `mm query value inventory`."""
    query_value_cmd(selector="inventory", json_out=False)


@query_app.command("multiples")
def query_multiples_cmd():
    """Inventory rows with quantity > 1, ordered by qty desc."""
    rows = _materialize_or_die("inventory qty>=2")
    rows.sort(key=lambda r: r.quantity, reverse=True)
    if not rows:
        typer.echo("(no multiples in inventory)"); return
    typer.echo(f"{'qty':>4} {'finish':>7} {'set':>6} {'cn':>6}  name")
    for r in rows:
        typer.echo(f"{r.quantity:>4} {r.finish:>7} {(r.card.get('set') or ''):>6} "
                   f"{r.card.get('collector_number',''):>6}  {_row_display_name(r)}")


@query_app.command("stats")
def query_stats_cmd(
    json_out: bool = typer.Option(False, "--json"),
):
    """Inventory rollup: totals, by-rarity, by-set, by-finish."""
    rows = _materialize_or_die("inventory")
    total = 0.0
    by_rarity: dict[str, dict] = {}
    by_set: dict[str, dict] = {}
    by_finish: dict[str, dict] = {}
    for r in rows:
        line = _row_line_value(r) or 0.0
        total += line
        rar = (r.card.get("rarity") or "unknown").lower()
        st = (r.card.get("set") or "unknown").lower()
        bucket = by_rarity.setdefault(rar, {"rows": 0, "qty": 0, "value": 0.0})
        bucket["rows"] += 1; bucket["qty"] += r.quantity; bucket["value"] += line
        bucket = by_set.setdefault(st, {"rows": 0, "qty": 0, "value": 0.0})
        bucket["rows"] += 1; bucket["qty"] += r.quantity; bucket["value"] += line
        bucket = by_finish.setdefault(r.finish, {"rows": 0, "qty": 0, "value": 0.0})
        bucket["rows"] += 1; bucket["qty"] += r.quantity; bucket["value"] += line
    out = {"total": total, "rows": len(rows),
           "qty": sum(r.quantity for r in rows),
           "by_rarity": by_rarity, "by_set": by_set, "by_finish": by_finish}
    if json_out:
        json.dump(out, sys.stdout, indent=2); sys.stdout.write("\n"); return
    typer.echo(f"Total: ${total:.2f} / {out['qty']} cards / {len(rows)} rows")
    typer.echo("\nBy rarity:")
    for rar, b in sorted(by_rarity.items()):
        typer.echo(f"  {rar:10} rows={b['rows']:>4} qty={b['qty']:>4} value=${b['value']:.2f}")
    typer.echo("\nBy set:")
    for st, b in sorted(by_set.items()):
        typer.echo(f"  {st.upper():10} rows={b['rows']:>4} qty={b['qty']:>4} value=${b['value']:.2f}")
    typer.echo("\nBy finish:")
    for fin, b in sorted(by_finish.items()):
        typer.echo(f"  {fin:10} rows={b['rows']:>4} qty={b['qty']:>4} value=${b['value']:.2f}")


@query_app.command("url")
def query_url_cmd(
    selector: str = typer.Argument(...),
    chunk_size: int = typer.Option(20, "--chunk-size",
                                   help="Cards per Scryfall search URL chunk (default 20; Scryfall web UI caps at 20 nested OR conditions)."),
    mode: str = typer.Option("oracle", "--mode",
                             help="'oracle' = !\"<name>\" form, dedupe by oracle name (good for shopping by name). "
                                  "'prints' = (set:CODE cn:\"CN\") form with unique=prints, one entry per printing "
                                  "(good for set-completion / 'which exact printing am I missing')."),
    sort: str = typer.Option("default", "--sort",
                             help="Sort order applied before chunking. default (set,cn,finish) | value-desc | value-asc | rarity. "
                                  "Use value-asc with --mode prints for cheapest-first set-completion URLs."),
):
    """Synthesize Scryfall search URLs for the result of a selector.

    Two modes:

    \b
    - oracle (default): emits `!"<oracle name>"` ORed terms, deduped by oracle
      name. Multiple finishes / printings of the same card collapse to one URL
      term. Best for shopping by name (let Scryfall show every printing so you
      can pick the cheapest).
    - prints: emits `(set:CODE cn:"CN")` ORed terms, one per distinct printing
      from the selector results, with `unique=prints&order=usd&dir=asc` appended
      to the URL so Scryfall returns each printing as a separate result sorted
      cheapest-first. Best for set-completion / "which exact printing am I
      missing" workflows. Honors `cn:"..."` quoting so hyphenated CNs (PMEI
      2025-13) and A-prefix variants (FIN A-248) work correctly.

    URLs are chunked at --chunk-size (default 20). Scryfall's web UI caps OR'd
    queries at 20 nested conditions; chunks larger than 20 will fail in the
    browser even if the API accepts them.
    """
    from urllib.parse import quote_plus
    rows = _materialize_or_die(selector)
    rows = _apply_sort(rows, sort)
    if not rows:
        typer.echo("(selector matched 0 rows)"); raise typer.Exit(1)

    if mode not in ("oracle", "prints"):
        typer.echo(f"error: --mode must be 'oracle' or 'prints', got {mode!r}", err=True)
        raise typer.Exit(2)

    if mode == "oracle":
        # Dedupe by oracle name — multiple finishes / printings of the same card
        # collapse to one URL term.
        names: list[str] = []
        seen: set[str] = set()
        for r in rows:
            nm = r.card.get("name")
            if nm and nm not in seen:
                seen.add(nm); names.append(nm)
        chunks = [names[i:i+chunk_size] for i in range(0, len(names), chunk_size)]
        typer.echo(f"{len(names)} distinct cards → {len(chunks)} URL(s) (mode=oracle)")
        for i, chunk in enumerate(chunks, start=1):
            terms = " or ".join(f'!"{nm}"' for nm in chunk)
            url = f"https://scryfall.com/search?q={quote_plus(terms)}"
            typer.echo(f"Chunk {i}/{len(chunks)} ({len(chunk)} cards): {url}")
        return

    # mode == "prints"
    # Collapse to one entry per (set, cn) — within a printing, multiple finishes
    # are the same Scryfall card. Preserve sort order from _apply_sort.
    seen_printings: set[tuple[str, str]] = set()
    printings: list[tuple[str, str]] = []  # [(set_code, cn), ...]
    for r in rows:
        setc = r.card.get("set") or ""
        cn = r.card.get("collector_number") or ""
        if not setc or not cn:
            continue
        key = (setc, cn)
        if key in seen_printings:
            continue
        seen_printings.add(key)
        printings.append(key)

    chunks = [printings[i:i+chunk_size] for i in range(0, len(printings), chunk_size)]
    typer.echo(f"{len(printings)} distinct printings → {len(chunks)} URL(s) (mode=prints)")
    for i, chunk in enumerate(chunks, start=1):
        terms = " or ".join(f'(set:{s} cn:"{cn}")' for s, cn in chunk)
        url = f"https://scryfall.com/search?q={quote_plus(terms)}&unique=prints&order=usd&dir=asc"
        typer.echo(f"Chunk {i}/{len(chunks)} ({len(chunk)} printings): {url}")


def _apply_preferred_post_filter(
    rows: list[sel_mod.MaterializedRow],
    anchor_code: str,
) -> list[sel_mod.MaterializedRow]:
    """Post-filter rows for `mm query missing-set` regular sub-selectors when
    `--treatment-class=preferred`. Applies two exclusions that the selector
    grammar's `treatment=preferred` already applies to the alt sub-selector,
    but which need to be applied to the regular sub-selectors here:

    1. **Digital-only (Arena/Alchemy rebalanced)** — drop unconditionally.
       Same rule the selector applies; these never have physical counterparts.

    2. **Datestamped reprints with a non-stamped sibling** at the same name and
       same treatment codes in the family. Catches PFIN's prerelease-stamped
       FIN cards that are visually identical to the FIN versions.
    """
    import json as _json
    from . import treatments as _treatments
    from .selectors import _is_digital_only as _digital_only

    if not rows:
        return rows

    # Step 1: drop digital-only prints unconditionally.
    rows = [r for r in rows if not _digital_only(r.card)]
    if not rows:
        return rows

    # Step 2: build family index for datestamped-with-sibling check.
    try:
        family_codes = set(sets_mod.resolve(anchor_code).all_codes)
    except LookupError:
        family_codes = {anchor_code}
    placeholders = ",".join("?" for _ in family_codes)
    with db.connect() as conn:
        fam_rows = conn.execute(
            f"SELECT scryfall_id, name, frame_effects, full_art, promo_types "
            f"FROM cards WHERE set_code IN ({placeholders})",
            list(family_codes),
        ).fetchall()
    by_name_codes: dict[tuple[str | None, frozenset[str]], list[dict]] = {}
    promo_index: dict[str, set[str]] = {}
    for fr in fam_rows:
        t = _treatments.compute_treatment(dict(fr))
        codes = frozenset(t.split("|")) if t else frozenset()
        pt = set(_json.loads(fr["promo_types"] or "[]"))
        promo_index[fr["scryfall_id"]] = pt
        by_name_codes.setdefault((fr["name"], codes), []).append({
            "scryfall_id": fr["scryfall_id"],
            "promo_types": pt,
        })
    out: list[sel_mod.MaterializedRow] = []
    for r in rows:
        sid = r.scryfall_id
        my_pt = promo_index.get(sid, set())
        if "datestamped" not in my_pt:
            out.append(r)
            continue
        t = _treatments.compute_treatment(r.card)
        codes = frozenset(t.split("|")) if t else frozenset()
        siblings = by_name_codes.get((r.card.get("name"), codes), [])
        non_stamped_sibling_exists = any(
            s["scryfall_id"] != sid and "datestamped" not in s["promo_types"]
            for s in siblings
        )
        if not non_stamped_sibling_exists:
            out.append(r)  # Keep — no cheaper sibling to substitute.
    return out


def _write_query_xlsx(
    rows: list[sel_mod.MaterializedRow],
    target: Path,
    selector: str,
    slug: str,
    kind: str = "query",
) -> None:
    """Write a list of materialized rows to an XLSX checklist artifact.

    Shared by `mm query xlsx` (kind="query", ad-hoc selector results) and
    `mm query missing-set` (kind="missing", canonical missing-checklist
    output). The `kind` field is recorded in the hidden `_meta` sheet so
    consumers can distinguish missing checklists from ad-hoc query results
    or from `mm set master-list`'s inventory checklists (which are written
    by a separate function in sets.py with `kind: "inventory"`).

    Columns: set, collector_number, name, rarity, finish, qty, unit_usd,
    line_value, scryfall_id. Hidden _meta sheet records the originating
    selector and timestamp so the file's lineage is traceable.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    target.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "results"
    headers = ["set", "collector_number", "name", "rarity", "finish",
               "qty", "unit_usd", "line_value", "scryfall_id"]
    ws.append(headers)
    for col, _ in enumerate(headers, start=1):
        ws.cell(row=1, column=col).font = Font(bold=True)
    for r in rows:
        unit = _row_unit_price(r); line = _row_line_value(r)
        ws.append([
            r.card.get("set"), r.card.get("collector_number"),
            _row_display_name(r), r.card.get("rarity"), r.finish,
            r.quantity, unit, line, r.scryfall_id,
        ])
        # Force CN to text to avoid Excel's "Number Stored as Text" warning.
        ws.cell(row=ws.max_row, column=2).number_format = "@"
    last = ws.max_row
    for col_idx in (7, 8):
        for row_idx in range(2, last + 1):
            ws.cell(row=row_idx, column=col_idx).number_format = '"$"#,##0.00'
    widths = {1: 6, 2: 8, 3: 48, 4: 10, 5: 8, 6: 5, 7: 9, 8: 11, 9: 38}
    for col_idx, w in widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = w
    ws.freeze_panes = "A2"

    meta_ws = wb.create_sheet("_meta")
    meta_ws.sheet_state = "hidden"
    meta_ws.append(["key", "value"])
    meta_ws.append(["kind", kind])
    meta_ws.append(["selector", selector])
    meta_ws.append(["slug", slug])
    meta_ws.append(["generated_at", datetime.now().isoformat(timespec="seconds")])
    meta_ws.append(["row_count", str(len(rows))])

    wb.save(target)


@query_app.command("xlsx")
def query_xlsx_cmd(
    selector: str = typer.Argument(...),
    name: str = typer.Option(None, "--name", help="Override the slug for the filename."),
    out: Path = typer.Option(None, "--out", help="Override the full output path."),
    sort: str = typer.Option("default", "--sort",
        help="Sort order: default (set,cn,finish) | value-desc | value-asc | rarity."),
):
    """Write the selector's rows to a queries/<slug>-<timestamp>.xlsx artifact.

    The XLSX has columns: set, collector_number, name, rarity, finish, qty,
    unit_usd, line_value. A hidden _meta sheet records the selector verbatim.
    Empty result still writes a file (with headers + empty body) and warns.
    """
    rows = _materialize_or_die(selector)
    rows = _apply_sort(rows, sort)
    slug = name or _selector_slug(selector)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    target = out if out else QUERIES_DIR / f"{slug}-{ts}.xlsx"
    _write_query_xlsx(rows, target, selector, slug)
    if not rows:
        typer.echo(f"warning: selector matched 0 rows; wrote empty file {target}", err=True)
    typer.echo(f"wrote {target} ({len(rows)} rows)")


@query_app.command("missing-set")
def query_missing_set_cmd(
    code: str = typer.Argument(
        ...,
        help="Anchor set code (e.g. 'fin', 'avatar', 'tmnt'). Resolves +related family automatically.",
    ),
    chunk_size: int = typer.Option(
        20, "--chunk-size",
        help="Cards per Scryfall URL chunk (default 20; matches Scryfall web UI's nested-conditions cap).",
    ),
    treatment_class: str = typer.Option(
        "preferred", "--treatment-class",
        help="Treatment class for the alt sub-selector. Default 'preferred' (collectible-alt minus "
             "datestamped-with-sibling and family-configured fancy-foil dupes). "
             "Pass 'collectible-alt' to skip the dupe filtering, 'alt' to also include pure-ff, "
             "'any-alt' to also include ext.",
    ),
):
    """Canonical "what am I missing from set <CODE>?" workflow.

    Materializes the union of three sub-selectors (rare-regular, mythic-regular,
    treatment-class) printing-level, then emits:

    \b
    1. Scryfall printing-specific URL chunks (markdown table → STDOUT for chat).
       Sorted cheapest-first; uses (set:CODE cn:"CN") form with unique=prints
       and order=usd&dir=asc so each URL renders the EXACT missing printings.
    2. XLSX checklist (set-grouped, sorted by CN within each set) → queries/.
    3. ManaPool bulk-add .txt (flat list, *F* foil markers per line) → queries/.
    4. TCGplayer Mass Entry .txt (flat list, no per-line foil marker — user runs
       TCGplayer's cart optimizer to select foil/nonfoil per row) → queries/.

    The chat output is always just the URL table + file:// link lines so the
    user can click to open the artifacts. The bulk-add files are NEVER rendered
    inline — the user explicitly wants them as files only, and they must be
    paste-ready (no comments, headers, or fences) since portals don't tolerate
    extra characters.

    When --treatment-class=preferred (default), the rare/mythic regular-treatment
    sub-selectors are ALSO post-filtered to drop datestamped reprints that have
    a non-stamped sibling at the same treatment in the family. This catches
    e.g. PFIN's prerelease-stamped versions of FIN cards that are otherwise
    visually identical.

    New families with no FAMILY_DUPE_FOIL_PROMO_TYPES config will fail with a
    clear error from the selector layer. Either configure the family or pass
    --treatment-class collectible-alt to opt into the looser pre-`preferred`
    behavior.

    Set-agnostic: works for FIN today, Avatar/TMNT/etc. tomorrow with the same
    invocation, once each new family is configured.
    """
    import re as _re
    import json as _json
    from urllib.parse import quote_plus as _quote_plus

    code_l = code.lower()
    SUBS = [
        ("rare-regular",     f"set:{code_l}+related missing rarity=rare treatment=regular"),
        ("mythic-regular",   f"set:{code_l}+related missing rarity=mythic treatment=regular"),
        (treatment_class,    f"set:{code_l}+related missing treatment={treatment_class}"),
    ]

    # 1. Materialize each sub-selector + dedupe to a printing-level union.
    union: dict[str, sel_mod.MaterializedRow] = {}
    sub_rows: dict[str, list[sel_mod.MaterializedRow]] = {}
    for slug_key, sel in SUBS:
        try:
            rs = sel_mod.materialize(sel)
        except sel_mod.SelectorParseError as e:
            typer.echo(f"error: invalid selector {sel!r}: {e}", err=True); raise typer.Exit(2)
        except LookupError as e:
            typer.echo(f"error: {e} (sub-selector {sel!r})", err=True); raise typer.Exit(2)
        sub_rows[slug_key] = rs

    # 1a. When using 'preferred' mode, also drop datestamped-with-sibling rows
    # from the rare/mythic regular sub-selectors. The 'preferred' filter only
    # runs on the alt sub-selector (treatment=preferred); regular-treatment
    # rows skip the filter unless we apply it here.
    if treatment_class == "preferred":
        sub_rows["rare-regular"]   = _apply_preferred_post_filter(sub_rows["rare-regular"], code_l)
        sub_rows["mythic-regular"] = _apply_preferred_post_filter(sub_rows["mythic-regular"], code_l)

    for slug_key in sub_rows:
        for r in sub_rows[slug_key]:
            union[r.scryfall_id] = r

    rows_union = list(union.values())
    if not rows_union:
        typer.echo(f"# No missing printings found for set:{code_l}+related (full collection? wrong code?).")
        raise typer.Exit(0)

    # 2. Cheapest-first ordering for the Scryfall URL chunks.
    def _cn_key(cn: str | None) -> tuple[int, str]:
        m = _re.match(r"^(\d+)(.*)$", cn or "")
        return (int(m.group(1)) if m else 0, m.group(2) if m else (cn or ""))

    rows_by_value = sorted(rows_union, key=lambda r: (
        0 if _row_line_value(r) is not None else 1,
        _row_line_value(r) or 0.0,
        r.card.get("set") or "", _cn_key(r.card.get("collector_number")),
    ))
    chunks = [rows_by_value[i:i+chunk_size] for i in range(0, len(rows_by_value), chunk_size)]

    # 3. Build the XLSX checklist artifact (grouped by set, sorted by CN within each).
    rows_for_xlsx = sorted(rows_union, key=lambda r: (
        r.card.get("set") or "",
        _cn_key(r.card.get("collector_number")),
        r.finish,
    ))
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    QUERIES_DIR.mkdir(parents=True, exist_ok=True)
    xlsx_path = QUERIES_DIR / f"missing-{code_l}-checklist-{ts}.xlsx"
    union_selector_repr = (
        f"({SUBS[0][1]}) ∪ ({SUBS[1][1]}) ∪ ({SUBS[2][1]})  [printing-level union]"
    )
    _write_query_xlsx(
        rows_for_xlsx, xlsx_path, union_selector_repr,
        f"missing-{code_l}-checklist", kind="missing",
    )

    # 4. Build the bulk-add artifacts.
    #    All three are plain text — no headings, no comments, no fences. Pasting
    #    into a portal's mass-entry box must succeed without any pre-edit.
    #    Order rows by (set, cn, finish) within each file for predictability.
    rows_for_bulk = sorted(rows_union, key=lambda r: (
        r.card.get("set") or "",
        _cn_key(r.card.get("collector_number")),
        r.finish,
    ))
    total_value = sum((_row_line_value(r) or 0.0) for r in rows_union)

    # ManaPool: single flat list, *F* foil markers preserved per-line.
    mp_path = QUERIES_DIR / f"missing-{code_l}-manapool-{ts}.txt"
    mp_path.write_text(exports.build("manapool", rows_for_bulk), encoding="utf-8")

    # TCGplayer: single flat list. Foil/nonfoil isn't marked per-line — the
    # user runs TCGplayer's cart optimizer afterward to pick finish per row.
    tcg_path = QUERIES_DIR / f"missing-{code_l}-tcgplayer-{ts}.txt"
    tcg_path.write_text(exports.build("tcgplayer", rows_for_bulk), encoding="utf-8")

    # 5. Emit chat output: URL table + file:// links. Nothing else.
    typer.echo(f"# Missing from set:{code_l}+related — {len(rows_union)} distinct printings · ${total_value:,.2f}")
    typer.echo(f"")
    typer.echo(f"## Scryfall URLs ({len(chunks)} chunks, cheapest first)")
    typer.echo(f"")
    typer.echo(f"| # | Printings | Price band | URL |")
    typer.echo(f"|---:|---:|---|---|")
    for i, chunk in enumerate(chunks, start=1):
        cheap = _row_line_value(chunk[0])
        most = _row_line_value(chunk[-1])
        cs = f"${cheap:.2f}" if cheap is not None else "—"
        ms = f"${most:.2f}" if most is not None else "—"
        terms = " or ".join(
            f'(set:{r.card.get("set")} cn:"{r.card.get("collector_number")}")' for r in chunk
        )
        url = f"https://scryfall.com/search?q={_quote_plus(terms)}&unique=prints&order=usd&dir=asc"
        typer.echo(f"| {i} | {len(chunk)} | {cs} → {ms} | [chunk {i}]({url}) |")
    typer.echo(f"")
    typer.echo(f"📋 Checklist (xlsx): [{xlsx_path}](file://{xlsx_path.resolve()})")
    typer.echo(f"🛒 ManaPool bulk-add ({len(rows_for_bulk)} rows): [{mp_path}](file://{mp_path.resolve()})")
    typer.echo(f"🛒 TCGplayer Mass Entry ({len(rows_for_bulk)} rows): [{tcg_path}](file://{tcg_path.resolve()})")


# ---------- ad-hoc scryfall query ----------

@app.command("scryfall")
def scryfall_cmd(
    query: str = typer.Argument(..., help="Scryfall search query (any syntax the API accepts)."),
    first: int = typer.Option(20, "--first", help="Show at most N results."),
    json_out: bool = typer.Option(False, "--json", help="Emit raw Scryfall JSON instead of the table."),
    fields: str = typer.Option(
        "set,collector_number,name,treatment,rarity",
        "--fields",
        help="Comma-separated columns. Available: set,collector_number,name,rarity,"
             "treatment,full_art,border_color,frame_effects,promo_types,security_stamp,"
             "prices_usd,prices_usd_foil,scryfall_uri",
    ),
):
    """Run an ad-hoc Scryfall search and pretty-print the results.

    Avoids the shell-quoting trap of writing one-shot Python at the prompt.
    Uses the rate-limited wrapper (``scryfall.sh``) under the hood, so
    multi-page queries paginate cleanly. Card-name apostrophes are passed
    through without escaping issues.

    Each row's computed treatment string (per ``treatments.compute_treatment``)
    is included by default, so distinct printings of the same card
    (e.g. Cloud, Ex-SOLDIER variants) are immediately visually distinguishable.
    """
    from .scryfall import search as sf_search
    from .treatments import compute_treatment

    cols = [c.strip().lower() for c in fields.split(",") if c.strip()]
    rows: list[dict] = []
    try:
        for i, c in enumerate(sf_search(query, unique="prints")):
            if i >= first:
                break
            rows.append(c)
    except Exception as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2)

    if not rows:
        typer.echo(f"(no results for {query!r})", err=True)
        raise typer.Exit(1)

    if json_out:
        json.dump(rows, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return

    def get(c: dict, col: str):
        if col == "treatment":
            return compute_treatment(c) or "—"
        if col == "frame_effects":
            return ",".join(c.get("frame_effects") or []) or "—"
        if col == "promo_types":
            return ",".join(c.get("promo_types") or []) or "—"
        if col == "prices_usd":
            return (c.get("prices") or {}).get("usd") or "—"
        if col == "prices_usd_foil":
            return (c.get("prices") or {}).get("usd_foil") or "—"
        if col == "scryfall_uri":
            return c.get("scryfall_uri") or "—"
        if col == "full_art":
            return "yes" if c.get("full_art") else "no"
        v = c.get(col, "—")
        return v if v not in (None, "") else "—"

    # Compute column widths for a tight table.
    widths = {col: max(len(col), max(len(str(get(r, col))) for r in rows)) for col in cols}
    header = "  ".join(col.ljust(widths[col]) for col in cols)
    typer.echo(header)
    typer.echo("  ".join("-" * widths[col] for col in cols))
    for r in rows:
        typer.echo("  ".join(str(get(r, col)).ljust(widths[col]) for col in cols))
    typer.echo("", err=True)
    typer.echo(f"# {len(rows)} result(s) for {query!r}", err=True)


# ---------- mtgjson (precon decks + set data) ----------

@mtgjson_app.command("meta")
def mtgjson_meta(
    json_out: bool = typer.Option(False, "--json", help="Emit raw JSON."),
):
    """Show MTGJSON's current build date and version."""
    from . import mtgjson as mj
    m = mj.meta()
    if json_out:
        json.dump(m, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    typer.echo(f"date:    {m.get('date')}")
    typer.echo(f"version: {m.get('version')}")


@mtgjson_app.command("set")
def mtgjson_set(
    set_code: str = typer.Argument(..., help="Set code, e.g. fic, FIC."),
    json_out: bool = typer.Option(False, "--json", help="Emit raw set JSON."),
):
    """Pretty-print MTGJSON's per-set summary."""
    from . import mtgjson as mj
    s = mj.set_file(set_code)
    if json_out:
        json.dump(s, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return
    typer.echo(f"name:           {s.get('name')}")
    typer.echo(f"code:           {s.get('code')}")
    typer.echo(f"type:           {s.get('type')}")
    typer.echo(f"releaseDate:    {s.get('releaseDate')}")
    typer.echo(f"totalSetSize:   {s.get('totalSetSize')}")
    typer.echo(f"baseSetSize:    {s.get('baseSetSize')}")
    cards = s.get("cards") or []
    tokens = s.get("tokens") or []
    decks = s.get("decks") or []
    typer.echo(f"cards:          {len(cards)}")
    typer.echo(f"tokens:         {len(tokens)}")
    typer.echo(f"decks (inline): {len(decks)}")


@mtgjson_app.command("decks")
def mtgjson_decks(
    set_code: str = typer.Option(None, "--set", help="Filter to one set code."),
    first: int = typer.Option(50, "--first", help="Show at most N rows."),
    json_out: bool = typer.Option(False, "--json", help="Emit raw DeckList JSON."),
):
    """List decks (filterable by set code) from MTGJSON's DeckList.json."""
    from . import mtgjson as mj
    rows = mj.deck_list(set_code=set_code)
    if json_out:
        json.dump(rows, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return
    if not rows:
        typer.echo(f"(no decks{f' for set {set_code.upper()}' if set_code else ''})", err=True)
        raise typer.Exit(1)
    rows = rows[:first]
    cols = ("code", "fileName", "name", "type", "releaseDate")
    widths = {c: max(len(c), max(len(str(r.get(c) or "")) for r in rows)) for c in cols}
    typer.echo("  ".join(c.ljust(widths[c]) for c in cols))
    typer.echo("  ".join("-" * widths[c] for c in cols))
    for r in rows:
        typer.echo("  ".join(str(r.get(c) or "—").ljust(widths[c]) for c in cols))


@mtgjson_app.command("deck")
def mtgjson_deck(
    file_name: str = typer.Argument(..., help="MTGJSON deck fileName, e.g. CounterBlitzFinalFantasyX_FIC."),
    json_out: bool = typer.Option(False, "--json", help="Emit raw deck JSON."),
    show: int = typer.Option(10, "--show", help="Show at most N cards per board in summary view."),
):
    """Pretty-print one MTGJSON deck file (commander, mainBoard, sideBoard)."""
    from . import mtgjson as mj
    d = mj.deck(file_name)
    if json_out:
        json.dump(d, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return
    typer.echo(f"name:        {d.get('name')}")
    typer.echo(f"code:        {d.get('code')}")
    typer.echo(f"type:        {d.get('type')}")
    typer.echo(f"releaseDate: {d.get('releaseDate')}")

    def emit(board: str):
        cards = d.get(board) or []
        if not cards:
            return
        typer.echo(f"\n{board} ({len(cards)} {'entry' if len(cards) == 1 else 'entries'}):")
        for c in cards[:show]:
            finish = "foil" if c.get("isFoil") else "nonfoil"
            sid = (c.get("identifiers") or {}).get("scryfallId", "—")
            typer.echo(
                f"  {c.get('count', 1):>2}x  ({c.get('setCode')}) {str(c.get('number')):>5}  "
                f"{(c.get('name') or '')[:40]:40}  {finish:7}  scryfall:{sid}"
            )
        if len(cards) > show:
            typer.echo(f"  … {len(cards) - show} more")

    emit("commander")
    emit("mainBoard")
    emit("sideBoard")
    emit("tokens")


@mtgjson_app.command("refresh")
def mtgjson_refresh(
    resource_path: str = typer.Argument(..., help="Resource path, e.g. FIC.json or DeckList.json."),
):
    """Delete the cached copy of ``resource_path`` so the next fetch re-downloads."""
    from . import mtgjson as mj
    mj.refresh(resource_path)
    typer.echo(f"refreshed: {resource_path}")


@mtgjson_app.command("check-stale")
def mtgjson_check_stale(
    resource_path: str = typer.Argument(..., help="Resource path, e.g. FIC.json or DeckList.json."),
):
    """Compare cached SHA-256 to MTGJSON's published .sha256 sidecar.

    Exits 0 if fresh, 1 if stale, 2 if not cached.
    """
    from . import mtgjson as mj
    try:
        stale = mj.is_stale(resource_path)
    except mj.MtgJsonError as e:
        typer.echo(f"absent ({e})", err=True)
        raise typer.Exit(2)
    if stale:
        typer.echo("stale")
        raise typer.Exit(1)
    typer.echo("fresh")


# ---------- db (snapshots, restore, integrity) ----------

@db_app.command("snapshot")
def db_snapshot_cmd(
    label: str = typer.Option(None, "--label", help="Suffix appended to the backup filename."),
):
    """Take a timestamped snapshot of the active DB next to the live file."""
    backup = db.snapshot(label=label)
    typer.echo(str(backup))


@db_app.command("snapshots")
def db_snapshots_cmd():
    """List local DB snapshots (newest first)."""
    snaps = db.list_snapshots()
    if not snaps:
        typer.echo("(no snapshots)", err=True)
        raise typer.Exit(0)
    for p in snaps:
        st = p.stat()
        size_mb = st.st_size / (1024 * 1024)
        when = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        typer.echo(f"{when}  {size_mb:>6.2f} MB  {p}")


@db_app.command("restore")
def db_restore_cmd(
    backup_path: Path = typer.Argument(..., help="Path to a snapshot file."),
):
    """Restore the active DB from a snapshot. Renames the current live DB to <live>.replaced-<ts>."""
    replaced = db.restore(backup_path)
    if replaced is not None:
        typer.echo(f"prior live DB moved to: {replaced}", err=True)
    typer.echo(f"restored from: {backup_path}")


@db_app.command("integrity")
def db_integrity_cmd():
    """Run PRAGMA integrity_check on the live DB. Exits non-zero if not 'ok'."""
    result = db._check_integrity(db.db_path())
    typer.echo(result)
    if result != "ok":
        raise typer.Exit(1)


# ---------- intake (scan-loop REPL) ----------

@app.command("intake")
def intake_cmd(
    name_or_code: str = typer.Argument(...),
    only: list[str] = typer.Option(None, "--only"),
    include: list[str] = typer.Option(None, "--include"),
):
    """Scan-loop REPL: type ``<set>? <cn> [+N|=N] [f]`` per card, qty updates live.

    Bound to a resolved set family. Writes directly to the V2 ``inventory``
    table — no master-list seeding required (any card synced via
    ``mm set sync`` is fair game). The first set code you type becomes
    sticky; subsequent lines without a set use it. Each entry is a separate
    DB transaction — Ctrl-C is safe.

    Modes per line:
      - bare              → +1 (default)
      - +N                → increment by N
      - =N                → overwrite to exactly N (requires N >= 0)
      - trailing f / foil → this card is foil

    Other commands: u/undo, s <code>/set <code>, ?/help, q/quit.
    """
    try:
        r, codes = _resolve_codes(
            name_or_code, include_kinds=list(include or []), only=list(only or []),
        )
    except (LookupError, typer.BadParameter) as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
    intake_mod.run_repl(r)


# ---------- export ----------

@app.command("export")
def export_cmd(
    target: str = typer.Argument(..., help="moxfield | manapool | tcgplayer | archidekt | plain | scryfall-json"),
    selector: str = typer.Argument(..., help="V2 selector, e.g. 'inventory', 'set:fca missing', 'wishlist:edh-staples'"),
    out: Path = typer.Option(None, "--out", help="Optional output path; otherwise prints to stdout."),
):
    """Materialize a V2 selector and emit a paste-ready block for the target service."""
    try:
        rows = sel_mod.materialize(selector)
    except sel_mod.SelectorParseError as e:
        typer.echo(f"error: invalid selector: {e}", err=True); raise typer.Exit(2)
    except LookupError as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
    if not rows:
        typer.echo(f"(selector matched 0 rows: {selector})", err=True)
        raise typer.Exit(1)
    text = exports.build(target, rows)

    typer.echo(f"# selector: {selector}", err=True)
    typer.echo(f"# target: {target}", err=True)
    typer.echo(f"# rows: {len(rows)}", err=True)
    if target == "tcgplayer":
        typer.echo("# NOTE: TCGplayer Mass Entry format is '1 Card Name [SETCODE] CN'.", err=True)
        typer.echo("#       Foil is set per-batch via the cart UI toggle, not per-line —", err=True)
        typer.echo("#       run twice with finish=nonfoil and finish=foil for a mixed cart.", err=True)

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        typer.echo(f"wrote {out}", err=True)
    else:
        typer.echo(text, nl=False)


# ---------- input/ inspection (used by the slash command) ----------

@checklists_app.command("list")
def input_list(
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List every active inventory checklist in ``input/`` with a summary and
    duplicate-vs-prior-ingest flag.

    The ``/ingest-new-inventory-list`` slash command reads the JSON form of
    this output to drive its per-file conversation. Every file shows up
    even if its hash matches a prior successful ingest — those are flagged
    for the user to triage.
    """
    if not INPUT_DIR.exists():
        if json_out:
            json.dump({"input_dir": str(INPUT_DIR), "files": []}, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            typer.echo(f"(input dir {INPUT_DIR}/ does not exist)")
        return

    # Walk both supported formats. Don't recurse into processed/ — those are
    # immutable archives, not active intake docs. Skip Excel/LibreOffice
    # temp-lock sidecars (``~$<name>.xlsx``, ``.~lock.<name>#``) — they aren't
    # real workbooks; the user just has the file open in Excel.
    files: list[Path] = []
    skipped_lock_files: list[str] = []
    for pattern in ("*.xlsx", "*.md"):
        for p in INPUT_DIR.glob(pattern):
            if not p.is_file():
                continue
            if p.name.startswith("~$") or p.name.startswith(".~lock."):
                skipped_lock_files.append(p.name)
                continue
            files.append(p)
    files = sorted(files)
    if skipped_lock_files and not json_out:
        typer.echo(
            f"(skipped {len(skipped_lock_files)} Excel/LibreOffice lock file(s); "
            f"close the workbook in your editor if you intended to ingest it: "
            f"{', '.join(skipped_lock_files)})",
            err=True,
        )
    out_files: list[dict] = []
    for f in files:
        sha = _file_sha256(f)
        with db.connect() as conn:
            prior = db.find_ingest_log_by_hash(conn, sha)
        prior_success = next((p for p in prior if p["status"] == "success"), None)
        prior_failed = next((p for p in prior if p["status"] == "failed"), None)
        try:
            summary = sets_mod.summarize_intake_file(f)
        except Exception as e:  # malformed XLSX shouldn't crash the listing
            summary = {"error": repr(e)}
        out_files.append({
            "path": str(f),
            "name": f.name,
            "sha256": sha,
            "size_bytes": f.stat().st_size,
            "summary": summary,
            "duplicate_of_log_id": prior_success["id"] if prior_success else None,
            "prior_success": prior_success,
            "prior_failed": prior_failed,
        })

    if json_out:
        json.dump({"input_dir": str(INPUT_DIR), "files": out_files}, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return

    if not out_files:
        typer.echo(f"(no XLSX files in {INPUT_DIR}/)"); return
    for f in out_files:
        typer.echo(f"- {f['name']} ({f['size_bytes']} bytes, sha={f['sha256'][:12]}…)")
        s = f["summary"]
        if "error" in s:
            typer.echo(f"    parse error: {s['error']}")
            continue
        rarity = ",".join(s.get("rarity_filter") or []) or "(none)"
        codes = ",".join(s.get("set_codes") or []) or "(none)"
        typer.echo(
            f"    anchor={s.get('anchor_code') or '?'} "
            f"set_codes={codes} rarity_filter={rarity}"
        )
        typer.echo(
            f"    rows_total={s['rows_total']} "
            f"rows_with_qty={s['rows_with_qty']} "
            f"total_qty={s['total_qty']} "
            f"value=${s['estimated_value']:.2f}"
        )
        if f["duplicate_of_log_id"]:
            ps = f["prior_success"]
            typer.echo(
                f"    ⚠ DUPLICATE: SHA matches log id {ps['id']} ingested at "
                f"{ps['at']} (likely a failed cleanup; pass --force to re-apply)"
            )
        if f["prior_failed"]:
            pf = f["prior_failed"]
            typer.echo(f"    ⚠ previously failed at {pf['at']}: {pf['error']}")


# ---------- entry point ----------

if __name__ == "__main__":
    app()

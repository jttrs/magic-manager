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

from . import db, exports, intake as intake_mod, lists as lists_mod, sets as sets_mod

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
list_app = typer.Typer(no_args_is_help=True, help="Labeled lists.")

checklists_app = typer.Typer(no_args_is_help=True,
                             help="Inspect inventory checklists in checklists/.")
mtgjson_app = typer.Typer(no_args_is_help=True,
                          help="Read MTGJSON.com data (precon decks, set files, etc.).")
db_app = typer.Typer(no_args_is_help=True,
                     help="Manage the local SQLite DB: snapshots, restore, integrity.")

app.add_typer(set_app, name="set")
app.add_typer(list_app, name="list")
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


def _intake_path(slug: str, slice_suffix: str = "", ext: str = "xlsx") -> Path:
    # ``-checklist`` suffix matches the user-facing artifact name. Filename
    # is ``<slug>-checklist.<ext>`` for the unsliced default,
    # ``<slug>-<slice>-checklist.<ext>`` for slices (e.g. rarity slices,
    # set-code slices). Pre-V1.6 was ``input/<slug>-<slice>.xlsx`` with
    # an explicit ``master`` token for the unsliced case.
    middle = f"-{slice_suffix}" if slice_suffix else ""
    return CHECKLISTS_DIR / f"{slug}{middle}-checklist.{ext}"


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
    label = f"set:{r.code}"
    slice_suffix = _slice_suffix(only_codes=only_codes, rarities=rarities)
    out_path = out or _intake_path(slug, slice_suffix, ext=fmt)

    # Collision detection: only when the user is using the default path.
    if out is None and out_path.exists() and not force:
        typer.echo(f"refusing to overwrite existing inventory checklist: {out_path}", err=True)
        typer.echo(f"current state of {label!r}:", err=True)
        s = lists_mod.summarize_label(label)
        typer.echo(
            f"  {s['distinct_rows']} distinct (card,finish) rows owned, "
            f"qty {s['total_qty']}, value ${s['total_value']:.2f}",
            err=True,
        )
        if s["top_value"]:
            typer.echo("  top by value:", err=True)
            for row in s["top_value"]:
                price = f"${row.unit_price:.2f}" if row.unit_price is not None else "—"
                typer.echo(
                    f"    {row.quantity}x {row.display_name} ({row.set_code.upper()}) "
                    f"{row.collector_number} [{row.finish}] @ {price}",
                    err=True,
                )
        typer.echo("", err=True)
        typer.echo("To proceed, either:", err=True)
        typer.echo(f"  - Finish editing the existing XLSX, then: mm set ingest {name_or_code!r}", err=True)
        typer.echo(f"  - Discard partial edits and regenerate: mm set master-list {name_or_code!r} --force", err=True)
        raise typer.Exit(EXIT_UNPROCESSED_INTAKE)

    typer.echo(f"Syncing {len(codes)} set(s): {' '.join(codes)}")
    n_synced = sets_mod.sync(codes)
    typer.echo(f"  → {n_synced} cards upserted")

    seeded = sets_mod.seed_set_list(label, codes, include_variants=include_variants)
    typer.echo(f"Seeded list {label!r} ({seeded} new rows at qty=0)")

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
        prepopulate_from_label=label,
        rarity_filter=rarities or None,
        anchor_code=r.code,
        slug=slug,
        include_variants=include_variants,
    )
    typer.echo(f"Wrote {n_rows} rows to {out_path}")
    if prefilled:
        typer.echo(f"  → {prefilled} qty cell(s) pre-filled from {label!r}")
    typer.echo()
    typer.echo("Next steps:")
    if fmt == "md":
        typer.echo(f"  1. Open {out_path} in any text editor and edit `[N:k F:k]` quantities.")
    else:
        typer.echo(f"  1. Open {out_path} in Excel/Numbers and fill in qty_normal / qty_foil.")
    typer.echo(f"  2. When done: mm set ingest {name_or_code!r}")


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
        "replace", "--mode",
        help="'replace' (default): xlsx cells inside the file's partition overwrite "
             "DB qty (missing in-partition rows go to 0). 'additive': only cells "
             "with qty>0 add to DB qty.",
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
    """
    if mode not in ("replace", "additive"):
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
            label = f"set:{anchor}"
            slug = meta.get("slug") or _slug(anchor)
        elif name_or_code:
            try:
                r = sets_mod.resolve(name_or_code)
            except LookupError as e:
                typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
            anchor = r.code
            label = f"set:{anchor}"
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
        label = f"set:{anchor}"
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

    # Hash + duplicate check.
    sha = _file_sha256(src)
    with db.connect() as conn:
        prior = db.find_ingest_log_by_hash(conn, sha)
    prior_success = next((p for p in prior if p["status"] == "success"), None)
    if prior_success and not force:
        msg = (
            f"this file's SHA-256 matches a previous successful ingest "
            f"(log id {prior_success['id']}, label {prior_success['label']!r}, "
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

    # Run the actual import.
    error: str | None = None
    result: dict | None = None
    try:
        result = lists_mod.list_import(label, path=src, mode=mode)
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

    # Persist the log entry.
    with db.connect() as conn:
        db.record_ingest_log(
            conn,
            label=label,
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

    summary = lists_mod.summarize_label(label) if error is None else None

    if json_out:
        out = {
            "status": "success" if error is None else "failed",
            "file": str(src),
            "archived_path": str(archived) if archived else None,
            "label": label,
            "mode": mode,
            "sha256": sha,
            "rows_added": (result or {}).get("added", 0),
            "rows_updated": (result or {}).get("updated", 0),
            "rows_zeroed": (result or {}).get("zeroed", 0),
            "warnings": (result or {}).get("warnings", []),
            "not_found": (result or {}).get("not_found", []),
            "extras": (result or {}).get("extras", []),
            "label_summary": (
                {
                    "distinct_rows": summary["distinct_rows"],
                    "total_qty": summary["total_qty"],
                    "total_value": summary["total_value"],
                }
                if summary else None
            ),
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
        f"List {label!r}: {result['updated']} updated, "
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
        typer.echo(f"  extra (not in seeded set list): {ex['raw']}", err=True)
    typer.echo(f"Archived inventory checklist → {archived}")
    typer.echo(
        f"{label!r} now: {summary['distinct_rows']} distinct rows, "
        f"qty {summary['total_qty']}, value ${summary['total_value']:.2f}"
    )


# ---------- list ----------

@list_app.command("import")
def list_import(
    label: str = typer.Argument(...),
    source: str = typer.Argument(None, help="Path to file (XLSX/text) or '-' for stdin (default: stdin)."),
):
    """Read a pasted block (stdin or text file) or a filled-in master-list
    XLSX and upsert into the labeled list."""
    text = None
    path = None
    if source is None or source == "-":
        text = sys.stdin.read()
    else:
        path = Path(source)
        if not path.exists():
            typer.echo(f"error: file not found: {path}", err=True); raise typer.Exit(2)

    result = lists_mod.list_import(label, text=text, path=path)
    typer.echo(f"List {label!r}: {result['updated']} updated, {result['added']} added")
    for w in result["warnings"]:
        typer.echo(f"  warning: {w}", err=True)
    for nf in result["not_found"]:
        if "raw" in nf:
            typer.echo(f"  not found: {nf['raw']} ({nf.get('reason','')})", err=True)
        else:
            typer.echo(f"  not found: {nf}", err=True)
    for ex in result["extras"]:
        typer.echo(f"  extra (not in seeded set list): {ex['raw']}", err=True)


@list_app.command("show")
def list_show(label: str = typer.Argument(...)):
    rows = lists_mod.list_show(label)
    if not rows:
        typer.echo(f"(empty list: {label})"); return
    typer.echo(f"{'qty':>4} {'finish':>7} {'set':>6} {'cn':>6}  name (rarity, usd)")
    for r in rows:
        if r.quantity == 0: continue
        usd = f"${r.unit_price:.2f}" if r.unit_price is not None else "—"
        # display_name renders as "<flavor_name> / <oracle_name>" for reskins,
        # plain oracle name otherwise. Matches the inventory-checklist XLSX.
        typer.echo(f"{r.quantity:>4} {r.finish:>7} {r.set_code:>6} "
                   f"{r.collector_number:>6}  {r.display_name} ({r.rarity}, {usd})")


@list_app.command("value")
def list_value(label: str = typer.Argument(...)):
    v = lists_mod.list_value(label)
    typer.echo(f"List {label!r}: ${v['total']:.2f} across {v['rows']} rows")
    if v["missing_price"]:
        typer.echo(f"Cards without USD price ({len(v['missing_price'])}):")
        for name, set_code, cn, finish in v["missing_price"]:
            typer.echo(f"  {name} ({set_code.upper()}) {cn} [{finish}]")


@list_app.command("delete")
def list_delete(label: str = typer.Argument(...),
                yes: bool = typer.Option(False, "--yes", "-y")):
    if not yes:
        typer.echo(f"refusing without --yes; this will delete list {label!r} and all its rows.", err=True)
        raise typer.Exit(2)
    n = lists_mod.list_delete(label)
    typer.echo(f"Deleted {n} list(s)")


@list_app.command("ls")
def list_ls():
    """List every saved list with row counts and total quantities."""
    rows = lists_mod.all_lists()
    if not rows:
        typer.echo("(no lists)"); return
    typer.echo(f"{'label':40} {'kind':10} {'qty':>6} {'rows':>6}  source")
    for r in rows:
        typer.echo(f"{r['label']:40} {r['kind']:10} {r['total_qty']:>6} "
                   f"{r['distinct_rows']:>6}  {r['source']}")


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

    Bound to ``set:<anchor>`` for the resolved family. The first set code you
    type becomes sticky; subsequent lines without a set use it. Each entry is
    a separate DB transaction — Ctrl-C is safe.

    Modes per line:
      - bare              → +1 (default)
      - +N                → increment by N
      - =N                → overwrite to exactly N (requires N >= 0)
      - trailing f / foil → this card is foil

    Other commands: u/undo, s <code>/set <code>, ?/help, q/quit.

    Run ``mm set master-list <name>`` once before this command — the REPL
    only updates rows that the master-list command has seeded into
    ``set:<anchor>``.
    """
    try:
        r, codes = _resolve_codes(
            name_or_code, include_kinds=list(include or []), only=list(only or []),
        )
    except (LookupError, typer.BadParameter) as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
    label = f"set:{r.code}"
    intake_mod.run_repl(r, label)


# ---------- export ----------

@app.command("export")
def export_cmd(
    target: str = typer.Argument(..., help="moxfield | manapool | tcgplayer | archidekt | plain | scryfall-json"),
    selector: str = typer.Argument(..., help="A selector string, e.g. 'label:set:fca' or 'set:fca missing'"),
    out: Path = typer.Option(None, "--out", help="Optional output path; otherwise prints to stdout."),
):
    """Materialize a selector and emit a paste-ready block for the target service."""
    try:
        rows = lists_mod.materialize(selector)
    except (ValueError, LookupError) as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)
    if not rows:
        typer.echo(f"(selector matched 0 rows: {selector})", err=True)
        raise typer.Exit(1)
    text = exports.build(target, rows)

    typer.echo(f"# selector: {selector}", err=True)
    typer.echo(f"# target: {target}", err=True)
    typer.echo(f"# rows: {len(rows)}", err=True)
    if target == "tcgplayer":
        typer.echo("# NOTE: TCGplayer Mass Entry format starts as '1 Card Name [Set Name]'.", err=True)
        typer.echo("#       On the FIRST paste, verify a few lines parse correctly. Adjust", err=True)
        typer.echo("#       src/magic_manager/exports/tcgplayer.py if reality disagrees.", err=True)

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
    # immutable archives, not active intake docs.
    files: list[Path] = []
    for pattern in ("*.xlsx", "*.md"):
        files.extend(p for p in INPUT_DIR.glob(pattern) if p.is_file())
    files = sorted(files)
    out_files: list[dict] = []
    for f in files:
        sha = _file_sha256(f)
        with db.connect() as conn:
            prior = db.find_ingest_log_by_hash(conn, sha)
        prior_success = next((p for p in prior if p["status"] == "success"), None)
        prior_failed = next((p for p in prior if p["status"] == "failed"), None)
        try:
            summary = lists_mod.summarize_xlsx_file(f)
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

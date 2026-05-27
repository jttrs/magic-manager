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

from . import db, exports, lists as lists_mod, sets as sets_mod

INPUT_DIR = Path("input")
PROCESSED_DIR = INPUT_DIR / "processed"

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

input_app = typer.Typer(no_args_is_help=True, help="Inspect intake XLSX files in input/.")

app.add_typer(set_app, name="set")
app.add_typer(list_app, name="list")
app.add_typer(input_app, name="input")


@app.callback()
def _app_init():
    """Run once-per-invocation startup tasks: dir migration + schema bump."""
    msg = db.migrate_inventory_to_input()
    if msg:
        typer.echo(f"info: {msg}", err=True)


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

    No slice → ``"master"`` (the V1.1 default).
    Codes only → ``codes-joined-by-plus``.
    Rarities only → ``rarities-joined-by-plus``.
    Both → ``codes-rarities``.
    """
    parts: list[str] = []
    if only_codes:
        parts.append("+".join(only_codes))
    if rarities:
        parts.append("+".join(rarities))
    return "-".join(parts) if parts else "master"


def _intake_path(slug: str, slice_suffix: str = "master") -> Path:
    return INPUT_DIR / f"{slug}-{slice_suffix}.xlsx"


def _processed_path(slug: str, slice_suffix: str = "master",
                    when: datetime | None = None) -> Path:
    when = when or datetime.now()
    return PROCESSED_DIR / f"{slug}-{slice_suffix}-{when:%Y-%m-%d-%H%M%S}.xlsx"


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
        help="Overwrite an existing intake XLSX without prompting.",
    ),
):
    """Build the inventory intake XLSX for a release family or a slice of it.

    The default family is the anchor set + every related set whose set_type
    is in {expansion, commander, masterpiece, promo}. Tokens, memorabilia
    (art series, scene boxes), and other set_types are excluded by default;
    opt them in with ``--include token,memorabilia``.

    The XLSX lands at ``input/<slug>-<slice>.xlsx`` where ``<slice>`` encodes
    the optional ``--only`` and ``--rarity`` filters (or ``master`` if neither
    is given). There can be at most one active intake per slice at a time;
    if one exists, the command refuses with exit
    ``EXIT_UNPROCESSED_INTAKE`` (3). Either ingest that file first via
    ``mm set ingest`` or pass ``--force``.
    """
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
    out_path = out or _intake_path(slug, slice_suffix)

    # Collision detection: only when the user is using the default path.
    if out is None and out_path.exists() and not force:
        typer.echo(f"refusing to overwrite existing intake doc: {out_path}", err=True)
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
                    f"    {row.quantity}x {row.name} ({row.set_code.upper()}) "
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

    seeded = sets_mod.seed_set_list(label, codes)
    typer.echo(f"Seeded list {label!r} ({seeded} new rows at qty=0)")

    if force and out_path.exists():
        typer.echo(f"  ! --force: overwriting {out_path}", err=True)

    n_rows, prefilled = sets_mod.write_master_list_xlsx(
        codes, out_path,
        # Tokens and memorabilia are governed by the family filter, not by a
        # second flag. If the user --included them they're in `codes` already.
        include_tokens=True,
        prepopulate_from_label=label,
        rarity_filter=rarities or None,
        anchor_code=r.code,
        slug=slug,
    )
    typer.echo(f"Wrote {n_rows} rows to {out_path}")
    if prefilled:
        typer.echo(f"  → {prefilled} qty cell(s) pre-filled from {label!r}")
    typer.echo()
    typer.echo("Next steps:")
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
        help="Override path to the intake XLSX. Default: input/<slug>-master.xlsx.",
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
    """Ingest a filled-in intake XLSX, then archive it under input/processed/.

    Imports the qty_normal / qty_foil cells into ``set:<anchor>`` honoring
    the file's partition (set codes + rarity from ``_meta`` or inferred from
    rows), then atomically renames the file with a timestamp so the next
    ``mm set master-list`` run will produce a fresh intake doc pre-populated
    from the now-saved DB state.
    """
    if mode not in ("replace", "additive"):
        typer.echo(f"error: --mode must be 'replace' or 'additive', got {mode!r}", err=True)
        raise typer.Exit(2)

    # Resolve path + anchor. Either name_or_code or --path must give us enough.
    if path is not None:
        src = path
        if not src.exists():
            typer.echo(f"error: no intake XLSX found at {src}", err=True)
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
        # Look for intake docs matching this family's slug. There can be more
        # than one (master + rarity slices); if exactly one matches use it,
        # otherwise force the user to disambiguate via --path.
        candidates = sorted(INPUT_DIR.glob(f"{slug}-*.xlsx")) if INPUT_DIR.exists() else []
        if not candidates:
            typer.echo(f"error: no intake XLSX found in {INPUT_DIR}/ for slug {slug!r}", err=True)
            typer.echo(f"  run `mm set master-list {name_or_code!r}` first", err=True)
            raise typer.Exit(2)
        if len(candidates) > 1:
            typer.echo(
                f"error: multiple intake XLSX files match slug {slug!r}; "
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
        # The stem is ``<slug>-<slice>`` (or just ``<slug>`` if no slice).
        stem = src.stem
        if stem.startswith(f"{slug}-"):
            slice_suffix = stem[len(slug) + 1:]
        else:
            slice_suffix = stem
        archived = _processed_path(slug, slice_suffix)
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
    typer.echo(f"Archived intake XLSX → {archived}")
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
        typer.echo(f"{r.quantity:>4} {r.finish:>7} {r.set_code:>6} "
                   f"{r.collector_number:>6}  {r.name} ({r.rarity}, {usd})")


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

@input_app.command("list")
def input_list(
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
):
    """List every active intake XLSX in ``input/`` with a summary and
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

    files = sorted(p for p in INPUT_DIR.glob("*.xlsx") if p.is_file())
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

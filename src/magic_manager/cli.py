"""``mm`` CLI: orchestrates set syncing, master-list generation, list import,
and exports.

Run via ``uv run mm …`` from the repo root.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import typer

from . import db, exports, lists as lists_mod, sets as sets_mod

INVENTORY_DIR = Path("inventory")
PROCESSED_DIR = INVENTORY_DIR / "processed"

# Exit codes used by master-list collision detection. The `generate-set-list`
# skill reads these to decide whether to prompt for ingest-or-force.
EXIT_UNPROCESSED_INTAKE = 3

app = typer.Typer(no_args_is_help=True, add_completion=False,
                  help="Local-first MTG collection / set / wishlist manager.")
set_app = typer.Typer(no_args_is_help=True, help="Set sync and master-list generation.")
list_app = typer.Typer(no_args_is_help=True, help="Labeled lists.")

app.add_typer(set_app, name="set")
app.add_typer(list_app, name="list")


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


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


def _intake_path(slug: str) -> Path:
    return INVENTORY_DIR / f"{slug}-master.xlsx"


def _processed_path(slug: str, when: datetime | None = None) -> Path:
    when = when or datetime.now()
    return PROCESSED_DIR / f"{slug}-master-{when:%Y-%m-%d-%H%M%S}.xlsx"


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
    out: Path = typer.Option(
        None, "--out",
        help="Override output path. When set, collision detection is skipped.",
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Overwrite an existing intake XLSX without prompting.",
    ),
):
    """Build the inventory intake XLSX for a release family.

    The default family is the anchor set + every related set whose set_type
    is in {expansion, commander, masterpiece, promo}. Tokens, memorabilia
    (art series, scene boxes), and other set_types are excluded by default;
    opt them in with ``--include token,memorabilia``.

    The XLSX lands at ``inventory/<slug>-master.xlsx`` (no date stamp — there
    is at most one active intake doc per family at a time). If one already
    exists, the command refuses with exit ``EXIT_UNPROCESSED_INTAKE`` (3) and
    prints a readout of what's currently in ``set:<anchor>``. Either ingest
    that file first via ``mm set ingest`` or pass ``--force``.
    """
    try:
        r, codes = _resolve_codes(name_or_code, include_kinds=list(include or []), only=list(only or []))
    except (LookupError, typer.BadParameter) as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)

    slug = _slug(r.name)
    label = f"set:{r.code}"
    out_path = out or _intake_path(slug)

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
    name_or_code: str = typer.Argument(...),
    path: Path = typer.Option(
        None, "--path",
        help="Override path to the intake XLSX. Default: inventory/<slug>-master.xlsx",
    ),
):
    """Ingest a filled-in intake XLSX, then archive it under inventory/processed/.

    Imports the qty_normal / qty_foil cells into ``set:<anchor>`` (same logic
    as ``mm list import``), then atomically renames the file with a timestamp
    so the next ``mm set master-list`` run will produce a fresh intake doc
    pre-populated from the now-saved DB state.
    """
    try:
        r = sets_mod.resolve(name_or_code)
    except LookupError as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)

    slug = _slug(r.name)
    label = f"set:{r.code}"
    src = path or _intake_path(slug)
    if not src.exists():
        typer.echo(f"error: no intake XLSX found at {src}", err=True)
        typer.echo(f"  run `mm set master-list {name_or_code!r}` first", err=True)
        raise typer.Exit(2)

    result = lists_mod.list_import(label, path=src)
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

    dest = _processed_path(slug)
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dest)
    typer.echo(f"Archived intake XLSX → {dest}")

    # Show the current state so the user can sanity-check before they walk away.
    s = lists_mod.summarize_label(label)
    typer.echo(
        f"{label!r} now: {s['distinct_rows']} distinct rows, qty {s['total_qty']}, "
        f"value ${s['total_value']:.2f}"
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


# ---------- entry point ----------

if __name__ == "__main__":
    app()

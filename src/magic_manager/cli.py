"""``mm`` CLI: orchestrates set syncing, master-list generation, list import,
and exports.

Run via ``uv run mm …`` from the repo root.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import typer

from . import db, exports, lists as lists_mod, sets as sets_mod

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


@set_app.command("master-list")
def set_master_list(
    name_or_code: str = typer.Argument(...),
    include_related: bool = typer.Option(False, "--include-related"),
    only: list[str] = typer.Option(None, "--only"),
    include_tokens: bool = typer.Option(False, "--include-tokens"),
    out: Path = typer.Option(None, "--out",
                             help="Output XLSX path. Default: inventory/<slug>-master-<YYYY-MM-DD>.xlsx"),
):
    """Sync the set, seed the labeled list ``set:<code>`` with every printing
    at qty=0, and emit a fillable XLSX."""
    try:
        r = sets_mod.resolve(name_or_code)
    except LookupError as e:
        typer.echo(f"error: {e}", err=True); raise typer.Exit(2)

    codes = r.all_codes if include_related else [r.code]
    if only:
        wanted = {c.strip().lower() for raw in only for c in raw.split(",")}
        codes = [c for c in codes if c in wanted]

    typer.echo(f"Syncing {len(codes)} set(s): {' '.join(codes)}")
    n_synced = sets_mod.sync(codes)
    typer.echo(f"  → {n_synced} cards upserted")

    label = f"set:{r.code}"
    seeded = sets_mod.seed_set_list(label, codes)
    typer.echo(f"Seeded list {label!r} ({seeded} new rows at qty=0)")

    out_path = out or Path("inventory") / f"{_slug(r.name)}-master-{date.today():%Y-%m-%d}.xlsx"
    rows = sets_mod.write_master_list_xlsx(codes, out_path, include_tokens=include_tokens)
    typer.echo(f"Wrote {rows} rows to {out_path}")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo(f"  1. Open {out_path} in Excel/Numbers and fill in qty_normal / qty_foil.")
    typer.echo(f"  2. Run: mm list import {label} {out_path}")


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

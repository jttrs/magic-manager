"""Scan-loop REPL for rapid manual inventory entry.

The user types ``<set>? <cn> [+N|=N] [f|foil]`` per line; each line maps to
one ``db.upsert_list_row`` call against the family-anchored ``set:<anchor>``
list. Sticky set context means after the first ``fca 4`` you can just type
``5`` and it's understood as ``fca 5``.

Persistence is per-line (each entry is its own DB transaction via
``db.connect()``), so Ctrl-C mid-session is safe — entries through the last
successful prompt are committed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import db, lists as lists_mod
from .sets import ResolvedSet


# Token forms accepted on a single input line.
SET_RE = re.compile(r"^[A-Za-z0-9]{2,6}$")
CN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-★]*$")
PLUS_RE = re.compile(r"^\+(\d+)$")
EQUALS_RE = re.compile(r"^=(\d+)$")
FOIL_TOKENS = ("f", "foil")


@dataclass
class Entry:
    """A successful entry — pushed to the undo stack so we can revert it."""
    set_code: str
    collector_number: str
    finish: str
    prev_qty: int
    new_qty: int


@dataclass
class ParsedLine:
    set_code: str | None
    collector_number: str
    qty_op: str   # "+N" or "=N"
    qty_n: int
    foil: bool


def parse_line(line: str, sticky_set: str | None) -> ParsedLine | None:
    """Parse one prompt line. Returns None if unparseable.

    Tokens are whitespace-separated. Order:
      - optional set code (3-6 alphanumeric)
      - collector number
      - optional ``+N`` or ``=N`` (default ``+1``)
      - optional ``f`` / ``foil``
    """
    tokens = line.strip().split()
    if not tokens:
        return None

    set_code: str | None = None
    cn: str | None = None
    qty_op = "+"
    qty_n = 1
    foil = False

    # The first token may be a set code OR a CN. Heuristic: if the next token
    # looks like a CN, treat the first as a set; otherwise treat the first as
    # the CN and use the sticky set.
    head = tokens[0]
    rest = tokens[1:]

    if SET_RE.match(head) and rest and CN_RE.match(rest[0]):
        # Standard form: "fca 4 ..."
        set_code = head.lower()
        cn = rest[0]
        rest = rest[1:]
    elif CN_RE.match(head):
        # Sticky-set form: "4 ..."
        set_code = sticky_set
        cn = head
    else:
        return None

    for tok in rest:
        if PLUS_RE.match(tok):
            qty_op = "+"
            qty_n = int(PLUS_RE.match(tok).group(1))
        elif EQUALS_RE.match(tok):
            qty_op = "="
            qty_n = int(EQUALS_RE.match(tok).group(1))
        elif tok.lower() in FOIL_TOKENS:
            foil = True
        else:
            # Unknown token — better to fail than silently ignore.
            return None

    return ParsedLine(
        set_code=set_code, collector_number=cn,
        qty_op=qty_op, qty_n=qty_n, foil=foil,
    )


def run_repl(resolved: ResolvedSet, label: str, prompt: str = "> ") -> None:
    """Open the REPL loop bound to ``label`` (e.g. ``set:fca``).

    The family is ``resolved.all_codes``; cards outside it are rejected.
    """
    family = set(resolved.all_codes)
    sticky_set = resolved.code
    undo_stack: list[Entry] = []
    session_count = 0

    print(f"mm intake — bound to {label!r} (family: {' '.join(resolved.all_codes)})")
    print(f"sticky set: {sticky_set!r}.  Type '?' for help, 'q' to quit.\n")

    while True:
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        cmd = line.strip().lower()
        if cmd in ("q", "quit", "exit"):
            break
        if cmd in ("?", "help", "h"):
            _print_help(sticky_set, undo_stack, session_count)
            continue
        if cmd in ("u", "undo"):
            sticky_set = _do_undo(undo_stack, label, sticky_set)
            continue
        if cmd.startswith("s ") or cmd.startswith("set "):
            new_set = cmd.split(maxsplit=1)[1].strip().lower()
            if SET_RE.match(new_set):
                if new_set not in family:
                    print(f"  [warn] {new_set!r} isn't in the family for {label!r} "
                          f"({sorted(family)}). Sticky set unchanged.")
                else:
                    sticky_set = new_set
                    print(f"  sticky set → {sticky_set!r}")
            else:
                print(f"  [error] invalid set code: {new_set!r}")
            continue
        if not line.strip():
            continue

        parsed = parse_line(line, sticky_set)
        if parsed is None:
            print(f"  [error] couldn't parse: {line!r}.  Try '<set> <cn> [+N|=N] [f]'.")
            continue
        if parsed.set_code is None:
            print(f"  [error] no sticky set yet — type 'set <code>' first or include the set code on this line.")
            continue
        if parsed.set_code not in family:
            print(f"  [error] {parsed.set_code!r} isn't in the family for {label!r}. "
                  f"Family: {sorted(family)}.")
            continue

        entry = _apply(label, parsed)
        if entry is None:
            continue

        # Sticky set follows the most recent successful entry.
        sticky_set = entry.set_code
        undo_stack.append(entry)
        session_count += 1

    _print_summary(label, session_count)


# ---------- internals ----------

def _print_help(sticky_set: str | None, undo_stack: list[Entry], count: int) -> None:
    print()
    print("  Line grammar:  <set>? <cn> [+N|=N] [f|foil]")
    print("    fca 4         increment Counterspell by 1 (default)")
    print("    4 +3          same set as last (sticky), increment by 3")
    print("    4 =1          set qty to exactly 1 (overwrite)")
    print("    4 f           same card, foil instead")
    print("    4 +2 f        increment foil by 2")
    print()
    print("  Commands:  q/quit  u/undo  s/set <code>  ?/help")
    print()
    print(f"  sticky set: {sticky_set!r}")
    print(f"  session entries so far: {count}")
    if undo_stack:
        last = undo_stack[-1]
        print(f"  last entry: ({last.set_code.upper()}) {last.collector_number} "
              f"{last.finish} {last.prev_qty} → {last.new_qty}")
    print()


def _apply(label: str, parsed: ParsedLine) -> Entry | None:
    """Run one entry as a DB transaction. Returns the Entry on success."""
    from .treatments import compute_treatment
    finish = "foil" if parsed.foil else "nonfoil"
    with db.connect() as conn:
        # Look up the printing. Pull the treatment-input fields too so the
        # feedback line can show e.g. [b|sm] alongside the card name.
        card = conn.execute(
            """
            SELECT c.scryfall_id, c.name, c.flavor_name,
                   c.prices_usd, c.prices_usd_foil,
                   c.frame_effects, c.promo_types, c.full_art
            FROM cards c
            WHERE LOWER(c.set_code) = ? AND c.collector_number = ?
            """,
            (parsed.set_code.lower(), parsed.collector_number),
        ).fetchone()

        if card is None:
            print(f"  [error] no card at ({parsed.set_code.upper()}) {parsed.collector_number} "
                  f"in the local DB. Run `mm set sync {parsed.set_code}` first if needed.")
            return None

        # Verify the card is in the seeded set list (master-list seeded it).
        existing = conn.execute(
            "SELECT quantity FROM list_rows WHERE label = ? AND scryfall_id = ? AND finish = ?",
            (label, card["scryfall_id"], finish),
        ).fetchone()
        if existing is None:
            print(f"  [error] card not seeded in {label!r}. "
                  f"Run `mm set master-list <name>` once before scanning.")
            return None

        prev_qty = existing["quantity"]
        if parsed.qty_op == "+":
            new_qty = prev_qty + parsed.qty_n
        else:  # "="
            if parsed.qty_n < 0:
                print(f"  [error] =N must be non-negative, got {parsed.qty_n}")
                return None
            new_qty = parsed.qty_n

        if new_qty == prev_qty:
            print(f"  [no-op] qty already {prev_qty}")
            return None

        db.upsert_list_row(conn, label, card["scryfall_id"], finish, new_qty)

        # Build display name for feedback.
        flavor = card["flavor_name"]
        display = f"{flavor} / {card['name']}" if flavor else card["name"]
        unit = card["prices_usd_foil"] if finish == "foil" else card["prices_usd"]
        unit_s = f"${unit:.2f}" if unit is not None else "—"
        delta_s = (
            f"qty {prev_qty} → {new_qty} (+{new_qty - prev_qty})"
            if parsed.qty_op == "+"
            else f"qty {prev_qty} → {new_qty} (=)"
        )
        treatment = compute_treatment(card)
        treatment_s = f" [{treatment}]" if treatment else ""
        print(f"  [OK] {display} ({parsed.set_code.upper()}) {parsed.collector_number} "
              f"{finish}{treatment_s}  {delta_s}  {unit_s}")

    return Entry(
        set_code=parsed.set_code.lower(),
        collector_number=parsed.collector_number,
        finish=finish, prev_qty=prev_qty, new_qty=new_qty,
    )


def _do_undo(undo_stack: list[Entry], label: str, sticky_set: str | None) -> str | None:
    if not undo_stack:
        print("  [undo] nothing to undo")
        return sticky_set
    last = undo_stack.pop()
    with db.connect() as conn:
        # Re-fetch the card so we can confirm it still exists; then revert.
        card = conn.execute(
            "SELECT scryfall_id FROM cards WHERE LOWER(set_code) = ? AND collector_number = ?",
            (last.set_code, last.collector_number),
        ).fetchone()
        if card is None:
            print("  [undo] couldn't re-find card; aborting")
            return sticky_set
        db.upsert_list_row(conn, label, card["scryfall_id"], last.finish, last.prev_qty)
    print(f"  [UNDO] {last.set_code.upper()} {last.collector_number} {last.finish}: "
          f"{last.new_qty} → {last.prev_qty}")
    return sticky_set


def _print_summary(label: str, count: int) -> None:
    s = lists_mod.summarize_label(label)
    print()
    print(f"Session ended.  {count} entr{'y' if count == 1 else 'ies'} applied.")
    print(f"{label!r} now: {s['distinct_rows']} distinct rows, "
          f"qty {s['total_qty']}, value ${s['total_value']:.2f}")

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

from . import db, inventory as inv_mod
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


def run_repl(resolved: ResolvedSet, prompt: str = "> ") -> None:
    """Open the REPL loop bound to ``resolved``'s family.

    Each accepted line writes directly to the V2 ``inventory`` table.
    Cards outside ``resolved.all_codes`` are rejected.
    """
    family = set(resolved.all_codes)
    sticky_set = resolved.code
    undo_stack: list[Entry] = []
    session_count = 0
    anchor = resolved.code

    print(f"mm intake — bound to family {anchor!r} ({' '.join(resolved.all_codes)})")
    print(f"sticky set: {sticky_set!r}.  Writes to inventory.  '?' for help, 'q' to quit.\n")

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
            sticky_set = _do_undo(undo_stack, sticky_set)
            continue
        if cmd.startswith("s ") or cmd.startswith("set "):
            new_set = cmd.split(maxsplit=1)[1].strip().lower()
            if SET_RE.match(new_set):
                if new_set not in family:
                    print(f"  [warn] {new_set!r} isn't in family {anchor!r} "
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
            print(f"  [error] {parsed.set_code!r} isn't in family {anchor!r}. "
                  f"Family: {sorted(family)}.")
            continue

        entry = _apply(parsed)
        if entry is None:
            continue

        sticky_set = entry.set_code
        undo_stack.append(entry)
        session_count += 1

    _print_summary(anchor, family, session_count)


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


def _apply(parsed: ParsedLine) -> Entry | None:
    """Run one entry against the inventory table. Returns the Entry on success."""
    from .treatments import compute_treatment
    finish = "foil" if parsed.foil else "nonfoil"
    with db.connect() as conn:
        # Look up the printing. Pull treatment-input fields too for feedback.
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

        existing = conn.execute(
            "SELECT quantity FROM inventory WHERE scryfall_id = ? AND finish = ?",
            (card["scryfall_id"], finish),
        ).fetchone()
        prev_qty = existing["quantity"] if existing else 0

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

    # Outside the connection: route through inventory module so behavior
    # (acquired_at, replace semantics) stays consistent.
    if new_qty == 0:
        inv_mod.inventory_remove(card["scryfall_id"], finish, qty=prev_qty)
    else:
        inv_mod.inventory_set(card["scryfall_id"], finish, new_qty)

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


def _do_undo(undo_stack: list[Entry], sticky_set: str | None) -> str | None:
    if not undo_stack:
        print("  [undo] nothing to undo")
        return sticky_set
    last = undo_stack.pop()
    with db.connect() as conn:
        card = conn.execute(
            "SELECT scryfall_id FROM cards WHERE LOWER(set_code) = ? AND collector_number = ?",
            (last.set_code, last.collector_number),
        ).fetchone()
        if card is None:
            print("  [undo] couldn't re-find card; aborting")
            return sticky_set
    if last.prev_qty == 0:
        inv_mod.inventory_remove(card["scryfall_id"], last.finish, qty=last.new_qty)
    else:
        inv_mod.inventory_set(card["scryfall_id"], last.finish, last.prev_qty)
    print(f"  [UNDO] {last.set_code.upper()} {last.collector_number} {last.finish}: "
          f"{last.new_qty} → {last.prev_qty}")
    return sticky_set


def _print_summary(anchor: str, family: set[str], count: int) -> None:
    rows = [r for r in inv_mod.inventory_show() if r.set_code in family]
    distinct = len(rows)
    total_qty = sum(r.quantity for r in rows)
    total_value = sum((r.line_value or 0.0) for r in rows)
    print()
    print(f"Session ended.  {count} entr{'y' if count == 1 else 'ies'} applied.")
    print(f"Inventory in family {anchor!r}: {distinct} distinct rows, "
          f"qty {total_qty}, value ${total_value:.2f}")

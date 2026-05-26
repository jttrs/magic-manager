"""Moxfield import-text format.

    1 Card Name (SET) CN
    4 Lightning Bolt (LEB) 162
    1 Sol Ring (CMM) 410 ★            (foil)
    1 Pegasus Guardian // Rescue the Foal (CLB) 36

Section headers go on their own line with a blank line above them. We don't
emit section headers for V1 lists — they're flat. ManaPool consumes this
format directly via its "import from Moxfield" path.
"""

from __future__ import annotations


def build(rows) -> str:
    out = []
    for r in rows:
        line = _line(r)
        out.append(line)
    return "\n".join(out) + ("\n" if out else "")


def _line(r) -> str:
    c = r.card
    name = c["name"]
    set_code = (c["set"] or "").upper()
    cn = c["collector_number"] or ""
    foil = " ★" if r.finish == "foil" else ""
    if set_code and cn:
        return f"{r.quantity} {name} ({set_code}) {cn}{foil}"
    return f"{r.quantity} {name}{foil}"

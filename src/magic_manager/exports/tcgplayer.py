"""TCGplayer Mass Entry text format.

    <qty> <Card Name> [<SETCODE>] <CN>
    1 Lightning Bolt [SLD] 84

Per TCGplayer's "Getting Started With Mass Entry" help article: the set
identifier is the bracketed UPPERCASE set code (NOT the full set name —
that was an earlier mistaken implementation), followed by the collector
number after the bracket. Quantity at the front, card name in the middle.

**Foil/nonfoil is NOT marked per-line.** TCGplayer's Mass Entry UI exposes a
foil-vs-nonfoil control next to the paste box, applied to the whole batch on
submit. To build a mixed cart, run this exporter twice with selectors
filtered on ``finish=nonfoil`` and ``finish=foil``, paste each block
separately, and toggle the UI control between pastes. The
``missing-from-set`` skill encapsulates this two-block workflow.

ManaPool consumes Moxfield-format directly (see ``moxfield.py`` and the
alias in ``__init__.py``); ManaPool's bulk-add parses the ``*F*`` per-line
foil marker (Moxfield's documented import token), so it stays single-block.
Don't confuse the two.
"""

from __future__ import annotations


def build(rows) -> str:
    out = []
    for r in rows:
        c = r.card
        name = c["name"]
        set_code = (c.get("set") or "").upper()
        cn = c.get("collector_number") or ""
        if set_code and cn:
            out.append(f"{r.quantity} {name} [{set_code}] {cn}")
        elif set_code:
            out.append(f"{r.quantity} {name} [{set_code}]")
        else:
            out.append(f"{r.quantity} {name}")
    text = "\n".join(out)
    return text + ("\n" if out else "")

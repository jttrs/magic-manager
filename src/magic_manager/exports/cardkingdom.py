"""Card Kingdom Deck Builder export (https://www.cardkingdom.com/builder).

Card Kingdom's bulk-buy paste box accepts only ``qty name`` lines — no set code,
collector number or foil marker — and asks the buyer to pick edition/finish in
its per-card dropdowns after "Find Cards". So exact printings can't be carried;
copies of the same card name (any printing/finish) are summed into one line,
in first-seen order. Double-faced names keep the front face, which is what the
builder matches.
"""

from __future__ import annotations

PASTE_URL = "https://www.cardkingdom.com/builder"


def build(rows) -> str:
    totals: dict[str, int] = {}
    for r in rows:
        name = (r.card.get("name") or "").split(" // ")[0].strip()
        if name:
            totals[name] = totals.get(name, 0) + max(1, int(r.quantity or 1))
    return "".join(f"{q} {n}\n" for n, q in totals.items())

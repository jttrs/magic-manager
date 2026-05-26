"""TSV plain-text export, for spreadsheet pivots.

    qty\tname\tset\tcn\tfinish\tunit_usd\tline_usd
"""

from __future__ import annotations


def build(rows) -> str:
    header = "qty\tname\tset\tcn\tfinish\tunit_usd\tline_usd"
    out = [header]
    for r in rows:
        c = r.card
        unit = c.get("prices_usd_foil") if r.finish == "foil" else c.get("prices_usd")
        line = unit * r.quantity if unit is not None else None
        out.append(
            f"{r.quantity}\t{c['name']}\t{(c['set'] or '').upper()}\t"
            f"{c['collector_number'] or ''}\t{r.finish}\t"
            f"{unit if unit is not None else ''}\t"
            f"{line if line is not None else ''}"
        )
    return "\n".join(out) + ("\n" if out else "")

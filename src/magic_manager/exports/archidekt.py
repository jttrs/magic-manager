"""Archidekt import format.

    1x Card Name (set) cn
    1x Sol Ring (cmm) 410

Archidekt's full format also supports per-card category tags ([Resilience],
[Maybeboard{noDeck}{noPrice},Mana Advantage]); V1 emits the basic form without
tags.
"""

from __future__ import annotations


def build(rows) -> str:
    out = []
    for r in rows:
        c = r.card
        set_code = (c["set"] or "").lower()
        cn = c["collector_number"] or ""
        if set_code and cn:
            out.append(f"{r.quantity}x {c['name']} ({set_code}) {cn}")
        else:
            out.append(f"{r.quantity}x {c['name']}")
    return "\n".join(out) + ("\n" if out else "")

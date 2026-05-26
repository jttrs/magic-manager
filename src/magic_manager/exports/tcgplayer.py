"""TCGplayer Mass Entry text format.

    1 Card Name [Set Name]
    1 Lightning Bolt [Magic 2021]

V1 starts with this widely-attested form. The Mass Entry tool's exact spec was
not accessible during planning; ``mm export tcgplayer`` prints a reminder
asking the user to verify the first paste, and we adjust this builder if
reality disagrees. ManaPool consumes Moxfield-format directly, so don't
confuse the two.

Set names come from Scryfall via a small in-memory cache. The wrapper caches
``/sets`` for 24h, so this is a single API call per session at worst.
"""

from __future__ import annotations

from .. import scryfall

_NAME_CACHE: dict[str, str] | None = None


def build(rows) -> str:
    out = []
    for r in rows:
        c = r.card
        set_name = _set_name(c["set"]) if c.get("set") else None
        if set_name:
            out.append(f"{r.quantity} {c['name']} [{set_name}]")
        else:
            out.append(f"{r.quantity} {c['name']}")
    text = "\n".join(out)
    return text + ("\n" if out else "")


def _set_name(code: str) -> str | None:
    global _NAME_CACHE
    if _NAME_CACHE is None:
        _NAME_CACHE = {s["code"]: s["name"] for s in scryfall.all_sets()}
    return _NAME_CACHE.get(code.lower())

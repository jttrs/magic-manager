"""TCGplayer Mass Entry text format.

    1 Card Name [Set Name]
    1 Lightning Bolt [Magic 2021]

**Foil/nonfoil is NOT marked per-line.** TCGplayer's Mass Entry UI exposes a
foil-vs-nonfoil control next to the paste box, applied to the whole batch on
submit. Adding a per-line marker (e.g. ``- Foil``) breaks the format. To
build a mixed cart, run this exporter twice with selectors filtered on
``finish=nonfoil`` and ``finish=foil``, paste each block separately, and
toggle the UI control between pastes. The ``missing-from-set`` skill
encapsulates this two-block workflow.

ManaPool consumes Moxfield-format directly (see ``moxfield.py`` and the
alias in ``__init__.py``); ManaPool's bulk-add accepts the ``★`` per-line
foil marker, so it stays single-block. Don't confuse the two.

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

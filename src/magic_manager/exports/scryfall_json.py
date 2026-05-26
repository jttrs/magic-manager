"""Scryfall /cards/collection identifier JSON.

    {"identifiers":[{"set":"fca","collector_number":"2"}, ...]}

Useful for piping into our own scryfall.sh collection subcommand or anywhere
else that takes Scryfall identifiers.
"""

from __future__ import annotations

import json


def build(rows) -> str:
    idents = []
    for r in rows:
        c = r.card
        if c.get("set") and c.get("collector_number"):
            idents.append({"set": c["set"], "collector_number": c["collector_number"]})
        else:
            idents.append({"name": c["name"]})
    return json.dumps({"identifiers": idents}, indent=2) + "\n"

"""Export-target builders. Each takes ``rows`` (list of MaterializedRow) and a
verbose flag, and returns a string ready to copy/paste into the target service.
"""

from . import moxfield, tcgplayer, archidekt, plain, scryfall_json

TARGETS = {
    "moxfield":      moxfield.build,
    "manapool":      moxfield.build,  # ManaPool consumes Moxfield format natively
    "tcgplayer":     tcgplayer.build,
    "archidekt":     archidekt.build,
    "plain-text":    plain.build,
    "plain":         plain.build,
    "scryfall-json": scryfall_json.build,
    "scryfall_json": scryfall_json.build,
}


def build(target: str, rows) -> str:
    if target not in TARGETS:
        raise ValueError(f"unknown export target {target!r}; "
                         f"valid: {sorted(set(TARGETS))}")
    return TARGETS[target](rows)

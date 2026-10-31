"""scripts/set_status.py precon_summary: the >=50%-of-cards fallback for decks
with no source_set_code reads the deck's CURRENT version (deck_cards is keyed
on deck_version_id, not deck_id)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "set_status_script", ROOT / "scripts" / "set_status.py")
set_status = importlib.util.module_from_spec(_spec)
sys.modules["set_status_script"] = set_status
_spec.loader.exec_module(set_status)


def test_null_source_deck_counted_by_card_share(seed_cards, make_card):
    from magic_manager import decks

    seed_cards([
        make_card(id="fin-a", set="fin", collector_number="1"),
        make_card(id="fin-b", set="fin", collector_number="2"),
        make_card(id="ltr-a", set="ltr", collector_number="1"),
    ])
    decks.deck_create("mostly-fin", "Mostly FIN")
    decks.deck_add_card("mostly-fin", "fin-a", "main", "nonfoil", 2)
    decks.deck_add_card("mostly-fin", "fin-b", "main", "nonfoil", 1)
    decks.deck_add_card("mostly-fin", "ltr-a", "main", "nonfoil", 1)
    decks.deck_create("mostly-ltr", "Mostly LTR")
    decks.deck_add_card("mostly-ltr", "ltr-a", "main", "nonfoil", 3)
    decks.deck_add_card("mostly-ltr", "fin-a", "main", "nonfoil", 1)

    assert sum(set_status.precon_summary(["fin"]).values()) == 1
    assert sum(set_status.precon_summary(["ltr"]).values()) == 1

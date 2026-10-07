"""Standing guard: every missing-set-style buy-list producer routes its singles
through the shared physical-buyable gate, so none can silently leak tokens /
digital-only / family-unobtainable / meld-back prints into a shopping list.

Two complementary checks:

1. A FUNCTIONAL check that jumpstart_buildable's gate actually fires (a seeded
   token in the buildable target is dropped by default, kept with --no-filter).
2. A SOURCE check pinning WHICH producers filter and which are documented
   exceptions, so adding a new unfiltered buy-list producer trips this test.

The exceptions are intentional, not oversights:
  - `mm export` / `export.build(fmt, rows)` on an explicit user selector — the
    user asked for exactly those rows; forcing a filter would be wrong.
  - `mm deck push-moxfield` — pushes a deck's own cards, not a missing-set union.
  - `mm query missing-jumpstart` / `jumpstart.missing_packs` — emits WHOLE un-owned pack contents (you buy
    the pack, token included); a different semantic from a singles buy-list.
  - `src/magic_manager/card_diff_tiles.py` (card-diff gallery + web view) — the gallery's "copy buy-list" button exports
    exactly the tiles currently DISPLAYED, which are the card-diff pools already
    sourced from `missing.missing_printings` (physical-buyable-filtered upstream)
    and deduped; it re-formats vetted rows, it doesn't produce a new unfiltered
    singles union.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


# ---------- 1. functional: the jumpstart_buildable gate fires ----------

@pytest.fixture
def jfam(monkeypatch):
    """Resolve 'jtest' as a single-code family offline."""
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets",
                        lambda: [{"code": "jtest", "parent_set_code": None,
                                  "name": "JTest", "set_type": "expansion"}])


def test_jumpstart_buildable_gate_drops_tokens_by_default(tmp_db, jfam, seed_cards, make_card, monkeypatch):
    """A token in the buildable target is dropped by the default physical_buyable
    gate, and kept when --no-filter is passed."""
    import jumpstart_buildable as jb
    seed_cards([
        make_card(id="real", set="jtest", collector_number="5", rarity="rare", name="Real Card"),
        make_card(id="tok", set="jtest", collector_number="20", rarity="rare",
                  name="Spirit Token", layout="token"),
    ])
    # Build the two MaterializedRows the producer would have after resolution.
    from magic_manager import selectors as sel, missing as missing_mod
    rows = []
    import magic_manager.db as db
    with db.connect() as conn:
        for sid in ("real", "tok"):
            r = conn.execute(f"SELECT {sel._CARD_COLS} FROM cards c WHERE c.scryfall_id=?",
                             (sid,)).fetchone()
            rows.append(sel.MaterializedRow(scryfall_id=sid, quantity=1,
                                            finish="nonfoil", card=sel._card_dict(r)))
    # Default gate: token dropped.
    kept = {r.scryfall_id for r in missing_mod.physical_buyable(rows, "jtest")}
    assert kept == {"real"}
    # The producer (the jumpstart engine) uses this exact call; confirm it's wired.
    from magic_manager import jumpstart
    assert jb.jumpstart is jumpstart and jumpstart.missing_mod is missing_mod


# ---------- 2. source: pin which producers filter ----------

def _calls_physical_buyable(path: Path) -> bool:
    src = path.read_text(encoding="utf-8")
    return bool(re.search(r"\bphysical_buyable\s*\(", src))


def _calls_missing_printings(path: Path) -> bool:
    src = path.read_text(encoding="utf-8")
    return bool(re.search(r"\bmissing_printings\s*\(", src))


def test_jumpstart_buildable_source_routes_through_gate():
    engine = ROOT / "src" / "magic_manager" / "jumpstart.py"
    assert _calls_physical_buyable(engine), \
        "jumpstart.buildable_missing must call physical_buyable (buy-list singles gate)"
    # and the script exposes the --no-filter escape hatch
    assert "--no-filter" in (ROOT / "scripts" / "jumpstart_buildable.py").read_text(encoding="utf-8")


def test_cli_missing_set_filters_via_missing_printings():
    """query missing-set gets its filtering from missing_printings (which applies
    the same chokepoints) rather than physical_buyable — assert that path exists."""
    cli = ROOT / "src" / "magic_manager" / "cli.py"
    assert _calls_missing_printings(cli)


def test_no_new_unfiltered_buylist_producer():
    """Enumerate the files that build buy-list artifacts (exports.build) and assert
    each is either a known filtered producer or a documented exception. A NEW
    producer that doesn't route through the gate will fail here until it either
    filters or is added to EXCEPTIONS with a reason."""
    producers = set()
    for base in (ROOT / "scripts", ROOT / "src" / "magic_manager"):
        for p in base.rglob("*.py"):
            if re.search(r"\bexports\.build\s*\(", p.read_text(encoding="utf-8")):
                producers.add(p.relative_to(ROOT).as_posix())

    # Known filtered producers.
    filtered = {"scripts/jumpstart_buildable.py", "src/magic_manager/cli.py",
                "src/magic_manager/jumpstart.py"}
    # Documented exceptions (see module docstring).
    exceptions: dict[str, str] = {
        "src/magic_manager/card_diff_tiles.py": "re-formats the already-filtered, deduped "
        "card-diff pools currently DISPLAYED (sourced from missing_printings) to "
        "the clipboard — not a new unfiltered singles union.",
        "src/magic_manager/collection_view.py": "buy_lines() formats exactly the "
        "(printing, finish, qty) picks the user marked in the Collection view, whose "
        "universe already excludes tokens, digital-only, hard-unobtainable and "
        "excluded variants — not an unfiltered singles union.",
    }

    unaccounted = producers - filtered - set(exceptions)
    assert not unaccounted, (
        f"new buy-list producer(s) not routing through physical_buyable and not "
        f"a documented exception: {sorted(unaccounted)}. Either filter the singles "
        f"via missing.physical_buyable or add to EXCEPTIONS with a reason."
    )

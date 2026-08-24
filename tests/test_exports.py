"""Unit tests for magic_manager.exports.build() dispatch + per-target output.

exports.build(target, rows) dispatches to per-module build(rows) functions in
exports/__init__.py's TARGETS map. tcgplayer.build() queries the local
``cards`` table (for same-set collision detection), so these tests use the
``tmp_db`` fixture even though no rows are seeded into it — an empty table
still lets the query run.

Exact output strings below were confirmed by running exports.build() before
asserting.
"""

from __future__ import annotations

import json

from magic_manager.selectors import MaterializedRow
from magic_manager import exports


def _rows():
    return [
        MaterializedRow(
            scryfall_id="id1",
            quantity=1,
            finish="nonfoil",
            card={
                "name": "Lightning Bolt",
                "set": "lea",
                "collector_number": "161",
                "prices_usd": 1.0,
                "prices_usd_foil": None,
                "rarity": "common",
                "flavor_name": None,
                "type_line": "Instant",
                "border_color": "black",
                "frame_effects": [],
                "promo_types": [],
            },
        ),
        MaterializedRow(
            scryfall_id="id2",
            quantity=2,
            finish="foil",
            card={
                "name": "Sol Ring",
                "set": "cmm",
                "collector_number": "410",
                "prices_usd": 2.0,
                "prices_usd_foil": 5.0,
                "rarity": "uncommon",
                "flavor_name": None,
                "type_line": "Artifact",
                "border_color": "black",
                "frame_effects": [],
                "promo_types": [],
            },
        ),
    ]


def test_moxfield_build_format(tmp_db):
    out = exports.build("moxfield", _rows())
    assert out == "1 Lightning Bolt (LEA) 161\n2 Sol Ring (CMM) 410 *F*\n"


def test_manapool_alias_matches_moxfield_format(tmp_db):
    # manapool consumes moxfield format natively per exports/__init__.py.
    assert exports.build("manapool", _rows()) == exports.build("moxfield", _rows())


def test_tcgplayer_build_format(tmp_db):
    out = exports.build("tcgplayer", _rows())
    assert out == "1 Lightning Bolt [LEA] 161\n2 Sol Ring [CMM] 410\n"


def test_plain_build_format(tmp_db):
    out = exports.build("plain", _rows())
    expected = (
        "qty\tname\tset\tcn\tfinish\tunit_usd\tline_usd\n"
        "1\tLightning Bolt\tLEA\t161\tnonfoil\t1.0\t1.0\n"
        "2\tSol Ring\tCMM\t410\tfoil\t5.0\t10.0\n"
    )
    assert out == expected


def test_archidekt_build_smoke(tmp_db):
    out = exports.build("archidekt", _rows())
    assert isinstance(out, str)
    assert out.strip() != ""
    assert "Lightning Bolt" in out
    assert "Sol Ring" in out


def test_scryfall_json_build_is_valid_json(tmp_db):
    out = exports.build("scryfall_json", _rows())
    parsed = json.loads(out)
    assert parsed
    assert parsed["identifiers"] == [
        {"set": "lea", "collector_number": "161"},
        {"set": "cmm", "collector_number": "410"},
    ]


def test_build_unknown_target_raises(tmp_db):
    import pytest

    with pytest.raises(ValueError):
        exports.build("not-a-real-target", _rows())

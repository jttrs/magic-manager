"""Unit tests for magic_manager.treatments.compute_treatment().

Pure function over plain dicts (raw-Scryfall shape or DB-row shape) — no
fixtures needed. Every expected value below was confirmed by actually
running compute_treatment() before asserting it (see PR/task notes).
"""

from __future__ import annotations

import json

from magic_manager import treatments


def test_plain_card_has_no_treatment():
    card = {
        "promo_types": ["universesbeyond"],
        "frame_effects": [],
        "full_art": False,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card) == ""


def test_showcase_inverted_card_is_b_shw():
    card = {
        "promo_types": ["japanshowcase", "boosterfun"],
        "frame_effects": ["showcase", "legendary", "inverted"],
        "full_art": True,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card) == "b|shw"


def test_showcase_inverted_fracturefoil_card_is_b_shw_ff():
    card = {
        "promo_types": ["fracturefoil", "japanshowcase", "boosterfun"],
        "frame_effects": ["showcase", "legendary", "inverted"],
        "full_art": True,
        "border_color": "white",
    }
    assert treatments.compute_treatment(card) == "b|shw|ff"


def test_full_art_alone_is_fa():
    card = {
        "promo_types": [],
        "frame_effects": [],
        "full_art": True,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card) == "fa"


def test_extended_art_frame_is_ext():
    card = {
        "promo_types": [],
        "frame_effects": ["extendedart"],
        "full_art": False,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card) == "ext"


def test_sourcematerial_promo_type_is_sm():
    card = {
        "promo_types": ["sourcematerial"],
        "frame_effects": [],
        "full_art": False,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card) == "sm"


def test_etched_frame_effect_is_ff():
    card = {
        "promo_types": [],
        "frame_effects": ["etched"],
        "full_art": False,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card) == "ff"


def test_fancy_foil_promo_type_is_ff_when_finish_none():
    card = {
        "promo_types": ["surgefoil"],
        "frame_effects": [],
        "full_art": False,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card, finish=None) == "ff"


def test_fancy_foil_promo_type_suppressed_on_nonfoil_finish():
    card = {
        "promo_types": ["surgefoil"],
        "frame_effects": [],
        "full_art": False,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card, finish="nonfoil") == ""


def test_fancy_foil_promo_type_present_on_foil_finish():
    card = {
        "promo_types": ["surgefoil"],
        "frame_effects": [],
        "full_art": False,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card, finish="foil") == "ff"


def test_full_art_suppressed_when_showcase_also_present():
    card = {
        "promo_types": [],
        "frame_effects": ["showcase"],
        "full_art": True,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card) == "shw"


def test_extended_art_and_sourcematerial_combine():
    card = {
        "promo_types": ["sourcematerial"],
        "frame_effects": ["extendedart"],
        "full_art": False,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card) == "ext|sm"


def test_json_encoded_fields_from_db_row_shape():
    # DB rows store frame_effects/promo_types as JSON-encoded TEXT and
    # full_art as an integer 0/1 rather than a Python bool/list.
    card = {
        "promo_types": json.dumps(["sourcematerial"]),
        "frame_effects": json.dumps([]),
        "full_art": 0,
        "border_color": "black",
    }
    assert treatments.compute_treatment(card) == "sm"

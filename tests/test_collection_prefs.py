"""'What counts' preferences: storage, validation, and each engine hook.

Offline: seeded tmp DB + faked all_sets (family 'tla', a configured family with
an empty dupe-foil set). With no preference stored every result is today's."""
from __future__ import annotations

import json

import pytest

from magic_manager import collection_prefs as cp
from magic_manager import db, missing, sets, undo


@pytest.fixture
def tla(monkeypatch):
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets",
                        lambda: [{"code": "tla", "parent_set_code": None,
                                  "name": "Avatar", "set_type": "expansion"}])


def _own(sid, finish="nonfoil", qty=1):
    with db.connect() as conn:
        conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) "
                     "VALUES (?,?,?,'2025-01-01')", (sid, finish, qty))


def _ids(**kw):
    return {r.scryfall_id for r in missing.missing_printings("tla", **kw)}


# ---------- storage ----------

def test_defaults_without_a_row(tmp_db):
    p = cp.get(fresh=True)
    assert p.changed == frozenset()
    assert p.set_types == sets.DEFAULT_INVENTORY_SET_TYPES
    assert (p.variant_prints, p.datestamped, p.chase_in_lists, p.foil_twins, p.tokens_in_missing) == (
        "hide", "hide", "exclude", "each", "exclude")
    assert p.missing_rarities == frozenset({"rare", "mythic", "uncommon_chase"})
    assert [k for k in (d.key for d in cp.DEFINITIONS)] == [
        "set_types", "variant_prints", "datestamped", "missing_rarities", "chase_in_lists",
        "foil_twins", "tokens_in_missing"]


def test_sub_selectors_default_is_todays_four(tmp_db):
    assert missing.sub_selectors("TLA") == [
        ("rare-regular", "set:tla+related missing rarity=rare treatment=regular"),
        ("mythic-regular", "set:tla+related missing rarity=mythic treatment=regular"),
        ("uncommon-chase", "set:tla+related missing rarity=uncommon treatment=regular chase"),
        ("preferred", "set:tla+related missing treatment=preferred"),
    ]


def test_update_round_trip_and_reset(tmp_db):
    p = cp.update("foil_twins", "once")
    assert p.foil_twins == "once" and p.changed == frozenset({"foil_twins"})
    p = cp.update("missing_rarities", ["common", "rare"])
    assert p.missing_rarities == frozenset({"rare", "common"})
    row = next(d for d in cp.describe() if d["key"] == "missing_rarities")
    assert row["value"] == ["rare", "common"] and row["changed"] and row["default"] == ["rare", "mythic", "uncommon_chase"]
    cp.update("foil_twins", None)
    cp.update("missing_rarities", None)
    assert cp.get(fresh=True).changed == frozenset()
    with db.connect() as conn:  # an empty dict removes the row
        assert conn.execute("SELECT 1 FROM settings WHERE key=?", (cp.SETTING_KEY,)).fetchone() is None


def test_errors(tmp_db):
    with pytest.raises(LookupError):
        cp.update("nope", "x")
    with pytest.raises(ValueError, match="hide, show"):
        cp.update("datestamped", "maybe")
    with pytest.raises(ValueError, match="allowed"):
        cp.update("set_types", ["expansion", "bogus"])
    with pytest.raises(ValueError):
        cp.update("missing_rarities", [])
    assert cp.update("set_types", []).set_types == frozenset()   # anchor always counts


def test_unknown_stored_keys_and_bad_values_are_ignored(tmp_db):
    with db.connect() as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (cp.SETTING_KEY, json.dumps(
            {"zzz": 1, "datestamped": "bogus", "missing_rarities": [], "foil_twins": "once"})))
    p = cp.get(fresh=True)
    assert p.foil_twins == "once" and p.datestamped == "hide"
    assert p.missing_rarities == frozenset({"rare", "mythic", "uncommon_chase"})
    assert p.changed == frozenset({"foil_twins"})


def test_cache_cleared_on_update(tmp_db):
    assert cp.get().foil_twins == "each"       # warm the cache
    cp.update("foil_twins", "once")
    assert cp.get().foil_twins == "once"       # no fresh=True needed


def test_restore_keeps_the_preference(tmp_db, seed_cards, make_card):
    seed_cards([make_card(id="a1", set="tst")])
    cp.update("datestamped", "show")
    undo.take("before")
    cp.update("datestamped", "hide")
    undo.restore()
    assert cp.get(fresh=True).datestamped == "hide"


def test_preference_alone_does_not_make_a_profile_data_holding():
    from magic_manager import userfiles
    assert cp.SETTING_KEY in userfiles._PROFILE_ONLY_SETTINGS


# ---------- hooks ----------

def test_set_types_hook(tmp_db):
    r = sets.ResolvedSet(code="tla", name="x", related=[
        {"code": "tla", "set_type": "expansion"},
        {"code": "ttla", "set_type": "token"},
        {"code": "atla", "set_type": "memorabilia"},
        {"code": "ptla", "set_type": "promo"},
    ])
    assert r.filtered_codes() == ["tla", "ptla"]
    cp.update("set_types", ["memorabilia"])
    assert r.filtered_codes() == ["tla", "atla"]
    assert r.filtered_codes(include_kinds={"token"}) == ["tla", "ttla", "atla"]


def test_set_types_and_variants_in_collection(tmp_db, monkeypatch, seed_cards, make_card):
    import magic_manager.scryfall as scry
    from magic_manager import collection_view as cv
    monkeypatch.setattr(scry, "all_sets", lambda: [
        {"code": "tst", "parent_set_code": None, "name": "T", "set_type": "expansion", "released_at": "2025-02-01"},
        {"code": "atst", "parent_set_code": "tst", "name": "A", "set_type": "memorabilia", "released_at": "2025-01-01"},
    ])
    seed_cards([
        make_card(id="r1", oracle_id="o1", set="tst", collector_number="1", name="One"),
        make_card(id="art", oracle_id="o9", set="atst", collector_number="1", name="Art"),
        make_card(id="pre", oracle_id="o1", set="tst", collector_number="1p", name="One", promo_types=["prerelease"]),
    ])
    ids = lambda: {c.scryfall_id for c in cv.family_cards("tst").cards}  # noqa: E731
    assert ids() == {"r1"}
    cp.update("set_types", ["expansion", "memorabilia"])
    assert ids() == {"r1", "art"}
    cp.update("variant_prints", "show")
    assert ids() == {"r1", "art", "pre"}
    cp.update("set_types", None)
    assert ids() == {"r1", "pre"}


def test_datestamped_hook(tmp_db, tla, seed_cards, make_card):
    seed_cards([
        make_card(id="plain", set="tla", collector_number="5", rarity="rare", name="Card"),
        make_card(id="stamp", set="tla", collector_number="6", rarity="rare", name="Card",
                  promo_types=["datestamped"]),
    ])
    assert _ids() == {"plain"}
    cp.update("datestamped", "show")
    assert _ids() == {"plain", "stamp"}


def test_meld_backs_dropped_whatever_datestamped_says(tmp_db, tla, seed_cards, make_card):
    """Regression: the meld-back drop is not a datestamped rule — showing
    date-stamped copies must never let a meld back face into missing lists."""
    seed_cards([
        make_card(id="front", set="tla", collector_number="99", rarity="rare", name="Front Half"),
        make_card(id="back", set="tla", collector_number="99b", rarity="rare", name="Merged Back"),
    ])
    cp.update("datestamped", "show")
    ids = _ids()
    assert "front" in ids
    assert "back" not in ids, "meld-back face leaked with datestamped=show"


def test_missing_rarities_hook(tmp_db, tla, seed_cards, make_card):
    seed_cards([
        make_card(id="r", set="tla", collector_number="1", rarity="rare", name="R", oracle_id="o1"),
        make_card(id="u", set="tla", collector_number="2", rarity="uncommon", name="U", oracle_id="o2"),
        make_card(id="c", set="tla", collector_number="3", rarity="common", name="C", oracle_id="o3"),
    ])
    assert _ids() == {"r"}
    cp.update("missing_rarities", ["rare", "uncommon", "common"])
    assert _ids() == {"r", "u", "c"}
    subs = [s for s, _ in missing.sub_selectors("tla")]
    assert subs == ["rare-regular", "uncommon-regular", "common-regular", "preferred"]
    cp.update("missing_rarities", ["common"])
    assert _ids() == {"c"}


def test_chase_hook_and_explicit_beats_pref(tmp_db, tla, seed_cards, make_card):
    seed_cards([
        make_card(id="base", set="tla", collector_number="1", rarity="rare", name="Base", oracle_id="o1"),
        make_card(id="hl", set="tla", collector_number="363", rarity="mythic", name="Aang", oracle_id="o2",
                  promo_types=["headliner"], finishes=["foil"]),
    ])
    assert _ids() == {"base"}
    cp.update("chase_in_lists", "include")
    assert _ids() == {"base", "hl"}
    assert _ids(chase="exclude") == {"base"}          # explicit wins
    cp.update("chase_in_lists", "only")
    assert _ids() == {"hl"}
    assert _ids(chase="exclude") == {"base"}


def test_tokens_hook(tmp_db, tla, seed_cards, make_card):
    seed_cards([
        make_card(id="tok", set="tla", collector_number="9", rarity="rare", name="Token", oracle_id="o5",
                  layout="token", type_line="Token Creature — Bird"),
        make_card(id="base", set="tla", collector_number="1", rarity="rare", name="Base", oracle_id="o1"),
    ])
    assert _ids() == {"base"}
    cp.update("tokens_in_missing", "include")
    assert _ids() == {"base", "tok"}


def _twin_cards(make_card):
    return [
        make_card(id="nf", set="tla", collector_number="10", rarity="rare", name="Twin", oracle_id="o1",
                  illustration_id="ill-1", finishes=["nonfoil"]),
        make_card(id="fo", set="tla", collector_number="110", rarity="rare", name="Twin", oracle_id="o1",
                  illustration_id="ill-1", finishes=["foil"]),
        make_card(id="other", set="tla", collector_number="11", rarity="rare", name="Other", oracle_id="o2",
                  illustration_id="ill-2", finishes=["nonfoil", "foil"]),
    ]


def test_foil_twins_unowned_drops_only_the_foil(tmp_db, tla, seed_cards, make_card):
    seed_cards(_twin_cards(make_card))
    assert _ids() == {"nf", "fo", "other"}
    cp.update("foil_twins", "once")
    assert _ids() == {"nf", "other"}


@pytest.mark.parametrize("owned", ["nf", "fo"])
def test_foil_twins_owning_either_drops_both(tmp_db, tla, seed_cards, make_card, owned):
    seed_cards(_twin_cards(make_card))
    _own(owned, "foil" if owned == "fo" else "nonfoil")
    cp.update("foil_twins", "once")
    assert _ids() == {"other"}


def test_cli_prefs_flow(tmp_db):
    from typer.testing import CliRunner
    from magic_manager.cli import app
    run = CliRunner().invoke
    r = run(app, ["prefs", "set", "missing_rarities", "rare", "common"])
    assert r.exit_code == 0, r.output
    r = run(app, ["prefs", "ls", "--json"])
    row = next(d for d in json.loads(r.stdout) if d["key"] == "missing_rarities")
    assert row["value"] == ["rare", "common"] and row["changed"]
    assert "*" in run(app, ["prefs", "ls"]).stdout
    assert run(app, ["prefs", "reset", "missing_rarities"]).exit_code == 0
    assert not cp.get(fresh=True).changed
    for args in (["set", "nope", "x"], ["set", "datestamped", "maybe"], ["set", "datestamped", "show", "hide"],
                 ["reset", "nope"]):
        r = run(app, ["prefs", *args])
        assert r.exit_code == 2 and "error:" in r.output, args

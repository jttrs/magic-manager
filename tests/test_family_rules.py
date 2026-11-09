"""Per-family rule switches ('What counts' → family rules): rule ids, per-user overrides,
the effective-rules gate, the catalog, the CLI.

Offline: a synthetic family 'tla' with one active hard rule, one active chase rule and one
proposed rule. With nothing saved the gate returns the shipped list object itself."""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from magic_manager import collection_prefs as cp
from magic_manager import collection_view, config, db, layout, missing, selectors, undo
from magic_manager.cli import app

HARD = {"promo_types_any_of": frozenset({"stamped"}), "tier": "hard"}
CHASE = {"promo_types_any_of": frozenset({"headliner"}), "tier": "chase"}
PROPOSED = {"frame_effects_all_of": frozenset({"showcase"}), "border_color": "black",
            "note": "why we might hide it"}
HID, CHS, PRO = config.rule_id(HARD), config.rule_id(CHASE), config.rule_id(PROPOSED)


@pytest.fixture
def tla(monkeypatch):
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets",
                        lambda: [{"code": "tla", "parent_set_code": None,
                                  "name": "Avatar", "set_type": "expansion"}])
    monkeypatch.setattr(selectors, "FAMILY_UNOBTAINABLE_RULES", {"tla": [HARD, CHASE]})
    monkeypatch.setattr(selectors, "FAMILY_PROPOSED_RULES", {"tla": [PROPOSED]})


@pytest.fixture
def cards(tla, tmp_db, seed_cards, make_card):
    seed_cards([
        make_card(id="base", set="tla", collector_number="1", rarity="rare", name="Base", oracle_id="o1"),
        make_card(id="st", set="tla", collector_number="2", rarity="rare", name="Stamped", oracle_id="o2",
                  promo_types=["stamped"]),
        make_card(id="hl", set="tla", collector_number="3", rarity="mythic", name="Head", oracle_id="o3",
                  promo_types=["headliner"], finishes=["foil"]),
        make_card(id="sc", set="tla", collector_number="4", rarity="rare", name="Show", oracle_id="o4",
                  frame_effects=["showcase"], border_color="black"),
    ])


def _ids(**kw):
    return {r.scryfall_id for r in missing.missing_printings("tla", **kw)}


def _coll():
    return {c.scryfall_id: c for c in collection_view.family_cards("tla").cards}


def _on():
    cp.update("by_family", "on")


def _own(sid):
    with db.connect() as conn:
        conn.execute("INSERT INTO inventory (scryfall_id,finish,quantity,acquired_at) "
                     "VALUES (?,?,?,'2025-01-01')", (sid, "nonfoil", 1))


# ---------- levels: variant group > kind > family All rules > rule ----------

def test_by_family_off_applies_nothing_but_keeps_the_pins(cards):
    cp.set_family_rule("tla", HID, "count")
    cp.set_family_all("tla", "hide")
    assert selectors._effective_family_rules("tla") is selectors.FAMILY_UNOBTAINABLE_RULES["tla"]
    assert "st" not in _coll()
    assert cp.family_rule_overrides("tla") == {HID: "count", "*": "hide"}
    _on()
    assert "st" in _coll()


def test_precedence_rule_beats_all_rules_beats_shipped(cards):
    _on()
    cp.set_family_all("tla", "count")
    cat = {r["id"]: r for r in selectors.family_rule_catalog("tla")}
    assert [(cat[i]["effective"], cat[i]["source"]) for i in (HID, CHS, PRO)] == [("count", "family")] * 3
    assert "hl" in _coll() and not _coll()["hl"].is_chase
    cp.set_family_rule("tla", CHS, "chase")
    cat = {r["id"]: r for r in selectors.family_rule_catalog("tla")}
    assert (cat[CHS]["effective"], cat[CHS]["source"]) == ("chase", "rule")
    assert _coll()["hl"].is_chase
    cp.set_family_rule("tla", PRO, "hide")
    assert "sc" not in _coll()
    cp.set_family_all("tla", None)
    assert selectors.family_rule_catalog("tla")[0]["source"] == "shipped"


def test_all_rules_hide_takes_a_proposal_out(cards):
    _on()
    cp.set_family_all("tla", "hide")
    assert "sc" not in _coll() and "st" not in _coll()


def test_variant_kinds_override_the_group(cards, monkeypatch):
    # default group hides stamped; the kind override includes it (no family rule hides it here)
    monkeypatch.setattr(selectors, "FAMILY_UNOBTAINABLE_RULES", {"tla": [CHASE]})
    assert "st" not in _coll()
    cp.set_variant_kind("promo_pack", "show")
    assert "st" in _coll()
    cp.set_variant_kind("promo_pack", None)
    assert "st" not in _coll()
    cp.update("variant_prints", "show")
    assert "st" in _coll()
    cp.set_variant_kind("promo_pack", "hide")
    assert "st" not in _coll()


def test_variant_hidden_matches_is_excluded_variant_without_overrides():
    from magic_manager import sets
    prefs = cp.get()
    def card(border=None, promo=None):
        return {"border_color": border, "promo_types": promo}
    cases = [card("white"), card("yellow"), card("black"), card(None, json.dumps(["prerelease"])),
             card(None, ["serialized", "x"]), card(None, json.dumps(["alchemy"])),
             card(None, json.dumps(["boosterfun"])), card()]
    for c in cases:
        assert sets.variant_hidden(c, prefs, {}) == sets.is_excluded_variant(c), c
    show = cp.Prefs(**{**prefs.__dict__, "variant_prints": "show"})
    assert not any(sets.variant_hidden(c, show, {}) for c in cases)
    # an unkinded signal (alchemy) follows the group; a kind override doesn't touch it
    assert sets.variant_hidden(card(None, ["alchemy"]), prefs, {"serialized": "show"})
    assert not sets.variant_hidden(card(None, ["serialized"]), prefs, {"serialized": "show"})
    assert sets.variant_hidden(card(None, ["serialized"]), show, {"serialized": "hide"})
    # an explicit hide on any signal wins; an explicit show beats the group on the card's other kinded signals
    assert sets.variant_hidden(card("white", ["serialized"]), prefs,
                               {"serialized": "show", "white_border": "hide"})
    assert not sets.variant_hidden(card("white", ["serialized"]), prefs, {"serialized": "show"})
    # ...but not on an unkinded one (alchemy), which keeps following the group
    assert sets.variant_hidden(card(None, ["serialized", "alchemy"]), prefs, {"serialized": "show"})


def test_explicit_count_keeps_prints_but_shipped_count_does_not(cards, monkeypatch):
    _on()
    card = {"set": "tla", "promo_types": ["stamped"], "frame_effects": None, "border_color": "black"}
    assert not selectors.family_rule_keeps_print(card, "tla")
    cp.set_family_rule("tla", HID, "count")
    assert selectors.family_rule_keeps_print(card, "tla")
    cp.set_family_rule("tla", HID, "hide")
    assert not selectors.family_rule_keeps_print(card, "tla")
    cp.set_family_rule("tla", HID, None)
    cp.set_family_all("tla", "chase")
    assert selectors.family_rule_keeps_print(card, "tla")
    cp.update("by_family", "off")
    assert not selectors.family_rule_keeps_print(card, "tla")


def test_also_hidden_counts_shipped_count_prints_the_variants_hide(cards, monkeypatch):
    stamped_proposal = {"promo_types_any_of": frozenset({"stamped"}), "note": "n"}
    monkeypatch.setattr(selectors, "FAMILY_UNOBTAINABLE_RULES", {"tla": [CHASE]})
    monkeypatch.setattr(selectors, "FAMILY_PROPOSED_RULES", {"tla": [stamped_proposal]})
    rid = config.rule_id(stamped_proposal)
    row = {r["id"]: r for r in selectors.family_rule_catalog("tla")}[rid]
    assert (row["prints"], row["also_hidden"]) == (1, 1)
    cp.set_variant_kind("promo_pack", "show")
    assert {r["id"]: r for r in selectors.family_rule_catalog("tla")}[rid]["also_hidden"] == 0
    cp.set_variant_kind("promo_pack", None)
    _on()
    cp.set_family_rule("tla", rid, "count")   # explicit Count brings them back: nothing "also hidden"
    assert {r["id"]: r for r in selectors.family_rule_catalog("tla")}[rid]["also_hidden"] == 0


def test_kind_catalog_and_errors(tmp_db):
    kinds = selectors.variant_kind_catalog()
    assert [k["key"] for k in kinds] == ["white_border", "yellow_border", "prerelease", "promo_pack",
                                         "japan_showcase", "serialized"]
    assert all(k["state"] is None and k["effective"] == "hide" for k in kinds)
    cp.update("variant_prints", "show")
    assert all(k["effective"] == "show" for k in selectors.variant_kind_catalog())
    with pytest.raises(LookupError):
        cp.set_variant_kind("nope", "hide")
    with pytest.raises(ValueError):
        cp.set_variant_kind("serialized", "maybe")
    with pytest.raises(LookupError):
        cp.set_family_all("nope", "hide")


def test_master_list_follows_kind_overrides(cards, tmp_path):
    from magic_manager import sets
    def n(**kw):
        return sets.write_master_list_md(["tla"], tmp_path / "m.md", **kw)[0]
    assert n(include_variants=None) == 3        # stamped hidden at default prefs
    assert n(include_variants=True) == 4
    cp.set_variant_kind("promo_pack", "show")
    assert n(include_variants=None) == 4
    assert n(include_variants=False) == 3       # the explicit flag keeps the old rule


# ---------- ids ----------

def test_rule_id_unique_per_family_and_stable_across_forms():
    for fam, rules in {**selectors.FAMILY_UNOBTAINABLE_RULES}.items():
        ids = [config.rule_id(r) for r in rules]
        assert len(ids) == len(set(ids)), fam
    for fam, rules in selectors.FAMILY_PROPOSED_RULES.items():
        ids = [config.rule_id(r) for r in rules]
        assert len(ids) == len(set(ids)), fam
        assert not set(ids) & {config.rule_id(r) for r in selectors.FAMILY_UNOBTAINABLE_RULES.get(fam, [])}


def test_rule_id_ignores_note_tier_enabled_and_form_but_not_predicates():
    base = config.rule_id(HARD)
    assert config.rule_id({**HARD, "tier": "chase", "note": "x"}) == base
    assert config.rule_id({"promo_types_any_of": ["Stamped"], "enabled": False, "note": "n"}) == base
    assert config.rule_id({**HARD, "border_color": "black"}) != base
    assert config.rule_id({"collector_numbers": ["2", "1"]}) == config.rule_id({"collector_numbers": ["1", "2"]})


def test_every_shipped_rule_id_matches_raw_toml_form():
    raw = config.load_toml("families.toml", required=True)["unobtainable"]
    evaluated = {**config.family_unobtainable_rules()}
    for fam, rules in config.family_proposed_rules().items():
        evaluated.setdefault(fam, [])
    for fam, body in raw.items():
        rid_raw = sorted(config.rule_id(r) for r in body.get("rules") or [])
        rid_eval = sorted(config.rule_id(r) for r in
                          config.family_unobtainable_rules().get(fam.lower(), [])
                          + config.family_proposed_rules().get(fam.lower(), []))
        assert rid_raw == rid_eval, fam


# ---------- invariance ----------

def test_no_override_returns_the_shipped_list_object(tla, tmp_db):
    assert selectors._effective_family_rules("tla") is selectors.FAMILY_UNOBTAINABLE_RULES["tla"]
    assert selectors._effective_family_rules("nope") is None


def test_shipped_default_path_is_the_very_object_for_real_families(tmp_db):
    for fam in ("fin", "ltr", "tla"):
        assert selectors._effective_family_rules(fam) is selectors.FAMILY_UNOBTAINABLE_RULES.get(fam)


def test_proposals_never_match_without_an_override(cards):
    card = {"set": "tla", "frame_effects": json.dumps(["showcase"]), "border_color": "black"}
    assert not selectors._is_family_unobtainable(card, "tla")
    assert "sc" in _coll()


# ---------- states ----------

def test_hide_a_proposed_rule_removes_from_collection_and_missing_but_owned_stays(cards):
    _on()
    assert "sc" in _coll()
    cp.set_family_rule("tla", PRO, "hide")
    assert "sc" not in _coll() and "sc" not in _ids()
    _own("sc")
    assert "sc" in _coll()
    cp.set_family_rule("tla", PRO, None)
    assert selectors._effective_family_rules("tla") is selectors.FAMILY_UNOBTAINABLE_RULES["tla"]


def test_chase_a_proposed_rule_tags_chase_and_follows_chase_in_lists(cards):
    _on()
    assert not _coll()["sc"].is_chase
    cp.set_family_rule("tla", PRO, "chase")
    assert _coll()["sc"].is_chase
    assert "sc" not in _ids()
    cp.update("chase_in_lists", "include")
    assert "sc" in _ids()


def test_count_an_active_hard_rule_surfaces_the_print(cards):
    _on()
    assert "st" not in _coll()
    cp.set_family_rule("tla", HID, "count")
    assert "st" in _coll() and not _coll()["st"].is_chase
    assert "hl" in _coll() and _coll()["hl"].is_chase   # the other active rule is untouched


def test_hide_flips_an_active_chase_rule_and_chase_flips_a_hard_one(cards):
    _on()
    cp.set_family_rule("tla", CHS, "hide")
    assert "hl" not in _coll()
    cp.set_family_rule("tla", HID, "chase")
    assert _coll()["st"].is_chase


def test_any_explicit_state_is_stored_even_the_shipped_one(cards):
    assert cp.set_family_rule("tla", HID, "hide") == {HID: "hide"}
    assert cp.set_family_rule("tla", PRO, "count") == {HID: "hide", PRO: "count"}
    assert cp.set_family_rule("tla", HID, None) == {PRO: "count"}
    assert cp.set_family_rule("tla", PRO, None) == {}
    with db.connect() as conn:
        assert conn.execute("SELECT 1 FROM settings WHERE key=?", (cp.FAMILY_RULES_KEY,)).fetchone() is None


def test_stale_override_is_ignored_and_bad_json_reads_empty(cards):
    with db.connect() as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)",
                     (cp.FAMILY_RULES_KEY, json.dumps({"tla": {"deadbeef00": "hide", PRO: "bogus"}, "x": 5})))
    cp.clear_cache()
    assert cp.family_rule_overrides("tla") == {"deadbeef00": "hide"}
    assert "sc" in _coll() and "st" not in _coll()
    assert selectors.family_rule_families()[0]["changed"] == 0
    with db.connect() as conn:
        conn.execute("UPDATE settings SET value='{not json' WHERE key=?", (cp.FAMILY_RULES_KEY,))
    cp.clear_cache()
    assert cp.family_rule_overrides("tla") == {}


def test_errors(cards):
    with pytest.raises(ValueError):
        cp.set_family_rule("tla", PRO, "maybe")
    with pytest.raises(LookupError):
        cp.set_family_rule("nope", PRO, "hide")
    with pytest.raises(LookupError):
        cp.set_family_rule("tla", "deadbeef00", "hide")
    with pytest.raises(LookupError):
        selectors.family_rule_catalog("nope")


def test_cache_cleared_on_update(cards):
    _on()
    cp.set_family_rule("tla", PRO, "hide")
    first = selectors._effective_family_rules("tla")
    assert any(r.get("border_color") == "black" and r["tier"] == "hard" and "note" not in r for r in first)
    cp.set_family_rule("tla", PRO, "chase")
    assert selectors._effective_family_rules("tla") != first
    assert selectors._effective_family_rules("tla")[-1]["tier"] == "chase"


def test_restore_keeps_the_overrides(cards):
    undo.take("before")
    cp.set_family_rule("tla", PRO, "hide")
    undo.restore()
    assert cp.family_rule_overrides("tla") == {PRO: "hide"}


def test_profile_only_and_undo_keep_keys():
    from magic_manager import userfiles
    assert cp.VARIANT_KINDS_KEY in userfiles._PROFILE_ONLY_SETTINGS
    assert cp.VARIANT_KINDS_KEY in undo.KEEP_SETTINGS
    assert cp.FAMILY_RULES_KEY in userfiles._PROFILE_ONLY_SETTINGS
    assert cp.FAMILY_RULES_KEY in undo.KEEP_SETTINGS


# ---------- catalog ----------

def test_describe_rule():
    d = selectors.describe_rule
    assert d({"promo_types_any_of": frozenset({"b", "a"})}) == "Promo type: a or b"
    assert d({"promo_types_all_of": frozenset({"b", "a"})}) == "Promo types: a + b"
    assert d({"frame_effects_all_of": frozenset({"showcase"}), "border_color": "black"}) == "Frame: showcase · Border: black"
    assert d({"set_codes": frozenset({"pala"}), "collector_numbers": frozenset(str(i) for i in range(1, 9))}) \
        == "Set: pala · CN: 1, 2, 3, 4, 5, 6 +2 more"


def test_catalog_counts_defaults_and_state(cards):
    _on()
    _own("st")
    cat = {r["id"]: r for r in selectors.family_rule_catalog("tla")}
    assert list(cat) == [HID, CHS, PRO]
    assert (cat[HID]["default"], cat[CHS]["default"], cat[PRO]["default"]) == ("hide", "chase", "count")
    assert (cat[HID]["prints"], cat[HID]["owned"]) == (1, 1)
    assert (cat[PRO]["prints"], cat[PRO]["owned"]) == (1, 0)
    assert cat[PRO]["note"] == "why we might hide it"   # shipped notes come from the raw TOML; this synthetic rule carries its own
    assert not any(r["changed"] for r in cat.values())
    cp.set_family_rule("tla", PRO, "hide")
    cat = {r["id"]: r for r in selectors.family_rule_catalog("tla")}
    assert cat[PRO]["state"] == "hide" and cat[PRO]["changed"] and cat[HID]["state"] is None
    assert (cat[HID]["effective"], cat[HID]["source"]) == ("hide", "shipped")


def test_catalog_prints_null_when_family_not_local(tla, tmp_db):
    assert all(r["prints"] is None and r["owned"] is None for r in selectors.family_rule_catalog("tla"))


def test_families_list_changed_first_and_named(cards, monkeypatch):
    monkeypatch.setattr(selectors, "FAMILY_PROPOSED_RULES", {"tla": [PROPOSED], "zzz": [HARD]})
    monkeypatch.setattr(selectors, "FAMILY_UNOBTAINABLE_RULES", {"tla": [HARD, CHASE], "aaa": [HARD]})
    import magic_manager.sets as sets_mod
    monkeypatch.setattr(sets_mod, "paper_families", lambda: [{"value": "tla", "label": "Avatar", "year": "2025"}])
    fams = selectors.family_rule_families()
    assert [f["code"] for f in fams] == ["aaa", "tla", "zzz"]
    assert fams[1] == {"code": "tla", "name": "Avatar", "rules": 3, "changed": 0}
    assert fams[0]["name"] == "AAA"
    cp.set_family_rule("tla", PRO, "hide")
    fams = selectors.family_rule_families()
    assert fams[0]["code"] == "tla" and fams[0]["changed"] == 1


def test_real_catalog_loads_for_every_family(tmp_db, monkeypatch):
    import magic_manager.scryfall as scry
    monkeypatch.setattr(scry, "all_sets", lambda: [])
    fams = selectors.family_rule_families()
    assert sum(f["rules"] for f in fams) >= 175
    for f in fams:
        assert len(selectors.family_rule_catalog(f["code"])) == f["rules"]


# ---------- per-user isolation ----------

def test_split_layout_overrides_are_per_user(tla, tmp_db, seed_cards, make_card, split_dir):
    from magic_manager import userfiles
    ub = "bbbbbbbbbbbbbbbb"
    userfiles.create(split_dir, ub)
    _on()
    cp.set_family_rule("tla", PRO, "hide")
    assert cp.family_rule_overrides("tla") == {PRO: "hide"}
    with layout.as_user(ub):
        assert cp.family_rule_overrides("tla") == {}
        assert selectors._effective_family_rules("tla") is selectors.FAMILY_UNOBTAINABLE_RULES["tla"]
    assert selectors._effective_family_rules("tla") is not selectors.FAMILY_UNOBTAINABLE_RULES["tla"]


def test_no_user_bound_falls_back_to_shipped(tla, tmp_db, monkeypatch):
    def boom():
        raise layout.NoUserBound("x")
    monkeypatch.setattr(db, "user_scope", boom)
    assert selectors._effective_family_rules("tla") is selectors.FAMILY_UNOBTAINABLE_RULES["tla"]
    assert cp.family_rule_overrides("tla") == {}


# ---------- CLI ----------

def test_cli_flow(cards):
    r = CliRunner()
    out = r.invoke(app, ["prefs", "rules", "tla"])
    assert out.exit_code == 0 and HID in out.output and PRO in out.output
    js = json.loads(r.invoke(app, ["prefs", "rules", "tla", "--json"]).output)
    assert [x["id"] for x in js["rules"]] == [HID, CHS, PRO] and js["all_rules"] is None
    assert r.invoke(app, ["prefs", "rule", "tla", PRO, "hide"]).exit_code == 0
    assert "hide *" in r.invoke(app, ["prefs", "rules", "tla"]).output
    assert r.invoke(app, ["prefs", "rule-reset", "tla", PRO]).exit_code == 0
    assert "hide *" not in r.invoke(app, ["prefs", "rules", "tla"]).output
    assert r.invoke(app, ["prefs", "rule", "tla", PRO, "chase"]).exit_code == 0
    assert r.invoke(app, ["prefs", "rule", "tla", PRO, "group"]).exit_code == 0
    assert cp.family_rule_overrides("tla") == {}
    assert r.invoke(app, ["prefs", "family-all", "tla", "count"]).exit_code == 0
    assert cp.family_rule_overrides("tla") == {"*": "count"}
    assert r.invoke(app, ["prefs", "family-all", "tla", "shipped"]).exit_code == 0
    assert cp.family_rule_overrides("tla") == {}
    assert r.invoke(app, ["prefs", "kind", "serialized", "show"]).exit_code == 0
    assert cp.variant_kind_overrides() == {"serialized": "show"}
    assert "serialized" in r.invoke(app, ["prefs", "kinds"]).output
    ks = json.loads(r.invoke(app, ["prefs", "kinds", "--json"]).output)
    assert {k["key"]: k["state"] for k in ks}["serialized"] == "show"
    assert r.invoke(app, ["prefs", "kind", "serialized", "group"]).exit_code == 0
    assert cp.variant_kind_overrides() == {}
    for argv in (["kind", "nope", "hide"], ["kind", "serialized", "maybe"], ["family-all", "nope", "hide"],
                 ["family-all", "tla", "maybe"]):
        assert r.invoke(app, ["prefs", *argv]).exit_code == 2, argv
    for argv in (["rule", "tla", PRO, "maybe"], ["rule", "nope", PRO, "hide"], ["rule", "tla", "deadbeef00", "hide"],
                 ["rule-reset", "nope", PRO], ["rules", "nope"]):
        res = r.invoke(app, ["prefs", *argv])
        assert res.exit_code == 2, argv
        assert "error:" in res.output


def test_serialized_unowned_print_reaches_the_variant_gate(cards, seed_cards, make_card):
    seed_cards([
        make_card(id="ser", set="tla", collector_number="10", rarity="mythic", name="Ser", oracle_id="o10",
                  promo_types=["serialized"]),
        make_card(id="reb", set="tla", collector_number="11", rarity="rare", name="Reb", oracle_id="o11",
                  promo_types=["rebalanced"]),
        make_card(id="ser_reb", set="tla", collector_number="12", rarity="rare", name="SerReb", oracle_id="o12",
                  promo_types=["serialized", "alchemy"]),
    ])
    assert not {"ser", "reb", "ser_reb"} & set(_coll())
    cp.set_variant_kind("serialized", "show")
    assert {"ser"} <= set(_coll()) and not {"reb", "ser_reb"} & set(_coll())
    cp.set_variant_kind("serialized", None)
    assert "ser" not in _coll()
    # an explicit Count on a matching rule, with by_family on
    rule = {"promo_types_any_of": frozenset({"serialized"}), "tier": "hard"}
    selectors.FAMILY_UNOBTAINABLE_RULES["tla"] = [HARD, CHASE, rule]
    _on()
    cp.set_family_rule("tla", config.rule_id(rule), "count")
    assert "ser" in _coll() and not {"reb", "ser_reb"} & set(_coll())


def test_register_set_target_none_follows_variant_group(tmp_db):
    from magic_manager import sets
    def stored():
        with db.connect() as conn:
            return conn.execute("SELECT include_variants FROM set_targets WHERE anchor_code='tla'").fetchone()[0]
    sets.register_set_target("tla", ["tla"], include_variants=None)
    assert stored() == 0
    cp.update("variant_prints", "show")
    sets.register_set_target("tla", ["tla"], include_variants=None)
    assert stored() == 1
    sets.register_set_target("tla", ["tla"], include_variants=False)
    assert stored() == 0
    sets.register_set_target("tla", ["tla"], include_variants=True)
    assert stored() == 1


def test_cli_rule_notes_when_by_family_is_off(cards):
    r = CliRunner().invoke(app, ["prefs", "rule", "tla", HID, "count"])
    assert r.exit_code == 0 and "not applied: mm prefs set by_family on" in r.output
    r = CliRunner().invoke(app, ["prefs", "family-all", "tla", "hide"])
    assert r.exit_code == 0 and "not applied" in r.output
    _on()
    r = CliRunner().invoke(app, ["prefs", "family-all", "tla", "hide"])
    assert r.exit_code == 0 and "not applied" not in r.output

"""Config schema + config↔docs sync validator (Phase 5c).

Models the exit-code/severity shape of scripts/audit_treatment_coverage.py but as
pytest. Guards the externalized config/families.toml so a hand-edit can't:
  - introduce an unknown predicate key (a typo like `promo_type_any_of`);
  - reference a family with no docs/sets/<anchor>.md (or vice versa) — the
    config↔docs §8 sync check that keeps rationale and rule aligned;
  - drift the loaded structure from what the selector matcher expects.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from magic_manager import config

ROOT = Path(__file__).resolve().parent.parent
FAMILIES_TOML = ROOT / "config" / "families.toml"
DOCS_SETS = ROOT / "docs" / "sets"

# The predicate-key vocabulary is the SINGLE source of truth in config — the
# loader derives its coercion from it and the matcher references the same keys,
# so this test can't drift from either (F6). Anything else in a rule table is a
# typo / unsupported.
_KNOWN_RULE_KEYS = set(config.UNOBTAINABLE_RULE_KEYS)

# Families intentionally in config without a docs/sets doc, or vice versa.
# (Keep empty; add with a reason if a legitimate exception arises.)
_CONFIG_ONLY_OK: set[str] = set()
_DOCS_ONLY_OK: set[str] = {"_template"}  # docs/sets/_TEMPLATE.md is not a family


@pytest.fixture(scope="module")
def raw():
    with open(FAMILIES_TOML, "rb") as f:
        return tomllib.load(f)


def test_unobtainable_rules_use_only_known_keys(raw):
    bad = []
    for fam, body in (raw.get("unobtainable") or {}).items():
        for i, rule in enumerate(body.get("rules", [])):
            unknown = set(rule) - _KNOWN_RULE_KEYS
            if unknown:
                bad.append(f"{fam}[{i}]: unknown key(s) {sorted(unknown)}")
    assert not bad, "unknown predicate keys in config/families.toml:\n" + "\n".join(bad)


def test_every_unobtainable_rule_has_a_predicate(raw):
    """A rule with only `note` and no predicate would match nothing (or, worse,
    everything if the matcher changed) — every rule must constrain something."""
    predicate_keys = _KNOWN_RULE_KEYS - {"note"}
    empty = []
    for fam, body in (raw.get("unobtainable") or {}).items():
        for i, rule in enumerate(body.get("rules", [])):
            if not (set(rule) & predicate_keys):
                empty.append(f"{fam}[{i}]")
    assert not empty, f"unobtainable rules with no predicate: {empty}"


def test_loader_coerces_every_set_kind_key_to_frozenset(raw):
    """build_unobtainable_rules must coerce EVERY set-kind key (per the shared
    config.UNOBTAINABLE_RULE_KEYS vocabulary) to a frozenset and strip `note`.

    Derived from the shared vocabulary — NOT a hardcoded key list — so adding a
    new set-valued predicate key to UNOBTAINABLE_RULE_KEYS without wiring its
    coercion fails HERE instead of silently storing a raw list that crashes the
    matcher's `.issubset`/`&` at query time (the F6 silent-crash gap)."""
    set_kinds = {"promo_set", "cn_set"}
    set_keys = {k for k, kind in config.UNOBTAINABLE_RULE_KEYS.items() if kind in set_kinds}
    rules = config.build_unobtainable_rules(raw)
    for fam, rlist in rules.items():
        for r in rlist:
            assert "note" not in r, f"{fam}: note leaked into evaluated rule"
            for k in set_keys:
                if k in r:
                    assert isinstance(r[k], frozenset), \
                        f"{fam}.{k} is a set-kind key but was not coerced to frozenset"


def test_dupe_foil_values_are_lists_of_strings(raw):
    for fam, vals in (raw.get("dupe_foil") or {}).items():
        assert isinstance(vals, list), f"dupe_foil.{fam} must be a list"
        assert all(isinstance(v, str) for v in vals), f"dupe_foil.{fam} non-string entry"


def test_scenes_have_required_fields(raw):
    for fam, scenes in (raw.get("scenes") or {}).items():
        for i, sc in enumerate(scenes):
            missing = {"name", "artist", "set", "cn_lo", "cn_hi"} - set(sc)
            assert not missing, f"scenes.{fam}[{i}] missing {missing}"
            assert sc["cn_lo"] <= sc["cn_hi"], f"scenes.{fam}[{i}] cn_lo > cn_hi"


def _docs_family_anchors() -> set[str]:
    return {p.stem.lower() for p in DOCS_SETS.glob("*.md")
            if p.stem.lower() not in _DOCS_ONLY_OK}


def _docs_referencing_family_config() -> set[str]:
    """Anchors whose doc references a FAMILY_* config key — i.e. docs that claim
    a family has config. These MUST have a matching config entry (and vice
    versa) so §8 'Code refs' and config don't drift."""
    pat = re.compile(r'FAMILY_(?:DUPE_FOIL_PROMO_TYPES|UNOBTAINABLE_RULES|SCENES)'
                     r'\["([a-z0-9]+)"\]')
    out: set[str] = set()
    for p in DOCS_SETS.glob("*.md"):
        for m in pat.finditer(p.read_text(encoding="utf-8")):
            out.add(m.group(1).lower())
    return out


def test_config_families_have_docs(raw):
    """Every family configured in families.toml has a docs/sets/<anchor>.md."""
    configured = (set(raw.get("dupe_foil") or {})
                  | set(raw.get("unobtainable") or {})
                  | set(raw.get("scenes") or {}))
    docs = _docs_family_anchors()
    orphan = {f for f in configured if f not in docs} - _CONFIG_ONLY_OK
    assert not orphan, (
        f"families in config/families.toml with no docs/sets/<anchor>.md: "
        f"{sorted(orphan)} — add the doc or an exception.")


def test_docs_config_refs_have_config(raw):
    """Every family a doc's §8 claims has FAMILY_* config actually exists in
    config/families.toml — the drift guard in the other direction."""
    configured = (set(raw.get("dupe_foil") or {})
                  | set(raw.get("unobtainable") or {})
                  | set(raw.get("scenes") or {}))
    referenced = _docs_referencing_family_config()
    missing = {f for f in referenced if f not in configured} - _CONFIG_ONLY_OK
    assert not missing, (
        f"docs/sets §8 reference FAMILY_* config for families absent from "
        f"config/families.toml: {sorted(missing)} — the doc and config drifted.")


# ---------- promo_types.toml ↔ baked-in default sync (F7) ----------
#
# The flat promo-type constants ship a baked-in Python default AND a committed
# config/promo_types.toml value; the file is OPTIONAL, so the two must agree or
# behavior silently depends on whether the file is present. These guards (the
# un-guarded sibling of the families.toml checks above) fail if either drifts.

PROMO_TYPES_TOML = ROOT / "config" / "promo_types.toml"

# (toml_key, the module constant that carries the baked-in default). Each
# constant is the frozenset the code binds; the committed TOML list must equal it.
_PROMO_SYNC_CASES = [
    ("excluded", "magic_manager.sets", "EXCLUDED_PROMO_TYPES"),
    ("unobtainable", "magic_manager.selectors", "UNOBTAINABLE_PROMO_TYPES"),
    ("digital_only", "magic_manager.selectors", "DIGITAL_ONLY_PROMO_TYPES"),
    ("fancy_foil", "magic_manager.treatments", "FANCY_FOIL_PROMO_TYPES"),
]


@pytest.mark.parametrize("key,module,attr", _PROMO_SYNC_CASES)
def test_promo_types_toml_matches_baked_in_default(key, module, attr):
    """The committed config/promo_types.toml value equals the module constant it
    backs — so an edit to one without the other can't silently diverge."""
    import importlib
    const = getattr(importlib.import_module(module), attr)
    with open(PROMO_TYPES_TOML, "rb") as f:
        toml_val = frozenset(str(v).lower() for v in tomllib.load(f).get(key, []))
    assert toml_val == const, (
        f"config/promo_types.toml [{key}] ({sorted(toml_val)}) diverged from "
        f"{module}.{attr} ({sorted(const)}) — update both or neither.")


# ---------- families.toml is REQUIRED, not optional (F1) ----------

def test_missing_families_toml_raises_not_silently_empty(tmp_path):
    """A config dir without families.toml makes the family loaders RAISE
    ConfigError (fatal) rather than silently returning {} and disabling
    missing-set for every family."""
    for loader in (config.family_dupe_foil, config.family_unobtainable_rules,
                   config.family_scenes):
        with pytest.raises(config.ConfigError):
            loader(override=tmp_path)


def test_unparseable_families_toml_raises(tmp_path):
    """A corrupt (unparseable) families.toml is fatal for the family loaders,
    not a silent warn-and-empty."""
    (tmp_path / "families.toml").write_text("this is = = not valid toml [[[")
    with pytest.raises(config.ConfigError):
        config.family_dupe_foil(override=tmp_path)


# ---------- override / config dir is honored (F2) ----------

def test_override_dir_yields_distinct_result(tmp_path):
    """Passing a different config dir reads THAT dir's families.toml (the parse
    cache keys on the resolved dir, so override isn't a stale-cache no-op)."""
    (tmp_path / "families.toml").write_text(
        '[[scenes.zzztest]]\n'
        'name = "T"\nartist = "N"\nset = "zzztest"\ncn_lo = 1\ncn_hi = 2\n')
    alt = config.family_scenes(override=tmp_path)
    assert set(alt) == {"zzztest"}
    # the real repo config is unaffected (distinct cache entry, not clobbered)
    assert "zzztest" not in config.family_scenes()

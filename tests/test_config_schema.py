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

# The predicate keys selectors._matches_unobtainable_rule understands, plus the
# rationale field. Anything else in a rule table is a typo / unsupported.
_KNOWN_RULE_KEYS = {
    "promo_types_any_of", "promo_types_all_of", "frame_effects_all_of",
    "collector_numbers", "border_color", "note",
}

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


def test_loader_reproduces_frozenset_shape(raw):
    """build_unobtainable_rules coerces the set-valued keys to frozensets and
    strips `note`, matching what the matcher consumes."""
    rules = config.build_unobtainable_rules(raw)
    for fam, rlist in rules.items():
        for r in rlist:
            assert "note" not in r, f"{fam}: note leaked into evaluated rule"
            for k in ("promo_types_any_of", "promo_types_all_of", "frame_effects_all_of"):
                if k in r:
                    assert isinstance(r[k], frozenset), f"{fam}.{k} not a frozenset"
            if "collector_numbers" in r:
                assert isinstance(r["collector_numbers"], frozenset)


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

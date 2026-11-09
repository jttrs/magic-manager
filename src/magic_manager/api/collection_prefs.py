"""'What counts' preferences API: adapters over :mod:`magic_manager.collection_prefs`."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .. import collection_prefs, selectors


class ChoiceOut(BaseModel):
    value: str
    label: str


class PrefOut(BaseModel):
    key: str
    title: str
    about: str
    kind: Literal["choice", "multi"]
    choices: list[ChoiceOut]
    value: str | list[str]
    default: str | list[str]
    changed: bool


class PrefsOut(BaseModel):
    prefs: list[PrefOut]


class PrefIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str | list[str] | None = None  # null resets the preference


def listing() -> PrefsOut:
    return PrefsOut(prefs=[PrefOut(**d) for d in collection_prefs.describe()])


def set_pref(key: str, req: PrefIn) -> PrefsOut:
    """Raises ``ValueError`` (bad value) / ``LookupError`` (unknown key); returns the full listing."""
    collection_prefs.update(key, req.value)
    return listing()


RuleState = Literal["count", "chase", "hide"]


class FamilyRuleOut(BaseModel):
    id: str
    description: str
    note: str | None
    default: RuleState
    state: RuleState
    changed: bool
    prints: int | None  # null when the family isn't synced locally
    owned: int | None


class FamilyRulesOut(BaseModel):
    code: str
    rules: list[FamilyRuleOut]


class RuleFamilyOut(BaseModel):
    code: str
    name: str
    rules: int
    changed: int


class RuleFamiliesOut(BaseModel):
    families: list[RuleFamilyOut]


class FamilyRuleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: RuleState | None = None  # null resets the rule to its shipped state


def rule_families() -> RuleFamiliesOut:
    return RuleFamiliesOut(families=[RuleFamilyOut(**f) for f in selectors.family_rule_families()])


def family_rules(anchor: str) -> FamilyRulesOut:
    """Raises ``LookupError`` for a family with no rules."""
    return FamilyRulesOut(code=anchor.lower(),
                          rules=[FamilyRuleOut(**r) for r in selectors.family_rule_catalog(anchor)])


def set_family_rule(anchor: str, rule_id: str, req: FamilyRuleIn) -> FamilyRulesOut:
    """Raises ``ValueError`` (bad state) / ``LookupError`` (unknown family or rule)."""
    collection_prefs.set_family_rule(anchor, rule_id, req.state)
    return family_rules(anchor)

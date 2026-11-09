"""'What counts' preferences: which sets, prints and rarities count toward a
collection family (Collection, checklists, missing lists).

Stored as one JSON object under the user's ``settings`` key ``collection.prefs``
(a user table, so per user in the hosted layout). Only the keys the user changed
are stored; a missing key, an unknown key or an invalid value reads as the
default, and every default equals the behaviour before this module existed.
Kept out of undo (like consent) so pressing Undo never reverts a preference.

Engines read :func:`get` at call time (never at import).
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Literal

from . import db
from . import layout as _layout

SETTING_KEY = "collection.prefs"
# Per-family rule switches: {anchor: {rule_id | "*": "count"|"chase"|"hide"}}; "*" is
# the family's "All rules" state. Any explicit state is stored, even the shipped one.
FAMILY_RULES_KEY = "collection.family_rules"
RULE_STATES = ("count", "chase", "hide")
ALL_RULES = "*"
# Per-kind variant overrides: {kind: "hide"|"show"} (absent = follow the group).
VARIANT_KINDS_KEY = "collection.variant_kinds"
KIND_STATES = ("hide", "show")
CACHE_SECONDS = 30.0

_cache: dict[str, tuple[float, "Prefs"]] = {}
_NO_RULES: dict[str, str] = {}
_rules_cache: dict[str, tuple[float, dict[str, dict[str, str]]]] = {}
_kinds_cache: dict[str, tuple[float, dict[str, str]]] = {}
_lock = threading.Lock()


@dataclass(frozen=True)
class PrefDef:
    key: str
    title: str
    about: str  # one plain sentence for the UI
    kind: Literal["choice", "multi"]
    choices: tuple[tuple[str, str], ...]  # (value, label)
    default: str | tuple[str, ...]  # tuple for multi, in choices order


_SET_TYPE_CHOICES: tuple[tuple[str, str], ...] = (
    ("expansion", "Expansion"),
    ("commander", "Commander"),
    ("masterpiece", "Masterpiece"),
    ("promo", "Promo"),
    ("eternal", "Eternal"),
    ("box", "Box set"),
    ("starter", "Starter"),
    ("funny", "Un-set (funny)"),
    ("masters", "Masters"),
    ("draft_innovation", "Draft innovation"),
    ("duel_deck", "Duel deck"),
    ("from_the_vault", "From the Vault"),
    ("spellbook", "Spellbook"),
    ("premium_deck", "Premium deck"),
    ("arsenal", "Arsenal"),
    ("memorabilia", "Memorabilia"),
)


def _default_set_types() -> tuple[str, ...]:
    from . import sets  # lazy: sets reads this module too
    return tuple(v for v, _ in _SET_TYPE_CHOICES if v in sets.DEFAULT_INVENTORY_SET_TYPES)


_HIDE_SHOW = (("hide", "Leave out"), ("show", "Include"))

DEFINITIONS: tuple[PrefDef, ...] = (
    PrefDef(
        "set_types", "Set types in a family",
        "Which kinds of related sets count as part of a family in Collection and on checklists. "
        "The family's own set always counts.",
        "multi", _SET_TYPE_CHOICES, _default_set_types(),
    ),
    PrefDef(
        "variant_prints", "Variant prints",
        "White- and yellow-bordered prints and stamped variants (prerelease, store, serialized) "
        "in Collection and on checklists.",
        "choice", _HIDE_SHOW, "hide",
    ),
    PrefDef(
        "by_family", "Customize by family",
        "Also set what each family's rules do. Off uses the shipped rules.",
        "choice", (("off", "Print kinds only"), ("on", "Also by family")), "off",
    ),
    PrefDef(
        "datestamped", "Date-stamped copies",
        "A date-stamped prerelease print that has the same art as a plain copy in the family.",
        "choice", _HIDE_SHOW, "hide",
    ),
    PrefDef(
        "missing_rarities", "Missing lists include",
        "Which plain-frame printings count as missing. Alternate-art printings are listed "
        "whatever their rarity.",
        "multi",
        (("rare", "Rares"), ("mythic", "Mythics"), ("uncommon_chase", "Chase uncommons"),
         ("uncommon", "All uncommons"), ("common", "Commons"), ("special", "Special")),
        ("rare", "mythic", "uncommon_chase"),
    ),
    PrefDef(
        "chase_in_lists", "Chase prints in missing lists",
        "Premium prints a family marks as chase.",
        "choice", (("exclude", "Leave out"), ("include", "Include"), ("only", "Only chase")), "exclude",
    ),
    PrefDef(
        "foil_twins", "Same-art foil twins",
        "When a set lists the foil of a card as its own printing with the same art (older core "
        "sets), count owning either finish as having it.",
        "choice", (("each", "Count each"), ("once", "Count once")), "each",
    ),
    PrefDef(
        "tokens_in_missing", "Tokens in missing lists",
        "Tokens and emblems from the family's token sets.",
        "choice", (("exclude", "Leave out"), ("include", "Include")), "exclude",
    ),
)

_BY_KEY = {d.key: d for d in DEFINITIONS}


@dataclass(frozen=True)
class Prefs:
    set_types: frozenset[str]
    variant_prints: str
    by_family: str
    datestamped: str
    missing_rarities: frozenset[str]
    chase_in_lists: str
    foil_twins: str
    tokens_in_missing: str
    changed: frozenset[str] = frozenset()


def _default_value(d: PrefDef):
    return list(d.default) if d.kind == "multi" else d.default


def _clean(d: PrefDef, value):
    """The canonical value (multi → list in choices order), or raise ValueError."""
    allowed = [v for v, _ in d.choices]
    if d.kind == "choice":
        if not isinstance(value, str) or value not in allowed:
            raise ValueError(f"{d.key} must be one of: {', '.join(allowed)}")
        return value
    if isinstance(value, str) or not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError(f"{d.key} takes a list of values from: {', '.join(allowed)}")
    items = set(value)
    bad = sorted(str(i) for i in items if not isinstance(i, str) or i not in allowed)
    if bad:
        raise ValueError(f"{d.key}: unknown value(s) {', '.join(bad)}; allowed: {', '.join(allowed)}")
    if not items and d.key != "set_types":
        raise ValueError(f"{d.key} needs at least one of: {', '.join(allowed)}")
    return [v for v in allowed if v in items]


def _read_json(key: str):
    """The parsed JSON saved under user setting ``key``; None when absent or unparseable."""
    with db.connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if not (row and row["value"]):
        return None
    try:
        return json.loads(row["value"])
    except ValueError:
        return None


def _write_json(key: str, value) -> None:
    """Save ``value`` under user setting ``key`` (deleted when empty)."""
    with db.connect() as conn:
        if value:
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                         "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                         (key, json.dumps(value, sort_keys=True)))
        else:
            conn.execute("DELETE FROM settings WHERE key = ?", (key,))


def _stored() -> dict:
    data = _read_json(SETTING_KEY)
    return data if isinstance(data, dict) else {}


def _values(stored: dict) -> tuple[dict, frozenset[str]]:
    """Every key's canonical value (stored when valid, else default) and the changed keys."""
    out: dict = {}
    changed: set[str] = set()
    for d in DEFINITIONS:
        val = _default_value(d)
        if d.key in stored:
            try:
                val = _clean(d, stored[d.key])
            except ValueError:
                val = _default_value(d)
        out[d.key] = val
        if val != _default_value(d):
            changed.add(d.key)
    return out, frozenset(changed)


def _build(stored: dict) -> Prefs:
    vals, changed = _values(stored)
    kw = {k: (frozenset(v) if _BY_KEY[k].kind == "multi" else v) for k, v in vals.items()}
    return Prefs(changed=changed, **kw)


def get(*, fresh: bool = False) -> Prefs:
    """This user's preferences (cached per user file). Defaults when nobody is bound."""
    try:
        scope = db.user_scope()
    except _layout.NoUserBound:
        return _build({})
    now = time.monotonic()
    with _lock:
        hit = _cache.get(scope)
        if hit and not fresh and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    p = _build(_stored())
    with _lock:
        _cache[scope] = (now, p)
    return p


def update(key: str, value) -> Prefs:
    """Set one preference; ``value=None`` resets it. Unknown key → LookupError,
    bad value → ValueError. Takes effect immediately."""
    d = _BY_KEY.get(key)
    if d is None:
        raise LookupError(f"unknown preference {key!r}; known: {', '.join(_BY_KEY)}")
    stored = _stored()
    if value is None:
        stored.pop(key, None)
    else:
        stored[key] = _clean(d, value)
    _write_json(SETTING_KEY, stored)
    clear_cache()
    # Per-user derived caches (family status, ...) recompute.
    db.forget_user_scope(db.user_scope())
    return get(fresh=True)


def describe() -> list[dict]:
    """Each definition with its current ``value`` (list for multi), ``default`` and ``changed``."""
    vals, changed = _values(_stored())
    return [
        {
            "key": d.key, "title": d.title, "about": d.about, "kind": d.kind,
            "choices": [{"value": v, "label": lbl} for v, lbl in d.choices],
            "value": vals[d.key], "default": _default_value(d),
            "changed": d.key in changed,
        }
        for d in DEFINITIONS
    ]


def clear_cache() -> None:
    with _lock:
        _cache.clear()
        _rules_cache.clear()
        _kinds_cache.clear()


# ---------- per-family rule overrides ----------

def _stored_rules() -> dict[str, dict[str, str]]:
    """The saved overrides, tolerant of bad JSON, wrong shapes and unknown states."""
    data = _read_json(FAMILY_RULES_KEY)
    if not isinstance(data, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for anchor, rules in data.items():
        if not isinstance(anchor, str) or not isinstance(rules, dict):
            continue
        clean = {rid: st for rid, st in rules.items()
                 if isinstance(rid, str) and st in RULE_STATES}
        if clean:
            out[anchor.lower()] = clean
    return out


def _all_family_rules() -> dict[str, dict[str, str]]:
    try:
        scope = db.user_scope()
    except _layout.NoUserBound:
        return {}
    now = time.monotonic()
    with _lock:
        hit = _rules_cache.get(scope)
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    data = _stored_rules()
    with _lock:
        _rules_cache[scope] = (now, data)
    return data


def family_rule_overrides(anchor: str) -> dict[str, str]:
    """This user's saved ``{rule_id: state}`` for one family (cached per user file;
    the SAME dict object until the cache expires or is cleared; empty when nothing is
    saved or no user is bound). Callers must not mutate it."""
    return _all_family_rules().get(anchor.lower(), _NO_RULES)


def _save_family_entry(anchor: str, rule_id: str, state: str | None) -> dict[str, str]:
    stored = _stored_rules()
    fam = dict(stored.get(anchor, {}))
    if state is None:
        fam.pop(rule_id, None)
    else:
        fam[rule_id] = state
    if fam:
        stored[anchor] = fam
    else:
        stored.pop(anchor, None)
    _write_json(FAMILY_RULES_KEY, stored)
    clear_cache()
    db.forget_user_scope(db.user_scope())
    return dict(fam)


def set_family_rule(anchor: str, rule_id: str, state: str | None) -> dict[str, str]:
    """Pin one rule's state for this user (any explicit state is stored, even the
    shipped one); ``state=None`` removes the pin. Unknown family or rule →
    ``LookupError``, bad state → ``ValueError``. Returns the family's overrides."""
    from . import selectors  # lazy: selectors reads this module too
    if state is not None and state not in RULE_STATES:
        raise ValueError(f"state must be one of: {', '.join(RULE_STATES)}")
    anchor = anchor.lower()
    defaults = selectors.family_rule_defaults(anchor)  # LookupError for an unknown family
    if rule_id not in defaults:
        raise LookupError(f"no rule {rule_id!r} in family {anchor!r}")
    return _save_family_entry(anchor, rule_id, state)


def set_family_all(anchor: str, state: str | None) -> dict[str, str]:
    """Set a family's "All rules" state (what its rules do unless one is pinned);
    ``None`` removes it. Same errors as :func:`set_family_rule`."""
    from . import selectors
    if state is not None and state not in RULE_STATES:
        raise ValueError(f"state must be one of: {', '.join(RULE_STATES)}")
    anchor = anchor.lower()
    selectors.family_rule_defaults(anchor)
    return _save_family_entry(anchor, ALL_RULES, state)


# ---------- per-kind variant overrides ----------

def _stored_kinds() -> dict[str, str]:
    data = _read_json(VARIANT_KINDS_KEY)
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(k, str) and v in KIND_STATES}


def variant_kind_overrides() -> dict[str, str]:
    """This user's saved ``{kind: "hide"|"show"}`` (cached per user file; the SAME
    dict until the cache expires or is cleared; empty when nothing is saved or no user
    is bound). Callers must not mutate it."""
    try:
        scope = db.user_scope()
    except _layout.NoUserBound:
        return _NO_RULES
    now = time.monotonic()
    with _lock:
        hit = _kinds_cache.get(scope)
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    data = _stored_kinds()
    with _lock:
        _kinds_cache[scope] = (now, data)
    return data


def set_variant_kind(kind: str, state: str | None) -> dict[str, str]:
    """Set one variant kind to ``hide`` or ``show`` (``None`` = follow the group).
    Unknown kind → ``LookupError``, bad state → ``ValueError``."""
    from . import sets  # lazy: sets reads this module too
    if kind not in {k for k, _l, _s in sets.VARIANT_KINDS}:
        raise LookupError(f"unknown variant kind {kind!r}")
    if state is not None and state not in KIND_STATES:
        raise ValueError(f"state must be one of: {', '.join(KIND_STATES)}")
    stored = _stored_kinds()
    if state is None:
        stored.pop(kind, None)
    else:
        stored[kind] = state
    _write_json(VARIANT_KINDS_KEY, stored)
    clear_cache()
    db.forget_user_scope(db.user_scope())
    return dict(stored)


@db.user_cache
def forget_scope(scope: str) -> None:
    """Drop one user's cached preferences (``db.user_scope()``; account deletion)."""
    with _lock:
        _cache.pop(scope, None)
        _rules_cache.pop(scope, None)
        _kinds_cache.pop(scope, None)

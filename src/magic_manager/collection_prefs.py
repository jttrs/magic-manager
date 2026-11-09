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
# Per-family rule switches: {anchor: {rule_id: "count"|"chase"|"hide"}}, only the
# rules whose state differs from the shipped default (selectors.family_rule_catalog).
FAMILY_RULES_KEY = "collection.family_rules"
RULE_STATES = ("count", "chase", "hide")
CACHE_SECONDS = 30.0

_cache: dict[str, tuple[float, "Prefs"]] = {}
_NO_RULES: dict[str, str] = {}
_rules_cache: dict[str, tuple[float, dict[str, dict[str, str]]]] = {}
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


def _stored() -> dict:
    with db.connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (SETTING_KEY,)).fetchone()
    if row and row["value"]:
        try:
            data = json.loads(row["value"])
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}
    return {}


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
    with db.connect() as conn:
        if stored:
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                         "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                         (SETTING_KEY, json.dumps(stored, sort_keys=True)))
        else:
            conn.execute("DELETE FROM settings WHERE key = ?", (SETTING_KEY,))
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


# ---------- per-family rule overrides ----------

def _stored_rules() -> dict[str, dict[str, str]]:
    """The saved overrides, tolerant of bad JSON, wrong shapes and unknown states."""
    with db.connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (FAMILY_RULES_KEY,)).fetchone()
    if not (row and row["value"]):
        return {}
    try:
        data = json.loads(row["value"])
    except ValueError:
        return {}
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


def set_family_rule(anchor: str, rule_id: str, state: str | None) -> dict[str, str]:
    """Set one rule's state for this user; ``state=None`` resets it to the shipped
    default (so does saving the default itself). Unknown family or rule →
    ``LookupError``, bad state → ``ValueError``. Returns the family's overrides."""
    from . import selectors  # lazy: selectors reads this module too
    if state is not None and state not in RULE_STATES:
        raise ValueError(f"state must be one of: {', '.join(RULE_STATES)}")
    anchor = anchor.lower()
    defaults = selectors.family_rule_defaults(anchor)  # LookupError for an unknown family
    if rule_id not in defaults:
        raise LookupError(f"no rule {rule_id!r} in family {anchor!r}")
    stored = _stored_rules()
    fam = dict(stored.get(anchor, {}))
    if state is None or state == defaults[rule_id]:
        fam.pop(rule_id, None)
    else:
        fam[rule_id] = state
    if fam:
        stored[anchor] = fam
    else:
        stored.pop(anchor, None)
    with db.connect() as conn:
        if stored:
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                         "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                         (FAMILY_RULES_KEY, json.dumps(stored, sort_keys=True)))
        else:
            conn.execute("DELETE FROM settings WHERE key = ?", (FAMILY_RULES_KEY,))
    clear_cache()
    db.forget_user_scope(db.user_scope())
    return dict(fam)


@db.user_cache
def forget_scope(scope: str) -> None:
    """Drop one user's cached preferences (``db.user_scope()``; account deletion)."""
    with _lock:
        _cache.pop(scope, None)
        _rules_cache.pop(scope, None)

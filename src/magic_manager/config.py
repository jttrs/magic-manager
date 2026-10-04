"""Declarative config loader — the one seam between the TOML files under
``config/`` and the Python constants that used to be hard-coded in
``selectors`` / ``mtgjson`` / ``sets`` / ``treatments``.

Two tiers of config, with DIFFERENT absent-file contracts:

- ``promo_types.toml`` / ``precon.toml`` are OPTIONAL — each loader ships a
  baked-in default equal to the historical constant, so the code works with
  those files absent; a file (when present) overrides, and a parse error warns
  to stderr and falls back to the default.
- ``families.toml`` is REQUIRED — it holds 34 families of per-family rules with
  no sane baked-in fallback. If it is missing or unparseable the family loaders
  raise :class:`ConfigError` (fatal) rather than silently returning ``{}`` and
  disabling ``mm query missing-set`` / ``treatment=preferred`` for every family.
  A present-but-section-absent file is still a legitimate empty result.

The config DIRECTORY is resolved per call from (precedence) an explicit
``override`` dir → ``$MAGIC_MANAGER_CONFIG_DIR`` → ``<repo>/config``; the parse
cache keys on the resolved dir, so changing the env var / passing ``override``
yields a fresh read. NOTE: the module-level constants that consume these loaders
(``selectors.FAMILY_*``, ``sets.EXCLUDED_PROMO_TYPES``,
``mtgjson.PRECON_MODERN_TYPES``, ``treatments.FANCY_FOIL_PROMO_TYPES``) are bound
at IMPORT TIME, so a process that wants its own config dir must set
``MAGIC_MANAGER_CONFIG_DIR`` BEFORE importing those modules. Callers that need a
different dir after import call the loaders directly with ``override=``.

Family rules carry a ``note=`` rationale field so the "why" travels with the
rule (no separate prose doc to drift from); a CI check
(tests/test_config_schema.py) keeps config family keys ↔ docs/sets §8 aligned.
"""

from __future__ import annotations

import os
import sys
import tomllib
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Single source of truth for the unobtainable-rule predicate vocabulary. Maps
# each supported rule key to how build_unobtainable_rules coerces its value:
#   "promo_set"  → frozenset of lowercased strings (membership via issubset/&)
#   "cn_set"     → frozenset of raw CN strings (case-sensitive)
#   "scalar"     → passed through verbatim (e.g. border_color)
#   "tier"       → the rule's exclusion TIER, lowercased str: "hard" (absent ⇒
#                  hard) is always-excluded/never-surfaced (prerelease stamps,
#                  serialized); "chase" is excluded by default but surfaceable
#                  via `mm query missing-set --chase include|only` (premium-art
#                  tiers: surgefoil/textured/neonink/headliner showcases). NOT a
#                  predicate — it gates WHICH tier filter the rule participates
#                  in (selectors._matches_unobtainable_rule's `tiers` arg).
#   "note"       → rationale only, stripped from the evaluated rule
# selectors._matches_unobtainable_rule consumes the predicate keys; the loader
# derives its coercion from here; tests/test_config_schema validates against it —
# so adding a key is a ONE-line change here, not a 3-site edit that can silently
# miss the frozenset coercion and crash the matcher at query time.
UNOBTAINABLE_RULE_KEYS: dict[str, str] = {
    "promo_types_any_of": "promo_set",
    "promo_types_all_of": "promo_set",
    "frame_effects_all_of": "promo_set",
    "collector_numbers": "cn_set",
    "border_color": "scalar",
    "tier": "tier",
    "note": "note",
}


class ConfigError(RuntimeError):
    """A REQUIRED config file is missing or unparseable."""


def config_dir(*, override: str | Path | None = None) -> Path:
    """The directory config TOML files are read from. Precedence:
    explicit ``override`` → ``$MAGIC_MANAGER_CONFIG_DIR`` → ``<repo>/config``."""
    if override is not None:
        return Path(override)
    env = os.environ.get("MAGIC_MANAGER_CONFIG_DIR")
    return Path(env) if env else _REPO_ROOT / "config"


@lru_cache(maxsize=None)
def _cached_toml(dir_str: str, name: str, required: bool) -> dict:
    """Parse ``<dir>/<name>`` once per (dir, name, required). Keyed on the
    RESOLVED dir so a changed config dir / override produces a distinct entry
    (not a stale hit). ``required`` controls the absent/unparseable contract:
    REQUIRED → raise :class:`ConfigError`; optional → warn/empty + ``{}``.
    (lru_cache does not memoize exceptions, so a required-missing file simply
    re-raises on each call.)"""
    path = Path(dir_str) / name
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        if required:
            raise ConfigError(f"required config file is missing: {path}") from None
        return {}
    except tomllib.TOMLDecodeError as e:
        if required:
            raise ConfigError(f"required config file is unparseable: {path}: {e}") from e
        print(f"warn: could not parse {path} ({e!r}); using defaults", file=sys.stderr)
        return {}


def load_toml(name: str, *, override: str | Path | None = None,
              required: bool = False) -> dict:
    """Load (and cache) ``config/<name>`` from the resolved config dir. Optional
    by default (missing/bad → ``{}``); pass ``required=True`` to make an absent
    or unparseable file fatal (:class:`ConfigError`)."""
    return _cached_toml(str(config_dir(override=override)), name, required)


def _as_frozenset(value, default: frozenset[str]) -> frozenset[str]:
    """Coerce a TOML list (or absent value) into a lowercased frozenset[str]."""
    if value is None:
        return default
    if not isinstance(value, (list, tuple)):
        return default
    return frozenset(str(v).lower() for v in value)


def as_frozenset_setting(
    file_name: str, key: str, default: frozenset[str],
    *, override: str | Path | None = None,
) -> frozenset[str]:
    """Load ``config/<file_name>``'s top-level ``key`` as a lowercased
    frozenset, falling back to ``default`` when the file/key is absent. The
    one-liner module-level constants (EXCLUDED_PROMO_TYPES, etc.) use this.
    These files are OPTIONAL — the ``default`` is the baked-in historical value."""
    data = load_toml(file_name, override=override)
    return _as_frozenset(data.get(key), default)


def get_setting(file_name: str, key: str, default,
                *, override: str | Path | None = None):
    """Load ``config/<file_name>``'s top-level ``key`` verbatim (scalar/list),
    falling back to ``default`` when absent."""
    data = load_toml(file_name, override=override)
    return data.get(key, default)


def build_unobtainable_rules(raw: dict) -> dict[str, list[dict]]:
    """Turn the TOML ``[[unobtainable.<fam>.rules]]`` tables into the exact
    nested shape ``selectors._matches_unobtainable_rule`` consumes:
    ``{anchor: [rule, …]}`` where each rule's set-valued predicate keys are
    rebuilt as ``frozenset`` (per :data:`UNOBTAINABLE_RULE_KEYS`).

    TOML shape (one array-of-tables per family)::

        [[unobtainable.clb.rules]]
        frame_effects_all_of = ["showcase"]
        border_color = "black"
        note = "76 D&D-rulebook showcase prints the user doesn't pursue; …"

    The ``note`` field is rationale-only (dropped from the evaluated rule).
    """
    out: dict[str, list[dict]] = {}
    for fam, body in (raw.get("unobtainable") or {}).items():
        rules: list[dict] = []
        for rule in (body.get("rules") or []):
            r: dict = {}
            for k, v in rule.items():
                kind = UNOBTAINABLE_RULE_KEYS.get(k)
                if kind == "note":
                    continue
                if kind == "promo_set":
                    r[k] = frozenset(str(x).lower() for x in v)
                elif kind == "cn_set":
                    r[k] = frozenset(str(x) for x in v)
                elif kind == "tier":
                    r[k] = str(v).lower()  # "hard" | "chase"; absence ⇒ hard (matcher's contract)
                else:  # "scalar" or an unknown key — pass through verbatim
                    r[k] = v
            rules.append(r)
        out[fam.lower()] = rules
    return out


def family_dupe_foil(*, override: str | Path | None = None) -> dict[str, frozenset[str]]:
    """``config/families.toml`` ``[dupe_foil]`` → ``{family: frozenset(promo_types)}``.
    An empty list is a CONFIGURED family with no dupe-foil signal (a present key),
    distinct from an absent family (unconfigured) — the preferred filter keys on
    membership, so this distinction matters. families.toml is REQUIRED: a
    missing/unparseable file raises :class:`ConfigError` rather than returning {}."""
    raw = load_toml("families.toml", override=override, required=True).get("dupe_foil") or {}
    return {k.lower(): frozenset(str(v).lower() for v in vals)
            for k, vals in raw.items()}


def family_unobtainable_rules(*, override: str | Path | None = None) -> dict[str, list[dict]]:
    """``config/families.toml`` ``[[unobtainable.<fam>.rules]]`` → the nested
    ``{family: [rule, …]}`` the selector matcher consumes (set-valued keys as
    frozensets, ``note`` stripped). families.toml is REQUIRED."""
    return build_unobtainable_rules(load_toml("families.toml", override=override, required=True))


def family_scenes(*, override: str | Path | None = None) -> dict[str, list[dict]]:
    """``config/families.toml`` ``[[scenes.<fam>]]`` → ``{family: [scene-dict, …]}``
    (plain dicts: name/artist/set/cn_lo/cn_hi). families.toml is REQUIRED."""
    raw = load_toml("families.toml", override=override, required=True).get("scenes") or {}
    return {k.lower(): [dict(sc) for sc in scenes] for k, scenes in raw.items()}


def collection_formats(*, override: str | Path | None = None) -> dict[str, dict]:
    """``config/collection_formats.toml`` → ``{service: format-dict}``.

    The declarative seam behind ``collection_sync.read_csv``/``write_csv``: one
    ``[<service>]`` block per external collection service (column map,
    finish/condition maps, write order, ``has_scryfall_id``, ``confidence``).
    REQUIRED — collection sync has no sane baked-in default (a column map can't
    be guessed), so a missing/unparseable file raises :class:`ConfigError`
    rather than silently disabling ``mm collection``. Service keys are
    lowercased so lookups are case-insensitive; the inner dicts are returned
    verbatim (plain TOML — collection_sync owns the interpretation)."""
    raw = load_toml("collection_formats.toml", override=override, required=True)
    return {str(k).lower(): dict(v) for k, v in raw.items() if isinstance(v, dict)}


# ---------- function_tags.toml (Scryfall Tagger function roots) ----------

# Baked-in default == config/function_tags.toml (OPTIONAL file; a test keeps the
# two in sync). Each root: (key, label, ((tag_uuid, tag_slug), …)).
_DEFAULT_FUNCTION_ROOTS: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = (
    ("ramp", "Ramp", (("2f3e4ad7-5e60-41b4-bdbc-653f16869cf6", "ramp"),)),
    ("draw", "Card draw", (("b6448c45-ce65-4848-aa98-2151e4e07437", "draw"),)),
    ("removal", "Removal", (("444f824c-f910-4530-9dbe-ede7a84cd7f9", "removal"),)),
    ("board-wipe", "Board wipe", (("3fb7e4fd-5304-4120-b7c4-8a89f70ad3f0", "sweeper"),)),
    ("counterspell", "Counterspell", (("690fc968-48ba-4854-a948-3db6bf19d3a9", "counterspell"),)),
    ("tutor", "Tutor", (("c768d2ec-3264-4a90-a98f-bea8467857d3", "tutor"),)),
    ("recursion", "Recursion", (("82b824ad-648f-467f-a190-2e0fa9a795d2", "recursion"),)),
    ("protection", "Protection", (("6e2cdc7c-b02c-4b59-a171-f93723721b79", "protection"),)),
    ("token-maker", "Token maker", (
        ("a9657a5d-e7f8-4000-a795-7a78b5fb8923", "repeatable-token-generator"),
        ("07808167-c4ef-4a2d-bfe9-fa38a5a9d17b", "multiple-bodies"),
    )),
    ("sac-outlet", "Sac outlet", (("c7bd55a7-1ea0-49da-b25e-0be470fbe8ec", "sacrifice-outlet"),)),
    ("lifegain", "Lifegain", (("4caab3cc-1d60-44fb-a26a-cc833bc67c97", "lifegain"),)),
    ("evasion", "Evasion", (("6cdeab4c-72a6-4f40-ab19-14284d6cf775", "gives-evasion"),)),
)
_DEFAULT_PREVIEW_LIMIT = 6
_DEFAULT_PREVIEW_EXCLUDE: tuple[str, ...] = (
    "card-names", "cycle", "flavors-of-vanilla", "type-errata", "unique-type-line",
    "triggered-ability", "activated-ability", "cheaper-than-mv",
    "more-expensive-than-mv", "staple-with-set-s-mechanic", "token-errata",
    "single-target-instant-sorcery", "drawback", "meme",
)


def function_tags(*, override: str | Path | None = None) -> dict:
    """``config/function_tags.toml`` → ``{"roots": [{key,label,tags:[{id,slug}]}],
    "preview_limit": int, "preview_exclude": [slug…]}``. OPTIONAL: a missing or
    unparseable file (or an absent key) falls back to the baked-in default."""
    raw = load_toml("function_tags.toml", override=override)
    roots = raw.get("roots")
    if not isinstance(roots, list) or not roots:
        roots = [{"key": k, "label": lbl, "tags": [{"id": i, "slug": s} for i, s in tags]}
                 for k, lbl, tags in _DEFAULT_FUNCTION_ROOTS]
    else:
        roots = [{"key": str(r["key"]), "label": str(r.get("label") or r["key"]),
                  "tags": [{"id": str(t.get("id") or ""), "slug": str(t.get("slug") or "")}
                           for t in (r.get("tags") or [])]}
                 for r in roots if isinstance(r, dict) and r.get("key")]
    limit = raw.get("preview_limit", _DEFAULT_PREVIEW_LIMIT)
    exclude = raw.get("preview_exclude", list(_DEFAULT_PREVIEW_EXCLUDE))
    return {"roots": roots, "preview_limit": int(limit),
            "preview_exclude": [str(s) for s in exclude]}

"""Declarative config loader — the one seam between the TOML files under
``config/`` and the Python constants that used to be hard-coded in
``selectors`` / ``mtgjson`` / ``sets`` / ``treatments``.

Mirrors the ``trueup_pools.py`` + ``config/product_priority.toml`` precedent:
every loader has baked-in defaults equal to the historical constant, so the code
works with NO config files present; a file (when present) overrides. A parse
error warns to stderr and falls back to defaults — bad config never breaks a run.

The eventual web app sets ONE thing — ``MAGIC_MANAGER_CONFIG_DIR`` (or passes an
explicit ``override`` dir) — to point the whole system at its own editable config
without touching code. Family rules carry a ``note=`` rationale field so the
"why" travels with the rule (no separate prose doc to drift from); a CI check
(tests/test_config_schema.py) keeps config family keys ↔ docs/sets §8 aligned.
"""

from __future__ import annotations

import os
import sys
import tomllib
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def config_dir(*, override: str | Path | None = None) -> Path:
    """The directory config TOML files are read from. Precedence:
    explicit ``override`` → ``$MAGIC_MANAGER_CONFIG_DIR`` → ``<repo>/config``."""
    if override is not None:
        return Path(override)
    env = os.environ.get("MAGIC_MANAGER_CONFIG_DIR")
    return Path(env) if env else _REPO_ROOT / "config"


def load_toml(name: str, *, override: str | Path | None = None) -> dict:
    """Load ``config/<name>`` (``name`` includes the ``.toml`` suffix). Missing
    file → ``{}``; parse error → warn to stderr + ``{}``. Never raises for
    bad/absent config (callers merge the result onto baked-in defaults)."""
    path = config_dir(override=override) / name
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:  # noqa: BLE001 — bad config must not break a run
        print(f"warn: could not parse {path} ({e!r}); using defaults", file=sys.stderr)
        return {}


def _as_frozenset(value, default: frozenset[str]) -> frozenset[str]:
    """Coerce a TOML list (or absent value) into a lowercased frozenset[str]."""
    if value is None:
        return default
    if not isinstance(value, (list, tuple)):
        return default
    return frozenset(str(v).lower() for v in value)


def as_frozenset_setting(
    file_name: str, key: str, default: frozenset[str],
) -> frozenset[str]:
    """Load ``config/<file_name>``'s top-level ``key`` as a lowercased
    frozenset, falling back to ``default`` when the file/key is absent. The
    one-liner module-level constants (EXCLUDED_PROMO_TYPES, etc.) use this."""
    data = _cached_toml(file_name)
    return _as_frozenset(data.get(key), default)


def get_setting(file_name: str, key: str, default):
    """Load ``config/<file_name>``'s top-level ``key`` verbatim (scalar/list),
    falling back to ``default`` when absent."""
    data = _cached_toml(file_name)
    return data.get(key, default)


def build_unobtainable_rules(raw: dict) -> dict[str, list[dict]]:
    """Turn the TOML ``[unobtainable.<fam>]`` tables into the exact nested shape
    ``selectors._matches_unobtainable_rule`` consumes: ``{anchor: [rule, …]}``
    where each rule's set-valued predicate keys are rebuilt as ``frozenset``.

    TOML shape (one array-of-tables per family)::

        [[unobtainable.clb.rules]]
        frame_effects_all_of = ["showcase"]
        border_color = "black"
        note = "76 D&D-rulebook showcase prints the user doesn't pursue; …"

    The ``note`` field is rationale-only (dropped from the evaluated rule — the
    matcher ignores unknown keys, but we strip it so the shape stays clean).
    """
    _SET_KEYS = {"promo_types_any_of", "promo_types_all_of", "frame_effects_all_of"}
    out: dict[str, list[dict]] = {}
    for fam, body in (raw.get("unobtainable") or {}).items():
        rules_in = body.get("rules") if isinstance(body, dict) else body
        rules: list[dict] = []
        for rule in rules_in or []:
            r: dict = {}
            for k, v in rule.items():
                if k == "note":
                    continue
                if k in _SET_KEYS:
                    r[k] = frozenset(str(x).lower() for x in v)
                elif k == "collector_numbers":
                    r[k] = frozenset(str(x) for x in v)
                else:
                    r[k] = v
            rules.append(r)
        out[fam.lower()] = rules
    return out


@lru_cache(maxsize=None)
def _cached_toml(name: str) -> dict:
    """Module-level cache (config files don't change within a process)."""
    return load_toml(name)

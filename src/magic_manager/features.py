"""Feature flags: gate internal-only features (e.g. the Mana Pool cart check).

``config/features.toml`` ships the defaults (internal features OFF);
``config/features.local.toml`` (git-ignored) turns them on per machine, and the
``MM_FEATURES`` environment variable overrides both (``cart_check,-other``).
Only flags declared in features.toml exist; unknown names are ignored.
"""
from __future__ import annotations

import os

from . import config


def _table(name: str) -> dict:
    return config.load_toml(name).get("features") or {}


def flags() -> dict[str, bool]:
    """Every declared flag with its effective value."""
    out = {k: bool(v) for k, v in _table("features.toml").items()}
    for k, v in _table("features.local.toml").items():
        if k in out:
            out[k] = bool(v)
    for raw in (os.environ.get("MM_FEATURES") or "").split(","):
        name = raw.strip()
        off = name.startswith("-")
        name = name.lstrip("-+")
        if name in out:
            out[name] = not off
    return out


def enabled(name: str) -> bool:
    return flags().get(name, False)


class FeatureDisabled(PermissionError):
    """Raised by a gated operation when its flag is off."""


def require(name: str) -> None:
    if not enabled(name):
        raise FeatureDisabled(f"the {name!r} feature is turned off on this machine")

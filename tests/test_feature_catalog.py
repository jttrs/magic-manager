"""The shipped config/features.toml: every flag carries its picker metadata."""
from __future__ import annotations

import re
from datetime import date

from magic_manager import config, features


def _shipped():
    config._cached_toml.cache_clear()
    flags = config.load_toml("features.toml", override=config._REPO_ROOT / "config")["flags"]
    config._cached_toml.cache_clear()
    return flags


def test_every_flag_is_fully_described():
    flags = _shipped()
    assert flags
    for name, t in flags.items():
        assert re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name), name
        assert isinstance(t["default"], bool), name
        assert 0 < len(t["title"]) <= 24, name
        assert 0 < len(t["about"]) <= 80 and t["about"].endswith("."), name
        assert t["kind"] in features.KINDS, name
        date.fromisoformat(t["added"])
        if t["kind"] == "release":
            assert date.fromisoformat(t["review_by"]) >= date.today(), f"{name}: review_by has passed"

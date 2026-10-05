"""features — flags from config/features.toml, a local override, and MM_FEATURES."""
from __future__ import annotations

import pytest

from magic_manager import config, features


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_MANAGER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("MM_FEATURES", raising=False)
    config._cached_toml.cache_clear()
    (tmp_path / "features.toml").write_text("[features]\ncart_check = false\nother = true\n")
    yield tmp_path
    config._cached_toml.cache_clear()


def test_defaults_then_local_then_env(cfg, monkeypatch):
    assert features.flags() == {"cart_check": False, "other": True}
    (cfg / "features.local.toml").write_text("[features]\ncart_check = true\nunknown = true\n")
    config._cached_toml.cache_clear()
    assert features.flags() == {"cart_check": True, "other": True}
    monkeypatch.setenv("MM_FEATURES", "-cart_check, other, nope")
    assert features.flags() == {"cart_check": False, "other": True}


def test_require_raises_when_off(cfg):
    with pytest.raises(features.FeatureDisabled):
        features.require("cart_check")
    assert not features.enabled("missing")


def test_shipped_internal_features_are_off():
    config._cached_toml.cache_clear()
    shipped = config.load_toml("features.toml", override=config._REPO_ROOT / "config")["features"]
    assert shipped["cart_check"] is False

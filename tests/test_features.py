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
    shipped = config.load_toml("features.toml", override=config._REPO_ROOT / "config")["flags"]
    assert shipped["cart_check"]["default"] is False


# ---------- the 'everyone' layer, resolve(), set_instance ----------

from magic_manager.auth import store  # noqa: E402


@pytest.fixture
def auth_db(cfg, tmp_path, monkeypatch):
    p = tmp_path / "auth-feat.db"
    monkeypatch.setenv("MM_AUTH_DB", str(p))
    return p


def _events():
    with store.connect() as conn:
        return [tuple(r) for r in conn.execute("SELECT flag, scope, user_id, value FROM feature_flag_events ORDER BY id")]


def test_instance_flags_never_create_auth_db(auth_db):
    assert features.instance_flags() == {}
    assert features.flags() == {"cart_check": False, "other": True}
    assert not auth_db.exists()


def test_layer_order_and_sources(auth_db, cfg, monkeypatch):
    (cfg / "features.local.toml").write_text("[features]\ncart_check = true\n")
    config._cached_toml.cache_clear()
    r = features.resolve(None)
    assert (r["cart_check"].value, r["cart_check"].source) == (True, "local_file")
    assert r["other"].source == "default"
    features.set_instance("cart_check", False)           # everyone beats the local file
    r = features.resolve(None)["cart_check"]
    assert (r.value, r.source, r.everyone, r.pinned_by_env) == (False, "everyone", False, False)
    monkeypatch.setenv("MM_FEATURES", "cart_check")      # env pin beats everyone
    r = features.resolve(None)["cart_check"]
    assert (r.value, r.source, r.everyone, r.pinned_by_env) == (True, "env", False, True)
    assert features.base_flags()["cart_check"] is True


def test_reset_falls_back_and_logs(auth_db):
    features.set_instance("other", False)
    assert features.flags()["other"] is False
    features.set_instance("other", None)
    assert features.flags()["other"] is True and features.resolve(None)["other"].everyone is None
    assert _events() == [("other", "everyone", None, 0), ("other", "everyone", None, None)]


def test_set_instance_unknown_flag(auth_db):
    with pytest.raises(ValueError, match="cart_check"):
        features.set_instance("nope", True)
    assert not auth_db.exists()


def test_user_override_beats_everyone_and_env(auth_db, monkeypatch):
    monkeypatch.setenv("MM_MODE", "hosted")
    u = store.redeem_invite(store.create_invite(is_admin=False).code, "discord", "1", "M", None)
    features.set_instance("cart_check", True)
    monkeypatch.setenv("MM_FEATURES", "cart_check")
    store.set_override(u.id, "cart_check", False)
    r = features.resolve(u.id)["cart_check"]
    assert (r.value, r.source, r.mine, r.everyone) == (False, "user", False, True)
    store.set_override(u.id, "cart_check", None)
    assert features.resolve(u.id)["cart_check"].value is True
    assert [e[1] for e in _events()] == ["everyone", "user", "user"]
    assert store.last_changes()[("cart_check", u.id)][0]


def test_legacy_features_table_still_parses(cfg):
    d = features.declared()
    assert d["other"] == features.FlagDef("other", True, "other", "", "release", None, None)
    assert features.about() == {"cart_check": "", "other": ""}


def test_flags_table_form(cfg):
    (cfg / "features.toml").write_text('[flags.x]\ndefault = true\ntitle = "X"\nabout = "Does x."\nkind = "ops"\n')
    config._cached_toml.cache_clear()
    assert features.declared()["x"].kind == "ops" and features.flags() == {"x": True}

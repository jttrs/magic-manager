"""Personal secrets: environment first, then the macOS Keychain; the cart login
never reads the repo's .env."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from magic_manager import secrets


def test_environment_wins_over_keychain(monkeypatch):
    monkeypatch.setattr(secrets, "keychain_get", lambda name: "from-keychain")
    monkeypatch.setenv("MANAPOOL_EMAIL", "from-env")
    assert secrets.get("MANAPOOL_EMAIL") == "from-env"
    monkeypatch.delenv("MANAPOOL_EMAIL")
    assert secrets.get("MANAPOOL_EMAIL") == "from-keychain"


def test_no_keychain_off_macos(monkeypatch):
    monkeypatch.setattr(secrets.sys, "platform", "linux")
    assert secrets.keychain_get("MANAPOOL_PASSWORD") is None


def test_cart_login_ignores_dotenv(tmp_path, monkeypatch, capsys):
    script = Path(__file__).resolve().parents[1] / "scripts" / "manapool_cart.py"
    spec = importlib.util.spec_from_file_location("manapool_cart_t", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    (tmp_path / ".env").write_text("MANAPOOL_EMAIL=dotenv@example.com\nMANAPOOL_PASSWORD=dotenv-pw\n")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    for k in secrets.PERSONAL:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(secrets, "keychain_get", lambda name: {"MANAPOOL_EMAIL": "me@example.com"}.get(name))
    assert mod._load_env() == {"MANAPOOL_EMAIL": "me@example.com"}
    assert "ignored" in capsys.readouterr().err

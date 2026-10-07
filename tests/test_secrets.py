"""Personal secrets: the personal login prefers the Keychain; the environment is the fallback."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

from magic_manager import secrets


def _fake_run(calls, rc=0, out=""):
    def run(argv, **kw):
        calls.append((argv, kw))
        return subprocess.CompletedProcess(argv, rc, stdout=out, stderr="")
    return run


def test_personal_prefers_keychain_over_environment(monkeypatch):
    monkeypatch.setattr(secrets, "keychain_get", lambda name: "from-keychain")
    monkeypatch.setenv("MANAPOOL_EMAIL", "from-env")
    assert secrets.get("MANAPOOL_EMAIL") == "from-keychain"
    monkeypatch.setattr(secrets, "keychain_get", lambda name: None)
    assert secrets.get("MANAPOOL_EMAIL") == "from-env"


def test_non_personal_prefers_environment(monkeypatch):
    monkeypatch.setattr(secrets, "keychain_get", lambda name: "from-keychain")
    monkeypatch.setenv("SOME_TOKEN", "from-env")
    assert secrets.get("SOME_TOKEN") == "from-env"
    monkeypatch.delenv("SOME_TOKEN")
    assert secrets.get("SOME_TOKEN") == "from-keychain"


def test_keychain_get_argv_and_failure(monkeypatch):
    calls: list = []
    monkeypatch.setattr(secrets, "keychain_available", lambda: True)
    monkeypatch.setattr(secrets.subprocess, "run", _fake_run(calls, 0, "s3cret\n"))
    assert secrets.keychain_get("MANAPOOL_PASSWORD") == "s3cret"
    assert calls[0][0] == ["security", "find-generic-password", "-s", "magic-manager", "-a", "MANAPOOL_PASSWORD", "-w"]
    assert calls[0][1]["timeout"] == 10
    monkeypatch.setattr(secrets.subprocess, "run", _fake_run([], 44, ""))
    assert secrets.keychain_get("MANAPOOL_PASSWORD") is None


def test_keychain_get_timeout_is_none(monkeypatch):
    def run(argv, **kw):
        raise subprocess.TimeoutExpired(argv, 10)
    monkeypatch.setattr(secrets, "keychain_available", lambda: True)
    monkeypatch.setattr(secrets.subprocess, "run", run)
    assert secrets.keychain_get("MANAPOOL_PASSWORD") is None


def test_set_interactive_keeps_secret_off_argv(monkeypatch):
    calls: list = []
    monkeypatch.setattr(secrets, "keychain_available", lambda: True)
    monkeypatch.setattr(secrets.subprocess, "run", _fake_run(calls))
    assert secrets.set_interactive("MANAPOOL_PASSWORD") == 0
    assert calls[0][0][-1] == "-w"


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

"""Credentials: the environment wins, else the repo-root .env; status shows sources, never values."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from typer.testing import CliRunner

from magic_manager import secrets
from magic_manager.cli import app

NAMES = ("MANAPOOL_EMAIL", "MANAPOOL_PASSWORD", "SOME_TOKEN")


def _setup(tmp_path, monkeypatch, dotenv: str | None):
    monkeypatch.setattr(secrets, "ROOT", tmp_path)
    if dotenv is not None:
        (tmp_path / ".env").write_text(dotenv)
    for k in NAMES:
        monkeypatch.delenv(k, raising=False)


def test_environment_wins_over_dotenv(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, "MANAPOOL_EMAIL=file@example.com\n")
    monkeypatch.setenv("MANAPOOL_EMAIL", "env@example.com")
    assert secrets.get("MANAPOOL_EMAIL") == "env@example.com"
    assert secrets.source("MANAPOOL_EMAIL") == "environment"


def test_empty_environment_falls_back_to_dotenv(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, "MANAPOOL_EMAIL=file@example.com\n")
    monkeypatch.setenv("MANAPOOL_EMAIL", "")
    assert secrets.get("MANAPOOL_EMAIL") == "file@example.com"
    assert secrets.source("MANAPOOL_EMAIL") == ".env"


def test_dotenv_parsing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch,
           "# comment\n\nMANAPOOL_EMAIL=\"me@example.com\"\n"
           "export MANAPOOL_PASSWORD='pw with = sign'\n"
           "SOME_TOKEN=first\nSOME_TOKEN=second\n")
    assert secrets.get("MANAPOOL_EMAIL") == "me@example.com"
    assert secrets.get("MANAPOOL_PASSWORD") == "pw with = sign"
    assert secrets.get("SOME_TOKEN") == "first"


def test_missing_file_and_missing_key_are_none(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, None)
    assert secrets.get("MANAPOOL_EMAIL") is None
    assert secrets.source("MANAPOOL_EMAIL") is None
    (tmp_path / ".env").write_text("OTHER=1\n")
    assert secrets.get("MANAPOOL_EMAIL") is None


def test_status_prints_sources_not_values(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, "MANAPOOL_PASSWORD=hunter2-secret\n")
    monkeypatch.setenv("MANAPOOL_EMAIL", "env-secret@example.com")
    out = CliRunner().invoke(app, ["secret", "status"]).output
    assert "MANAPOOL_EMAIL: environment" in out
    assert "MANAPOOL_PASSWORD: .env" in out
    assert "hunter2-secret" not in out and "env-secret" not in out


def test_status_not_set(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, None)
    out = CliRunner().invoke(app, ["secret", "status"]).output
    assert "MANAPOOL_EMAIL: not set" in out


def test_cart_script_reads_dotenv_login(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / "scripts" / "manapool_cart.py"
    spec = importlib.util.spec_from_file_location("manapool_cart_t", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _setup(tmp_path, monkeypatch, "MANAPOOL_EMAIL=a@example.com\nMANAPOOL_PASSWORD=pw\n")
    assert mod._load_env() == {"MANAPOOL_EMAIL": "a@example.com", "MANAPOOL_PASSWORD": "pw"}

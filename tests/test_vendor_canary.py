"""The nightly vendor canary script: which outcomes fail CI (offline)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "vendor_canary_script", ROOT / "scripts" / "vendor_canary.py")
script = importlib.util.module_from_spec(_spec)
sys.modules["vendor_canary_script"] = script
_spec.loader.exec_module(script)

V1 = SimpleNamespace(name="Store One", key="one", mode="shopify")
V2 = SimpleNamespace(name="Store Two", key="two", mode="meta")

OK = (V1, "ok", None, 9.99, True, "")
BLOCKED = (V2, "unverified", "scrape.blocked", None, None, "blocked")
FAIL = (V2, "fail", "scrape.no_price", None, None, "no price")


@pytest.mark.parametrize("outcome,code,expected", [
    ("ok", None, False),
    ("fail", "scrape.no_price", True),
    ("unverified", "scrape.blocked", False),
    ("unverified", "scrape.unreachable", False),
    ("unverified", "scrape.sample_gone", True),
])
def test_fails_ci(outcome, code, expected):
    assert script.fails_ci(outcome, code) is expected


def _main(monkeypatch, capsys, rows, argv):
    monkeypatch.setattr(script, "run", lambda: (rows, ["Open Tab Store"]))
    monkeypatch.setattr(sys, "argv", ["vendor_canary.py", *argv])
    code = script.main()
    return code, capsys.readouterr()


def test_blocked_does_not_fail(monkeypatch, capsys):
    code, out = _main(monkeypatch, capsys, [OK, BLOCKED], ["--markdown"])
    assert code == 0
    assert "⚠️" in out.out
    assert "Couldn't check from CI" in out.out
    assert "1 of 2 recipes read; 1 couldn't be checked from CI; 0 failed" in out.err


def test_fail_exits_1(monkeypatch, capsys):
    code, out = _main(monkeypatch, capsys, [OK, FAIL], ["--markdown"])
    assert code == 1
    assert "❌" in out.out


def test_plain_output_words(monkeypatch, capsys):
    code, out = _main(monkeypatch, capsys, [OK, BLOCKED, FAIL], [])
    assert code == 1
    assert "skip" in out.out and "FAIL" in out.out and "ok  " in out.out

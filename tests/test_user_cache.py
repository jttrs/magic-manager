"""Per-user process caches register with ``db.user_cache``; account deletion clears them all."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from magic_manager import db, family_status, market
from magic_manager.analytics import consent


def test_the_three_caches_are_registered_once():
    for f in (consent.forget_scope, market.forget_scope, family_status.forget_scope):
        assert db._USER_CACHES.count(f) == 1
        assert db.user_cache(f) is f
        assert db._USER_CACHES.count(f) == 1


def test_forget_user_scope_clears_only_that_scope(monkeypatch):
    monkeypatch.setattr(family_status, "_ST_INDEX", {"X": ({}, {}), "Y": ({}, {})})
    monkeypatch.setattr(market, "_cost_memo", {("X", "a"): (0, (), {}), ("Y", "a"): (0, (), {})})
    monkeypatch.setattr(consent, "_cache", {"X|errors": 1, "Y|errors": 2})
    db.forget_user_scope("X")
    assert set(family_status._ST_INDEX) == {"Y"}
    assert set(market._cost_memo) == {("Y", "a")}
    assert set(consent._cache) == {"Y|errors"}


def test_forget_user_scope_runs_all_then_raises_first(monkeypatch):
    calls = []

    def boom(scope):
        calls.append("boom")
        raise RuntimeError("first")

    def after(scope):
        calls.append("after")

    monkeypatch.setattr(db, "_USER_CACHES", [boom, after])
    with pytest.raises(RuntimeError, match="first"):
        db.forget_user_scope("X")
    assert calls == ["boom", "after"]


def test_every_user_scoped_cache_registers_its_forget_function():
    src = Path(db.__file__).parent
    missing = [
        str(p.relative_to(src)) for p in sorted(src.rglob("*.py"))
        if p != Path(db.__file__) and "user_scope()" in p.read_text()
        and not re.search(r"@(db\.)?user_cache\b", p.read_text())
    ]
    assert not missing, (
        f"{missing} key a process-wide cache on db.user_scope() but do not register a "
        "forget function: decorate the module's forget_scope with @db.user_cache"
    )

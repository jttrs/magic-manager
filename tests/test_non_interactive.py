"""Non-interactive use: every prompt has a flag; off a terminal without it the
command fails fast naming the flag (never blocks, never 'Aborted.' + exit 0).

CliRunner's stdin is not a terminal — exactly how agents and the web app run."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from magic_manager import db, interactive, inventory, undo

runner = CliRunner()
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def app():
    from magic_manager.cli import app
    return app


@pytest.fixture
def owned(tmp_db, seed_cards, make_card):
    seed_cards([make_card(id="a", set="tst", collector_number="1", name="Alpha")])
    inventory.inventory_add("a", "nonfoil", 2)


def _copies():
    with db.connect() as conn:
        return conn.execute("SELECT COALESCE(SUM(quantity),0) FROM inventory").fetchone()[0]


def _refused(res, flag):
    assert res.exit_code == interactive.EXIT_NEEDS_FLAG, res.output
    assert flag in res.output and "no terminal" in res.output
    assert "Aborted" not in res.output


def test_db_undo_restore_needs_yes(owned, app):
    undo.take("t")
    inventory.inventory_add("a", "nonfoil", 3)
    _refused(runner.invoke(app, ["db", "undo", "--restore"]), "--yes")
    assert _copies() == 5                         # nothing restored
    res = runner.invoke(app, ["db", "undo", "--restore", "--yes"])
    assert res.exit_code == 0, res.output and "restored" in res.output
    assert _copies() == 2


def test_db_unlock_needs_yes(tmp_db, app):
    with db.connect() as conn:
        conn.execute("SELECT 1")
    p = db.db_path()
    shm = p.with_name(p.name + "-shm")
    shm.write_bytes(b"")
    _refused(runner.invoke(app, ["db", "unlock"]), "--yes")
    assert shm.exists()
    res = runner.invoke(app, ["db", "unlock", "--yes"])
    assert res.exit_code == 0, res.output
    assert not shm.exists()


def test_analytics_forget_needs_yes(tmp_db, app, monkeypatch):
    from magic_manager import analytics
    monkeypatch.setattr(analytics, "forget_user", lambda: 0)
    _refused(runner.invoke(app, ["analytics", "forget"]), "--yes")
    res = runner.invoke(app, ["analytics", "forget", "--yes"])
    assert res.exit_code == 0 and "deleted 0 events" in res.output


def test_intake_refuses_off_terminal(tmp_db, app, monkeypatch):
    from magic_manager import cli, intake
    monkeypatch.setattr(cli, "_resolve_codes", lambda *a, **k: (object(), ["tst"]))
    monkeypatch.setattr(intake, "run_repl", lambda r: pytest.fail("REPL started"))
    res = runner.invoke(app, ["intake", "tst"])
    assert res.exit_code == interactive.EXIT_NEEDS_FLAG
    assert "inventory add-card" in res.output


def test_set_ingest_modify_needs_zero_untouched_choice(tmp_db, app, seed_cards, make_card,
                                                      tmp_path, monkeypatch):
    from magic_manager import sets
    seed_cards([make_card(id="a", set="tst", collector_number="1", name="Alpha")])
    monkeypatch.chdir(tmp_path)
    md = tmp_path / "checklists" / "tst-modify-checklist.md"
    md.parent.mkdir()
    md.write_text("- (TST) 1 [N:4 F:0] — card 1\n", encoding="utf-8")
    monkeypatch.setattr(sets, "read_master_list_meta",
                        lambda p: {"mode": "modify", "anchor_code": "tst", "set_codes": ["tst"]})
    seen = {}

    def fake_ingest(path, **kw):
        seen.update(kw)
        raise SystemExit(0)
    monkeypatch.setattr(sets, "ingest_inventory_from_xlsx", fake_ingest)

    _refused(runner.invoke(app, ["set", "ingest", "--path", str(md)]), "--no-zero-untouched")
    assert seen == {}                              # refused before any write
    res = runner.invoke(app, ["set", "ingest", "--path", str(md), "--no-zero-untouched"])
    assert seen.get("zero_untouched") is False, res.output


def test_confirm_asks_on_a_terminal(monkeypatch):
    monkeypatch.setattr(interactive, "is_interactive", lambda: True)
    import typer
    monkeypatch.setattr(typer, "confirm", lambda q, default=False: True)
    assert interactive.confirm("go?", flag="--yes") is True


def test_force_off_env(monkeypatch):
    monkeypatch.setenv("MM_NONINTERACTIVE", "1")
    assert not interactive.is_interactive()
    assert not interactive.can_wait_for_enter()
    with pytest.raises(SystemExit) as e:
        interactive.wait_for_enter("press Enter", alternative="use X")
    assert e.value.code == interactive.EXIT_NEEDS_FLAG


def test_deck_fetcher_runs_without_a_terminal(monkeypatch):
    """The web app's deck import spawns import_deck.py with no stdin and
    MM_NONINTERACTIVE, so a manual Moxfield login fails fast."""
    import subprocess
    from magic_manager import addcards
    seen = {}

    class P:
        returncode = 0
        stdout = __import__("io").StringIO('{"cards": []}')
        stderr = __import__("io").StringIO("")

        def wait(self):
            return 0

    def popen(cmd, **kw):
        seen.update(kw)
        return P()
    monkeypatch.setattr(subprocess, "Popen", popen)
    addcards.fetch_deck_payload("https://moxfield.com/decks/x")
    assert seen["stdin"] is subprocess.DEVNULL
    assert seen["env"]["MM_NONINTERACTIVE"] == "1"


_PROMPT = re.compile(r"\b(typer|click)\.(confirm|prompt)\(|(?<![\w.])input\(|getpass\(")
_ALLOWED = {
    "src/magic_manager/interactive.py",     # the one helper
    "src/magic_manager/intake.py",          # the REPL (cli refuses it off a terminal)
}


def test_no_prompt_bypasses_the_helper():
    """New prompts must go through magic_manager.interactive (flag + fail fast)."""
    offenders = []
    for base in ("src", "scripts"):
        for p in (ROOT / base).rglob("*.py"):
            rel = p.relative_to(ROOT).as_posix()
            if rel in _ALLOWED:
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("#", 1)[0]
                if _PROMPT.search(code):
                    offenders.append(f"{rel}:{i}: {line.strip()}")
    assert offenders == [], "route prompts through magic_manager.interactive:\n" + "\n".join(offenders)

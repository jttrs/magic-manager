"""scripts/pr_review.py: the pre-merge review stamp (CLAUDE.md rule 4)."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "pr_review.py"
spec = importlib.util.spec_from_file_location("pr_review", SCRIPT)
pr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pr)


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path, monkeypatch):
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "README.md").write_text("hi\n")
    _git(tmp_path, "add", "."); _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "checkout", "-qb", "feat")
    (tmp_path / "a.py").write_text("x = 2\n")
    _git(tmp_path, "commit", "-qam", "change")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _stamp(capsys):
    class A: base, head, fixed, deferred, refuted = "main", "HEAD", 1, 0, 2
    pr.stamp(A)
    return capsys.readouterr().out


def _check(body, tmp_path):
    f = tmp_path / "body.md"; f.write_text(body)
    class A: pr, body_file, base, head = None, str(f), "main", "HEAD"
    return pr.check(A)


def test_stamp_passes_and_survives_a_clean_rebase(repo, capsys):
    body = _stamp(capsys)
    assert "`/ce-code-review`: run" in body and "fixed 1 · deferred 0 · refuted 2" in body
    assert _check(body, repo) == 0
    _git(repo, "checkout", "-q", "main"); (repo / "b.py").write_text("y = 1\n")
    _git(repo, "add", "."); _git(repo, "commit", "-qm", "main moves")
    _git(repo, "checkout", "-q", "feat"); _git(repo, "rebase", "-q", "main")
    assert _check(body, repo) == 0


def test_new_code_after_review_needs_a_fresh_stamp(repo, capsys):
    body = _stamp(capsys)
    (repo / "a.py").write_text("x = 3\n"); _git(repo, "commit", "-qam", "more")
    assert _check(body, repo) == 1
    assert "different code" in capsys.readouterr().out


def test_generated_files_do_not_change_the_fingerprint(repo, capsys):
    body = _stamp(capsys)
    (repo / "web/src/core/api").mkdir(parents=True)
    (repo / "web/src/core/api/types.gen.ts").write_text("// regen\n")
    _git(repo, "add", "."); _git(repo, "commit", "-qm", "Regenerate API client")
    assert _check(body, repo) == 0


def test_missing_stamp_fails_and_docs_only_is_exempt(repo, capsys):
    assert _check("## What changes\nstuff\n", repo) == 1
    _git(repo, "checkout", "-q", "main"); _git(repo, "checkout", "-qb", "docs")
    (repo / "README.md").write_text("hello\n"); _git(repo, "commit", "-qam", "docs")
    assert _check("no stamp", repo) == 0

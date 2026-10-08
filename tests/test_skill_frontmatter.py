"""Skill/command/agent frontmatter must parse as STRICT YAML.

Copilot CLI rejects frontmatter Claude Code tolerates (an unquoted
``description:`` containing ``": "`` → "mapping values are not allowed"),
and an unquoted ``" #"`` silently truncates the value as a comment in both.
Quote such values (``description: "..."``) or use a folded block (``>-``).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
FILES = sorted(
    p
    for base in (ROOT / ".claude", ROOT / ".github")
    if base.is_dir()
    for p in base.rglob("*.md")
    if p.read_text(encoding="utf-8").startswith("---\n")
)


def _frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---", 4)
    assert end != -1, f"{path}: unterminated frontmatter"
    return text[4:end]


def test_frontmatter_files_found():
    assert any(p.name == "SKILL.md" for p in FILES)


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_frontmatter_is_strict_yaml(path: Path):
    fm = _frontmatter(path)
    try:
        data = yaml.safe_load(fm)
    except yaml.YAMLError as e:
        pytest.fail(f"{path.relative_to(ROOT)}: invalid YAML frontmatter — quote the value.\n{e}")
    assert isinstance(data, dict), f"{path.relative_to(ROOT)}: frontmatter is not a mapping"

    # A plain (unquoted) one-line scalar must round-trip verbatim; a ' #' comment would truncate it.
    for m in re.finditer(r"^([\w-]+): (.+)$", fm, re.M):
        key, raw = m.groups()
        if raw[:1] in "\"'>|[{&*!" or not isinstance(data.get(key), str):
            continue
        assert data[key] == raw.rstrip(), (
            f"{path.relative_to(ROOT)}: `{key}` is truncated/altered by YAML (e.g. ' #' starts a comment) — quote it."
        )

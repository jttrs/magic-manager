"""Credentials: the process environment first, else the gitignored repo-root ``.env``.

Your own Mana Pool login (``PERSONAL``, used only to read YOUR cart) lives in ``.env``
alongside the service credentials — kept in a plain file for transparency (owner
decision 2026-10-11). ``.env`` is gitignored; never commit or log its values. Python
does not load ``.env`` into ``os.environ``, so ``get`` reads the file itself.

``.env`` format: simple ``KEY=VALUE`` lines; blanks and ``#`` comments are ignored, an
optional leading ``export `` is allowed, matching surrounding quotes are stripped, and
the first match wins. ``get`` is the only place a value is returned — ``source`` reports
where a name comes from, never its value.
"""
from __future__ import annotations

import os
from pathlib import Path

# This file is at src/magic_manager/secrets.py, so parents[2] is the repo root.
ROOT = Path(__file__).resolve().parents[2]

# Your own Mana Pool login — used only to read your cart.
PERSONAL = ("MANAPOOL_EMAIL", "MANAPOOL_PASSWORD")


def _dotenv_get(name: str) -> str | None:
    try:
        text = (ROOT / ".env").read_text()
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        if not sep or key.strip() != name:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        return value or None
    return None


def get(name: str) -> str | None:
    """The environment value if set and non-empty, else the ``.env`` value, else None."""
    return os.environ.get(name) or _dotenv_get(name)


def source(name: str) -> str | None:
    """Where ``get(name)`` comes from: ``"environment"``, ``".env"`` or None. Never the value."""
    if os.environ.get(name):
        return "environment"
    return ".env" if _dotenv_get(name) else None

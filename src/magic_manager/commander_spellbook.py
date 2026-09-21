"""Thin Python wrapper over the project's spellbook.sh script.

Every Commander Spellbook HTTP request in this codebase MUST go through
spellbook.sh — it paces requests (~80/min), caches responses for 24h, and
backs off 35s after an HTTP 429. A PreToolUse hook blocks any direct ``curl
backend.commanderspellbook.com``. Don't reimplement HTTP here; just shell out.

This module is network I/O behind the wrapper + guard. The offline test
suite monkeypatches THIS module (mirroring the ``fake_scryfall`` /
``fake_mtgjson`` conftest fixtures) so `brackets.py` and its callers never
touch the network in tests.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

WRAPPER = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "commander-spellbook" / "spellbook.sh"
)


class CommanderSpellbookError(RuntimeError):
    """Raised when the wrapper exits non-zero or the API returns an error object."""


def _run(args: list[str], stdin: str | None = None) -> dict:
    if not WRAPPER.exists():
        raise CommanderSpellbookError(f"wrapper missing: {WRAPPER}")
    res = subprocess.run(
        [str(WRAPPER), *args],
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )
    if res.returncode != 0:
        raise CommanderSpellbookError(
            f"spellbook.sh {' '.join(args)} exited {res.returncode}: "
            f"{res.stderr.strip() or res.stdout.strip()}"
        )
    try:
        body = json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise CommanderSpellbookError(f"non-JSON response from spellbook.sh: {e}") from e
    if isinstance(body, dict) and body.get("object") == "error":
        raise CommanderSpellbookError(f"Commander Spellbook error: {body.get('details') or body}")
    return body


def _decklist_body(*, commander: list[str] | None, main: list[str] | None) -> dict:
    """Build the shared request-body shape for /find-my-combos and /estimate-bracket.

    Best-effort against the documented Commander Spellbook API: a
    ``commanders`` list and a ``main`` list of card NAMES. Centralized here so
    a shape fix (if the real API disagrees) is a one-line change.
    """
    return {
        "commanders": list(commander or []),
        "main": list(main or []),
    }


def find_my_combos(*, commander: list[str] | None = None, main: list[str] | None = None) -> dict:
    """POST /find-my-combos — combos findable in a decklist.

    ``commander`` and ``main`` are card NAMES (commander-board and
    main-board respectively). Network I/O behind spellbook.sh; raises
    ``CommanderSpellbookError`` on failure. Callers (e.g. ``brackets.suggest``)
    should wrap this in a try/except — the network may be unavailable.
    """
    body = _decklist_body(commander=commander, main=main)
    return _run(["find-my-combos"], stdin=json.dumps(body))


def estimate_bracket(*, commander: list[str] | None = None, main: list[str] | None = None) -> dict:
    """POST /estimate-bracket — Commander Spellbook's own bracket estimate.

    Same request-body shape as ``find_my_combos``. Network I/O behind
    spellbook.sh; raises ``CommanderSpellbookError`` on failure.
    """
    body = _decklist_body(commander=commander, main=main)
    return _run(["estimate-bracket"], stdin=json.dumps(body))

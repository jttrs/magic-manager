"""Thin Python wrapper over the project's mtgjson.sh script.

Every MTGJSON HTTP request in this codebase goes through mtgjson.sh — it
content-addresses the cache (one file per resource path) and offers
opt-in staleness checks via the published `.sha256` sidecars. A PreToolUse
hook blocks any direct ``curl mtgjson.com``.

Cache strategy:
- Per-deck files: cache forever (precon decklists are immutable).
- Per-set files / DeckList: cache until refreshed; check ``is_stale()`` on demand.
- Meta: small enough to fetch on every probe.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable

WRAPPER = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "mtgjson-search" / "mtgjson.sh"
)


class MtgJsonError(RuntimeError):
    """Raised when the wrapper exits non-zero or returns non-JSON."""


def _run(args: list[str]) -> str:
    if not WRAPPER.exists():
        raise MtgJsonError(f"wrapper missing: {WRAPPER}")
    res = subprocess.run(
        [str(WRAPPER), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if res.returncode != 0:
        raise MtgJsonError(
            f"mtgjson.sh {' '.join(args)} exited {res.returncode}: "
            f"{res.stderr.strip() or res.stdout.strip()}"
        )
    return res.stdout


def _run_json(args: list[str]) -> dict:
    out = _run(args)
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise MtgJsonError(f"non-JSON response from mtgjson.sh {args}: {e}") from e


# ---------- single-file resources ----------

def meta() -> dict:
    """Return the inner ``data`` block of Meta.json: ``{date, version}``."""
    body = _run_json(["meta"])
    return body.get("data", {})


def set_list() -> list[dict]:
    """Return SetList.json's ``data`` array — every set's metadata."""
    body = _run_json(["setlist"])
    return body.get("data", [])


def set_file(set_code: str) -> dict:
    """Return ``<SETCODE>.json``'s ``data`` block — full set + every printing."""
    body = _run_json(["set", set_code])
    return body.get("data", {})


def deck(file_name: str) -> dict:
    """Return ``decks/<file_name>.json``'s ``data`` block.

    ``file_name`` is the MTGJSON deck filename (e.g. ``CounterBlitzFinalFantasyX_FIC``);
    the ``.json`` suffix is optional. Cached forever — precon decks don't change.
    """
    body = _run_json(["deck", file_name])
    return body.get("data", {})


def deck_list(*, set_code: str | None = None) -> list[dict]:
    """Return DeckList.json's ``data`` array, optionally filtered to ``set_code``.

    Each entry: ``{code, fileName, name, releaseDate, type}``. The
    ``set_code`` filter is case-insensitive and matches MTGJSON's uppercase
    ``code`` field.
    """
    body = _run_json(["decklist"])
    rows = body.get("data", [])
    if set_code is not None:
        wanted = set_code.upper()
        rows = [r for r in rows if r.get("code") == wanted]
    return rows


# ---------- staleness + cache management ----------

def is_stale(resource_path: str) -> bool:
    """True if the cached SHA-256 for ``resource_path`` differs from MTGJSON's
    published ``.sha256`` sidecar. False if it matches. Raises if the resource
    isn't cached yet (use ``set_file()`` etc. to populate the cache first).

    ``resource_path`` is the path under ``/api/v5/`` (e.g. ``"FIC.json"``,
    ``"DeckList.json"``, ``"decks/CounterBlitzFinalFantasyX_FIC.json"``).
    """
    out = _run(["check-stale", resource_path]).strip()
    if out == "fresh":
        return False
    if out == "stale":
        return True
    if out == "absent":
        raise MtgJsonError(f"{resource_path} is not cached; fetch it first")
    raise MtgJsonError(f"unexpected check-stale output: {out!r}")


def refresh(resource_path: str) -> None:
    """Delete the cached copy of ``resource_path`` so the next fetch re-downloads."""
    _run(["refresh", resource_path])


# ---------- helpers for the precon-attribution use case ----------

def deck_card_scryfall_ids(deck_data: dict, *, boards: Iterable[str] = ("mainBoard", "sideBoard", "commander")) -> list[str]:
    """Pull every ``identifiers.scryfallId`` from the requested boards of a deck.

    This is the bridge from MTGJSON's UUID-keyed world back to our
    ``cards.scryfall_id`` PK. Returns IDs in deck order (main, then side,
    then commander by default). Tokens are excluded by default — pass
    ``boards=("tokens",)`` if you want them.
    """
    ids: list[str] = []
    for board in boards:
        for card in deck_data.get(board) or []:
            sid = (card.get("identifiers") or {}).get("scryfallId")
            if sid:
                ids.append(sid)
    return ids

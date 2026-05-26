"""Thin Python wrapper over the project's scryfall.sh script.

Every Scryfall HTTP request in this codebase MUST go through scryfall.sh — it
enforces the 500ms /cards/* rate limit, caches responses for 24h, and backs off
35s after an HTTP 429. A PreToolUse hook blocks any direct ``curl
api.scryfall.com``. Don't reimplement HTTP here; just shell out.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Iterable, Iterator
from urllib.parse import urlparse

WRAPPER = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "scryfall-search" / "scryfall.sh"
)


class ScryfallError(RuntimeError):
    """Raised when the wrapper exits non-zero or the API returns an error object."""


def _run(args: list[str], stdin: str | None = None) -> dict:
    if not WRAPPER.exists():
        raise ScryfallError(f"wrapper missing: {WRAPPER}")
    res = subprocess.run(
        [str(WRAPPER), *args],
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )
    if res.returncode != 0:
        raise ScryfallError(
            f"scryfall.sh {' '.join(args)} exited {res.returncode}: "
            f"{res.stderr.strip() or res.stdout.strip()}"
        )
    try:
        body = json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise ScryfallError(f"non-JSON response from scryfall.sh: {e}") from e
    if isinstance(body, dict) and body.get("object") == "error":
        raise ScryfallError(f"Scryfall error: {body.get('details') or body}")
    return body


# ---------- search (paginated) ----------

def search(query: str, **params: str) -> Iterator[dict]:
    """Yield every card row matching ``query``, transparently paginating.

    ``params`` are extra query-string keys the wrapper accepts (``order``,
    ``unique``, ``dir``, ``page``).
    """
    args = ["search", query]
    for k, v in params.items():
        args.append(f"{k}={v}")
    page = _run(args)
    yield from page.get("data", [])
    while page.get("has_more") and page.get("next_page"):
        page = _follow(page["next_page"])
        yield from page.get("data", [])


def _follow(next_page_url: str) -> dict:
    parsed = urlparse(next_page_url)
    if parsed.netloc != "api.scryfall.com":
        raise ScryfallError(f"unexpected next_page host: {parsed.netloc}")
    return _run(["raw", parsed.path, parsed.query])


# ---------- single-resource lookups ----------

def named(exact_name: str) -> dict:
    return _run(["named", exact_name])


def get_set(set_code: str) -> dict:
    """GET /sets/<code>."""
    return _run(["raw", f"/sets/{set_code.lower()}", ""])


def all_sets() -> list[dict]:
    """GET /sets — full list of every Magic set Scryfall knows about."""
    body = _run(["raw", "/sets", ""])
    return body.get("data", [])


# ---------- bulk identifier lookup ----------

def collection(identifiers: Iterable[dict]) -> tuple[list[dict], list[dict]]:
    """POST /cards/collection in batches of 75. Returns (found, not_found).

    Each ``identifier`` is one of ``{"name": ...}``, ``{"name": ..., "set": ...}``,
    ``{"set": ..., "collector_number": ...}``, or ``{"id": ...}``.
    """
    ids = list(identifiers)
    found: list[dict] = []
    not_found: list[dict] = []
    for i in range(0, len(ids), 75):
        body = json.dumps({"identifiers": ids[i : i + 75]})
        page = _run(["collection"], stdin=body)
        found.extend(page.get("data", []))
        not_found.extend(page.get("not_found", []))
    return found, not_found

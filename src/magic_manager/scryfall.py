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
import time
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



def bulk_file(bulk_type: str, *, refresh: bool = False) -> Path:
    """Local path of a Scryfall bulk-data file (e.g. ``oracle_tags``).

    Delegates to ``scryfall.sh bulk`` — it resolves the type via the cached
    ``/bulk-data`` listing (24h TTL), downloads the daily file from
    ``data.scryfall.io`` once, and prints the cached path. ``refresh`` bypasses
    the listing cache (a new daily file is fetched only if Scryfall published one).
    """
    if not WRAPPER.exists():
        raise ScryfallError(f"wrapper missing: {WRAPPER}")
    args = [str(WRAPPER), "bulk", bulk_type] + (["--refresh"] if refresh else [])
    res = subprocess.run(args, text=True, capture_output=True, check=False)
    if res.returncode != 0:
        raise ScryfallError(
            f"scryfall.sh bulk {bulk_type} exited {res.returncode}: "
            f"{res.stderr.strip() or res.stdout.strip()}"
        )
    path = Path(res.stdout.strip().splitlines()[-1]) if res.stdout.strip() else None
    if path is None or not path.exists():
        raise ScryfallError(f"scryfall.sh bulk {bulk_type} returned no file")
    return path

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


def search_total(query: str, **params: str) -> int:
    """How many cards match ``query`` (first page's ``total_cards``; 0 when none)."""
    args = ["search", query, *(f"{k}={v}" for k, v in params.items())]
    try:
        return int(_run(args).get("total_cards") or 0)
    except ScryfallError as e:
        if "HTTP 404" in str(e):
            return 0
        raise


def _follow(next_page_url: str) -> dict:
    parsed = urlparse(next_page_url)
    if parsed.netloc != "api.scryfall.com":
        raise ScryfallError(f"unexpected next_page host: {parsed.netloc}")
    return _run(["raw", parsed.path, parsed.query])


# ---------- single-resource lookups ----------

def named(exact_name: str) -> dict:
    return _run(["named", exact_name])


def random_card(query: str = "") -> dict | None:
    """GET /cards/random?q= — one random printing matching ``query`` (never
    cached by the wrapper). ``None`` when nothing matches (Scryfall's 404)."""
    try:
        return _run(["random", query])
    except ScryfallError as e:
        if "HTTP 404" in str(e) or "0 cards matched" in str(e):
            return None
        raise


def get_set(set_code: str) -> dict:
    """GET /sets/<code>."""
    return _run(["raw", f"/sets/{set_code.lower()}", ""])


_ALL_SETS_TTL_S = 300.0
_all_sets_memo: tuple[float, list[dict]] | None = None


def all_sets() -> list[dict]:
    """GET /sets — full list of every Magic set Scryfall knows about.

    The wrapper already caches the response on disk for 24h, but every call
    still spawns it and re-parses ~1000 sets; `sets.resolve` runs once per set
    code, so family listing paid that ~90×. Memoized in-process for a few
    minutes (callers must not mutate the returned list)."""
    global _all_sets_memo
    now = time.monotonic()
    if _all_sets_memo is not None and now - _all_sets_memo[0] < _ALL_SETS_TTL_S:
        return _all_sets_memo[1]
    body = _run(["raw", "/sets", ""])
    data = body.get("data", [])
    _all_sets_memo = (now, data)
    return data


def deck_export(deck_id: str) -> dict:
    """GET /decks/<id>/export/json — a public, anonymous deck export.

    Returns the ``object:"deck"`` payload: ``name``/``format`` plus ``entries``
    keyed by section (commanders/nonlands/lands/maybeboard/outside), each a
    ``deck_entry`` carrying ``count``, ``finish``, and a nested ``card_digest``
    (id/set/collector_number/name) for full printing fidelity. This ``export/*``
    sub-route is public even though the bare ``/decks/<id>`` route is auth-gated;
    it is undocumented, so ``decksource.parse_scryfall`` localizes the shape.
    """
    return _run(["raw", f"/decks/{deck_id}/export/json", ""])


# ---------- bulk identifier lookup ----------

def collection(identifiers: Iterable[dict]) -> tuple[list[dict], list[dict]]:
    """POST /cards/collection in batches of 75. Returns (found, not_found).

    Each ``identifier`` is one of ``{"name": ...}``, ``{"name": ..., "set": ...}``,
    ``{"set": ..., "collector_number": ...}``, or ``{"id": ...}``.

    **Error-tolerant.** Scryfall returns a clean ``not_found`` list for identifiers
    it can't match, but HTTP 400s the WHOLE request when one is MALFORMED (e.g. a
    non-existent set code — ``prm-wpn`` and other pseudo-sets). A single bad
    identifier must not sink the batch, so a page that raises :class:`ScryfallError`
    is BISECTED to isolate the offender: it splits and recurses until a singleton
    still errors, and that lone identifier is folded into ``not_found`` (semantics:
    Scryfall couldn't resolve it). Every caller of this shared seam — deck import,
    collection sync, EV, price checks — gets this tolerance for free.
    """
    ids = list(identifiers)
    found: list[dict] = []
    not_found: list[dict] = []
    for i in range(0, len(ids), 75):
        f, nf = _collection_page(ids[i : i + 75])
        found.extend(f)
        not_found.extend(nf)
    return found, not_found


def _collection_page(ids: list[dict]) -> tuple[list[dict], list[dict]]:
    """One ≤75 /cards/collection call, bisecting on a hard error to quarantine a
    malformed identifier. Returns ``(found, not_found)`` for this page."""
    if not ids:
        return [], []
    try:
        page = _run(["collection"], stdin=json.dumps({"identifiers": ids}))
        return page.get("data", []), page.get("not_found", [])
    except ScryfallError:
        if len(ids) == 1:
            return [], [ids[0]]  # this lone identifier is the malformed one
        mid = len(ids) // 2
        lf, lnf = _collection_page(ids[:mid])
        rf, rnf = _collection_page(ids[mid:])
        return lf + rf, lnf + rnf


def resolve_identifiers(
    id_idents: list[dict],
    setcn_idents: list[dict],
    name_idents: list[dict] | tuple = (),
) -> tuple[dict, dict, dict, list[str]]:
    """Batch-resolve pre-built identifier tiers and index the matches.

    The shared resolution core behind ``decksource._resolve_cards`` and
    ``collection_sync.resolve_rows`` (both built this inline before): runs each
    non-empty tier through the 400-tolerant :func:`collection`, folds every
    ``not_found`` into warnings, and builds the three lookup indexes callers match
    against — ``by_sid`` (``id`` → card), ``by_setcn`` (``(set.lower(), cn)`` →
    card), and ``by_name`` (lowercased oracle name AND the front face of a split/
    DFC ``"A // B" → "A"`` → card). TIER-BUILDING stays with the caller (it
    legitimately differs: decksource submits a name tier, collection_sync does
    not, and each decides whether an id-bearing row also contributes a (set,cn)
    fallback), so this helper owns only the duplicated batch+index step.
    """
    warnings: list[str] = []
    found: list[dict] = []
    for idents in (id_idents, setcn_idents, list(name_idents)):
        if not idents:
            continue
        got, not_found = collection(idents)
        found.extend(got)
        for nf in not_found:
            warnings.append(f"scryfall could not resolve identifier {nf!r}")

    by_sid = {c["id"]: c for c in found if c.get("id")}
    by_setcn = {
        ((c.get("set") or "").lower(), str(c.get("collector_number") or "")): c
        for c in found
    }
    by_name: dict[str, dict] = {}
    for c in found:
        nm = (c.get("name") or "").lower()
        if nm:
            by_name.setdefault(nm, c)
            by_name.setdefault(nm.split(" // ")[0], c)
    return by_sid, by_setcn, by_name, warnings

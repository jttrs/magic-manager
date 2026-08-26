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


def jumpstart_variants(set_code: str) -> list[dict]:
    """DeckList entries for a set's Jumpstart pack variants.

    Filter of ``deck_list(set_code=...)`` to ``type == 'Jumpstart'``. Sets
    like TLE/J25/JMP/J22 publish 50+ variants; sets without Jumpstart product
    return ``[]``.
    """
    return [d for d in deck_list(set_code=set_code) if d.get("type") == "Jumpstart"]


# Deck ``type`` values that have their OWN dedicated workflow (Jumpstart →
# `mm set jumpstart-list`; Secret Lair Drop → the `bulk-add` skill) or are
# digital-only (``MTGO *``). They never belong in a physical-precon checklist.
PRECON_EXCLUDED_TYPES: frozenset[str] = frozenset({"Jumpstart", "Secret Lair Drop"})

# The default "precon" scope: the constructed preconstructed-deck product a
# collector actually tracks — Commander decks, box/duel/planeswalker/starter
# decks, and the beginner intro/welcome/starter lines (which ship as themed
# constructed decks, one per color or color-pair). Deliberately excludes
# non-deck / digital-adjacent product lines (Deck Builder's Toolkit, Sample
# Deck, Arena Starter Deck, Welcome Booster, Shandalar/World Championship, …)
# and everything ``--all-physical`` (``types=None``) still reaches.
#
# NOTE: this is the one knob that decides what "counts" as a precon. When the
# user says a product line is missing, the fix is almost always adding its
# exact MTGJSON ``type`` string here (see `mm mtgjson decks` / DeckList types).
PRECON_MODERN_TYPES: frozenset[str] = frozenset({
    "Commander Deck",
    "Box Set",
    "Duel Deck",
    "Planeswalker Deck",
    "Starter Kit",
    "Starter Deck",
    "Spellslinger Starter Kit",
    "Welcome Deck",
    "Intro Pack",
    "Challenger Deck",
    "Pioneer Challenger Deck",
    "Guild Kit",
    "Brawl Deck",
    "Clash Pack",
    "Game Night Deck",
    "Archenemy Deck",
    "Planechase Deck",
})


def _is_collector_edition(name: str) -> bool:
    """True if a deck name marks a Collector's Edition product.

    Catches both the modern premium-variant twins (``… Collector's Edition``,
    e.g. ``Counter Blitz Collector's Edition``) and the 1993 standalone box
    sets whose apostrophe sits differently (``Collectors' Edition``,
    ``Intl. Collectors' Edition``). All are premium/collector product the
    collection doesn't track.
    """
    return "collector's edition" in name.lower() or "collectors' edition" in name.lower()


def precon_variants(
    set_code: str | None = None,
    *,
    only_type: str | None = None,
    types: frozenset[str] | set[str] | None = PRECON_MODERN_TYPES,
    include_collector: bool = False,
) -> list[dict]:
    """DeckList entries for physical preconstructed-deck products.

    Filter of ``deck_list(set_code=...)`` that keeps physical sealed products
    while dropping the types with their own workflow (``PRECON_EXCLUDED_TYPES``)
    and the digital ``MTGO *`` types. ``set_code=None`` (the default) spans
    **every** set — the precon catalog is global, not per-set (there are only a
    handful of precons per set, so a per-set file would be pointless).

    Scope of ``type`` values, in precedence order:
      - ``only_type`` set → keep only that exact type (e.g. ``"Commander
        Deck"``); overrides ``types``.
      - else ``types`` set → keep types in that allow-set (default
        ``PRECON_MODERN_TYPES``).
      - ``types=None`` → keep every physical type (the ``--all-physical`` mode).

    ``include_collector=False`` (the default) drops the ``… Collector's
    Edition`` twins MTGJSON ships alongside the standard decks — the user
    doesn't collect those. Returns ``[]`` when nothing matches.
    """
    out: list[dict] = []
    for d in deck_list(set_code=set_code):
        t = d.get("type") or ""
        if t in PRECON_EXCLUDED_TYPES or t.startswith("MTGO"):
            continue
        if only_type is not None:
            if t != only_type:
                continue
        elif types is not None and t not in types:
            continue
        if not include_collector and _is_collector_edition(d.get("name") or ""):
            continue
        out.append(d)
    return out


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

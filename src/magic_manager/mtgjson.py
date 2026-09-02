"""Thin Python wrapper over the project's mtgjson.sh script.

Every MTGJSON HTTP request in this codebase goes through mtgjson.sh — it
content-addresses the cache (one file per resource path) and offers
opt-in staleness checks via the published `.sha256` sidecars. A PreToolUse
hook blocks any direct ``curl mtgjson.com``.

Cache strategy:
- Per-deck files: cache forever (precon decklists are immutable).
- Per-set files / DeckList: cache until refreshed; check ``is_stale()`` on demand.
- Meta: small enough to fetch on every probe.

Product membership vs. deck ``type`` — READ THIS BEFORE ANSWERING "what's in
product X". A per-set file (``<CODE>.json``) carries THREE arrays: ``cards[]``,
``decks[]``, and ``sealedProduct[]``. The **authoritative** "which decks/cards
ship in a given SKU" mapping lives ONLY in ``sealedProduct[].contents`` (see
``sealed_products`` / ``sealed_product_decks``). A deck's ``type`` field
(``"Jumpstart"``, ``"Box Set"``, …) describes its FORMAT FLAVOR, NOT which
product it shipped in — e.g. the Foundations Beginner Box's 10 decks are typed
``"Jumpstart"`` while the Avatar (TLA) Beginner Box's are typed ``"Box Set"``.
Never conclude "no decklist exists" for a product from the ``DeckList`` ``type``
field or from a product's absence in a per-set ``DeckList`` scan; check
``sealedProduct`` first.
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
    """Return ``<SETCODE>.json``'s ``data`` block.

    The block carries three arrays worth knowing:
      - ``cards[]``          — every printing in the set.
      - ``decks[]``          — decklists filed under this set code.
      - ``sealedProduct[]``  — the physical SKUs (Beginner Box, Bundle, Scene
        Box, booster boxes, …). Each has ``name``, ``category``, ``subtype``,
        ``cardCount``, and ``contents`` (``deck[]`` / ``sealed[]`` / ``other[]``
        / ``card[]`` / ``pack[]``). This is the AUTHORITATIVE product → contents
        mapping — see ``sealed_products`` / ``sealed_product_decks``. Do NOT
        infer product membership from a deck's ``type`` field.
    """
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


def sealed_products(set_code: str, *, category: str | None = None,
                    subtype: str | None = None) -> list[dict]:
    """The ``sealedProduct[]`` array from ``<set_code>.json`` — the physical SKUs.

    Each entry: ``{name, category, subtype, cardCount, contents{...},
    identifiers, purchaseUrls, releaseDate, uuid}``. This is the AUTHORITATIVE
    record of what a product contains — the ONLY place that says which decks a
    Beginner Box / Bundle / Scene Box actually ships. Optionally filter by
    ``category`` (e.g. ``"box_set"``, ``"bundle"``, ``"deck"``) and/or
    ``subtype`` (e.g. ``"starter_deck"``), both matched case-insensitively.

    Returns ``[]`` for sets with no sealed-product data.
    """
    products = set_file(set_code).get("sealedProduct") or []
    cat = category.lower() if category else None
    sub = subtype.lower() if subtype else None
    out = []
    for p in products:
        if cat is not None and (p.get("category") or "").lower() != cat:
            continue
        if sub is not None and (p.get("subtype") or "").lower() != sub:
            continue
        out.append(p)
    return out


def sealed_product_deck_refs(set_code: str, product_name: str) -> dict:
    """Resolve one sealed product's component decks, reporting completeness.

    Like :func:`sealed_product_decks`, but distinguishes decks that resolved to
    a DeckList entry from ``contents.deck`` refs that did NOT — so a caller can
    tell a fully-resolved box from a partial one (some refs unmatched) and from
    a genuinely deckless product (no ``contents.deck`` at all). Returns::

        {"resolved":   list[dict],   # matched DeckList entries {code,fileName,name,type,…}
         "unresolved": list[dict],   # contents.deck refs {name,set} with NO DeckList match
         "has_deck_contents": bool}  # whether contents.deck was non-empty

    Membership comes from ``contents.deck``, NOT the deck ``type`` (see
    :func:`sealed_product_decks`). Raises ``LookupError`` if no product matches
    ``product_name``.
    """
    products = set_file(set_code).get("sealedProduct") or []
    want = product_name.strip().lower()
    match = next((p for p in products if (p.get("name") or "").lower() == want), None)
    if match is None:
        # Fall back to substring so callers don't need the exact SKU name.
        cands = [p for p in products if want in (p.get("name") or "").lower()]
        if len(cands) == 1:
            match = cands[0]
    if match is None:
        available = ", ".join(sorted(p.get("name", "?") for p in products)) or "(none)"
        raise LookupError(
            f"no sealedProduct named {product_name!r} in {set_code.upper()}; "
            f"available: {available}"
        )
    deck_refs = (match.get("contents") or {}).get("deck") or []
    # Index this set's DeckList by (deck-name-lower, set-code-lower) so we can
    # resolve each contents.deck {name, set} ref to its full entry + fileName.
    # contents.deck refs can point at a different set code than the product's
    # (rare), so index the referenced sets, not just set_code.
    ref_codes = {(r.get("set") or set_code).upper() for r in deck_refs}
    by_key: dict[tuple[str, str], dict] = {}
    for code in ref_codes:
        for entry in deck_list(set_code=code):
            by_key[((entry.get("name") or "").lower(), (entry.get("code") or "").lower())] = entry
    resolved, unresolved = [], []
    for r in deck_refs:
        key = ((r.get("name") or "").lower(), (r.get("set") or set_code).lower())
        entry = by_key.get(key)
        if entry is not None:
            resolved.append(entry)
        else:
            unresolved.append(r)
    return {
        "resolved": resolved,
        "unresolved": unresolved,
        "has_deck_contents": bool(deck_refs),
    }


def sealed_product_decks(set_code: str, product_name: str) -> list[dict]:
    """Resolve one sealed product's component decks to their DeckList entries.

    Finds the ``sealedProduct`` named ``product_name`` (case-insensitive) in
    ``set_code``'s file, reads its ``contents.deck`` (each ``{name, set}``), and
    matches those against ``deck_list()`` to return the full DeckList entries
    (``{code, fileName, name, releaseDate, type}``) — so a caller can
    ``deck(entry["fileName"])`` each to get card-by-card lists.

    Membership comes from ``contents.deck``, NOT the deck ``type``: this returns
    the FDN Beginner Box's 10 decks (typed ``"Jumpstart"`` in the DeckList) and
    the TLA Beginner Box's decks (typed ``"Box Set"``) identically. Raises
    ``LookupError`` if no product matches ``product_name``; returns ``[]`` if the
    product has no ``contents.deck`` (or if no refs resolved — use
    :func:`sealed_product_deck_refs` to tell those two cases apart).
    """
    return sealed_product_deck_refs(set_code, product_name)["resolved"]


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


# ---------- precon "pool" classification ----------
#
# Most precon products are playable decks (state 'built'). A few are card
# POOLS — never a playable deck, just a bunch of cards you build your own decks
# from (the Foundations Starter Collection, a 387-card library) or loose
# collectible cards (Scene Boxes, `booster: null`). Those should ingest as
# state 'pool' (cards → inventory, a marker deck row, no pledge), NOT as one
# giant "built" deck.
#
# Neither `type` nor `sealedProduct.subtype` distinguishes them (a "Box Set"
# spans 6→387 cards; Starter Collection and Beginner Box are both
# box_set/starter_deck). So classification is name-pattern + a card-count
# backstop. This is the single knob — when a new pool product appears, add its
# name substring here.
POOL_NAME_PATTERNS: frozenset[str] = frozenset({
    "scene box",
    "starter collection",
})

# A single deck this large isn't a playable deck — it's a build-your-own pool.
# Playable decks top out at 100 (Commander); the Starter Collection is 387.
POOL_CARD_COUNT_THRESHOLD = 150


def _deck_total_cards(deck_data: dict) -> int:
    """Total card count across a deck's playable boards (for pool detection)."""
    total = 0
    for board in ("commander", "mainBoard", "sideBoard"):
        for e in deck_data.get(board) or []:
            total += int(e.get("count", 1) or 1)
    return total


def _pool_named_product_decks(set_code: str) -> set[str]:
    """Lowercased names of every deck that a pool-named sealedProduct (Scene Box,
    Starter Collection, …) in ``set_code`` lists in its ``contents.deck``.

    A Scene Box's "pool" signal lives on the PRODUCT name, not the component
    deck's name (the deck is just "The Black Sun Invasion"), so we resolve
    membership through ``sealedProduct``.
    """
    out: set[str] = set()
    try:
        for p in sealed_products(set_code):
            pname = (p.get("name") or "").lower()
            if any(pat in pname for pat in POOL_NAME_PATTERNS):
                for e in (p.get("contents") or {}).get("deck") or []:
                    out.add((e.get("name") or "").lower())
    except Exception:
        pass
    return out


def default_precon_state(file_name: str, *, name: str | None = None) -> str:
    """Recommend the default ingest state for a precon: ``"pool"`` or ``"built"``.

    ``"deconstructed"`` is never a *default* — it's an explicit user action.
    A product is a pool if ANY of:
      1. its deck name matches ``POOL_NAME_PATTERNS`` (e.g. "Starter Collection");
      2. it's a component of a pool-named sealedProduct (e.g. a Scene Box's
         decks, whose "Scene Box" marker is on the PRODUCT name, not the deck);
      3. its single deck has an absurd-for-a-deck card count
         (> ``POOL_CARD_COUNT_THRESHOLD``) — the mechanical backstop.

    ``name`` (the deck display name) is used for test 1 if given; otherwise read
    from the deck file. Network-tolerant: MTGJSON failures degrade to whatever
    tests could run, then ``"built"``.
    """
    display = (name or "").lower()
    if not display:
        try:
            display = (deck(file_name).get("name") or "").lower()
        except Exception:
            display = ""
    if display and any(pat in display for pat in POOL_NAME_PATTERNS):
        return "pool"
    # Scene-Box-style: the deck is a component of a pool-named sealedProduct.
    # Derive the set code from the Words_CODE fileName suffix.
    if "_" in file_name and display:
        set_code = file_name.rsplit("_", 1)[1]
        if display in _pool_named_product_decks(set_code):
            return "pool"
    try:
        if _deck_total_cards(deck(file_name)) > POOL_CARD_COUNT_THRESHOLD:
            return "pool"
    except Exception:
        pass
    return "built"


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

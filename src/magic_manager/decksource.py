"""Read a deck from an external builder (Moxfield / Archidekt / MTGGoldfish) into
the local DB.

This is the **offline core**: source detection, per-source payload → normalized
cards, and the shared orchestrator that resolves those cards against Scryfall and
writes them to a deck. **No network fetch happens here** — the raw payload is
handed in already-fetched (by ``scripts/import_deck.py``, which owns the network
per the repo's sanctioned-wrapper rule). Scryfall resolution DOES go out, but only
through the rate-limited ``scryfall.collection`` wrapper that ``parsers.resolve``
already uses.

Normalized-card schema (the wire format between the fetch script and the CLI, and
the return type of every ``parse_*``): a plain ``dict`` with keys

    {
      "qty": int,                       # copies (>0)
      "board": str,                     # deck_cards vocab: main/side/commander/
                                        #   companion/maybe/token
      "finish": "foil" | "nonfoil",
      "scryfall_id": str | None,        # preferred resolution key when present
      "set": str | None,                # fallback resolution key (with cn)
      "collector_number": str | None,
      "name": str | None,               # informational / diagnostics
      "category": str | None,           # Archidekt category string (preserved)
    }

``parsers.Entry`` is intentionally NOT used as the carrier: it has no slot for a
pre-known ``scryfall_id`` or a ``board``, and Moxfield/Archidekt hand us the
Scryfall id directly. The dict schema above is the DRY seam instead.
"""

from __future__ import annotations

import html
import re
from typing import Literal
from urllib.parse import urlparse

from . import db, decks as decks_mod, scryfall

Source = Literal["moxfield", "archidekt", "mtggoldfish", "manabox", "scryfall"]

# ---------------------------------------------------------------------------
# Board vocab — the target is deck_cards' CHECK set (decks._ALLOWED_BOARDS):
#   main / side / commander / companion / maybe / token
# ---------------------------------------------------------------------------

# Moxfield v3 keys its ``boards`` dict by these names.
MOXFIELD_BOARD_MAP = {
    "mainboard": "main",
    "sideboard": "side",
    "maybeboard": "maybe",
    "commanders": "commander",
    "companions": "companion",
    "tokens": "token",
    # occasional singular / alt spellings — be forgiving
    "commander": "commander",
    "companion": "companion",
    "main": "main",
    "side": "side",
}

# Archidekt has no board field; membership is expressed via reserved CATEGORY
# names. Everything not in a reserved category is a mainboard card.
ARCHIDEKT_CATEGORY_BOARD_MAP = {
    "commander": "commander",
    "companion": "companion",
    "sideboard": "side",
    "maybeboard": "maybe",
    "tokens": "token",
    "token": "token",
}

_FOIL_MODIFIERS = {"foil", "etched"}

# ManaBox keys board membership by an integer ``boardCategory`` in its embedded
# payload. Observed on Commander decks: 0 = commander, 3 = mainboard. Codes for
# sideboard/companion/maybe are UNVERIFIED (only Commander decks were sampled);
# unknown codes fall back to "main" via the .get() default in parse_manabox — add
# a mapping here if a 60-card deck later surfaces a sideboard code.
MANABOX_BOARD_MAP = {
    0: "commander",
    3: "main",
}

# Scryfall's deck export keys entries by section name. commanders → commander,
# nonlands+lands → mainboard, maybeboard → maybe. The "outside" section is
# Scryfall's out-of-deck "considering" bucket (not part of the 100) and is
# SKIPPED — a section absent from this map is dropped, not defaulted to main, so
# `outside` cards don't leak into the deck.
SCRYFALL_SECTION_BOARD_MAP = {
    "commanders": "commander",
    "nonlands": "main",
    "lands": "main",
    "maybeboard": "maybe",
}


# ---------------------------------------------------------------------------
# Source detection
# ---------------------------------------------------------------------------

def source_of(url_or_id: str) -> Source:
    """Classify a deck URL by host. Raises ValueError if not one we support."""
    host = (urlparse(url_or_id).netloc or "").lower()
    if "moxfield.com" in host:
        return "moxfield"
    if "archidekt.com" in host:
        return "archidekt"
    if "mtggoldfish.com" in host:
        return "mtggoldfish"
    if "manabox.app" in host:
        return "manabox"
    if "scryfall.com" in host:
        return "scryfall"
    raise ValueError(
        f"unrecognized deck source in {url_or_id!r}; expected a moxfield.com / "
        f"archidekt.com / mtggoldfish.com / manabox.app / scryfall.com URL"
    )


def deck_id_from_url(url: str) -> str:
    """Extract the source-native deck id from a URL.

    Moxfield:    moxfield.com/decks/<publicId>[/anything]
    Archidekt:   archidekt.com/decks/<id>[-slug]
    MTGGoldfish: mtggoldfish.com/deck/<id>[#...]
    ManaBox:     manabox.app/decks/<base64url-id>
    Scryfall:    scryfall.com/@<user>/decks/<uuid>

    The id is the segment immediately AFTER the ``decks``/``deck`` marker (so a
    trailing ``/primer`` etc. doesn't get mistaken for the id, and Scryfall's
    ``@user`` segment before ``decks`` is ignored). ManaBox's base64url ids and
    Scryfall's uuids can contain ``-``/``_``; the Archidekt slug-strip below only
    fires when the head is all-digits, so those ids are returned intact.
    """
    parts = [p for p in urlparse(url).path.split("/") if p]
    if not parts:
        raise ValueError(f"no deck id found in {url!r}")
    seg = parts[-1]
    for i, p in enumerate(parts):
        if p.lower() in ("decks", "deck") and i + 1 < len(parts):
            seg = parts[i + 1]
            break
    # Archidekt appends a slug: "12345-my-deck" → the leading integer is the id.
    head = seg.split("-", 1)[0]
    return head if head.isdigit() else seg


# ---------------------------------------------------------------------------
# Per-source parsers → list[normalized-card dict]
# ---------------------------------------------------------------------------

def _norm(qty, board, finish, *, scryfall_id=None, set_code=None,
          collector_number=None, name=None, category=None) -> dict:
    return {
        "qty": int(qty),
        "board": board,
        "finish": finish,
        "scryfall_id": scryfall_id or None,
        "set": (set_code or None),
        "collector_number": (str(collector_number) if collector_number not in (None, "") else None),
        "name": name or None,
        "category": category or None,
    }


def _first(d: dict, *keys, default=None):
    """First present, non-None value among ``keys`` (defensive to shape drift)."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def parse_moxfield(data: dict) -> list[dict]:
    """Moxfield v3 deck JSON → normalized cards.

    Shape (observed / defensively handled): ``data["boards"]`` is a dict keyed by
    board name; each board has ``cards`` (a dict of entry-id → entry). Each entry
    carries ``quantity`` and a ``card`` object with ``scryfall_id``, ``set``,
    ``cn``/``collector_number``, and a foil signal (``isFoil`` on the entry, or
    ``finish`` on the card).
    """
    out: list[dict] = []
    boards = data.get("boards") or {}
    for board_name, board in boards.items():
        target = MOXFIELD_BOARD_MAP.get(str(board_name).lower())
        if target is None:
            continue  # unknown board (e.g. a UI-only bucket) — skip, don't guess
        entries = board.get("cards") if isinstance(board, dict) else None
        if not isinstance(entries, dict):
            continue
        for entry in entries.values():
            card = entry.get("card") or {}
            qty = _first(entry, "quantity", "qty", default=1)
            finish = _moxfield_finish(entry, card)
            out.append(_norm(
                qty, target, finish,
                scryfall_id=_first(card, "scryfall_id", "scryfallId", "id"),
                set_code=_first(card, "set", "setCode", "set_code"),
                collector_number=_first(card, "cn", "collector_number", "collectorNumber", "number"),
                name=_first(card, "name"),
            ))
    return out


def _moxfield_finish(entry: dict, card: dict) -> str:
    if entry.get("isFoil") or entry.get("foil"):
        return "foil"
    fin = str(_first(entry, "finish", default="") or _first(card, "finish", default="")).lower()
    return "foil" if fin in _FOIL_MODIFIERS else "nonfoil"


def parse_archidekt(data: dict) -> list[dict]:
    """Archidekt ``/api/decks/{id}/`` JSON → normalized cards.

    Shape: ``data["cards"]`` is a list; each item has ``quantity``, ``modifier``
    (Foil/Etched/Normal), ``categories`` (list of strings), and a ``card`` object
    with ``uid`` (Scryfall id), ``collectorNumber``, ``edition.editioncode``, and
    ``oracleCard.name``.
    """
    out: list[dict] = []
    for item in data.get("cards") or []:
        card = item.get("card") or {}
        edition = card.get("edition") or {}
        oracle = card.get("oracleCard") or {}
        qty = _first(item, "quantity", "qty", default=1)
        modifier = str(item.get("modifier") or "").lower()
        finish = "foil" if modifier in _FOIL_MODIFIERS else "nonfoil"
        board, category = _archidekt_board(item.get("categories") or [])
        out.append(_norm(
            qty, board, finish,
            scryfall_id=_first(card, "uid", "scryfallId", "scryfall_id"),
            set_code=_first(edition, "editioncode", "editionCode", "setCode", "set"),
            collector_number=_first(card, "collectorNumber", "collector_number", "cn"),
            name=_first(oracle, "name") or _first(card, "name"),
            category=category,
        ))
    return out


def _archidekt_board(categories: list) -> tuple[str, str | None]:
    """Map an Archidekt category list to (board, preserved_category_string).

    A reserved category (Commander/Sideboard/Maybeboard/…) picks the board;
    everything else is a mainboard card whose (first) category we preserve for
    reference. The first reserved match wins.
    """
    cats = [str(c) for c in categories if c]
    for c in cats:
        board = ARCHIDEKT_CATEGORY_BOARD_MAP.get(c.lower())
        if board is not None:
            return board, c
    return "main", (cats[0] if cats else None)


def parse_mtggoldfish(text: str) -> list[dict]:
    """MTGGoldfish ``/deck/download/{id}`` text → normalized cards.

    The download endpoint returns the ``<qty> Name (SET) CN`` block every builder
    converges on, so we delegate to the existing ``parsers.parse_text`` rather
    than write a new parser, then lift each Entry into the normalized schema.
    Section headers (Sideboard:, Commander:) are honored via Entry.section.
    """
    from . import parsers as _parsers

    result = _parsers.parse_text(text)
    section_to_board = {
        "mainboard": "main", "sideboard": "side", "commander": "commander",
        "companion": "companion", "maybeboard": "maybe",
    }
    out: list[dict] = []
    for e in result.entries:
        out.append(_norm(
            e.qty, section_to_board.get(e.section, "main"),
            "foil" if e.foil else "nonfoil",
            set_code=e.set, collector_number=e.collector_number, name=e.name,
        ))
    return out


# ManaBox (manabox.app) — plain-GET SSR page with an embedded Astro island-
# hydration payload. Fields are HTML-escaped (``&quot;``) and encoded as
# ``"key":[0, value]`` tuples, one card object per ``"internalId":[0,N]``. This is
# an Archidekt-tier source (no Cloudflare / auth / browser) that nonetheless
# carries full printing data (setId + collectorNumber + variant), so it resolves
# via the exact ``(set, cn)`` tier — no name-only degradation.
_MB_CARD_SPLIT = re.compile(r'(?="internalId":\[0,)')


def _mb_str(chunk: str, key: str) -> str | None:
    m = re.search(r'"' + re.escape(key) + r'":\[0,"([^"]*)"\]', chunk)
    return m.group(1) if m else None


def _mb_int(chunk: str, key: str) -> int | None:
    m = re.search(r'"' + re.escape(key) + r'":\[0,(\d+)\]', chunk)
    return int(m.group(1)) if m else None


def parse_manabox(html_text: str) -> list[dict]:
    """ManaBox ``manabox.app/decks/{id}`` SSR HTML → normalized cards.

    Un-escapes the page (the payload ships HTML-escaped), splits it into per-card
    chunks at each ``"internalId"`` boundary — chunking keeps a card's fields
    aligned, where a single flat regex over the whole doc would desync when a
    field is absent — and lifts ``name``/``collectorNumber``/``setId``/
    ``quantity``/``variant``/``boardCategory`` from each. The pre-first-card chunk
    (deck metadata: name/format/…) has no ``"internalId"`` and yields no card.
    """
    text = html.unescape(html_text)
    out: list[dict] = []
    for chunk in _MB_CARD_SPLIT.split(text):
        if '"internalId":[0,' not in chunk:
            continue  # deck-metadata preamble, not a card
        qty = _mb_int(chunk, "quantity")
        name = _mb_str(chunk, "name")
        if not qty or not name:
            continue
        bc = _mb_int(chunk, "boardCategory")
        variant = (_mb_str(chunk, "variant") or "").lower()
        out.append(_norm(
            qty,
            MANABOX_BOARD_MAP.get(bc, "main"),
            "foil" if variant in _FOIL_MODIFIERS else "nonfoil",
            set_code=_mb_str(chunk, "setId"),
            collector_number=_mb_str(chunk, "collectorNumber"),
            name=name,
        ))
    return out


def deck_name_manabox(html_text: str) -> str | None:
    """ManaBox deck name — the page ``<title>`` (carries the deck name verbatim)."""
    m = re.search(r"<title>([^<]*)</title>", html_text)
    if not m:
        return None
    name = html.unescape(m.group(1)).strip()
    return name or None


def parse_scryfall(deck: dict) -> list[dict]:
    """Scryfall ``/decks/{id}/export/json`` payload → normalized cards.

    ``deck["entries"]`` is keyed by section; each entry is a ``deck_entry`` with
    ``count``, ``finish`` (``false``/``null``/``"nonfoil"``/``"foil"`` — only
    ``"foil"`` is foil), and a nested ``card_digest`` (``id``/``set``/
    ``collector_number``/``name``) giving the exact printing. Two filters:
    **placeholder rows** (``found:false``, ``card_digest:null`` — every section
    carries some) are skipped, and sections not in ``SCRYFALL_SECTION_BOARD_MAP``
    (i.e. ``outside``) are dropped. The ``card_digest.id`` flows through the
    ``scryfall_id`` resolution tier — the strongest key.
    """
    out: list[dict] = []
    for section, rows in (deck.get("entries") or {}).items():
        board = SCRYFALL_SECTION_BOARD_MAP.get(section)
        if board is None:
            continue  # e.g. "outside" — not part of the deck
        for row in rows or []:
            if not (row.get("found") and row.get("card_digest")):
                continue  # placeholder / unresolved row
            cd = row["card_digest"]
            out.append(_norm(
                _first(row, "count", default=1), board,
                "foil" if row.get("finish") == "foil" else "nonfoil",
                scryfall_id=cd.get("id"),
                set_code=cd.get("set"),
                collector_number=cd.get("collector_number"),
                name=cd.get("name"),
            ))
    return out


def deck_name_scryfall(deck: dict) -> str | None:
    """Scryfall deck name — the export's top-level ``name`` (no author field)."""
    return deck.get("name") or None


PARSERS = {
    "moxfield": parse_moxfield,
    "archidekt": parse_archidekt,
    "mtggoldfish": parse_mtggoldfish,
    "manabox": parse_manabox,
    "scryfall": parse_scryfall,
}


def author_moxfield(data: dict) -> str | None:
    """Moxfield deck creator: ``createdByUser.userName`` (defensive to key drift)."""
    u = data.get("createdByUser") or data.get("author") or {}
    if isinstance(u, dict):
        return _first(u, "userName", "username", "displayName", "name")
    return u if isinstance(u, str) else None


def author_archidekt(data: dict) -> str | None:
    """Archidekt deck owner: ``owner.username``."""
    o = data.get("owner") or {}
    if isinstance(o, dict):
        return _first(o, "username", "userName", "name")
    return o if isinstance(o, str) else None


# ---------------------------------------------------------------------------
# Shared resolve + write orchestrator
# ---------------------------------------------------------------------------

def _resolve_cards(cards: list[dict]) -> tuple[dict, dict, dict, list[str]]:
    """Resolve normalized cards against Scryfall.

    Returns ``(by_sid, by_setcn, by_name, warnings)``: three lookup indexes plus
    warnings. Resolution key per card, in priority order:
      1. ``scryfall_id`` — Moxfield/Archidekt carry it (exact printing).
      2. ``(set, collector_number)`` — exact printing without an id.
      3. ``name`` — the last resort. MTGGoldfish's text download is frequently
         name-only (no set/cn), so this tier is what makes those decks import;
         Scryfall returns its default printing for a bare name (like a pasted
         Moxfield block does today via ``parsers.resolve``).
    The tiered batch-resolve + index-build is the shared
    ``scryfall.resolve_identifiers`` seam; this function owns only the
    deck-specific tier-building (it submits all three tiers, name included — a
    name-only MTGGoldfish row is still importable).
    """
    id_idents: list[dict] = []
    setcn_idents: list[dict] = []
    name_idents: list[dict] = []
    seen_ids: set[str] = set()
    seen_setcn: set[tuple] = set()
    seen_names: set[str] = set()
    for c in cards:
        sid = c.get("scryfall_id")
        if sid:
            if sid not in seen_ids:
                seen_ids.add(sid)
                id_idents.append({"id": sid})
            continue
        setc, cn = c.get("set"), c.get("collector_number")
        if setc and cn:
            key = (setc.lower(), str(cn))
            if key not in seen_setcn:
                seen_setcn.add(key)
                setcn_idents.append({"set": setc.lower(), "collector_number": str(cn)})
            continue
        nm = c.get("name")
        if nm and nm.lower() not in seen_names:
            seen_names.add(nm.lower())
            name_idents.append({"name": nm})

    by_sid, by_setcn, by_name, warnings = scryfall.resolve_identifiers(
        id_idents, setcn_idents, name_idents
    )
    return by_sid, by_setcn, by_name, warnings


def import_deck(cards: list[dict], *, slug: str, name: str | None = None,
                source_set_code: str | None = None, author: str | None = None,
                source: str | None = None, source_deck_id: str | None = None,
                force: bool = False, conn=None) -> dict:
    """Resolve normalized cards and write them into a deck (create-or-find).

    Every source funnels through here. Cards are resolved (id first, set+cn
    fallback), upserted into ``cards``, then written with ``decks.deck_add_card``
    (which owns board/finish validation, conflict-summing, and version routing).

    ``author`` (the source's deck creator/owner) is stamped on the deck row ONLY
    at creation — re-importing into an existing deck never overwrites it.

    **Re-pull dedup (V25).** When both ``source`` and ``source_deck_id`` are given,
    a deck already imported from that upstream is detected via
    ``decks.deck_find_by_source``:
      * without ``force`` → return ``{"duplicate": True, "existing_slug": …}`` and
        write NOTHING (the caller refuses). This is what stops a second pull of the
        same deck from silently doubling every card (``deck_add_card`` sums).
      * with ``force`` → target the EXISTING deck's slug, clear its current-version
        cards (``deck_replace_cards``), and re-add the fresh pull — a REPLACE, not a
        sum. The ``slug`` argument is ignored in this case (the dedup match wins).
    With no source keys (e.g. a hand-fed ``--file`` import) the historical
    create-or-append behavior is unchanged.

    Returns ``{"slug", "created", "added", "updated", "not_found", "warnings"}``,
    plus ``"replaced": bool``; or ``{"duplicate": True, "existing_slug", "source",
    "source_deck_id"}`` on a refused re-pull.
    """
    with db.transaction(conn) as conn:
        # Dedup gate — only when the caller supplied both source keys.
        existing = decks_mod.deck_find_by_source(source, source_deck_id, conn=conn)
        if existing is not None:
            if not force:
                return {
                    "duplicate": True, "existing_slug": existing.slug,
                    "source": source, "source_deck_id": source_deck_id,
                }
            slug = existing.slug  # a forced re-pull targets the matched deck

        by_sid, by_setcn, by_name, warnings = _resolve_cards(cards)

        created = replaced = False
        if decks_mod.deck_get(slug, conn=conn) is None:
            decks_mod.deck_create(
                slug, name or slug, source_set_code=source_set_code,
                author=author, source=source, source_deck_id=source_deck_id,
                conn=conn,
            )
            created = True
        elif force and existing is not None:
            # Replace the matched deck's composition rather than summing onto it.
            decks_mod.deck_replace_cards(slug, conn=conn)
            replaced = True

        added = updated = 0
        not_found: list[dict] = []
        for c in cards:
            card = _match(c, by_sid, by_setcn, by_name)
            if card is None:
                not_found.append({
                    "qty": c["qty"], "name": c.get("name"),
                    "set": c.get("set"), "collector_number": c.get("collector_number"),
                    "reason": "unresolved against Scryfall",
                })
                continue
            db.upsert_card(conn, card)
            sid = card["id"]
            r = decks_mod.deck_add_card(slug, sid, c["board"], c["finish"], c["qty"], conn=conn)
            if r["action"] == "inserted":
                added += 1
            else:
                updated += 1

    return {
        "slug": slug, "created": created, "replaced": replaced,
        "added": added, "updated": updated,
        "not_found": not_found, "warnings": warnings,
    }


def _match(c: dict, by_sid: dict, by_setcn: dict, by_name: dict) -> dict | None:
    sid = c.get("scryfall_id")
    if sid and sid in by_sid:
        return by_sid[sid]
    setc, cn = c.get("set"), c.get("collector_number")
    if setc and cn:
        hit = by_setcn.get((setc.lower(), str(cn)))
        if hit is not None:
            return hit
    nm = c.get("name")
    if nm:
        return by_name.get(nm.lower())
    return None

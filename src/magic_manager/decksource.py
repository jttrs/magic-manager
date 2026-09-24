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

from typing import Literal
from urllib.parse import urlparse

from . import db, decks as decks_mod, scryfall

Source = Literal["moxfield", "archidekt", "mtggoldfish"]

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
    raise ValueError(
        f"unrecognized deck source in {url_or_id!r}; expected a moxfield.com / "
        f"archidekt.com / mtggoldfish.com URL"
    )


def deck_id_from_url(url: str) -> str:
    """Extract the source-native deck id from a URL.

    Moxfield:    moxfield.com/decks/<publicId>[/anything]
    Archidekt:   archidekt.com/decks/<id>[-slug]
    MTGGoldfish: mtggoldfish.com/deck/<id>[#...]

    The id is the segment immediately AFTER the ``decks``/``deck`` marker (so a
    trailing ``/primer`` etc. doesn't get mistaken for the id).
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


PARSERS = {
    "moxfield": parse_moxfield,
    "archidekt": parse_archidekt,
    "mtggoldfish": parse_mtggoldfish,
}


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
    Reuses the same rate-limited ``scryfall.collection`` batch wrapper.
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

    warnings: list[str] = []
    found: list[dict] = []
    for idents in (id_idents, setcn_idents, name_idents):
        if not idents:
            continue
        got, not_found = scryfall.collection(idents)
        found.extend(got)
        for nf in not_found:
            warnings.append(f"scryfall could not resolve identifier {nf!r}")

    by_sid = {c["id"]: c for c in found if c.get("id")}
    by_setcn = {
        ((c.get("set") or "").lower(), str(c.get("collector_number") or "")): c
        for c in found
    }
    # Index by both oracle name and the front face of a split/DFC ("A // B" → "A").
    by_name: dict[str, dict] = {}
    for c in found:
        nm = (c.get("name") or "").lower()
        if nm:
            by_name.setdefault(nm, c)
            by_name.setdefault(nm.split(" // ")[0], c)
    return by_sid, by_setcn, by_name, warnings


def import_deck(cards: list[dict], *, slug: str, name: str | None = None,
                source_set_code: str | None = None, conn=None) -> dict:
    """Resolve normalized cards and write them into a deck (create-or-find).

    Every source funnels through here. Cards are resolved (id first, set+cn
    fallback), upserted into ``cards``, then written with ``decks.deck_add_card``
    (which owns board/finish validation, conflict-summing, and version routing).

    Returns ``{"slug", "created", "added", "updated", "not_found", "warnings"}``.
    """
    by_sid, by_setcn, by_name, warnings = _resolve_cards(cards)

    with db.transaction(conn) as conn:
        created = False
        if decks_mod.deck_get(slug, conn=conn) is None:
            decks_mod.deck_create(
                slug, name or slug, source_set_code=source_set_code, conn=conn,
            )
            created = True

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
        "slug": slug, "created": created, "added": added, "updated": updated,
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

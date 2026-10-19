"""Deck editing engine: build / break down a deck, copy a recipe, start a new
deck, and save an edited decklist as a new version — re-balancing the pledges of
a physically built deck so its assignments match the new recipe.

Single source of truth behind the web Deck Manager's actions and editor
(:mod:`magic_manager.api.decks`). Composes the existing primitives in
:mod:`magic_manager.decks` (versions, compose plan, assign / unassign batches);
nothing here re-implements their bounds checks.

Pledge vocabulary (physical): **pull** = copies leaving a built deck (unpledged,
back to the free pool), **sleeve** = free copies going into it (pledged),
**short** = copies the new recipe needs that you don't have free.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import db, decks, ingest, inventory

PLAYABLE = decks.PLAYABLE_BOARDS


class ReadOnlyDeck(PermissionError):
    """Precon recipes are reference data (product attribution measures against
    them) — edit a copy instead."""


class Shortfall(ValueError):
    """A Build would leave cards un-pledged (not free); ``short`` lists them."""

    def __init__(self, short: list[dict]):
        self.short = short
        super().__init__(f"{sum(r['qty'] for r in short)} cards aren't free")


class StaleDraft(RuntimeError):
    """The deck changed since the draft was opened (another save won)."""


@dataclass(frozen=True)
class DraftCard:
    scryfall_id: str
    board: str
    finish: str    # nonfoil | foil | either
    count: int


# ---------- helpers ----------

def _deck(conn, slug: str):
    row = decks._fetch_deck(conn, slug)
    if row is None:
        raise LookupError(f"deck with slug {slug!r} not found")
    return row


def _recipe_rows(slug: str) -> list[str]:
    """Every deck row (copy) of the recipe ``slug`` belongs to, oldest first."""
    with db.connect() as conn:
        d = _deck(conn, slug)
        fn = d["source_precon_file_name"]
        if not fn:
            return [slug]
        return [r[0] for r in conn.execute(
            "SELECT slug FROM decks WHERE source_precon_file_name = ? ORDER BY deck_id", (fn,))]


def _pledged(conn, deck_id: int) -> dict[tuple[str, str], int]:
    return {(r[0], r[1]): r[2] for r in conn.execute(
        "SELECT scryfall_id, finish, count FROM deck_assignments WHERE deck_id = ?", (deck_id,))}


def _state(conn, slug: str) -> str:
    return _deck(conn, slug)["precon_state"]


def _unique_slug(conn, name: str) -> str:
    return decks.unique_slug(conn, decks._slug(name) or "deck")


def _needs(cards: list[DraftCard], pledged: dict[tuple[str, str], int],
           free: dict[tuple[str, str], int]) -> dict[tuple[str, str], int]:
    """Collapse a playable decklist to per-(sid, finish) copies. Exact finishes
    first; then each 'either' slot keeps copies already pledged, then takes free
    nonfoil, then free foil (splitting across finishes), and any excess lands on
    nonfoil (short). Free copies are shared across slots, never double-counted.
    Token rows aren't pledged by a Build, but copies already pledged to them stay
    (never sleeved, never pulled)."""
    out: dict[tuple[str, str], int] = {}

    def add(key: tuple[str, str], n: int) -> None:
        if n > 0:
            out[key] = out.get(key, 0) + n

    def kept(key: tuple[str, str]) -> int:       # pledged copies not yet claimed
        return max(0, pledged.get(key, 0) - out.get(key, 0))

    def room(key: tuple[str, str]) -> int:       # free copies not yet claimed
        return max(0, free.get(key, 0) - max(0, out.get(key, 0) - pledged.get(key, 0)))

    playable = [c for c in cards if c.board in PLAYABLE and c.count > 0]
    for c in playable:
        if c.finish in ("nonfoil", "foil"):
            add((c.scryfall_id, c.finish), c.count)
    for c in playable:
        if c.finish in ("nonfoil", "foil"):
            continue
        left = c.count
        for pick in (kept, room):
            for fin in ("nonfoil", "foil"):
                key = (c.scryfall_id, fin)
                take = min(left, pick(key))
                add(key, take)
                left -= take
        add((c.scryfall_id, "nonfoil"), left)
    for c in cards:
        if c.board != "token" or c.count <= 0:
            continue
        left = c.count
        for fin in (("nonfoil", "foil") if c.finish == "either" else (c.finish,)):
            key = (c.scryfall_id, fin)
            take = min(left, kept(key))
            add(key, take)
            left -= take
    return out


def _free_map(sids) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    with db.connect() as conn:
        for sid in set(sids):
            for fin in ("nonfoil", "foil"):
                out[(sid, fin)] = inventory.free_quantity(sid, fin, conn=conn)
    return out


def _swap(needs: dict[tuple[str, str], int], pledged: dict[tuple[str, str], int],
          free: dict[tuple[str, str], int]) -> dict:
    """pull / sleeve / short lists turning ``pledged`` into ``needs``."""
    pull, sleeve, short = [], [], []
    for key in sorted(set(needs) | set(pledged)):
        delta = needs.get(key, 0) - pledged.get(key, 0)
        if delta < 0:
            pull.append({"scryfall_id": key[0], "finish": key[1], "qty": -delta})
        elif delta > 0:
            take = min(delta, max(0, free.get(key, 0)))
            if take:
                sleeve.append({"scryfall_id": key[0], "finish": key[1], "qty": take})
            if delta > take:
                short.append({"scryfall_id": key[0], "finish": key[1], "qty": delta - take})
    return {"pull": pull, "sleeve": sleeve, "short": short}


def _current_cards(conn, version_id: int) -> list[DraftCard]:
    return [DraftCard(r[0], r[1], r[2], r[3]) for r in conn.execute(
        "SELECT scryfall_id, board, finish, count FROM deck_cards WHERE deck_version_id = ?", (version_id,))]


# ---------- build / break down ----------

def build_target(slug: str) -> str | None:
    """The copy a Build would assemble: the first non-built copy of the recipe,
    else ``slug`` itself when it's built but not fully pledged; None when every
    copy is already built and complete."""
    rows = _recipe_rows(slug)
    with db.connect() as conn:
        for s in rows:
            if _state(conn, s) != "built":
                return s
    sw = _target_swap(slug)
    return slug if sw["sleeve"] or sw["short"] else None


def _target_swap(slug: str) -> dict:
    """pull / sleeve / short turning ``slug``'s pledges into its PLAYABLE recipe
    (the one completeness rule shared by build_target, build_plan and build)."""
    with db.connect() as conn:
        d = _deck(conn, slug)
        pledged = _pledged(conn, d["deck_id"])
        cards = _current_cards(conn, d["current_version_id"])
    free = _free_map(c.scryfall_id for c in cards)
    needs = _needs(cards, pledged, free)
    return {**_swap(needs, pledged, free), "need": sum(needs.values()), "pledged": sum(pledged.values())}


def build_plan(slug: str) -> dict:
    """Preview a Build: which copy, copies the recipe needs, how many are free,
    the shortfalls (per printing), and whether a Build can pledge anything at
    all (``buildable`` — False when no card is free and nothing is pledged yet,
    so :func:`build` would refuse)."""
    target = build_target(slug)
    if target is None:
        return {"target": None, "need": 0, "covered": 0, "short": [], "buildable": False}
    sw = _target_swap(target)
    short = sum(s["qty"] for s in sw["short"])
    return {"target": target, "need": sw["need"], "covered": sw["need"] - short, "short": sw["short"],
            "buildable": bool(sw["sleeve"] or sw["pledged"])}


def build(slug: str, *, allow_shortfall: bool = False) -> dict:
    """Assemble a copy of the recipe from free cards: pledge them and mark the
    copy built. Refuses on shortfalls unless ``allow_shortfall`` (then pledges
    what's free). Built follows pledges: a Build that would leave the copy with
    nothing pledged refuses (:class:`Shortfall`) even with ``allow_shortfall``."""
    target = build_target(slug)
    if target is None:
        raise ValueError("every copy of this deck is already built")
    sw = _target_swap(target)
    if sw["short"] and not allow_shortfall:
        raise Shortfall(sw["short"])
    if not sw["sleeve"] and not sw["pledged"]:
        if sw["short"]:
            raise Shortfall(sw["short"])
        raise ValueError("this deck has no cards to build")
    if sw["sleeve"]:
        decks.deck_assign_batch(target, [(s["scryfall_id"], s["finish"], s["qty"]) for s in sw["sleeve"]],
                                allow_shortfall=True)
    decks.set_precon_state(target, "built")
    return {"slug": target, "sleeved": sum(s["qty"] for s in sw["sleeve"]), "short": sw["short"]}


def break_down(slug: str) -> dict:
    """Disassemble one built copy: unpledge every card (they return to the free
    pool) and mark the copy deconstructed. The recipe is kept."""
    rows = _recipe_rows(slug)
    with db.connect() as conn:
        built = [s for s in rows if _state(conn, s) == "built"]
    if not built:
        raise ValueError("no built copy of this deck to break down")
    target = slug if slug in built else built[-1]
    res = decks.deck_unassign_batch(target, "all")
    decks.set_precon_state(target, "deconstructed")
    return {"slug": target, "pulled": res["unassigned_qty"]}


# ---------- new / copy ----------

def create_deck(name: str, *, format: str = "commander",
                commander: str | None = None) -> str:
    """A new, empty hand-built deck (optionally seeded with its commander).
    Not built: nothing is pledged until you Build it."""
    with db.connect() as conn:
        slug = _unique_slug(conn, name)
    decks.deck_create(slug, name.strip() or "Untitled deck", format=format,
                      precon_state="deconstructed")
    if commander:
        decks.deck_add_card(slug, commander, "commander", "either", 1)
    return slug


def copy_recipe(slug: str, *, name: str | None = None) -> str:
    """Copy a deck's current recipe into a new hand-built deck you can edit —
    the copy is NOT a precon (no product link), and nothing is pledged."""
    with db.connect() as conn:
        d = _deck(conn, slug)
        cards = _current_cards(conn, d["current_version_id"])
        new_name = (name or f"{d['name']} (copy)").strip()
        new_slug = _unique_slug(conn, new_name)
    decks.deck_create(new_slug, new_name, format=d["format"], precon_state="deconstructed")
    with db.transaction() as conn:
        db.require_cards(conn, [c.scryfall_id for c in cards])
        for c in cards:
            decks.deck_add_card(new_slug, c.scryfall_id, c.board, c.finish, c.count, conn=conn)
    return new_slug


def add_recipe_to_collection(slug: str, *, label: str | None = None) -> dict:
    """Add one copy of a deck's playable cards (commander, main, companion,
    sideboard — not maybe or tokens) to the collection as a single ``deck``
    ingest event. 'either' slots land as nonfoil when the printing has it.
    Does NOT pledge them: building stays an explicit step."""
    from . import addcards, collection_view

    with db.connect() as conn:
        d = _deck(conn, slug)
        cards = _current_cards(conn, d["current_version_id"])
        fins = {r[0]: collection_view.inventory_finishes(r[1]) for r in conn.execute(
            f"SELECT scryfall_id, finishes FROM cards WHERE scryfall_id IN ({','.join('?' * len(cards)) or 'NULL'})",
            [c.scryfall_id for c in cards])}
    items = []
    for c in cards:
        if c.board not in PLAYABLE or c.count <= 0:
            continue
        fin = c.finish if c.finish != "either" else ("nonfoil" if "nonfoil" in fins.get(c.scryfall_id, ["nonfoil"]) else "foil")
        items.append((c.scryfall_id, fin, c.count))
    if not items:
        return {"copies": 0, "printings": 0, "summary": "nothing to add"}
    return addcards.commit(items, source="deck", label=label or d["name"])


def import_payload(payload: dict, *, force: bool = False, ingest_id: int | None = None) -> dict:
    """Save a fetched deck (``scripts/import_deck.py`` JSON: source / id / name /
    author / cards) as a decklist — recipe only, never built. A deck already
    imported from the same source is not duplicated: returns its slug with
    ``duplicate=True`` (``force`` replaces its cards instead).

    ``ingest_id``: the deck-import event that just added these cards (Add cards →
    "Also save the decklist"). A newly created deck is linked to it so reverting
    that import removes the deck too; ignored unless it is an unreverted web deck
    import no other deck is linked to."""
    from . import decksource

    cards = payload.get("cards") or []
    if not cards:
        raise ValueError("the fetched deck has no cards")
    name = (payload.get("name") or "Imported deck").strip()
    with db.connect() as conn:
        slug = _unique_slug(conn, name)
        link = ingest_id if ingest_id is not None and ingest.deck_import_linkable(conn, ingest_id) else None
    res = decksource.import_deck(
        cards, slug=slug, name=name, author=payload.get("author"),
        source=payload.get("source"), source_deck_id=payload.get("id"), force=force,
        created_by_ingest_id=link,
    )
    if res.get("duplicate"):
        return {"slug": res["existing_slug"], "duplicate": True, "created": False, "not_found": 0}
    return {"slug": res["slug"], "duplicate": False, "created": bool(res.get("created")),
            "not_found": len(res.get("not_found") or [])}


# ---------- edit: preview + save ----------

def is_editable(slug: str) -> bool:
    with db.connect() as conn:
        return not _deck(conn, slug)["source_precon_file_name"]


def _keep_tokens(cards: list[DraftCard], current: list[DraftCard]) -> list[DraftCard]:
    """The editor doesn't show the token board: a draft with no token rows keeps
    the current version's tokens (so a save never silently drops them)."""
    if any(c.board == "token" for c in cards):
        return cards
    return [*cards, *(c for c in current if c.board == "token")]


def preview(slug: str, cards: list[DraftCard]) -> dict:
    """What saving ``cards`` would change: per-row diff vs the current version,
    and — for a built copy — the physical pull / sleeve / short lists. A draft
    without token rows keeps the deck's tokens (:func:`_keep_tokens`)."""
    with db.connect() as conn:
        d = _deck(conn, slug)
        current = _current_cards(conn, d["current_version_id"])
        pledged = _pledged(conn, d["deck_id"])
        built = d["precon_state"] == "built"
    cards = _keep_tokens(cards, current)
    cur = {(c.scryfall_id, c.board, c.finish): c.count for c in current}
    new = {(c.scryfall_id, c.board, c.finish): c.count for c in cards if c.count > 0}
    changes = [
        {"scryfall_id": k[0], "board": k[1], "finish": k[2], "before": cur.get(k, 0), "after": new.get(k, 0)}
        for k in sorted(set(cur) | set(new)) if cur.get(k, 0) != new.get(k, 0)
    ]
    swap = None
    if built:
        free = _free_map(c.scryfall_id for c in [*cards, *current])
        swap = _swap(_needs(cards, pledged, free), pledged, free)
    return {"version_id": d["current_version_id"], "built": built, "changes": changes, "swap": swap}


def save(slug: str, cards: list[DraftCard], *, expected_version_id: int,
         name: str | None = None) -> dict:
    """Write ``cards`` as a NEW version of the deck (the old one stays as
    history) and, for a built copy, move its pledges to match. Precons are
    read-only (:class:`ReadOnlyDeck`); a deck changed since the draft opened
    raises :class:`StaleDraft`."""
    for c in cards:
        decks._validate_board(c.board)
        decks._validate_finish(c.finish)
        if c.count < 0:
            raise ValueError(f"count must be >= 0 (got {c.count})")
    with db.connect() as conn:
        d = _deck(conn, slug)
        if d["source_precon_file_name"]:
            raise ReadOnlyDeck("precon recipes are read-only — copy the deck to edit it")
        if d["current_version_id"] != expected_version_id:
            raise StaleDraft("this deck changed since you opened it — reload to see the latest list")
        status = conn.execute("SELECT status FROM deck_versions WHERE deck_version_id = ?",
                              (d["current_version_id"],)).fetchone()[0]
        cards = _keep_tokens(cards, _current_cards(conn, d["current_version_id"]))
    pv = preview(slug, cards)
    if not pv["changes"] and not (name and name.strip() and name.strip() != d["name"]):
        return {**pv, "version_number": None, "pulled": 0, "sleeved": 0}

    with db.transaction() as conn:
        if name and name.strip() and name.strip() != d["name"]:
            conn.execute("UPDATE decks SET name = ? WHERE slug = ?", (name.strip(), slug))
        v = None
        if pv["changes"]:
            v = decks.create_version(slug, status=status, change_reason="web edit", conn=conn)
            db.require_cards(conn, [c.scryfall_id for c in cards if c.count > 0])
            for c in cards:
                if c.count > 0:
                    decks.deck_add_card(slug, c.scryfall_id, c.board, c.finish, c.count, conn=conn)
    pulled = sleeved = 0
    sw = pv["swap"]
    if sw:
        if sw["pull"]:
            res = decks.deck_unassign_batch(slug, [(p["scryfall_id"], p["finish"], p["qty"]) for p in sw["pull"]])
            pulled = res["unassigned_qty"]
        if sw["sleeve"]:
            res = decks.deck_assign_batch(slug, [(s["scryfall_id"], s["finish"], s["qty"]) for s in sw["sleeve"]],
                                          allow_shortfall=True)
            sleeved = res["assigned_qty"]
    return {**pv, "version_number": v.version_number if v else None, "pulled": pulled, "sleeved": sleeved}


# ---------- editor: legality + bracket floor ----------

def draft_rows(slug: str, cards: list[DraftCard]) -> tuple[str, list[dict]]:
    """An (unsaved) decklist's format and its legality-shaped rows (zero counts
    dropped). Format = the deck's, else Commander when the draft has a commander
    (imports record no format; a commander makes it Commander-shaped), else ''.
    Shared by :func:`check` and the Earmarked tab (``card_earmarks.for_deck``).
    Raises ``LookupError`` for an unknown deck."""
    live = [c for c in cards if c.count > 0]
    with db.connect() as conn:
        fmt = (_deck(conn, slug)["format"] or "").lower()
        rows = decks.materialize_rows_for_checks(
            conn, [(c.scryfall_id, c.board, c.finish, c.count) for c in live])
    if not fmt and any(c.board == "commander" for c in live):
        fmt = "commander"
    return fmt, rows


def check(slug: str, cards: list[DraftCard], *, combos: bool = False) -> dict:
    """Check an (unsaved) decklist against its deck's format — the same engines
    :func:`decks.finalize` stores on a version, nothing written. Legality reads
    Scryfall's per-format legality; for Commander-like formats it also returns
    the bracket FLOOR from Wizards' official criteria (Game Changers, mass land
    denial, extra turns; two-card combos only when ``combos`` asks Commander
    Spellbook — network). Advisory, never blocking. A deck with no format
    (imports record none) is checked as Commander when it has a commander,
    else not checked at all (``format`` None, one ``no_format`` note)."""
    from . import brackets, legality

    fmt, rows = draft_rows(slug, cards)
    if not fmt:
        report = legality.LegalityReport(
            format="", legal=True, checked_count=len(legality._non_token_cards(rows)),
            violations=[legality.Violation(code="no_format", severity="info", cards=[],
                                           message="This deck has no format, so legality isn't checked.")])
        return {"format": None, "bracket": None, "legality": report.to_json()}
    report = legality.validate(rows, format=fmt).to_json()
    bracket = None
    if fmt in legality._COMMANDER_LIKE_FORMATS:
        spellbook = None
        if combos:
            from . import commander_spellbook as spellbook
        bracket = brackets.suggest(rows, spellbook=spellbook).to_json()
    return {"format": fmt, "legality": report, "bracket": bracket}


# ---------- editor: commander suggestions ----------

def most_free(options: list[tuple[str, int]], free: dict[str, int]) -> str:
    """Of your printings ``[(scryfall_id, owned qty)]``, the one with the most
    FREE copies (ties → most owned) — the printing a deck should use."""
    return max(options, key=lambda t: (free.get(t[0], 0), t[1]))[0]


def usable_printings(oracle_ids) -> tuple[dict[str, str], dict[str, list[tuple[str, int]]], dict[str, int]]:
    """The printing to add for each oracle card: your printing with the most FREE
    copies when you own the card, else its first standard printing. Returns
    ``(pick {oracle_id: scryfall_id}, owned {oracle_id: [(scryfall_id, qty)]},
    free {scryfall_id: qty})`` — shared by suggestions and combo near-misses."""
    from . import sets

    oids = list(dict.fromkeys(o for o in oracle_ids if o))
    owned_by_oracle: dict[str, list[tuple[str, int]]] = {}
    if oids:
        with db.connect() as conn:
            for i in range(0, len(oids), 400):
                part = oids[i:i + 400]
                for oid, sid, q in conn.execute(
                    f"""SELECT c.oracle_id, i.scryfall_id, SUM(i.quantity) FROM inventory i
                        JOIN cards c ON c.scryfall_id = i.scryfall_id
                        WHERE i.quantity > 0 AND c.oracle_id IN ({','.join('?' * len(part))})
                        GROUP BY i.scryfall_id""", part,
                ):
                    owned_by_oracle.setdefault(oid, []).append((sid, q))
    free = inventory.free_quantities([sid for v in owned_by_oracle.values() for sid, _ in v])
    std = sets.standard_printing_by_oracle(oids)
    pick: dict[str, str] = {}
    for oid in oids:
        mine = owned_by_oracle.get(oid)
        if mine:
            pick[oid] = most_free(mine, free)
        elif oid in std:
            pick[oid] = std[oid]["scryfall_id"]
    return pick, owned_by_oracle, free

def suggestions(commander: str, *, limit: int = 300) -> dict:
    """EDHREC's recommended cards for ``commander`` (cached page, synced once if
    absent), highest inclusion first, each on a printing you can use: your
    printing with the most FREE copies when you own the card, else its first
    standard printing. ``owned`` / ``free`` count copies across every printing."""
    from . import addcards, edhrec

    name, _slug, entries = edhrec._commander_card_entries(commander)
    ranked = sorted(entries.values(), key=lambda e: -(e.inclusion_pct or 0))[:limit]
    pick, owned_by_oracle, free = usable_printings([e.oracle_id for e in ranked if e.oracle_id])
    printings = addcards.printings_for_ids(pick.values())
    cards = []
    for e in ranked:
        sid = pick.get(e.oracle_id or "")
        if not sid or sid not in printings:
            continue
        mine = owned_by_oracle.get(e.oracle_id, [])
        cards.append({
            "printing": printings[sid], "inclusion_pct": e.inclusion_pct, "synergy": e.synergy,
            "tags": sorted(e.tags), "owned": sum(q for _, q in mine),
            "free": sum(free.get(s, 0) for s, _ in mine),
        })
    return {"commander": re.sub(r"\s*\(Commander\)$", "", name), "cards": cards}

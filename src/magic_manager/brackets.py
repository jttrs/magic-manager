"""Commander "bracket" classification: a PURE-ish, mostly-OFFLINE function of
already-materialized card data.

This module does no DB access itself — callers (``decks.py`` / ``cli.py``)
resolve a deck's cards (JSON-decoding the ``cards`` table's
``legalities``/``game_changer`` columns into native Python types) and hand
the resulting list of dicts to :func:`suggest`. The only side effect is the
OPTIONAL injected ``spellbook`` client (an object exposing
``find_my_combos(commander=..., main=...)`` — see
:mod:`magic_manager.commander_spellbook`); passing ``None`` (the default)
keeps this module fully offline and testable.

``game_changer`` on a card comes from the V16 ``cards.game_changer`` column
(Scryfall's boolean mirroring the official Commander "Game Changers" list —
the bracket-3+ gate). Rows synced before V16 read ``game_changer=0`` and
``legalities=NULL``; :func:`suggest` never crashes on that — it emits a
``stale_data`` note rather than asserting a confident bracket.

The suggested bracket is a FLOOR, not an authoritative answer — brackets are
a deckbuilding-intent spectrum (1 Exhibition .. 5 cEDH) the *player* declares;
this heuristic can only detect a handful of hard gates (Game Changers, mass
land denial, two-card combos) and floors the suggestion at the highest gate
it can prove is crossed. cEDH (bracket 5) is a meta/intent designation and is
never auto-assigned.

The public shape is :class:`BracketDetail`, JSON-serializable for storage
alongside a deck version (mirroring :class:`magic_manager.legality.LegalityReport`).
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------- curated seed sets — small, extend later ----------
# Matched by exact card NAME (not oracle text parsing). Use oracle_id where
# possible for other classifications (game changers); these two sets are
# name-keyed because there's no dedicated Scryfall flag for either category.

MASS_LAND_DENIAL_NAMES: frozenset[str] = frozenset({
    "Armageddon", "Ravages of War", "Ruination", "Catastrophe", "Winter Orb",
    "Static Orb", "Blood Moon", "Back to Basics", "Jokulhaups", "Obliterate",
    "Decree of Annihilation", "Cataclysm", "Boil", "Boiling Seas", "Impending Disaster",
})

EXTRA_TURN_NAMES: frozenset[str] = frozenset({
    "Time Warp", "Temporal Manipulation", "Capture of Jingzhou", "Time Stretch",
    "Temporal Mastery", "Nexus of Fate", "Alrund's Epiphany", "Karn's Temporal Sundering",
    "Part the Waterveil", "Temporal Trespass", "Savor the Moment", "Walk the Aeons",
})


@dataclass
class BracketDetail:
    """The full result of assessing a deck's suggested Commander bracket.

    ``suggested_bracket`` is ``1``..``4`` or ``None`` when the deck has no
    commander (brackets only apply to Commander decks) — see the module
    docstring on why this is a floor, not an authoritative answer.
    ``combos`` is whatever list of combo dicts :func:`suggest` could extract
    from the Commander Spellbook response (empty if unavailable/none found).
    """

    suggested_bracket: int | None
    game_changer_count: int
    game_changers: list[str]
    mass_land_denial: list[str]
    extra_turns: list[str]
    combos: list[dict]
    two_card_combos: int
    rationale: list[str]
    stale_data: bool
    spellbook_available: bool

    def to_json(self) -> dict:
        """Serialize to a plain dict, suitable for ``json.dumps``."""
        return {
            "suggested_bracket": self.suggested_bracket,
            "game_changer_count": self.game_changer_count,
            "game_changers": list(self.game_changers),
            "mass_land_denial": list(self.mass_land_denial),
            "extra_turns": list(self.extra_turns),
            "combos": list(self.combos),
            "two_card_combos": self.two_card_combos,
            "rationale": list(self.rationale),
            "stale_data": self.stale_data,
            "spellbook_available": self.spellbook_available,
        }

    @classmethod
    def from_json(cls, d: dict) -> BracketDetail:
        """Inverse of :meth:`to_json`."""
        return cls(
            suggested_bracket=d.get("suggested_bracket"),
            game_changer_count=d.get("game_changer_count", 0),
            game_changers=list(d.get("game_changers") or []),
            mass_land_denial=list(d.get("mass_land_denial") or []),
            extra_turns=list(d.get("extra_turns") or []),
            combos=list(d.get("combos") or []),
            two_card_combos=d.get("two_card_combos", 0),
            rationale=list(d.get("rationale") or []),
            stale_data=bool(d.get("stale_data", False)),
            spellbook_available=bool(d.get("spellbook_available", False)),
        )


# ---------- shared helpers ----------

def _name(card: dict) -> str:
    """Coerce a card's ``name`` to ``str`` (defensive against a missing key)."""
    return str(card.get("name") or "")


def _non_token_cards(cards: list[dict]) -> list[dict]:
    """Every card NOT on the ``'token'`` board — tokens ride the deck but
    aren't part of the bracket assessment."""
    return [c for c in cards if c.get("board") != "token"]


def _game_changer_names(cards: list[dict]) -> list[str]:
    """Distinct names of every ``game_changer == 1`` card, deduped by
    ``oracle_id`` (falling back to ``name`` when ``oracle_id`` is missing —
    e.g. un-resynced rows)."""
    seen: set[str] = set()
    names: list[str] = []
    for c in cards:
        if not c.get("game_changer"):
            continue
        key = c.get("oracle_id") or _name(c)
        if key in seen:
            continue
        seen.add(key)
        names.append(_name(c))
    return names


def _names_in(cards: list[dict], pool: frozenset[str]) -> list[str]:
    """Distinct names present in ``cards`` that also appear in ``pool``."""
    seen: set[str] = set()
    names: list[str] = []
    for c in cards:
        name = _name(c)
        if name in pool and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _extract_combos(response: dict) -> list[dict]:
    """Best-effort extraction of the combo list from a ``/find-my-combos``
    response. The exact API shape isn't pinned down here — try common
    top-level keys in order and fall back to an empty list rather than
    raising; this keeps :func:`suggest` resilient to a shape mismatch."""
    if not isinstance(response, dict):
        return []
    for key in ("results", "included", "combos"):
        val = response.get(key)
        if isinstance(val, list):
            return val
    return []


def _combo_card_count(combo: dict) -> int | None:
    """Best-effort card count for one combo dict, or ``None`` if the shape
    doesn't expose a countable card list."""
    for key in ("uses", "cards"):
        val = combo.get(key)
        if isinstance(val, list):
            return len(val)
    return None


def _count_two_card_combos(combos: list[dict]) -> int:
    """Number of ``combos`` with exactly 2 cards, if every combo's card count
    is inferable; else ``len(combos)`` (can't distinguish, so treat every
    combo as a risk)."""
    if not combos:
        return 0
    counts = [_combo_card_count(c) for c in combos]
    if all(n is not None for n in counts):
        return sum(1 for n in counts if n == 2)
    return len(combos)


def _call_spellbook(
    spellbook, commander_names: list[str], main_names: list[str]
) -> tuple[list[dict], bool, str | None]:
    """Try ``spellbook.find_my_combos``; return
    ``(combos, spellbook_available, error_note)``. Any exception (network
    down, wrapper missing, malformed response) is caught here so a Spellbook
    outage never breaks bracket suggestion — it just degrades combo
    detection."""
    try:
        response = spellbook.find_my_combos(commander=commander_names, main=main_names)
    except Exception as e:  # noqa: BLE001 - deliberately broad: any failure degrades gracefully
        return [], False, f"Commander Spellbook lookup failed: {e}"
    return _extract_combos(response), True, None


# ---------- public entry point ----------

def suggest(cards: list[dict], *, spellbook=None) -> BracketDetail:
    """Suggest a Commander bracket FLOOR for ``cards`` (never authoritative
    — see the module docstring).

    ``cards`` is the full board (all boards, including ``'token'`` — token
    rows are excluded from every check internally). ``spellbook`` is an
    optional client exposing ``find_my_combos(commander=..., main=...)``
    (see :mod:`magic_manager.commander_spellbook`); pass ``None`` (the
    default) to skip combo detection entirely and stay fully offline.
    """
    non_token = _non_token_cards(cards)
    commanders = [c for c in non_token if c.get("board") == "commander"]
    rest = [c for c in non_token if c.get("board") != "commander"]

    game_changer_names = _game_changer_names(non_token)
    mass_land_denial = _names_in(non_token, MASS_LAND_DENIAL_NAMES)
    extra_turns = _names_in(non_token, EXTRA_TURN_NAMES)

    combos: list[dict] = []
    two_card_combos = 0
    spellbook_available = False
    spellbook_error: str | None = None
    if spellbook is not None:
        commander_names = [_name(c) for c in commanders]
        main_names = [_name(c) for c in rest]
        combos, spellbook_available, spellbook_error = _call_spellbook(
            spellbook, commander_names, main_names
        )
        two_card_combos = _count_two_card_combos(combos)

    stale_data = any(not c.get("legalities") for c in non_token)

    rationale: list[str] = []

    if game_changer_names:
        rationale.append(
            f"{len(game_changer_names)} Game Changer(s) present: {', '.join(game_changer_names)}"
        )
    else:
        rationale.append("no Game Changers present")

    if mass_land_denial:
        rationale.append(
            f"mass land denial present ({', '.join(mass_land_denial)}) — "
            "prohibited below bracket 4"
        )

    if extra_turns:
        rationale.append(f"extra-turn effect(s) present ({', '.join(extra_turns)})")

    if spellbook is not None:
        if spellbook_available:
            if two_card_combos:
                rationale.append(
                    f"{two_card_combos} two-card combo(s) found via Commander Spellbook "
                    "— prohibited below bracket 4"
                )
            elif combos:
                rationale.append(f"{len(combos)} combo(s) found via Commander Spellbook")
            else:
                rationale.append("no combos found via Commander Spellbook")
        else:
            rationale.append(
                spellbook_error or "Commander Spellbook lookup failed; combo detection skipped"
            )

    if stale_data:
        rationale.append(
            "one or more cards have no synced legality data; run `mm set sync` "
            "— this suggestion may be based on incomplete data"
        )

    if not commanders:
        rationale.append(
            "not a Commander deck (no commander); brackets apply to Commander only"
        )
        suggested_bracket = None
    else:
        floor = 2
        no_risk_factors = (
            not game_changer_names
            and not mass_land_denial
            and not extra_turns
            and not combos
        )
        if no_risk_factors:
            rationale.append(
                "no risk factors detected; could be bracket 1 (Exhibition) or "
                "bracket 2 (Core) — this heuristic can't distinguish a theme/precon "
                "deck from a core deck"
            )
        else:
            gc_count = len(game_changer_names)
            if 1 <= gc_count <= 3:
                floor = 3
            elif gc_count > 3:
                floor = 4

        if two_card_combos > 0 or mass_land_denial:
            floor = max(floor, 4)

        # cEDH (bracket 5) is a meta/intent designation, never auto-assigned —
        # cap the suggested floor at 4 regardless of how many gates are crossed.
        floor = min(floor, 4)

        rationale.append(
            f"suggested floor: bracket {floor} — a SUGGESTION, never authoritative; "
            "the user declares the actual bracket, and cEDH (bracket 5) is a "
            "meta/intent designation that is never auto-assigned"
        )
        suggested_bracket = floor

    return BracketDetail(
        suggested_bracket=suggested_bracket,
        game_changer_count=len(game_changer_names),
        game_changers=game_changer_names,
        mass_land_denial=mass_land_denial,
        extra_turns=extra_turns,
        combos=combos,
        two_card_combos=two_card_combos,
        rationale=rationale,
        stale_data=stale_data,
        spellbook_available=spellbook_available,
    )

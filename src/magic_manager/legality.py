"""Deck-legality validation: a PURE, OFFLINE function of already-materialized
card data.

This module does no DB access and no network I/O — callers (``decks.py`` /
``cli.py``) resolve a deck's cards (JSON-decoding the ``cards`` table's
``legalities``/``keywords``/``color_identity`` TEXT columns into native
Python types) and hand the resulting list of dicts to :func:`validate`. That
keeps this module trivially testable offline and reusable anywhere a deck's
composition is already in hand (e.g. finalizing a ``deck_versions`` row).

``legalities`` on a card comes from the V16 ``cards.legalities`` column
(Scryfall's per-format map: ``legal``/``not_legal``/``banned``/``restricted``).
Rows synced before V16 carry ``legalities = NULL`` — :func:`validate` never
crashes on that; it emits an ``info``-severity freshness warning
(``code="stale_data"``) and treats missing legality data as "unknown" for
banlist purposes rather than failing the check.

The public shape is a :class:`LegalityReport` of :class:`Violation` rows,
JSON-serializable for storage in ``deck_versions.legality_report``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Singleton-format deck sizes. Commander/Brawl/Paupercommander all use the
# same "N-1 library + 1 commander" shape; the default target below is
# Commander's 100. Callers pass ``size_override`` for formats that deviate
# (e.g. some Brawl variants use 60/40).
_DEFAULT_COMMANDER_SIZE = 100

# Formats validated by the singleton/commander-shaped path.
_COMMANDER_LIKE_FORMATS = frozenset({"commander", "brawl", "paupercommander"})

# Formats validated by the 60-card constructed path.
_SIXTY_CARD_FORMATS = frozenset({
    "standard", "pioneer", "modern", "legacy", "vintage",
    "pauper", "premodern", "oldschool",
})

_SIXTY_MIN_MAIN = 60
_SIXTY_MAX_SIDE = 15
_SIXTY_MAX_COPIES = 4


@dataclass
class Violation:
    """One rule violation (or informational note) surfaced by :func:`validate`.

    ``code`` is a stable machine identifier (e.g. ``"deck_size"``,
    ``"singleton"``, ``"color_identity"``, ``"banned"``, ``"restricted"``,
    ``"commander_eligibility"``, ``"stale_data"``, ``"companion_rule"``,
    ``"unknown_format"``) — callers can filter/group on it without parsing
    ``message``. ``severity`` is ``"error"`` (makes the deck illegal),
    ``"warning"``, or ``"info"``. ``cards`` lists the affected card names;
    empty for whole-deck violations (e.g. deck size).
    """

    code: str
    severity: str
    message: str
    cards: list[str] = field(default_factory=list)


@dataclass
class LegalityReport:
    """The full result of validating a deck against one format.

    ``legal`` is derived (never set directly by callers of this dataclass):
    ``True`` iff no violation has ``severity == "error"``. ``checked_count``
    is the number of distinct (non-token) cards examined.
    """

    format: str
    legal: bool
    violations: list[Violation]
    checked_count: int

    def to_json(self) -> dict:
        """Serialize to a plain dict, suitable for ``json.dumps`` and storage
        in ``deck_versions.legality_report``."""
        return {
            "format": self.format,
            "legal": self.legal,
            "checked_count": self.checked_count,
            "violations": [
                {
                    "code": v.code,
                    "severity": v.severity,
                    "message": v.message,
                    "cards": list(v.cards),
                }
                for v in self.violations
            ],
        }

    @classmethod
    def from_json(cls, d: dict) -> LegalityReport:
        """Inverse of :meth:`to_json`."""
        return cls(
            format=d["format"],
            legal=d["legal"],
            checked_count=d["checked_count"],
            violations=[
                Violation(
                    code=v["code"],
                    severity=v["severity"],
                    message=v["message"],
                    cards=list(v.get("cards") or []),
                )
                for v in d.get("violations", [])
            ],
        )


# ---------- shared helpers ----------

def _as_list(v) -> list:
    """Coerce a possibly-``None`` list-shaped field to a list."""
    return v if v is not None else []


def _as_text(v) -> str:
    """Coerce a possibly-``None`` text field to a string."""
    return v if v is not None else ""


def _name(card: dict) -> str:
    """Coerce a card's ``name`` to ``str`` (defensive against a missing key)."""
    return str(card.get("name") or "")


def _is_basic_land(card: dict) -> bool:
    """A basic land is any card whose type line contains the word "Basic"
    (case-insensitive) — exempt from copy limits and singleton."""
    return "basic" in _as_text(card.get("type_line")).lower()


def _non_token_cards(cards: list[dict]) -> list[dict]:
    """Every card NOT on the ``'token'`` board — tokens ride the deck but
    aren't part of the legal list and are excluded from all counting/checking."""
    return [c for c in cards if c.get("board") != "token"]


def _freshness_violation(cards: list[dict]) -> Violation | None:
    """An ``info`` violation if any non-token card has no synced legality
    data (``legalities`` is ``None`` or an empty dict) — i.e. it was synced
    before the V16 migration. ``None`` if every card has legality data."""
    stale = [c for c in cards if not c.get("legalities")]
    if not stale:
        return None
    return Violation(
        code="stale_data",
        severity="info",
        message=(
            f"{len(stale)} card(s) have no synced legality data; run "
            "`mm set sync` — banlist checks may be incomplete"
        ),
        cards=[],
    )


def _card_legality(card: dict, format: str) -> str | None:
    """The card's legality status for ``format``, or ``None`` if unknown
    (missing/empty ``legalities``)."""
    legalities = card.get("legalities")
    if not legalities:
        return None
    return legalities.get(format)


# ---------- commander-shaped validation ----------

def _validate_commander(cards: list[dict], size_override: int | None) -> list[Violation]:
    """Commander/Brawl/Paupercommander singleton-format rules.

    See the module-level rule doc in the calling skill spec: deck size (exact
    100, or ``size_override``), commander presence + eligibility, singleton,
    color identity, banlist, and a companion-presence note.
    """
    violations: list[Violation] = []
    non_token = _non_token_cards(cards)

    # Deck size: exact target across all non-token boards.
    target = size_override if size_override is not None else _DEFAULT_COMMANDER_SIZE
    total = sum(c.get("count", 0) for c in non_token)
    if total != target:
        violations.append(Violation(
            code="deck_size",
            severity="error",
            message=f"deck has {total} card(s); commander decks must be exactly {target}",
            cards=[],
        ))

    # Commander presence + eligibility.
    commanders = [c for c in non_token if c.get("board") == "commander"]
    if not commanders:
        violations.append(Violation(
            code="commander_eligibility",
            severity="error",
            message="no commander designated",
            cards=[],
        ))
    else:
        for c in commanders:
            type_line = _as_text(c.get("type_line")).lower()
            oracle_text = _as_text(c.get("oracle_text")).lower()
            eligible = (
                ("legendary" in type_line and "creature" in type_line)
                or "can be your commander" in oracle_text
                or "background" in type_line
            )
            if not eligible:
                violations.append(Violation(
                    code="commander_eligibility",
                    severity="error",
                    message=f"{_name(c)} is not eligible to be a commander",
                    cards=[_name(c)],
                ))

    # Singleton: group by name (basics exempt) across all boards.
    name_counts: dict[str, int] = {}
    for c in non_token:
        if _is_basic_land(c):
            continue
        name = _name(c)
        name_counts[name] = name_counts.get(name, 0) + c.get("count", 0)
    dupes = sorted(name for name, n in name_counts.items() if n > 1)
    if dupes:
        violations.append(Violation(
            code="singleton",
            severity="error",
            message=f"{len(dupes)} card(s) exceed the singleton limit (max 1 copy)",
            cards=dupes,
        ))

    # Color identity: union of the commander's (and any Background's) identity.
    identity: set[str] = set()
    for c in commanders:
        identity.update(_as_list(c.get("color_identity")))
    off_identity: list[str] = []
    for c in non_token:
        if c.get("board") == "commander":
            continue
        card_identity = set(_as_list(c.get("color_identity")))
        if not card_identity.issubset(identity):
            off_identity.append(_name(c))
    if off_identity:
        violations.append(Violation(
            code="color_identity",
            severity="error",
            message=(
                f"{len(off_identity)} card(s) fall outside the commander's "
                f"color identity ({''.join(sorted(identity)) or 'colorless'})"
            ),
            cards=sorted(set(off_identity)),
        ))

    # Banlist (commander has no "restricted").
    banned: list[str] = []
    for c in non_token:
        if _card_legality(c, "commander") == "banned":
            banned.append(_name(c))
    if banned:
        violations.append(Violation(
            code="banned",
            severity="error",
            message=f"{len(banned)} card(s) are banned in commander",
            cards=sorted(set(banned)),
        ))

    # Companion presence (informational only — the deckbuilding restriction
    # on the companion card itself is not deeply validated here).
    companions = [
        _name(c) for c in non_token
        if "Companion" in _as_list(c.get("keywords"))
        and c.get("board") in ("side", "maybe")
    ]
    if companions:
        violations.append(Violation(
            code="companion_rule",
            severity="info",
            message=(
                "a companion is present; its deckbuilding restriction is not "
                "automatically checked"
            ),
            cards=sorted(set(companions)),
        ))

    return violations


# ---------- 60-card constructed validation ----------

def _validate_sixty(
    cards: list[dict], format: str, size_override: int | None
) -> list[Violation]:
    """Standard/Pioneer/Modern/Legacy/Vintage/Pauper/Premodern/Oldschool rules:
    deck size, sideboard size, copy limit (incl. Vintage-restricted max-1),
    banlist, and (Pauper only) commons-only legality."""
    violations: list[Violation] = []
    non_token = _non_token_cards(cards)

    main = [c for c in non_token if c.get("board") == "main"]
    side = [c for c in non_token if c.get("board") == "side"]

    main_total = sum(c.get("count", 0) for c in main)
    min_main = size_override if size_override is not None else _SIXTY_MIN_MAIN
    if main_total < min_main:
        violations.append(Violation(
            code="deck_size",
            severity="error",
            message=f"main deck has {main_total} card(s); minimum is {min_main}",
            cards=[],
        ))

    side_total = sum(c.get("count", 0) for c in side)
    if side_total > _SIXTY_MAX_SIDE:
        violations.append(Violation(
            code="deck_size",
            severity="error",
            message=f"sideboard has {side_total} card(s); maximum is {_SIXTY_MAX_SIDE}",
            cards=[],
        ))

    # Copy limit: group by name across main+side (basics exempt).
    name_counts: dict[str, int] = {}
    for c in main + side:
        if _is_basic_land(c):
            continue
        name = _name(c)
        name_counts[name] = name_counts.get(name, 0) + c.get("count", 0)

    over_limit: list[str] = []
    restricted_violations: list[str] = []
    banned: list[str] = []
    pauper_illegal: list[str] = []

    # Card lookup by name for legality checks (first occurrence wins; a
    # printing's legality doesn't vary by which copy, only by name).
    by_name: dict[str, dict] = {}
    for c in main + side:
        by_name.setdefault(_name(c), c)

    for name, count in name_counts.items():
        card = by_name.get(name, {})
        status = _card_legality(card, format)
        if status == "restricted":
            # Vintage-only: max 1 copy.
            if count > 1:
                restricted_violations.append(name)
            continue
        if count > _SIXTY_MAX_COPIES:
            over_limit.append(name)

    for name, card in by_name.items():
        status = _card_legality(card, format)
        if status == "banned":
            banned.append(name)
        elif format == "pauper" and status == "not_legal":
            pauper_illegal.append(name)

    if over_limit:
        violations.append(Violation(
            code="copies",
            severity="error",
            message=f"{len(over_limit)} card(s) exceed the {_SIXTY_MAX_COPIES}-copy limit",
            cards=sorted(set(over_limit)),
        ))

    if restricted_violations:
        violations.append(Violation(
            code="restricted",
            severity="error",
            message=(
                f"{len(restricted_violations)} restricted card(s) exceed the "
                "1-copy limit"
            ),
            cards=sorted(set(restricted_violations)),
        ))

    if banned:
        violations.append(Violation(
            code="banned",
            severity="error",
            message=f"{len(banned)} card(s) are banned in {format}",
            cards=sorted(set(banned)),
        ))

    if pauper_illegal:
        violations.append(Violation(
            code="banned",
            severity="error",
            message="not legal in pauper (commons only)",
            cards=sorted(set(pauper_illegal)),
        ))

    return violations


# ---------- public entry point ----------

def validate(
    cards: list[dict], *, format: str, size_override: int | None = None
) -> LegalityReport:
    """Validate a materialized deck against ``format``'s deckbuilding rules.

    ``cards`` is the full board (all boards, including ``'token'`` — token
    rows are excluded from every check internally). ``format`` is lowercased
    before dispatch. ``size_override`` overrides the format's default exact
    (commander-shaped) or minimum (60-card) deck size — for house-rule
    variants (e.g. a smaller Brawl pod, a Commander bracket house rule).

    Unhandled formats return ``legal=True`` with a single ``info`` violation
    (``code="unknown_format"``) rather than raising — an unvalidated format
    is not the same as an illegal deck.
    """
    fmt = format.lower()
    non_token = _non_token_cards(cards)

    violations: list[Violation] = []
    freshness = _freshness_violation(non_token)
    if freshness is not None:
        violations.append(freshness)

    if fmt in _COMMANDER_LIKE_FORMATS:
        violations.extend(_validate_commander(cards, size_override))
    elif fmt in _SIXTY_CARD_FORMATS:
        violations.extend(_validate_sixty(cards, fmt, size_override))
    else:
        violations.append(Violation(
            code="unknown_format",
            severity="info",
            message=f"format {format!r} is not validated",
            cards=[],
        ))

    legal = not any(v.severity == "error" for v in violations)
    return LegalityReport(
        format=format,
        legal=legal,
        violations=violations,
        checked_count=len(non_token),
    )

"""TCGplayer Mass Entry text format.

    <qty> <Product Name> [<SETCODE>] <CN>
    1 Lightning Bolt [SLD] 84
    1 Joshua, Phoenix's Dominant (Borderless) [FIN] 397
    1 Blessing of the Oracle - Akroma's Will (Showcase) [FCA] 21
    1 Stiltzkin, Moogle Merchant (Borderless) (Chocobo Track Foil) [FIN] 565
    1 Plains (0572) (Surge Foil) [FIN] 572
    1 Lightning, Army of One (0320) (Borderless) [FIN] 320

Per TCGplayer's "Getting Started With Mass Entry" help article: the set
identifier is the bracketed UPPERCASE set code, followed by the collector
number after the bracket. Quantity at the front, **product name** in the
middle.

The product name is NOT the same as the Scryfall card name. TCGplayer's
catalog labels alt-treatment prints with parenthetical suffix tokens and
renames UB-reskin cards to use the flavor name. Without these renames,
mass entry matches a default print that may not exist in our intended
set/CN, and the row is rejected. Empirical rules verified 2026-06-06
against the FIN family on TCGplayer:

**Name transforms** (applied before suffixes):

- Double-faced cards (``name`` contains ``" // "``) — emit only the front
  face. TCGplayer's catalog never includes the back half in product names.
- Reskin (``flavor_name`` set, e.g. all FCA prints) — emit
  ``<flavor_name> - <oracle_name>``. Reskins always carry a ``(Showcase)``
  suffix on TCGplayer.

**Suffix tokens** (in this order, separated by spaces):

- Treatment frame (mutually exclusive with one another):
    - ``border_color == 'borderless'``        → ``(Borderless)``
    - ``frame_effects`` contains ``showcase`` → ``(Showcase)``
    - ``frame_effects`` contains ``extendedart`` → ``(Extended Art)``
    - reskin (always)                         → ``(Showcase)``
- Foil-sheet override (in addition to the treatment, if any):
    - ``promo_types`` contains ``chocobotrackfoil`` → ``(Chocobo Track Foil)``
    - ``promo_types`` contains ``surgefoil``       → ``(Surge Foil)``
    - ``promo_types`` contains ``neonink``         → ``(Neon Ink <Color>)``
      via per-(set, CN) lookup in ``_NEON_INK_COLORS`` (TCGplayer files
      each neon-ink color as a distinct product). Falls back to bare
      ``(Neon Ink)`` for unmapped (set, CN) pairs.
    - ``promo_types`` contains ``serialized``      → ``(Serial Numbered)``
      (Scryfall's term is "serialized"; TCGplayer's product label is
      "Serial Numbered" — translate at emit time).

**Collector-number disambiguation prefix** ``(NNNN)``:

- Inserted between the name and the first suffix token, but ONLY when
  another printing in the SAME SET has the same product-name string.
  The CN is zero-padded to 4 digits (Lightning, Army of One 320 →
  ``(0320)``). Letter-suffix CNs (e.g. ``551a``) keep the full string
  intact, zero-padding only the leading numeric portion (→ ``(0551a)``).
- Collision detection runs against the WHOLE cards table for that set
  (not just rows being exported), because TCGplayer rejects ambiguous
  matches against its full catalog regardless of what's in our paste.
  E.g. Lightning, Army of One has two borderless prints in FIN (320,
  400) — both need ``(0320)``/``(0400)`` even if only one is in the
  current export.
- Stiltzkin (FIN 565) has only one borderless+chocobo-track-foil print,
  so the product name is just ``Stiltzkin, Moogle Merchant (Borderless)
  (Chocobo Track Foil)`` — no CN prefix. Mass entry's "more specificity
  is OK" tolerance does NOT extend to redundant CN prefixes; adding
  ``(0565)`` rejects the row. The prefix is only for actual collisions.
- Basic lands ALWAYS get the CN prefix when there's any suffix, even if
  the suffix-string is unique on its own. TCGplayer's catalog files
  ``Plains (0572) (Surge Foil)`` rather than ``Plains (Surge Foil)``,
  presumably because the bare-name ``Plains`` collides with multiple
  base prints in the same set and TCGplayer's matcher gives up rather
  than disambiguate. ``_is_basic_land()`` detects via ``type_line``.

**Foil/nonfoil is NOT marked per-line.** TCGplayer's Mass Entry UI exposes
a foil-vs-nonfoil control next to the paste box, applied to the whole
batch on submit. Mixed-finish carts: paste once, then run TCGplayer's
cart optimizer (it picks finish per row based on seller listings). The
``missing-from-set`` orchestrator emits a single combined file because
the optimizer handles finish selection downstream.

ManaPool consumes Moxfield-format directly (see ``moxfield.py`` and the
alias in ``__init__.py``); ManaPool's bulk-add parses the ``*F*``
per-line foil marker (Moxfield's documented import token), so it stays
single-block. Don't confuse the two.
"""

from __future__ import annotations

import json
import re

from .. import db


def build(rows) -> str:
    # Collision detection: for every set involved, find which (set, base
    # product name) pairs have multiple printings. Those need the (NNNN)
    # prefix to be unambiguous on TCGplayer.
    sets_in_play = {(r.card.get("set") or "").lower() for r in rows}
    collisions = _collision_map(sets_in_play)

    out = []
    for r in rows:
        set_code = (r.card.get("set") or "").upper()
        cn = r.card.get("collector_number") or ""
        base = _base_product_name(r.card)

        # Insert (NNNN) when there's a same-set collision on the product-
        # name string OR when this is a basic land with any suffix. Basic
        # lands always need the CN prefix on TCGplayer because the bare
        # name collides with the regular printings of the same land
        # regardless of which suffix variant we want.
        needs_cn_prefix = _has_suffix(base) and (
            (set_code, base) in collisions
            or _is_basic_land(r.card)
        )
        if needs_cn_prefix:
            product = _insert_cn_prefix(base, cn)
        else:
            product = base

        if set_code and cn:
            out.append(f"{r.quantity} {product} [{set_code}] {cn}")
        elif set_code:
            out.append(f"{r.quantity} {product} [{set_code}]")
        else:
            out.append(f"{r.quantity} {product}")

    text = "\n".join(out)
    return text + ("\n" if out else "")


def _is_basic_land(c: dict) -> bool:
    """True if this card's type_line indicates a basic land. Basic lands
    are a special case for the TCGplayer CN prefix — see ``build()``.
    """
    tl = (c.get("type_line") or "").lower()
    return "basic" in tl and "land" in tl


# Per-set neon-ink color mapping. Scryfall's ``promo_types`` carries a flat
# ``neonink`` token; TCGplayer files each color as a distinct product. The
# only known instance today is the Final Fantasy Traveling Chocobo 551
# series, hand-mapped from the FIN catalog page. Add new entries here when
# new sets ship neon-ink prints with multiple colors.
_NEON_INK_COLORS = {
    ("fin", "551a"): "(Neon Ink Yellow)",
    ("fin", "551b"): "(Neon Ink Pink)",
    ("fin", "551c"): "(Neon Ink Blue)",
    ("fin", "551d"): "(Neon Ink Green)",
}


def _neon_ink_color_token(c: dict) -> str | None:
    """Look up the per-CN neon-ink color suffix for this print. Returns
    ``None`` if the (set, CN) pair isn't in the hardcoded map; the caller
    falls back to a generic ``(Neon Ink)`` token.
    """
    set_code = (c.get("set") or "").lower()
    cn = c.get("collector_number") or ""
    return _NEON_INK_COLORS.get((set_code, cn))


def _collision_map(set_codes: set[str]) -> set[tuple[str, str]]:
    """Return the set of ``(SET_CODE_UPPER, base_product_name)`` keys that
    have more than one printing in the local cards table for the given
    sets. Used to decide whether a given row needs the ``(NNNN)`` prefix.
    """
    if not set_codes:
        return set()
    counts: dict[tuple[str, str], int] = {}
    placeholders = ",".join("?" for _ in set_codes)
    with db.connect() as conn:
        rows = conn.execute(
            f"""
            SELECT set_code, name, flavor_name, collector_number,
                   border_color, frame_effects, promo_types
            FROM cards
            WHERE set_code IN ({placeholders})
            """,
            tuple(set_codes),
        ).fetchall()
    for r in rows:
        d = {
            "set":              r["set_code"],
            "name":             r["name"],
            "flavor_name":      r["flavor_name"],
            "collector_number": r["collector_number"],
            "border_color":     r["border_color"],
            "frame_effects":    r["frame_effects"],
            "promo_types":      r["promo_types"],
        }
        base = _base_product_name(d)
        key = (r["set_code"].upper(), base)
        counts[key] = counts.get(key, 0) + 1
    return {k for k, n in counts.items() if n > 1}


def _base_product_name(c: dict) -> str:
    """Build the product name without any (NNNN) collision prefix.

    Returns ``<base name>[ <suffix tokens>]`` where suffix tokens are
    (Borderless) / (Showcase) / (Extended Art) and/or the foil-sheet
    qualifiers (Chocobo Track Foil) / (Surge Foil) / etc.
    """
    oracle = c.get("name") or ""
    if " // " in oracle:
        oracle = oracle.split(" // ", 1)[0]

    flavor = c.get("flavor_name")
    frame_effects = _decode_list(c.get("frame_effects"))
    promo_types = _decode_list(c.get("promo_types"))
    border_color = c.get("border_color")

    # Base name: reskin renames to "<flavor> - <oracle>", everything else
    # uses the oracle name (DFC front face, set above).
    if flavor:
        name = f"{flavor} - {oracle}"
    else:
        name = oracle

    # Treatment frame suffix (at most one).
    treatment_token: str | None = None
    if flavor:
        treatment_token = "(Showcase)"
    elif border_color == "borderless":
        treatment_token = "(Borderless)"
    elif "showcase" in frame_effects:
        treatment_token = "(Showcase)"
    elif "extendedart" in frame_effects:
        treatment_token = "(Extended Art)"

    # Foil-sheet qualifier (independent of treatment).
    foil_token: str | None = None
    if "chocobotrackfoil" in promo_types:
        foil_token = "(Chocobo Track Foil)"
    elif "surgefoil" in promo_types:
        foil_token = "(Surge Foil)"
    elif "neonink" in promo_types:
        foil_token = _neon_ink_color_token(c) or "(Neon Ink)"
    elif "serialized" in promo_types:
        foil_token = "(Serial Numbered)"

    suffix_parts = [t for t in (treatment_token, foil_token) if t]
    if suffix_parts:
        return f"{name} {' '.join(suffix_parts)}"
    return name


def _has_suffix(base: str) -> bool:
    """True when the base product name has at least one (...) suffix token,
    i.e. a place to slot the (NNNN) collision prefix in front of.
    """
    return base.rstrip().endswith(")")


def _insert_cn_prefix(base: str, cn: str) -> str:
    """Insert ``(NNNN)`` between the name and the first suffix token.

    ``base`` looks like ``"<name> (Suffix1)[ (Suffix2)]"``. Find the first
    `` (`` that opens a suffix and splice ``(NNNN) `` before it.
    """
    # The first " (" after the name marks the start of the suffix block.
    # `name` is everything before that; suffixes are everything after.
    idx = base.find(" (")
    if idx < 0:
        # Defensive: shouldn't happen if _has_suffix(base) was true.
        return base
    name_part = base[:idx]
    suffix_part = base[idx + 1:]  # drop the leading space; it'll come back
    return f"{name_part} ({_pad_cn(cn)}) {suffix_part}"


def _pad_cn(cn: str) -> str:
    """Zero-pad the leading numeric portion of a collector number to 4
    digits, preserving any letter suffix (e.g. ``551a`` → ``0551a``,
    ``320`` → ``0320``).
    """
    m = re.match(r"^(\d+)(.*)$", cn)
    if not m:
        return cn
    return f"{int(m.group(1)):04d}{m.group(2)}"


def _decode_list(v) -> list[str]:
    """frame_effects / promo_types are stored as JSON-encoded arrays on the
    cards table; some code paths may pass them through as Python lists
    already. Tolerate both and return a flat list of strings.
    """
    if not v:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except (json.JSONDecodeError, ValueError):
            pass
    return []

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
        # Skip tokens. TCGplayer catalogs them as "Foo // Bar Double-Sided
        # Token" with slashed CNs (e.g. "11 // 6"); the back-face data isn't
        # part of our cards row. Excluding tokens from the export keeps the
        # rest of the rows valid; the user can hand-add tokens if needed.
        type_line = (r.card.get("type_line") or "")
        if type_line.startswith("Token"):
            continue
        # TCGplayer files special-distribution promos under umbrella sets
        # (UMP for bundle inserts, BABP for buy-a-box promos, etc.) rather
        # than the parent expansion. The set-code in the Mass Entry line
        # must match TCGplayer's catalog set, NOT Scryfall's.
        scryfall_set = (r.card.get("set") or "").lower()
        tcg_set = _tcg_set_remap(r.card)
        set_code = (tcg_set or scryfall_set).upper()
        cn = r.card.get("collector_number") or ""
        base = _base_product_name(r.card)
        # Strip combining accents — TCGplayer's product titles use ASCII
        # equivalents (Lórien → Lorien, dûr → dur). The matcher rejects
        # accented versions even when the underlying card is the same.
        base = _strip_accents(base)

        # Insert (NNNN) when there's a same-set collision on the product-
        # name string OR when this is a basic land with any suffix. Basic
        # lands always need the CN prefix on TCGplayer because the bare
        # name collides with the regular printings of the same land
        # regardless of which suffix variant we want. Both rules are
        # disabled per-family for releases that use suffix combinations
        # alone for disambiguation (e.g. LTR uses `(Borderless Poster)` to
        # distinguish CN 731 from CN 305 without any numeric prefix).
        policy = _policy_for(r.card.get("set"))
        collision_match = (set_code, base) in collisions and policy["collision_cn_prefix"]
        basic_match = _is_basic_land(r.card) and policy["basic_land_cn_prefix"]
        needs_cn_prefix = _has_suffix(base) and (collision_match or basic_match)
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
# TCGplayer set-code remapping by promo_types. Some special-distribution
# promos are filed under umbrella sets ("Unique and Miscellaneous Promos",
# "Buy-A-Box Promos") rather than the Scryfall parent set. Mass Entry's
# (SETCODE) bracket must match TCGplayer's set, not Scryfall's, or the row
# is rejected as "card not found in this set."
#
# Empirically verified for LTR (2026-06-15):
#   - LTR 451 The One Ring (bundle) → set UMP
#   - LTR 398 Lórien Brooch (buyabox) → set BABP
#
# When a card has multiple promo_types that match different remaps, the
# first match in this dict wins (Python preserves insertion order). The
# defaults below are conservative — only entries the user has confirmed.
_PROMO_TYPE_TCG_SET = {
    "bundle":            "UMP",   # confirmed: LTR 451 The One Ring (LTR Bundle)
    "buyabox":           "BABP",  # confirmed: LTR 398 Lórien Brooch
    "playpromo":         "PTP",   # confirmed: LTR 299 Gandalf the White
    "tourney":           "PTP",   # confirmed: LTR 301 Sauron, the Dark Lord
    "storechampionship": "GAME",  # confirmed: LTR 300 Saruman of Many Colors
                                  # ("Game Day & Store Championship Promos")
}


# Scryfall-set-code remapping. Some sets in Scryfall's family graph don't
# exist as standalone TCGplayer sets at all — their cards are filed under
# umbrella promo sets. Keyed on the LOWERCASE Scryfall set code.
# Confirmed for LTR family (2026-06-15):
#   pltc (Tales of Middle-earth Deluxe Commander Kit) → UMP. Frodo,
#     Determined Hero PLTC 1 is filed under "Unique and Miscellaneous
#     Promos" at TCGplayer with bare oracle name and CN 1.
_SCRYFALL_SET_TCG_SET = {
    "pltc": "UMP",
}


def _tcg_set_remap(c: dict) -> str | None:
    """Return the TCGplayer set code if this card maps to a non-Scryfall
    umbrella set, else None (caller falls back to the Scryfall set code).

    Two layers of mapping, checked in order:
      1. Scryfall-set-code remap: some Scryfall sets don't exist as
         standalone TCGplayer sets (PLTC's cards live in UMP).
      2. Promo-type remap: cards with bundle / buyabox / playpromo etc.
         promo_types are filed under product-specific umbrella sets
         regardless of their Scryfall set membership.
    """
    scryfall_set = (c.get("set") or "").lower()
    if scryfall_set in _SCRYFALL_SET_TCG_SET:
        return _SCRYFALL_SET_TCG_SET[scryfall_set]
    for pt in _decode_list(c.get("promo_types")):
        if pt in _PROMO_TYPE_TCG_SET:
            return _PROMO_TYPE_TCG_SET[pt]
    return None


def _strip_accents(s: str) -> str:
    """Replace combining-accent characters with their ASCII equivalents.
    TCGplayer titles use 'Lorien' for Scryfall's 'Lórien', 'dur' for 'dûr'.
    """
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


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
        # Strip accents to match the form `build()` uses at lookup time.
        # Otherwise the key 'Barad-dûr (Borderless)' won't match the
        # post-strip lookup key 'Barad-dur (Borderless)'.
        base = _strip_accents(_base_product_name(d))
        key = (r["set_code"].upper(), base)
        counts[key] = counts.get(key, 0) + 1
    return {k for k, n in counts.items() if n > 1}


# Per-family TCGplayer naming policy. TCGplayer's product catalog doesn't use
# a single naming convention across all releases — different sets file
# alt-treatment prints differently. Defaults below are FIN's behavior (the
# original target); override per family via _FAMILY_POLICY.
#
# Empirical adjustments observed:
#   FIN family  : reskins suffix `(Showcase)`, borderless suffix `(Borderless)`,
#                 (NNNN) CN prefix on collisions.
#   LTR family  : reskins have NO `(Showcase)` suffix. Compound suffixes:
#                 borderless+showcase → `(Showcase)`, borderless+inverted →
#                 `(Borderless)`, borderless+poster → `(Borderless Poster)`.
#                 silverfoil+scroll → `(Showcase Scrolls)` (handled by the
#                 unobtainable filter so rarely emitted, but kept for
#                 completeness). No (NNNN) CN prefix needed.
#
# Add a new family entry by reading TCGplayer product titles for ~3 different
# treatment combinations, then wiring the rule mapping below.
_DEFAULT_POLICY = {
    # If True, reskin (flavor_name set) appends "(Showcase)" after the
    # "<flavor> - <oracle>" base name. False → bare base name.
    "reskin_showcase_suffix": True,
    # If True, basic-land + any-suffix gets the (NNNN) prefix unconditionally.
    "basic_land_cn_prefix": True,
    # If True, multi-printing-collisions get the (NNNN) prefix.
    "collision_cn_prefix": True,
}

_LTR_POLICY = {
    "reskin_showcase_suffix": False,
    # Basic lands DO get the (NNNN) CN prefix when a foil-sheet suffix is
    # present. Confirmed via Plains LTR 713 surgefoil: TCGplayer titles it
    # "Plains (0713) (Surge Foil)" — same convention as FIN.
    "basic_land_cn_prefix": True,
    # Collision prefix IS used for LTR same-name same-treatment pairs.
    # Confirmed via Barad-dur 340 vs 425 (both borderless inverted, no
    # other distinguishing suffix → TCGplayer titles them "Barad-dur (0340)
    # (Borderless)" and "Barad-dur (0425) (Borderless)"). Same for Minas
    # Tirith 341/420. The earlier Aragorn 317/434/741 case avoided the
    # prefix because each had a different suffix combination
    # (Showcase / Borderless / Borderless Poster).
    "collision_cn_prefix": True,
}

_FAMILY_POLICY: dict[str, dict] = {
    "ltr": _LTR_POLICY,
    "ltc": _LTR_POLICY,
    "pltr": _LTR_POLICY,
    "pltc": _LTR_POLICY,
    "altr": _LTR_POLICY,
    "altc": _LTR_POLICY,
    "tltr": _LTR_POLICY,
    "tltc": _LTR_POLICY,
    "fltr": _LTR_POLICY,
    "mltr": _LTR_POLICY,
}


def _policy_for(set_code: str) -> dict:
    return _FAMILY_POLICY.get((set_code or "").lower(), _DEFAULT_POLICY)


def _treatment_token(c: dict) -> str | None:
    """Compute the TCGplayer treatment-frame suffix for a card.

    Default rules (FIN-derived):
      - reskin (flavor_name)       → (Showcase) [if policy enables]
      - border_color borderless    → (Borderless)
      - frame_effects showcase     → (Showcase)
      - frame_effects extendedart  → (Extended Art)

    LTR family compound rules (override the simple ladder above):
      - borderless + showcase frame              → (Showcase)
      - borderless + inverted (no showcase)      → (Borderless)
      - borderless + poster                      → (Borderless Poster)
      - silverfoil + scroll showcase             → (Showcase Scrolls)
    """
    set_code = (c.get("set") or "").lower()
    flavor = c.get("flavor_name")
    border_color = c.get("border_color")
    frame_effects = _decode_list(c.get("frame_effects"))
    promo_types = _decode_list(c.get("promo_types"))
    policy = _policy_for(set_code)

    if set_code in _FAMILY_POLICY and _FAMILY_POLICY[set_code] is _LTR_POLICY:
        # LTR family compound treatment naming.
        # Reskin lands split by silverfoil presence:
        #   LTC 348-377 (no silverfoil): "<flavor> - <oracle>" with NO suffix
        #   LTC 515-519 (silverfoil reskin): "<flavor> - <oracle> (Borderless)"
        # TCGplayer treats the non-silverfoil reskin form as the canonical
        # product and adds a suffix only when the sheet/foil distinguishes it.
        if flavor:
            if "silverfoil" in promo_types:
                return "(Borderless)"
            return None
        if border_color == "borderless" and "poster" in promo_types:
            return "(Borderless Poster)"
        if border_color == "borderless" and "showcase" in frame_effects:
            return "(Showcase)"
        if border_color == "borderless":
            return "(Borderless)"
        if "scroll" in promo_types and "silverfoil" in promo_types:
            return "(Showcase Scrolls)"
        if "showcase" in frame_effects:
            return "(Showcase)"
        if "extendedart" in frame_effects:
            return "(Extended Art)"
        return None

    # Default ladder (FIN-style).
    if flavor and policy["reskin_showcase_suffix"]:
        return "(Showcase)"
    if border_color == "borderless":
        return "(Borderless)"
    if "showcase" in frame_effects:
        return "(Showcase)"
    if "extendedart" in frame_effects:
        return "(Extended Art)"
    return None


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
    promo_types = _decode_list(c.get("promo_types"))

    # Base name: reskin renames to "<flavor> - <oracle>", everything else
    # uses the oracle name (DFC front face, set above).
    if flavor:
        name = f"{flavor} - {oracle}"
    else:
        name = oracle

    treatment_token = _treatment_token(c)

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

    # Distribution-product qualifier (independent of treatment + foil).
    # TCGplayer appends a "(<Set> Bundle)" / "(<Set> Buy-A-Box)" /
    # "(<Set> Promo Pack)" suffix to identify which physical product
    # contained the print, AFTER the treatment and foil tokens.
    # Confirmed for LTR bundle: "The One Ring (Borderless) (LTR Bundle)"
    # at TCGplayer set UMP. The set token in the suffix uses the Scryfall
    # parent expansion code, NOT the remapped TCGplayer set code.
    distribution_token: str | None = None
    if "bundle" in promo_types:
        distribution_token = f"({(c.get('set') or '').upper()} Bundle)"

    suffix_parts = [t for t in (treatment_token, foil_token, distribution_token) if t]
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

"""Compute the user-facing ``treatment`` keyword string for a printing.

Single source of truth for the keyword space. Called from the XLSX writer,
the markdown writer, the intake REPL feedback, and the ``mm scryfall``
ad-hoc query tool, so all surfaces show the same code for the same card.

The keyword space is fixed at six codes (``b``, ``fa``, ``shw``, ``ext``,
``sm``, ``ff``) per the V1.5 design. See ``docs/scryfall-printing-treatments.md``
for the full rationale, audit data, and worked examples.
"""

from __future__ import annotations

import json
from typing import Any, Iterable


# Promo-type tags that all visually mean "non-standard foil finish."
# Collapsed under a single user-facing keyword (``ff``) because they don't
# co-occur on the same card and the user doesn't need to distinguish e.g.
# surgefoil from rainbowfoil at-a-glance — Scryfall URL has the detail.
FANCY_FOIL_PROMO_TYPES = frozenset({
    "surgefoil", "rainbowfoil", "firstplacefoil", "raisedfoil",
    "doublerainbow", "confettifoil", "fracturefoil", "ripplefoil",
    "galaxyfoil", "oilslick", "texturedfoil", "halofoil", "dazzlefoil",
    "dragonscalefoil", "cosmicfoil", "silverfoil", "chocobotrackfoil",
    "gilded", "neonink", "embossed", "manafoil", "textured",
})


def _as_list(v: Any) -> list[str]:
    """Coerce a card-row value to a list of strings.

    Card rows may carry these fields as Python lists (when fed straight from
    Scryfall) or as JSON-encoded TEXT (when read from our SQLite ``cards``
    table). Handle both transparently.
    """
    if v is None:
        return []
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                return [str(x) for x in parsed] if isinstance(parsed, list) else [s]
            except json.JSONDecodeError:
                return [s]
        return [s]
    if isinstance(v, Iterable):
        return [str(x) for x in v]
    return [str(v)]


def _row_get(row, key, default=None):
    """Read a field from either a dict (Scryfall API) or a sqlite3.Row.

    sqlite3.Row supports ``row[key]`` but not ``row.get(key)``, so we
    duck-type on the absence of ``.get``. ``key`` must exist as a column
    when the row is a sqlite3.Row — callers are expected to pull all of
    {frame_effects, full_art, promo_types} in their SELECT.
    """
    if hasattr(row, "get"):
        return row.get(key, default)
    try:
        v = row[key]
    except (KeyError, IndexError):
        return default
    return v if v is not None else default


def compute_treatment(card_row) -> str:
    """Return the ``|``-delimited treatment keyword string for a printing.

    Accepts either a Scryfall API response dict or a sqlite3.Row from our
    local ``cards`` table — the only fields read are:
    ``frame_effects``, ``full_art``, ``promo_types``.

    Returns an empty string for standard prints. Codes are emitted in a
    fixed visual-prominence order so the same printing always renders the
    same string.
    """
    fes = {x.lower() for x in _as_list(_row_get(card_row, "frame_effects"))}
    pts = {x.lower() for x in _as_list(_row_get(card_row, "promo_types"))}
    fa = bool(_row_get(card_row, "full_art"))

    codes: list[str] = []

    # Frame-treatment axis. ``b`` and ``fa`` are mutually exclusive (b takes
    # precedence when ``inverted`` is present, since that's the more specific
    # signal — see Q1 in the V1.5 plan and the printing-treatments doc).
    if "inverted" in fes:
        codes.append("b")
    elif fa and "showcase" not in fes:
        # Pure full-art (FDN starter-collection, Zendikar-style basic lands).
        # Suppressed when ``showcase`` is also present because the showcase
        # frame already conveys the visual difference and ``fa`` would be
        # redundant noise on Strixhaven Mystical Archive borderless prints.
        codes.append("fa")

    # Showcase is orthogonal to the b/fa axis. Comic-style SPM premiums
    # legitimately have both ``inverted`` and ``showcase``.
    if "showcase" in fes:
        codes.append("shw")

    if "extendedart" in fes:
        codes.append("ext")

    # Sourcematerial = UB reskin sheet (FCA / MAR / PZA). Always coincides
    # with at least one visual flag in our audit, but the user explicitly
    # wants it called out as a primary signal because the conceptual category
    # ("UB-themed reprint sheet") isn't recoverable from frame fields alone.
    if "sourcematerial" in pts:
        codes.append("sm")

    if "etched" in fes or pts & FANCY_FOIL_PROMO_TYPES:
        codes.append("ff")

    return "|".join(codes)


# Public legend, used by the XLSX/MD writers and the skills.
LEGEND: tuple[tuple[str, str], ...] = (
    ("b",   "modern overlay/bleed treatment — text/UI on bleeding art "
            "(reskin sheets, modern booster-fun premiums, art series)"),
    ("fa",  "art-extended frame — art panel reaches card edges, "
            "standard text box (FDN starter-collection, Zendikar lands)"),
    ("shw", "themed UI elements — Mystical Archive, BLB storybook, "
            "Spider-Man comic title bars, etc. (orthogonal to b)"),
    ("ext", "extended art — art panel extends past normal text-box edges, "
            "standard frame otherwise"),
    ("sm",  "Universes Beyond reskin sheet — FCA, MAR, PZA "
            "(sourcematerial promo type)"),
    ("ff",  "fancy foil finish — surgefoil, rainbowfoil, fracturefoil, "
            "etched, etc. (collapsed under one keyword)"),
)

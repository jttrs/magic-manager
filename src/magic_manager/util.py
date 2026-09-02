"""Small shared helpers with no domain dependencies.

Consolidates formatters/sort-keys that had drifted into 3+ ad-hoc copies across
cli.py, selectors.py, and scripts/. Kept dependency-free so both the package and
the standalone scripts can import it.
"""

from __future__ import annotations

import json
import re

_CN_RE = re.compile(r"^(\d+)(.*)$")

# MTG's canonical color order. Multicolor collapses to 'M', colorless to 'C'.
WUBRG_ORDER = "WUBRG"


def format_color_identity(identity, *, collapse_multicolor: bool) -> str:
    """Render a color identity as a WUBRG-ordered code.

    ``identity`` is a list of color letters (``["W","G"]``) or the raw JSON
    string the DB stores (``'["W","G"]'``) — both accepted so callers can pass
    ``cards.color_identity`` straight through. Letters are filtered to
    ``{W,U,B,R,G}``, deduped, and ordered W→U→B→R→G.

    - Empty / colorless → ``"C"``.
    - ``collapse_multicolor=True`` (single-card convention): any 2+ colors
      render as ``"M"`` (the WUBRGM convention); one color renders as itself.
    - ``collapse_multicolor=False`` (deck/pack convention): the actual letters,
      e.g. white+green → ``"WG"``, five-color → ``"WUBRG"``.
    """
    if isinstance(identity, str):
        try:
            identity = json.loads(identity)
        except (ValueError, TypeError):
            identity = []
    letters = {c for c in (identity or []) if c in WUBRG_ORDER}
    if not letters:
        return "C"
    if collapse_multicolor and len(letters) >= 2:
        return "M"
    return "".join(c for c in WUBRG_ORDER if c in letters)


def cn_sort_key(cn: str | None) -> tuple[int, str]:
    """Sort key for collector numbers: numeric part first, then suffix.

    Orders ``1858 < 1858a < 1859`` and ``9 < 10`` (numeric, not lexicographic).
    Non-numeric or empty CNs sort first as ``(0, <cn>)``. Tolerates ``None``.

    Canonical implementation — previously duplicated as ``selectors._cn_sort_key``,
    a local ``_cn_key`` in ``cli.query_missing_set_cmd``, and
    ``scripts/foil_price_diff._cn_sort_key`` (all three verified to produce
    identical orderings before consolidation).
    """
    m = _CN_RE.match(cn or "")
    if not m:
        return (0, cn or "")
    return (int(m.group(1)), m.group(2))


def fmt_usd(v: float | None) -> str:
    """Render a USD amount as ``$X.XX``, or ``—`` when ``None``."""
    return f"${v:.2f}" if v is not None else "—"


# Default point size for all generated XLSX artifacts. openpyxl's built-in
# default (Calibri 11) renders too small; every worksheet writer calls
# apply_base_font_size() before save so cells inherit this.
XLSX_FONT_SIZE = 16


def apply_base_font_size(ws, size: int = XLSX_FONT_SIZE) -> None:
    """Bump every populated cell's font to ``size`` points, preserving all other
    font attributes (bold/italic/color/underline/strike/vertAlign).

    openpyxl won't let us change the effective default font on save (the Normal
    style mutation is ignored), so we set the size explicitly per cell. Idempotent
    and style-preserving — safe to call once on each worksheet just before
    ``wb.save(...)``. The ``openpyxl`` import is local so ``util`` stays
    dependency-free for the standalone scripts that only need the sort/format
    helpers.
    """
    from openpyxl.styles import Font
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is None:
                continue
            f = cell.font
            cell.font = Font(
                name=f.name, size=size, bold=f.bold, italic=f.italic,
                color=f.color, underline=f.underline, strike=f.strike,
                vertAlign=f.vertAlign,
            )

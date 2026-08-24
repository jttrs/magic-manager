"""Small shared helpers with no domain dependencies.

Consolidates formatters/sort-keys that had drifted into 3+ ad-hoc copies across
cli.py, selectors.py, and scripts/. Kept dependency-free so both the package and
the standalone scripts can import it.
"""

from __future__ import annotations

import re

_CN_RE = re.compile(r"^(\d+)(.*)$")


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

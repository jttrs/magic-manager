"""Canonical ownership queries — the single home for "how many / which of these
does the user own?" rolled up by grain (``scryfall_id`` or ``oracle_id``).

Consolidates two previously-separate SUM-grain queries that had drifted into
different modules: ``missing.owned_oracle_ids`` (oracle-grained set, scoped by
family set codes) and ``scripts/jumpstart_buildable._owned_totals``
(scryfall-grained dict, scoped by a scryfall_id list). Both are the same
``SUM(inventory.quantity) GROUP BY <grain>`` shape over DIFFERENT grains/scopes,
so they belong behind one parameterized helper.

Ownership counts INCLUDE copies pledged to built decks — a pledged card is
deconstructable, so it still counts toward "do I have this?". That matches the
semantics both original queries had (neither filtered on deck assignment).

NOT a home for ``family_status._owned_rows_for_codes``: that returns full
MaterializedRows via the selector engine to handle set_targets family unions
(e.g. spm ∪ mar) the selector grammar can't express as one term — a different
concern (row materialization, not grain counting) that stays cohesive in
``family_status`` alongside its only callers.
"""

from __future__ import annotations

from typing import Iterable, Literal

from . import db

Grain = Literal["scryfall_id", "oracle_id"]


def owned_counts(
    *,
    grain: Grain,
    scryfall_ids: Iterable[str] | None = None,
    family_codes: Iterable[str] | None = None,
    conn=None,
) -> dict[str, int]:
    """``{<grain-value>: total owned quantity}`` summed across finishes.

    Exactly ONE scope must be given:
    - ``scryfall_ids`` — restrict to these printings.
    - ``family_codes`` — restrict to printings whose ``LOWER(set_code)`` is in
      this set (callers pass already-resolved family codes).

    ``grain="scryfall_id"`` keys by printing; ``grain="oracle_id"`` keys by
    mechanically-unique card (NULL oracle_ids are skipped). Keys with no positive
    owned quantity are omitted (``GROUP BY`` drops absent rows; the ``if r["q"]``
    guard additionally drops any zero/NULL sum defensively).

    The ``grain="scryfall_id"`` + ``scryfall_ids`` combination queries
    ``inventory`` directly with NO join to ``cards`` — a small optimization
    matching the original ``_owned_totals`` (the inventory→cards FK means the
    join wouldn't change the result anyway). Every other combination joins
    ``cards`` (needed for ``oracle_id`` or the ``set_code`` scope).
    """
    if (scryfall_ids is None) == (family_codes is None):
        raise ValueError("pass exactly one of scryfall_ids / family_codes")

    def _run(c) -> dict[str, int]:
        if grain == "scryfall_id" and scryfall_ids is not None:
            ids = list(scryfall_ids)
            if not ids:
                return {}
            ph = ",".join("?" for _ in ids)
            rows = c.execute(
                f"SELECT scryfall_id AS k, SUM(quantity) AS q FROM inventory "
                f"WHERE scryfall_id IN ({ph}) GROUP BY scryfall_id",
                ids,
            ).fetchall()
            return {r["k"]: r["q"] for r in rows if r["q"]}

        # Joined path: need cards for oracle_id and/or the set_code scope.
        key_col = "c.oracle_id" if grain == "oracle_id" else "i.scryfall_id"
        where = ["i.quantity > 0"]
        params: list = []
        if grain == "oracle_id":
            where.append("c.oracle_id IS NOT NULL")
        if scryfall_ids is not None:
            ids = list(scryfall_ids)
            if not ids:
                return {}
            where.append(f"i.scryfall_id IN ({','.join('?' for _ in ids)})")
            params += ids
        else:
            codes = list(family_codes)  # type: ignore[arg-type]
            if not codes:
                return {}
            where.append(f"LOWER(c.set_code) IN ({','.join('?' for _ in codes)})")
            params += codes
        rows = c.execute(
            f"SELECT {key_col} AS k, SUM(i.quantity) AS q FROM inventory i "
            f"JOIN cards c ON c.scryfall_id = i.scryfall_id "
            f"WHERE {' AND '.join(where)} GROUP BY {key_col}",
            params,
        ).fetchall()
        return {r["k"]: r["q"] for r in rows if r["q"]}

    if conn is not None:
        return _run(conn)
    with db.connect() as c:
        return _run(c)


def owned_oracle_ids(family_codes: Iterable[str], *, conn=None) -> set[str]:
    """oracle_ids the user owns ANY printing/finish of, within the given family
    set codes (already lowercased by the caller). Thin convenience wrapper over
    :func:`owned_counts` — the set of keys with a positive owned count."""
    return set(owned_counts(grain="oracle_id", family_codes=family_codes, conn=conn))

"""Jumpstart front/title cards — quarantined from the ``cards`` table.

Jumpstart packs ship a decorative front/title card (e.g. "Scarlet", "DOOM")
that lives in its own Scryfall memorabilia set (``fmsc`` for Marvel ``msh``,
``jtla`` for Avatar ``tle``). The front card is NOT referenced in MTGJSON
deck JSON — the link is by NAME MATCH into the front-card set, via
``normalize_theme()``.

These cards must add to a Jumpstart pack's singles value and be available in
a bulk-output command, but must NEVER leak into ``set:*``/``missing-set``/
master-list/inventory queries. The isolation is structural: front cards live
ONLY in the dedicated ``front_cards`` table, never in ``cards`` — every query
that reads ``cards`` is automatically blind to them.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from . import db

if TYPE_CHECKING:
    from .selectors import MaterializedRow

# Sanctioned Mana Pool wrapper (rate-limited, 24h-cached, 429 backoff). Used
# ONLY as a price fallback for front cards below — never for the main `cards`
# table. See ``_manapool_prices``.
_MANAPOOL_SH = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "manapool-search" / "manapool.sh"
)


def normalize_theme(name: str) -> str:
    """Normalize a pack theme / front-card name for cross-source matching.

    ``s = name.strip().lower()``, then strip a trailing ``" (theme)"``. Maps
    all 51 MSH pack themes 1:1 to fmsc cards (``HYDRA`` → ``hydra``,
    ``Kang Dynasty`` → ``Kang Dynasty (Theme)``).
    """
    return name.strip().lower().removesuffix(" (theme)")


def front_set_code_for(anchor: str) -> str | None:
    """Return the memorabilia set code holding ``anchor``'s Jumpstart front
    cards (e.g. ``fmsc`` for ``msh``), or ``None`` if the family has none.

    Cached in ``settings`` under ``front_set:<anchor>`` — an empty cached
    value means "known-none". Best-effort: a Scryfall lookup/network failure
    returns ``None`` rather than raising.
    """
    anchor = anchor.lower()
    cache_key = f"front_set:{anchor}"
    with db.connect() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (cache_key,)
        ).fetchone()
        if row is not None:
            return row["value"] or None

    from . import sets as sets_mod

    try:
        r = sets_mod.resolve(anchor)
    except Exception:
        return None

    code = None
    for s in r.related:
        if s.get("set_type") == "memorabilia" and "jumpstart front cards" in (s.get("name") or "").lower():
            code = s["code"].lower()
            break

    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (cache_key, code or ""),
        )
    return code


def sync_front_cards(anchor: str) -> int:
    """Pull every printing in ``anchor``'s front-card set into ``front_cards``.

    Scryfall is the primary source. Because Scryfall carries no USD price for
    most front cards (fmsc/jtla are memorabilia it doesn't track), a second
    pass fills ``prices_usd`` from the Mana Pool catalog — but ONLY for front
    cards, and ONLY where Scryfall left the price NULL (Scryfall always wins
    when it has a price). ``price_source`` records the provenance.

    Best-effort: returns 0 (rather than raising) if the family has no
    front-card set or the Scryfall fetch fails. The Mana Pool fallback is
    itself best-effort — a failure there leaves the Scryfall-sourced rows
    intact.
    """
    code = front_set_code_for(anchor)
    if code is None:
        return 0

    from . import scryfall

    anchor_lower = anchor.lower()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n = 0
    try:
        with db.connect() as conn:
            for card in scryfall.search(f"e:{code} lang:en", unique="prints"):
                _upsert_front_card(conn, card, anchor=anchor_lower, now=now)
                n += 1
    except Exception:
        return 0

    _fill_manapool_prices(anchor_lower)
    return n


def _fill_manapool_prices(anchor: str) -> None:
    """Fallback-fill ``prices_usd`` for front cards Scryfall didn't price,
    using the Mana Pool catalog. GUARDED: this is the only place the Mana Pool
    price source touches the DB, and it writes ONLY to ``front_cards`` — the
    main ``cards`` table is never priced from Mana Pool. Best-effort; any
    failure is swallowed so the Scryfall-sourced rows survive.
    """
    with db.connect() as conn:
        unpriced = conn.execute(
            "SELECT scryfall_id FROM front_cards "
            "WHERE family_anchor = ? AND prices_usd IS NULL",
            (anchor,),
        ).fetchall()
    sids = [r["scryfall_id"] for r in unpriced if r["scryfall_id"]]
    if not sids:
        return

    prices = _manapool_prices(sids)  # {scryfall_id: usd_float}
    if not prices:
        return

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.connect() as conn:
        for sid, usd in prices.items():
            conn.execute(
                "UPDATE front_cards SET prices_usd = ?, price_source = 'manapool', "
                "fetched_at = ? WHERE scryfall_id = ? AND prices_usd IS NULL",
                (usd, now, sid),
            )


def _manapool_prices(scryfall_ids: list[str]) -> dict[str, float]:
    """Return ``{scryfall_id: market_usd}`` from the Mana Pool catalog for the
    given ids, skipping any without a usable price. Best-effort: returns ``{}``
    on any wrapper/parse failure. Uses the market price (falls back to the NM
    catalog price), in dollars.
    """
    if not _MANAPOOL_SH.exists() or not scryfall_ids:
        return {}
    try:
        res = subprocess.run(
            [str(_MANAPOOL_SH), "products", *scryfall_ids],
            capture_output=True, text=True, check=False,
        )
        if res.returncode != 0:
            return {}
        data = json.loads(res.stdout).get("data", [])
    except Exception:
        return {}

    out: dict[str, float] = {}
    for row in data:
        sid = row.get("scryfall_id")
        if not sid:
            continue
        cents = row.get("price_market")
        if cents is None:
            cents = row.get("price_cents_nm")
        if isinstance(cents, (int, float)) and cents > 0:
            out[sid] = round(cents / 100.0, 2)
    return out


def _upsert_front_card(conn: sqlite3.Connection, card: dict, *, anchor: str, now: str) -> None:
    name = card.get("name") or ""
    prices = card.get("prices") or {}
    usd = _f(prices.get("usd"))
    # Scryfall is the source of record for the price it does provide. Where it
    # has no price (usd is None), leave price_source NULL so the Mana Pool
    # fallback pass (_fill_manapool_prices) can claim the row. Re-running the
    # Scryfall pass intentionally resets prices_usd/price_source from Scryfall,
    # clearing any stale Mana Pool value before the fallback re-fills it.
    price_source = "scryfall" if usd is not None else None
    conn.execute(
        """
        INSERT INTO front_cards (
            scryfall_id, set_code, family_anchor, name, normalized_name,
            collector_number, prices_usd, prices_usd_foil, finishes,
            scryfall_uri, fetched_at, price_source
        ) VALUES (
            :scryfall_id, :set_code, :family_anchor, :name, :normalized_name,
            :collector_number, :prices_usd, :prices_usd_foil, :finishes,
            :scryfall_uri, :fetched_at, :price_source
        )
        ON CONFLICT(scryfall_id) DO UPDATE SET
            set_code          = excluded.set_code,
            family_anchor     = excluded.family_anchor,
            name              = excluded.name,
            normalized_name   = excluded.normalized_name,
            collector_number  = excluded.collector_number,
            prices_usd        = excluded.prices_usd,
            prices_usd_foil   = excluded.prices_usd_foil,
            finishes          = excluded.finishes,
            scryfall_uri      = excluded.scryfall_uri,
            fetched_at        = excluded.fetched_at,
            price_source      = excluded.price_source
        """,
        {
            "scryfall_id": card.get("id"),
            "set_code": (card.get("set") or "").lower(),
            "family_anchor": anchor,
            "name": name,
            "normalized_name": normalize_theme(name),
            "collector_number": card.get("collector_number"),
            "prices_usd": usd,
            "prices_usd_foil": _f(prices.get("usd_foil")),
            "finishes": json.dumps(card.get("finishes") or []),
            "scryfall_uri": card.get("scryfall_uri"),
            "fetched_at": now,
            "price_source": price_source,
        },
    )


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def front_card_for_theme(anchor: str, theme: str) -> sqlite3.Row | None:
    """Look up the cached front card matching ``theme`` within ``anchor``'s
    family, by normalized-name match. Returns ``None`` if not found."""
    with db.connect() as conn:
        return conn.execute(
            "SELECT * FROM front_cards WHERE family_anchor = ? AND normalized_name = ? LIMIT 1",
            (anchor.lower(), normalize_theme(theme)),
        ).fetchone()


def front_card_row(fc) -> MaterializedRow:
    """Build a ``MaterializedRow`` for a front-card row (as returned by
    ``front_card_for_theme``), so it can be appended alongside gameplay
    singles in an export.
    """
    from . import selectors

    finishes = json.loads(fc["finishes"]) if fc["finishes"] else []
    finish = "foil" if finishes == ["foil"] else "nonfoil"
    card = {
        "scryfall_id":      fc["scryfall_id"],
        "name":             fc["name"],
        "flavor_name":      None,
        "set":              fc["set_code"],
        "collector_number": fc["collector_number"],
        "rarity":           None,
        "prices_usd":       fc["prices_usd"],
        "prices_usd_foil":  fc["prices_usd_foil"],
        "cmc":              None,
        "type_line":        None,
        "mana_cost":        None,
        "frame_effects":    None,
        "full_art":         None,
        "promo_types":      None,
        "border_color":     None,
        "scryfall_uri":     fc["scryfall_uri"],
        "security_stamp":   None,
    }
    return selectors.MaterializedRow(
        scryfall_id=fc["scryfall_id"],
        quantity=1,
        finish=finish,
        card=card,
    )

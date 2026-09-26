"""EDHREC community-signal client + sync engine.

EDHREC has no official API. Its Next.js front-end fetches name-keyed JSON from
``json.edhrec.com/pages/…`` (the ``/pages/`` prefix is mandatory; there is no
``api.edhrec.com``). The join key on EDHREC is a **sanitized card name** — no
scryfall/oracle id anywhere — so integrating means: up-level a printing to its
oracle name, slugify it, fetch, then re-attach ``oracle_id`` on our side by
resolving names against the local ``cards`` table (lazy Scryfall by-name fill for
gaps).

Two layers live here, mirroring ``scryfall.py`` / ``mtgjson.py``:

  * **Client** — thin subprocess wrapper over ``.claude/skills/edhrec-search/
    edhrec.sh`` (rate-limit + 24h cache + 429 backoff). Never issues HTTP itself.
  * **Engine** — ``sync_commander`` / ``sync_card`` / ``sync_rankings``: fetch →
    persist the raw page (``edhrec_pages``) → parse cardlists → resolve names to
    oracle_ids → upsert the normalized tables → return an enriched report object
    the report script/CLI render.

The normalized tables (``edhrec_commander_cards`` etc.) are a rebuildable cache;
the raw ``edhrec_pages`` snapshot is the source of truth they're derived from.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import db, scryfall, sets, util

WRAPPER = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "edhrec-search" / "edhrec.sh"
)


class EdhrecError(RuntimeError):
    """Raised when the wrapper exits non-zero or returns a non-JSON body."""


# ---------- client ----------

def _run(args: list[str]) -> dict:
    if not WRAPPER.exists():
        raise EdhrecError(f"wrapper missing: {WRAPPER}")
    res = subprocess.run(
        [str(WRAPPER), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if res.returncode != 0:
        raise EdhrecError(
            f"edhrec.sh {' '.join(args)} exited {res.returncode}: "
            f"{res.stderr.strip() or res.stdout.strip()}"
        )
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise EdhrecError(f"non-JSON response from edhrec.sh: {e}") from e


def commander_page(slug: str) -> dict:
    """GET /pages/commanders/<slug>.json — the card-as-commander view."""
    return _run(["commander", slug])


def card_page(slug: str) -> dict:
    """GET /pages/cards/<slug>.json — the card-in-the-99 view."""
    return _run(["card", slug])


def commanders_ranking(timeframe: str = "week") -> dict:
    """GET /pages/commanders/<timeframe>.json — general commander rankings."""
    return _run(["commanders", timeframe])


def top_ranking(segment: str = "week") -> dict:
    """GET /pages/top/<segment>.json — top cards (week|month|year) or 'salt'."""
    return _run(["top", segment])


# ---------- slug + parse helpers ----------

def slugify(name: str) -> str:
    """Turn a card NAME into the EDHREC page slug.

    The canonical rule (matches EDHREC's front-end and the pyedhrec library):
    lowercase → strip apostrophes and commas → non-alphanumerics collapse to a
    single hyphen → trim leading/trailing hyphens. Double-faced ``A // B`` names
    use the FRONT face only (EDHREC pages a DFC under its front face).

    Examples::

        "Atraxa, Praetors' Voice" -> "atraxa-praetors-voice"
        "Ragavan, Nimble Pilferer" -> "ragavan-nimble-pilferer"
        "Jace, Vryn's Prodigy // Jace, Telepath Unbound" -> "jace-vryns-prodigy"
    """
    front = util.front_face(name)
    s = front.lower()
    s = s.replace("'", "").replace("’", "")  # straight + curly apostrophes
    s = s.replace(",", "")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def cardlists(page: dict) -> dict[str, list[dict]]:
    """Return ``{list_tag: [cardview, …]}`` from a page's nested cardlists.

    EDHREC nests the useful data at ``container.json_dict.cardlists`` — a list of
    ``{header, tag, cardviews}`` groups. This flattens it to a tag→cardviews map
    so callers don't re-walk the nesting. Tolerant of a missing container.
    """
    lists = (
        (page or {})
        .get("container", {})
        .get("json_dict", {})
        .get("cardlists")
        or []
    )
    return {cl.get("tag") or "": (cl.get("cardviews") or []) for cl in lists}


# Commander-page cardlist tags that are per-card recommendations (workflow A).
# Excludes the commander-page 'newcommanders'/'topcommanders' (those only appear
# on CARD pages, workflow B) — kept as the canonical set so a report can present
# every recommendation list.
COMMANDER_CARD_TAGS = (
    "newcards", "highsynergycards", "topcards", "gamechangers",
    "creatures", "instants", "sorceries", "utilityartifacts",
    "manaartifacts", "enchantments", "battles", "planeswalkers",
    "utilitylands", "lands",
)

# Card-page cardlist tags that list COMMANDERS running the card (workflow B).
CARD_COMMANDER_TAGS = ("topcommanders", "newcommanders")


# ---------- name -> oracle resolution ----------

def resolve_names_to_oracle(names: Iterable[str]) -> dict[str, dict]:
    """Map card NAMES → ``{oracle_id, scryfall_id, name}`` (oracle identity).

    Local-first: resolve against the ``cards`` table by name (free, offline).
    For names with no local row, one batched Scryfall ``/cards/collection``
    by-name call fills the gap and the results are upserted into ``cards`` so the
    metadata sticks for later (enrichment, pricing). Keys of the returned dict are
    the CASEFOLDED names so callers can look up case-insensitively; unresolved
    names are simply absent.
    """
    wanted = list(dict.fromkeys(n for n in names if n))
    if not wanted:
        return {}

    out: dict[str, dict] = {}

    def _record(name: str, oracle_id, scryfall_id) -> None:
        """Key the identity under BOTH the full name and the DFC front face.

        EDHREC pages a double-faced card under its FRONT face only ("Tergrid,
        God of Fright"), but Scryfall / our cards table store the full
        "Front // Back" name — so we index both casefolded forms, letting a
        front-face lookup (what EDHREC gives us) hit a full-name row. Won't
        clobber an existing entry that already has an oracle_id."""
        entry = {"oracle_id": oracle_id, "scryfall_id": scryfall_id, "name": name}
        for key in {(name or "").casefold(), util.front_face(name).casefold()}:
            if key not in out or (not out[key].get("oracle_id") and oracle_id):
                out[key] = entry

    with db.connect() as conn:
        placeholders = ",".join("?" for _ in wanted)
        # collate lower(name) so EDHREC's exact display names match our oracle names
        rows = conn.execute(
            f"SELECT scryfall_id, oracle_id, name FROM cards "
            f"WHERE name COLLATE NOCASE IN ({placeholders})",
            wanted,
        ).fetchall()
        for r in rows:
            _record(r["name"], r["oracle_id"], r["scryfall_id"])

        # DFC front-face pass: a name EDHREC gave as a front face ("Tergrid, God
        # of Fright") won't match a full "Front // Back" row via IN, so look those
        # still-missing names up in one batched query against the front-face slice
        # of the name.
        front_wanted = [n for n in wanted if n.casefold() not in out and " // " not in n]
        if front_wanted:
            ph = ",".join("?" for _ in front_wanted)
            rows = conn.execute(
                f"SELECT scryfall_id, oracle_id, name FROM cards "
                f"WHERE name LIKE '% // %' "
                f"AND substr(name, 1, instr(name, ' // ') - 1) COLLATE NOCASE IN ({ph})",
                front_wanted,
            ).fetchall()
            for r in rows:
                _record(r["name"], r["oracle_id"], r["scryfall_id"])

    missing = [n for n in wanted if n.casefold() not in out]
    if missing:
        found, _not_found = scryfall.collection([{"name": n} for n in missing])
        if found:
            with db.transaction() as conn:
                db.upsert_cards(conn, found)
            for c in found:
                _record(c.get("name"), c.get("oracle_id"), c.get("id"))
    return out


def resolve_oracle_name(ref: str) -> str:
    """Up-level a user card reference (a name, or a 'SET CN' printing) to its
    ORACLE name via Scryfall, so reprints all collapse to one EDHREC page.

    Accepts a bare name ("Sol Ring") or a printing "SET CN" ("cmm 425"). A
    printing is resolved via Scryfall's exact endpoint; a bare name is looked up
    by the fuzzy/named endpoint. Returns the oracle name (front face for DFCs).
    """
    parts = ref.split()
    # "SET CN" form: 2 tokens, second is a collector-number-ish token.
    if len(parts) == 2 and any(ch.isdigit() for ch in parts[1]):
        set_code, cn = parts[0].lower(), parts[1]
        found, _ = scryfall.collection([{"set": set_code, "collector_number": cn}])
        if found:
            return util.front_face(found[0].get("name") or ref)
    # bare name → Scryfall named (exact if possible; tolerant fuzzy fallback)
    try:
        card = scryfall.named(ref)
        return util.front_face(card.get("name") or ref)
    except scryfall.ScryfallError:
        # last resort: use the raw input; slugify still works for exact names
        return ref


def _inclusion_pct(num: int | None, pot: int | None) -> float | None:
    if not num or not pot:
        return None
    return round(100.0 * num / pot, 2)


# ---------- report objects ----------

@dataclass
class EnrichedCardRow:
    """One card in a report: EDHREC metrics + local metadata (filled downstream)."""
    name: str
    slug: str
    oracle_id: str | None
    list_tag: str
    num_decks: int | None = None
    potential_decks: int | None = None
    inclusion_pct: float | None = None
    synergy: float | None = None
    lift: float | None = None
    trend_zscore: float | None = None
    salt: float | None = None
    rank: int | None = None
    # local enrichment (populated by the report layer via lowest_price_by_oracle)
    type_line: str | None = None
    cmc: float | None = None
    mana_cost: str | None = None
    color_identity: list[str] | None = None  # decoded to a real list in enrich_rows
    rarity: str | None = None
    lowest_usd: float | None = None
    lowest_usd_foil: float | None = None


@dataclass
class SyncResult:
    """What a sync_* call persisted + a flat list of rows for the report layer."""
    kind: str                      # 'commander' | 'card' | 'rankings'
    slug: str
    name: str
    scope: str | None = None       # rankings only
    timeframe: str | None = None   # rankings only
    rows: list[EnrichedCardRow] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


# ---------- sync engines ----------

def _store_page(conn, *, page_type: str, slug: str, timeframe: str, page: dict, at: str) -> None:
    conn.execute(
        """
        INSERT INTO edhrec_pages (slug, page_type, timeframe, json, http_status, fetched_at)
        VALUES (:slug, :page_type, :timeframe, :json, 200, :at)
        ON CONFLICT(page_type, slug, timeframe) DO UPDATE SET
            json = excluded.json, http_status = excluded.http_status,
            fetched_at = excluded.fetched_at
        """,
        {"slug": slug, "page_type": page_type, "timeframe": timeframe,
         "json": json.dumps(page), "at": at},
    )


def sync_commander(commander_name: str) -> SyncResult:
    """Workflow A: fetch a commander page, persist it, and return its card rows.

    ``commander_name`` is the ORACLE name (caller resolves a printing to it first).
    Every recommendation cardlist (topcards, highsynergycards, creatures, …) is
    flattened into rows tagged with their list; oracle_ids are attached by
    resolving the card names. Rows are NOT yet locally enriched (the report layer
    does that via ``sets.lowest_price_by_oracle`` so pricing/staleness stays there).
    """
    slug = slugify(commander_name)
    page = commander_page(slug)
    at = db._utcnow_iso()
    header = page.get("header") or commander_name
    lists = cardlists(page)

    # Collect card names across all recommendation lists, resolve once.
    names: list[str] = []
    for tag in COMMANDER_CARD_TAGS:
        for cv in lists.get(tag, []):
            if cv.get("name"):
                names.append(cv["name"])
    names.append(commander_name)
    resolved = resolve_names_to_oracle(names)
    cmd_oid = resolved.get(commander_name.casefold(), {}).get("oracle_id")

    rows: list[EnrichedCardRow] = []
    with db.transaction() as conn:
        _store_page(conn, page_type="commander", slug=slug, timeframe="", page=page, at=at)
        for tag in COMMANDER_CARD_TAGS:
            for cv in lists.get(tag, []):
                name = cv.get("name")
                if not name:
                    continue
                oid = resolved.get(name.casefold(), {}).get("oracle_id")
                num, pot = cv.get("num_decks"), cv.get("potential_decks")
                pct = _inclusion_pct(num, pot)
                conn.execute(
                    """
                    INSERT INTO edhrec_commander_cards
                        (commander_oracle_id, commander_slug, commander_name,
                         card_oracle_id, card_slug, card_name, list_tag,
                         num_decks, potential_decks, inclusion_pct, synergy,
                         trend_zscore, fetched_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(commander_slug, card_slug, list_tag) DO UPDATE SET
                        commander_oracle_id=excluded.commander_oracle_id,
                        card_oracle_id=excluded.card_oracle_id,
                        num_decks=excluded.num_decks,
                        potential_decks=excluded.potential_decks,
                        inclusion_pct=excluded.inclusion_pct,
                        synergy=excluded.synergy,
                        trend_zscore=excluded.trend_zscore,
                        fetched_at=excluded.fetched_at
                    """,
                    (cmd_oid, slug, header, oid, cv.get("slug") or slugify(name),
                     name, tag, num, pot, pct, cv.get("synergy"),
                     cv.get("trend_zscore"), at),
                )
                rows.append(EnrichedCardRow(
                    name=name, slug=cv.get("slug") or slugify(name), oracle_id=oid,
                    list_tag=tag, num_decks=num, potential_decks=pot,
                    inclusion_pct=pct, synergy=cv.get("synergy"),
                    trend_zscore=cv.get("trend_zscore"),
                ))
    return SyncResult(kind="commander", slug=slug, name=header, rows=rows, raw=page)


def sync_card(card_name: str) -> SyncResult:
    """Workflow B: fetch a card page, persist it, return the commanders running it.

    ``card_name`` is the ORACLE name. Card-page ``topcommanders``/``newcommanders``
    cardviews carry deck counts but no synergy/lift, so those columns stay NULL.
    """
    slug = slugify(card_name)
    page = card_page(slug)
    at = db._utcnow_iso()
    header = page.get("header") or card_name
    lists = cardlists(page)

    names: list[str] = []
    for tag in CARD_COMMANDER_TAGS:
        for cv in lists.get(tag, []):
            if cv.get("name"):
                names.append(cv["name"])
    names.append(card_name)
    resolved = resolve_names_to_oracle(names)
    card_oid = resolved.get(card_name.casefold(), {}).get("oracle_id")

    rows: list[EnrichedCardRow] = []
    with db.transaction() as conn:
        _store_page(conn, page_type="card", slug=slug, timeframe="", page=page, at=at)
        for tag in CARD_COMMANDER_TAGS:
            for cv in lists.get(tag, []):
                name = cv.get("name")
                if not name:
                    continue
                oid = resolved.get(name.casefold(), {}).get("oracle_id")
                num, pot = cv.get("num_decks"), cv.get("potential_decks")
                pct = _inclusion_pct(num, pot)
                conn.execute(
                    """
                    INSERT INTO edhrec_card_commanders
                        (card_oracle_id, card_slug, card_name,
                         commander_oracle_id, commander_slug, commander_name,
                         list_tag, num_decks, potential_decks, inclusion_pct,
                         lift, fetched_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(card_slug, commander_slug, list_tag) DO UPDATE SET
                        card_oracle_id=excluded.card_oracle_id,
                        commander_oracle_id=excluded.commander_oracle_id,
                        num_decks=excluded.num_decks,
                        potential_decks=excluded.potential_decks,
                        inclusion_pct=excluded.inclusion_pct,
                        lift=excluded.lift,
                        fetched_at=excluded.fetched_at
                    """,
                    (card_oid, slug, header, oid, cv.get("slug") or slugify(name),
                     name, tag, num, pot, pct, cv.get("lift"), at),
                )
                rows.append(EnrichedCardRow(
                    name=name, slug=cv.get("slug") or slugify(name), oracle_id=oid,
                    list_tag=tag, num_decks=num, potential_decks=pot,
                    inclusion_pct=pct, lift=cv.get("lift"),
                ))
    return SyncResult(kind="card", slug=slug, name=header, rows=rows, raw=page)


# the set of valid ranking scopes accepted by sync_rankings
_RANKING_SCOPES = frozenset({"commanders", "cards", "salt"})


def sync_rankings(scope: str, timeframe: str = "week") -> SyncResult:
    """Workflow C: general rankings — 'commanders' | 'cards' | 'salt'.

    'commanders'/'cards' take a timeframe (week/month/year); 'salt' ignores it
    (the endpoint is ``/pages/top/salt.json``). Rank is taken from the cardview
    when present (commanders pages), else derived from array position (cards/salt).
    """
    if scope not in _RANKING_SCOPES:
        raise EdhrecError(f"unknown ranking scope {scope!r} (expected commanders|cards|salt)")

    if scope == "commanders":
        page = commanders_ranking(timeframe)
    elif scope == "salt":
        page = top_ranking("salt")
        timeframe = "all"
    else:  # cards
        page = top_ranking(timeframe)

    at = db._utcnow_iso()
    lists = cardlists(page)
    # rankings pages carry a single cardlist; take the first non-empty one.
    cardviews: list[dict] = next((cv for cv in lists.values() if cv), [])

    names = [cv["name"] for cv in cardviews if cv.get("name")]
    resolved = resolve_names_to_oracle(names)

    rows: list[EnrichedCardRow] = []
    with db.transaction() as conn:
        _store_page(conn, page_type=("commanders" if scope == "commanders" else "top"),
                    slug=scope, timeframe=timeframe, page=page, at=at)
        for i, cv in enumerate(cardviews, start=1):
            name = cv.get("name")
            if not name:
                continue
            oid = resolved.get(name.casefold(), {}).get("oracle_id")
            rank = cv.get("rank") or i
            conn.execute(
                """
                INSERT INTO edhrec_rankings
                    (scope, timeframe, entity_oracle_id, entity_slug, entity_name,
                     rank, num_decks, salt, trend_zscore, fetched_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(scope, timeframe, entity_slug) DO UPDATE SET
                    entity_oracle_id=excluded.entity_oracle_id,
                    entity_name=excluded.entity_name,
                    rank=excluded.rank,
                    num_decks=excluded.num_decks,
                    salt=excluded.salt,
                    trend_zscore=excluded.trend_zscore,
                    fetched_at=excluded.fetched_at
                """,
                (scope, timeframe, oid, cv.get("slug") or slugify(name), name,
                 rank, cv.get("num_decks"), cv.get("salt"), cv.get("trend_zscore"), at),
            )
            rows.append(EnrichedCardRow(
                name=name, slug=cv.get("slug") or slugify(name), oracle_id=oid,
                list_tag=scope, num_decks=cv.get("num_decks"),
                salt=cv.get("salt"), rank=rank, trend_zscore=cv.get("trend_zscore"),
            ))
    return SyncResult(kind="rankings", slug=scope, name=f"{scope} ({timeframe})",
                      scope=scope, timeframe=timeframe, rows=rows, raw=page)


def enrich_rows(rows: list[EnrichedCardRow]) -> list[EnrichedCardRow]:
    """Fill local metadata (type/cmc/mana/color/rarity + lowest USD) onto rows.

    Uses ``sets.lowest_price_by_oracle`` — the oracle-grain price/identity source
    of truth — for every row that resolved to an oracle_id. Rows that didn't
    resolve keep their EDHREC data and leave the local columns blank. Mutates and
    returns ``rows``.
    """
    oids = [r.oracle_id for r in rows if r.oracle_id]
    meta = sets.lowest_price_by_oracle(oids)
    for r in rows:
        m = meta.get(r.oracle_id or "")
        if not m:
            continue
        r.type_line = m.get("type_line")
        r.cmc = m.get("cmc")
        r.mana_cost = m.get("mana_cost")
        _ci = m.get("color_identity")
        r.color_identity = json.loads(_ci) if _ci else []
        r.rarity = m.get("rarity")
        r.lowest_usd = m.get("lowest_usd")
        r.lowest_usd_foil = m.get("lowest_usd_foil")
    return rows

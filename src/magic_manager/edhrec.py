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
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import db, legality, scryfall, scryfall_tags, sets, util

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


def color_ranking(color_slug: str, timeframe: str | None = None) -> dict:
    """GET /pages/commanders/<color-slug>[/<timeframe>].json — commanders of a
    color identity (e.g. ``mono-red``, ``azorius``, ``bant``, ``five-color``)."""
    path = f"commanders/{color_slug}"
    if timeframe:
        path += f"/{timeframe}"
    return _run(["raw", path])


def tag_ranking(tag_slug: str) -> dict:
    """GET /pages/tags/<slug>.json — the tag/theme/creature-type page (one
    namespace for both themes and typals); carries a ``topcommanders`` ranking
    list. Unlike color pages, tag pages do NOT accept a timeframe segment (a
    ``tags/<slug>/<tf>`` request 403s), so this is all-time only."""
    return _run(["raw", f"tags/{tag_slug}"])


def set_page(set_code: str) -> dict:
    """GET /pages/sets/<code>.json — a set's page; carries per-set-code
    ``commanders(<code>)`` ranking lists."""
    return _run(["raw", f"sets/{set_code.lower()}"])


# ---------- slug + parse helpers ----------

def slugify(name: str) -> str:
    """Turn a card NAME into the EDHREC page slug.

    The canonical rule (matches EDHREC's front-end and the pyedhrec library):
    ASCII-fold accents → lowercase → strip apostrophes and commas →
    non-alphanumerics collapse to a single hyphen → trim leading/trailing
    hyphens. Double-faced ``A // B`` names use the FRONT face only (EDHREC pages
    a DFC under its front face).

    The accent fold (NFKD-decompose, then drop combining marks) is load-bearing:
    EDHREC folds ``é``→``e``, so ``Éowyn, Shieldmaiden`` pages at
    ``eowyn-shieldmaiden``. Without the fold the accented letter would hit the
    ``[^a-z0-9]`` catch-all and be *dropped* (``owyn-…``), 403ing the fetch.

    Examples::

        "Atraxa, Praetors' Voice" -> "atraxa-praetors-voice"
        "Ragavan, Nimble Pilferer" -> "ragavan-nimble-pilferer"
        "Jace, Vryn's Prodigy // Jace, Telepath Unbound" -> "jace-vryns-prodigy"
        "Éowyn, Shieldmaiden" -> "eowyn-shieldmaiden"
        "Sméagol, Helpful Guide" -> "smeagol-helpful-guide"
    """
    front = util.front_face(name)
    # NFKD splits accented letters into base + combining mark; dropping the
    # marks (category "Mn") leaves the ASCII base (é→e, û→u, ó→o).
    folded = "".join(
        ch for ch in unicodedata.normalize("NFKD", front)
        if unicodedata.category(ch) != "Mn"
    )
    s = folded.lower()
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


# EDHREC's color-identity → ranking-slug map. Keyed by the frozenset of WUBRG
# letters so any letter order resolves the same (a color IDENTITY, not a
# sequence). 0/1/2/3/4/5-color all have a canonical EDHREC slug:
# colorless, the mono-* set, the ten guilds, the ten shards/wedges, the five
# nephilim names, and five-color. (Verified live against json.edhrec.com.)
_COLOR_SLUGS: dict[frozenset[str], str] = {
    frozenset(): "colorless",
    frozenset("W"): "mono-white", frozenset("U"): "mono-blue",
    frozenset("B"): "mono-black", frozenset("R"): "mono-red",
    frozenset("G"): "mono-green",
    frozenset("WU"): "azorius", frozenset("UB"): "dimir",
    frozenset("BR"): "rakdos", frozenset("RG"): "gruul",
    frozenset("GW"): "selesnya", frozenset("WB"): "orzhov",
    frozenset("UR"): "izzet", frozenset("BG"): "golgari",
    frozenset("RW"): "boros", frozenset("GU"): "simic",
    frozenset("GWU"): "bant", frozenset("WUB"): "esper",
    frozenset("UBR"): "grixis", frozenset("BRG"): "jund",
    frozenset("RGW"): "naya", frozenset("WBG"): "abzan",
    frozenset("URW"): "jeskai", frozenset("BRW"): "mardu",
    frozenset("UBG"): "sultai", frozenset("URG"): "temur",
    frozenset("WUBR"): "yore-tiller", frozenset("UBRG"): "glint-eye",
    frozenset("WBRG"): "dune-brood", frozenset("WURG"): "ink-treader",
    frozenset("WUBG"): "witch-maw",
    frozenset("WUBRG"): "five-color",
}

# All EDHREC color slugs (for accepting a slug/name passed through directly).
_COLOR_SLUG_NAMES: frozenset[str] = frozenset(_COLOR_SLUGS.values())


def color_filter_slug(spec: str) -> str:
    """Map a color spec to its EDHREC color-ranking slug.

    Accepts WUBRG letters in any order (``"wu"``, ``"rgw"``, ``"wubrg"``), the
    guild/shard/wedge/nephilim/mono-* names or ``five-color``/``colorless``
    themselves (passed through), and ``"c"``/empty → ``colorless``. Raises
    :class:`EdhrecError` on anything unrecognized."""
    s = spec.strip().lower()
    if s in _COLOR_SLUG_NAMES:
        return s
    if s in ("c", "colourless", ""):
        return "colorless"
    letters = frozenset(ch.upper() for ch in s if ch.upper() in "WUBRG")
    # only treat as a letter-spec if EVERY char was a color letter (else it's a
    # misspelled name, which should error rather than silently drop chars)
    if letters and all(ch.upper() in "WUBRG" for ch in s):
        slug = _COLOR_SLUGS.get(letters)
        if slug:
            return slug
    raise EdhrecError(
        f"unrecognized color spec {spec!r} — use WUBRG letters (e.g. 'wu'), a "
        f"guild/shard/wedge name (e.g. 'azorius', 'bant'), 'mono-red', "
        f"'five-color', or 'colorless'"
    )


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


def resolve_oracle_card(ref: str) -> tuple[str, dict | None]:
    """Up-level a card reference to ``(oracle_name, scryfall_card_dict)``.

    Accepts a bare name ("Sol Ring") or a printing "SET CN" ("cmm 425"). A
    printing is resolved via Scryfall's exact endpoint; a bare name via the
    fuzzy/named endpoint. The name is the front face (so reprints and DFCs
    collapse to one EDHREC page); the card dict carries ``type_line``/
    ``oracle_text`` so callers can gate on commander eligibility. ``card`` is
    ``None`` only when Scryfall can't resolve the ref (then ``name`` falls back
    to the raw input — the slug is still derivable for an exact name)."""
    parts = ref.split()
    # "SET CN" form: 2 tokens, first is a set-code-shaped token (3-6
    # alphanumerics, no hyphen — so a hyphenated card name like "Spider-Man
    # 2099" is NOT mistaken for a printing), second is collector-number-ish.
    if (
        len(parts) == 2
        and re.fullmatch(r"[A-Za-z0-9]{3,6}", parts[0])
        and any(ch.isdigit() for ch in parts[1])
    ):
        set_code, cn = parts[0].lower(), parts[1]
        # Fail-soft: a malformed guess (or Scryfall hiccup) falls through to
        # bare-name resolution rather than crashing the whole sync.
        try:
            found, _ = scryfall.collection([{"set": set_code, "collector_number": cn}])
            if found:
                return util.front_face(found[0].get("name") or ref), found[0]
        except scryfall.ScryfallError:
            pass
    # bare name → Scryfall named (exact if possible; tolerant fuzzy fallback)
    try:
        card = scryfall.named(ref)
        return util.front_face(card.get("name") or ref), card
    except scryfall.ScryfallError:
        # last resort: use the raw input; slugify still works for exact names
        return ref, None


def resolve_oracle_name(ref: str) -> str:
    """Front-face ORACLE name for a card reference (see :func:`resolve_oracle_card`)."""
    return resolve_oracle_card(ref)[0]


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
    fetched_at: str | None = None  # rankings: when this batch was fetched


@dataclass
class DualSyncResult:
    """Outcome of a symmetric ingest (:func:`sync_both`).

    ``commander`` is the commander-page ``SyncResult`` (``None`` when the card is
    not commander-eligible, or — rarely — eligible but EDHREC has no page yet).
    ``card`` is the card-in-the-99 ``SyncResult`` (``None`` only on an unexpected
    card-page miss). ``eligible`` records whether the card cleared the
    commander-eligibility gate."""
    name: str
    commander: SyncResult | None = None
    card: SyncResult | None = None
    eligible: bool = False


@dataclass
class BulkSyncResult:
    """Tally of a :func:`sync_bulk` run over a list of names."""
    total: int                        # names considered (before resume-skip)
    already: int = 0                  # skipped — commander page already cached
    ok: int = 0                       # sync_both succeeded (didn't raise)
    eligible: int = 0                 # of ok, had a commander page
    card_only: int = 0                # of ok, card page only (no commander page)
    failed: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)  # (name, error)


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

# Timeframes EDHREC serves for commander/card rankings (``year`` is EDHREC's
# "past 2 years" page). Salt and tag rankings are all-time; set rankings have none.
RANKING_TIMEFRAMES = ("week", "month", "year")


def color_options() -> list[dict]:
    """Every EDHREC color-identity filter in display order (0 → 5 colors):
    ``{slug, label, colors}`` where ``colors`` is the WUBRG identity."""
    order = "WUBRG"
    out = []
    for letters, slug in _COLOR_SLUGS.items():
        colors = "".join(c for c in order if c in letters)
        out.append({"slug": slug, "colors": colors,
                    "label": "-".join(p.capitalize() for p in slug.split("-"))})
    return out


@dataclass(frozen=True)
class RankingKey:
    """The stored identity of one ranking in ``edhrec_rankings`` — computed
    OFFLINE from a request, so a cached ranking can be read without fetching."""
    scope: str        # commanders | cards | salt
    timeframe: str    # week|month|year, 'all' (salt/tag) or '' (set)
    filter: str       # '' | 'color:<slug>' | 'tag:<slug>' | 'set:<anchor>'


def _check_ranking_args(scope: str, color, tag, set_family) -> int:
    """Validate a rankings request; returns the number of filters (0 or 1)."""
    n_filters = sum(x is not None for x in (color, tag, set_family))
    if n_filters > 1:
        raise EdhrecError("color/tag/set filters are mutually exclusive — pass at most one")
    if n_filters == 1 and scope != "commanders":
        raise EdhrecError(f"filters apply only to the 'commanders' scope, not {scope!r}")
    if n_filters == 0 and scope not in _RANKING_SCOPES:
        raise EdhrecError(f"unknown ranking scope {scope!r} (expected commanders|cards|salt)")
    return n_filters


def ranking_key(scope: str = "commanders", timeframe: str = "week", *,
                color: str | None = None, tag: str | None = None,
                set_family: str | None = None) -> RankingKey:
    """Where :func:`sync_rankings` stores this request (no network beyond a
    cached set-family resolve). Raises :class:`EdhrecError` on a bad request."""
    _check_ranking_args(scope, color, tag, set_family)
    if color is not None:
        return RankingKey("commanders", timeframe, f"color:{color_filter_slug(color)}")
    if tag is not None:
        return RankingKey("commanders", "all", f"tag:{slugify(tag)}")
    if set_family is not None:
        return RankingKey("commanders", "", f"set:{sets.resolve(set_family).code}")
    if scope == "salt":
        return RankingKey("salt", "all", "")
    return RankingKey(scope, timeframe, "")


def cached_rankings(key: RankingKey) -> SyncResult | None:
    """The latest stored sync of ``key`` (rows of its newest batch, rank order),
    or ``None`` when it was never fetched. Pure local read."""
    with db.connect() as conn:
        latest = conn.execute(
            "SELECT MAX(fetched_at) FROM edhrec_rankings WHERE scope=? AND timeframe=? AND filter=?",
            (key.scope, key.timeframe, key.filter),
        ).fetchone()[0]
        if latest is None:
            return None
        rows = conn.execute(
            """SELECT entity_oracle_id, entity_slug, entity_name, rank, num_decks, salt, trend_zscore
               FROM edhrec_rankings WHERE scope=? AND timeframe=? AND filter=? AND fetched_at=?
               ORDER BY rank, entity_name""",
            (key.scope, key.timeframe, key.filter, latest),
        ).fetchall()
    return SyncResult(
        kind="rankings", slug=key.filter or key.scope, name=ranking_title(key),
        scope=key.scope, timeframe=key.timeframe, fetched_at=latest,
        rows=[EnrichedCardRow(
            name=r["entity_name"], slug=r["entity_slug"], oracle_id=r["entity_oracle_id"],
            list_tag=key.scope, num_decks=r["num_decks"], salt=r["salt"],
            rank=r["rank"], trend_zscore=r["trend_zscore"],
        ) for r in rows],
    )


def rankings(scope: str = "commanders", timeframe: str = "week", *,
             color: str | None = None, tag: str | None = None,
             set_family: str | None = None, refresh: bool = False,
             progress=None) -> SyncResult:
    """Read-or-sync: the cached ranking when present (instant), else fetch it
    via :func:`sync_rankings`. ``refresh`` always re-fetches."""
    key = ranking_key(scope, timeframe, color=color, tag=tag, set_family=set_family)
    if not refresh:
        hit = cached_rankings(key)
        if hit is not None:
            return hit
    res = sync_rankings(scope, timeframe, color=color, tag=tag,
                        set_family=set_family, progress=progress)
    return cached_rankings(key) or res


_TIMEFRAME_LABELS = {"week": "past week", "month": "past month", "year": "past 2 years"}


def ranking_title(key: RankingKey) -> str:
    """Human title for a ranking — the ONE naming rule shared by the CLI report
    and the web (``Top commanders · Mono-Red · past week``)."""
    when = _TIMEFRAME_LABELS.get(key.timeframe)
    kind, _, val = key.filter.partition(":")
    noun = {"commanders": "Top commanders", "cards": "Top cards", "salt": "Saltiest cards"}[key.scope]
    if kind == "color":
        noun += " · " + "-".join(p.capitalize() for p in val.split("-"))
    elif kind == "tag":
        noun += f" · {val.replace('-', ' ').capitalize()} tag"
    elif kind == "set":
        noun += f" · {val.upper()} family"
    return f"{noun} · {when}" if when else noun


@dataclass
class _RankingPlan:
    """Resolved fetch for one rankings request — filled by :func:`_plan_rankings`."""
    cardviews: list[dict]                  # the ranking list (deck-count-ordered)
    filter_key: str                        # '' | 'color:…' | 'tag:…' | 'set:…'
    result_slug: str                       # SyncResult.slug (used in artifact names)
    timeframe: str                         # effective timeframe stored on rows
    snapshots: list[tuple[str, str, dict]] # (page_type, slug, page) to _store_page
    primary_page: dict                     # SyncResult.raw


def _dedupe_cardviews(cardviews: list[dict]) -> list[dict]:
    """Merge cardviews by slug, first-wins, then sort by num_decks desc so a
    unioned/merged list ranks meaningfully."""
    by_slug: dict[str, dict] = {}
    for cv in cardviews:
        key = cv.get("slug") or slugify(cv.get("name") or "")
        if key and key not in by_slug:
            by_slug[key] = cv
    return sorted(by_slug.values(), key=lambda c: -(c.get("num_decks") or 0))


def _plan_rankings(scope: str, timeframe: str, *,
                   color: str | None, tag: str | None,
                   set_family: str | None, progress=None) -> _RankingPlan:
    """Fetch the right EDHREC page(s) for a (scope, filter) request and select
    the correct ranking cardlist. Filters are commander-only and mutually
    exclusive (enforced by the caller). List selection is EXPLICIT per filter —
    a tags page's first non-empty list is ``newcommanders`` (5), not the
    ``topcommanders`` (24) we want."""
    if color is not None:
        slug = color_filter_slug(color)
        page = color_ranking(slug, timeframe)
        lists = cardlists(page)
        # color pages carry a single '<slug>commanders' list.
        cardviews = lists.get(f"{slug}commanders") or next((cv for cv in lists.values() if cv), [])
        return _RankingPlan(
            cardviews=cardviews, filter_key=f"color:{slug}", result_slug=slug,
            timeframe=timeframe, snapshots=[("commanders", slug, page)],
            primary_page=page,
        )

    if tag is not None:
        tslug = slugify(tag)
        # tag pages are all-time only (no timeframe segment — a tf 403s).
        page = tag_ranking(tslug)
        lists = cardlists(page)
        # EXPLICIT: topcommanders (24) then newcommanders (5), deduped.
        cardviews = _dedupe_cardviews(list(lists.get("topcommanders") or [])
                                      + list(lists.get("newcommanders") or []))
        return _RankingPlan(
            cardviews=cardviews, filter_key=f"tag:{tslug}", result_slug=f"tag-{tslug}",
            timeframe="all", snapshots=[("commanders", f"tags/{tslug}", page)],
            primary_page=page,
        )

    if set_family is not None:
        resolved_set = sets.resolve(set_family)
        anchor = resolved_set.code
        codes = resolved_set.all_codes
        snapshots: list[tuple[str, str, dict]] = []
        merged: list[dict] = []
        primary: dict = {}
        for i, code in enumerate(codes):
            if progress:
                progress(i, len(codes), f"Reading {code.upper()}")
            page = set_page(code)
            if not primary:
                primary = page
            snapshots.append(("commanders", f"sets/{code}", page))
            lists = cardlists(page)
            # a set page carries per-code 'commanders(<code>)' lists — take them all.
            for tagname, cvs in lists.items():
                if tagname.startswith("commanders(") and cvs:
                    merged.extend(cvs)
        return _RankingPlan(
            cardviews=_dedupe_cardviews(merged), filter_key=f"set:{anchor}",
            result_slug=f"set-{anchor}",
            timeframe="", snapshots=snapshots, primary_page=primary,
        )

    # unfiltered: the original three global scopes.
    if scope == "commanders":
        page = commanders_ranking(timeframe)
        tf = timeframe
    elif scope == "salt":
        page = top_ranking("salt")
        tf = "all"
    else:  # cards
        page = top_ranking(timeframe)
        tf = timeframe
    lists = cardlists(page)
    cardviews = next((cv for cv in lists.values() if cv), [])
    return _RankingPlan(
        cardviews=cardviews, filter_key="", result_slug=scope,
        timeframe=tf,
        snapshots=[(("commanders" if scope == "commanders" else "top"), scope, page)],
        primary_page=page,
    )


def sync_rankings(scope: str = "commanders", timeframe: str = "week", *,
                  color: str | None = None, tag: str | None = None,
                  set_family: str | None = None, progress=None) -> SyncResult:
    """Workflow C: commander/card/salt rankings, optionally FILTERED.

    Unfiltered scopes: 'commanders' | 'cards' | 'salt' (salt ignores timeframe).
    Filters (commander-only, MUTUALLY EXCLUSIVE — at most one): ``color`` (a WUBRG
    letter spec or guild/shard/wedge/mono-*/five-color/colorless name), ``tag`` (a
    theme OR creature type — EDHREC serves both from /tags/<slug>), ``set_family``
    (a set name/code, expanded via :func:`sets.resolve` and unioned across the
    family's codes). Rank derives from array position within the deck-count-ordered
    list. Each filtered ranking is persisted under its own ``filter`` key.

    ``progress(done, total, message)`` (optional) ticks per page fetched — a set
    family fetches one page per code."""
    n_filters = _check_ranking_args(scope, color, tag, set_family)
    key = ranking_key(scope, timeframe, color=color, tag=tag, set_family=set_family)
    plan = _plan_rankings(scope, timeframe, color=color, tag=tag,
                          set_family=set_family, progress=progress)
    # Filtered rankings are always commander rankings; unfiltered keeps its scope.
    row_scope = "commanders" if n_filters == 1 else scope
    at = db._utcnow_iso()

    names = [cv["name"] for cv in plan.cardviews if cv.get("name")]
    if not names:
        # An empty page (no lists, or a redirect for a mistyped tag) would store
        # nothing and leave the ranking looking never-read; fail loudly instead.
        raise EdhrecError(f"EDHREC lists nothing for {ranking_title(key)} — check the spelling or try another filter")
    if progress:
        progress(1, 1, f"Matching {len(names)} cards to your collection")
    resolved = resolve_names_to_oracle(names)

    rows: list[EnrichedCardRow] = []
    with db.transaction() as conn:
        for page_type, slug, page in plan.snapshots:
            _store_page(conn, page_type=page_type, slug=slug,
                        timeframe=plan.timeframe, page=page, at=at)
        for i, cv in enumerate(plan.cardviews, start=1):
            name = cv.get("name")
            if not name:
                continue
            oid = resolved.get(name.casefold(), {}).get("oracle_id")
            rank = cv.get("rank") or i
            conn.execute(
                """
                INSERT INTO edhrec_rankings
                    (scope, timeframe, filter, entity_oracle_id, entity_slug,
                     entity_name, rank, num_decks, salt, trend_zscore, fetched_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(scope, timeframe, filter, entity_slug) DO UPDATE SET
                    entity_oracle_id=excluded.entity_oracle_id,
                    entity_name=excluded.entity_name,
                    rank=excluded.rank,
                    num_decks=excluded.num_decks,
                    salt=excluded.salt,
                    trend_zscore=excluded.trend_zscore,
                    fetched_at=excluded.fetched_at
                """,
                (row_scope, plan.timeframe, plan.filter_key, oid,
                 cv.get("slug") or slugify(name), name, rank,
                 cv.get("num_decks"), cv.get("salt"), cv.get("trend_zscore"), at),
            )
            rows.append(EnrichedCardRow(
                name=name, slug=cv.get("slug") or slugify(name), oracle_id=oid,
                list_tag=row_scope, num_decks=cv.get("num_decks"),
                salt=cv.get("salt"), rank=rank, trend_zscore=cv.get("trend_zscore"),
            ))
    return SyncResult(kind="rankings", slug=plan.result_slug, name=ranking_title(key),
                      scope=row_scope, timeframe=plan.timeframe, rows=rows,
                      raw=plan.primary_page, fetched_at=at)


def sync_both(ref: str, *, resolved: tuple[str, dict | None] | None = None) -> DualSyncResult:
    """Ingest a card as BOTH its EDHREC views in one pass — the symmetric-ingest
    seam every ingest path routes through.

    Always ingests the card-in-the-99 page (every card has one). Ingests the
    commander page ONLY if the card is commander-eligible — a deterministic gate
    via :func:`legality.is_commander_eligible` on the resolved Scryfall card, NOT
    a 404 probe, so we never fetch a commander page EDHREC can't serve. The
    commander ``try/except`` is a belt-and-suspenders fallback for the rare
    eligible-but-not-yet-on-EDHREC case (a brand-new legendary).

    ``resolved`` lets a caller that has ALREADY up-levelled the ref pass in the
    ``(oracle_name, scryfall_card)`` pair so the resolve isn't repeated — e.g.
    :func:`sync_bulk`, which resolves each name to decide the resume-skip and then
    threads the result straight through."""
    name, card = resolved if resolved is not None else resolve_oracle_card(ref)
    eligible = card is not None and legality.is_commander_eligible(card)

    commander_res: SyncResult | None = None
    if eligible:
        try:
            commander_res = sync_commander(name)
        except EdhrecError:
            commander_res = None

    card_res: SyncResult | None = None
    try:
        card_res = sync_card(name)
    except EdhrecError:
        card_res = None

    return DualSyncResult(name=name, commander=commander_res,
                          card=card_res, eligible=eligible)


# ---------- bulk cache-warming (selector-driven) ----------

def _cached_slugs() -> tuple[set[str], set[str]]:
    """``(commander_slugs, card_slugs)`` already present in ``edhrec_pages``.

    Both sets are needed for a correct resume: an eligible card is only fully
    warmed once BOTH its commander and card pages are cached, while a card-only
    card is done once its card page is. Keyed on the stored slug (``slugify`` of
    the resolved oracle name), which is what the resume check re-derives."""
    with db.connect() as conn:
        commander = {
            r[0] for r in conn.execute(
                "SELECT DISTINCT slug FROM edhrec_pages WHERE page_type='commander'"
            ).fetchall()
        }
        card = {
            r[0] for r in conn.execute(
                "SELECT DISTINCT slug FROM edhrec_pages WHERE page_type='card'"
            ).fetchall()
        }
    return commander, card


def names_from_selector(selector: str, *, card_type: str | None = None) -> list[str]:
    """Materialize a selector to a deduped, sorted list of oracle card names.

    The selector DSL (``set:CODE+related``, ``cards:Q``, ``deck:SLUG``,
    ``inventory``, …) is the repo's universal "set of cards" input, so bulk
    EDHREC warming rides it rather than a bespoke family+type query. Each
    materialized row already carries ``type_line``, so ``card_type`` filters
    OFFLINE via a case-insensitive substring (``"legendary creature"``,
    ``"creature"``, ``"planeswalker"``, …).

    Two classes are dropped because they have no paper EDHREC page: **tokens**
    (``is_token`` — the same hard-exclude the missing-set pipeline applies; you
    don't warm EDHREC for a Treasure or a Goblin token) and **digital-only**
    cards (``selectors._is_digital_only`` — Arena/Alchemy rebalanced reprints AND
    the arena-stamped Alchemy *originals* that carry no ``A-`` prefix, plus
    serialized 1-of-N). Reusing ``_is_digital_only`` keeps this in lockstep with
    the one canonical unobtainable-card predicate rather than a weaker name-prefix
    heuristic.
    """
    from . import selectors  # local import: selectors imports heavy siblings

    names: set[str] = set()
    for row in selectors.materialize(selector):
        if row.card.get("is_token") or selectors._is_digital_only(row.card):
            continue
        type_line = row.card.get("type_line") or ""
        if card_type and card_type.lower() not in type_line.lower():
            continue
        name = row.card.get("name") or ""
        if name:
            names.add(name)
    return sorted(names)


def names_for_bulk(
    *, selector: str | None = None, families: Iterable[str] | None = None,
    card_type: str | None = None,
) -> list[str]:
    """Resolve a bulk-warm universe: exactly one of a selector string OR set-family
    anchors (each unioned as ``set:<anchor>+related``). The single home for the
    ``--selector``/``--family`` input shared by the CLI and the web job. Raises
    ``ValueError`` unless exactly one is given; selector errors propagate
    (``SelectorParseError`` / ``LookupError``)."""
    anchors = [a.strip() for a in (families or []) if a and a.strip()]
    if bool(selector) == bool(anchors):
        raise ValueError("provide exactly one of a selector or family anchors")
    if selector:
        return names_from_selector(selector, card_type=card_type)
    out: set[str] = set()
    for anchor in anchors:
        out.update(names_from_selector(f"set:{anchor}+related", card_type=card_type))
    return sorted(out)


def sync_bulk(
    names: Iterable[str],
    *,
    resume: bool = True,
    progress=None,
    on_resolve=None,
) -> BulkSyncResult:
    """Warm the EDHREC cache for every name via :func:`sync_both`.

    Loops the per-card symmetric-ingest seam, so each name warms its
    card-in-99 page and (when commander-eligible) its commander page, into
    ``edhrec_pages`` + the normalized tables.

    **Resumable (per-eligibility).** When ``resume``, a name is skipped only when
    its EDHREC pages are already fully cached — and "fully" depends on
    eligibility: a commander-eligible card needs BOTH its commander and card
    pages; a card-only card needs just its card page. We therefore resolve each
    name up front (to know eligibility) and thread that resolve straight into
    :func:`sync_both` so it isn't repeated. Resolves are 24h-cached in
    ``scryfall.sh``, so the pre-pass is cheap on a re-run. (The earlier
    commander-slug-only key silently re-fetched every card-only card each run —
    the bulk of a ``set:X+related`` universe.)

    **Fail-soft, with a bug/transient split.** Expected transient failures
    (``EdhrecError`` / ``ScryfallError``) are tallied into ``failed``/``failures``
    and the loop continues. Any OTHER exception (an ``AttributeError`` /
    ``KeyError`` from a changed EDHREC page shape, a ``sqlite3`` error, …) is a
    code/parse bug, not flaky network — it's tagged distinctly (``BUG: <type>``)
    so a deterministic failure that resume can never repair reads as a bug rather
    than fetch noise. The loop still continues (one bad card shouldn't abort a
    1000-item batch).

    ``on_resolve(i, total, name)`` — optional callback per name during the
    resolve/resume pre-pass (which can take minutes on a cold cache and is
    otherwise silent).

    ``progress(i, total, name, tag)`` — optional callback per attempted name;
    ``tag`` is ``"cmd+card"`` / ``"card-only"`` / ``"none"`` / ``"ERROR: …"`` /
    ``"BUG: …"`` / ``"skip (cached)"``.
    """
    names = list(names)
    result = BulkSyncResult(total=len(names))
    cmd_cached, card_cached = _cached_slugs() if resume else (set(), set())

    # Resolve-then-partition: resolve each name once (24h-cached), decide the
    # resume-skip against the correct page-set for its eligibility, and carry the
    # resolve into sync_both so it isn't repeated. Skipped names are counted but
    # not progress-logged (a large resume shouldn't spam a line per cache hit).
    todo: list[tuple[str, tuple[str, dict | None]]] = []
    for n_resolved, name in enumerate(names, 1):
        if on_resolve is not None:
            on_resolve(n_resolved, len(names), name)
        try:
            oracle_name, card = resolve_oracle_card(name)
        except scryfall.ScryfallError:
            # Couldn't resolve to decide skip — let sync_both re-attempt and tally.
            todo.append((name, (name, None)))
            continue
        eligible = card is not None and legality.is_commander_eligible(card)
        slug = slugify(oracle_name)
        # A card-only card is done once its card page is cached; an eligible card
        # needs BOTH pages (an interrupted run may have written only one).
        fully_cached = slug in card_cached and (not eligible or slug in cmd_cached)
        if resume and fully_cached:
            result.already += 1
        else:
            todo.append((name, (oracle_name, card)))

    for i, (name, resolved) in enumerate(todo, 1):
        try:
            res = sync_both(name, resolved=resolved)
            result.ok += 1
            if res.commander is not None:
                result.eligible += 1
                tag = "cmd+card"
            elif res.card is not None:
                result.card_only += 1
                tag = "card-only"
            else:
                tag = "none"
        except (EdhrecError, scryfall.ScryfallError) as e:
            # Expected transient (network / API / missing page) — flaky, retryable.
            result.failed += 1
            result.failures.append((name, str(e)))
            tag = f"ERROR: {e}"
        except Exception as e:  # noqa: BLE001 — unexpected: a code/parse bug, surface it
            result.failed += 1
            result.failures.append((name, f"UNEXPECTED {type(e).__name__}: {e}"))
            tag = f"BUG: {type(e).__name__}: {e}"
        if progress is not None:
            progress(i, len(todo), name, tag)

    return result


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


# ---------- commander comparison (workflow D) ----------

@dataclass
class CompareCard:
    """One card in a two-commander comparison. Carries the per-commander
    inclusion metrics for whichever side(s) recommend it, the bucket it lands in
    (``a_only`` / ``both`` / ``b_only``), the EDHREC category ``tags`` it appeared
    under (deduped across lists), and local enrichment incl. a representative
    printing's image/link (via the extended ``sets.lowest_price_by_oracle``)."""
    name: str
    oracle_id: str | None
    slug: str
    bucket: str                       # 'a_only' | 'both' | 'b_only'
    tags: list[str] = field(default_factory=list)
    a_pct: float | None = None
    b_pct: float | None = None
    a_decks: int | None = None
    b_decks: int | None = None
    delta: float | None = None        # abs(a_pct - b_pct); None unless 'both'
    synergy_a: float | None = None
    synergy_b: float | None = None
    trend_a: float | None = None
    trend_b: float | None = None
    # local enrichment
    type_line: str | None = None
    cmc: float | None = None
    mana_cost: str | None = None
    color_identity: list[str] | None = None
    rarity: str | None = None
    lowest_usd: float | None = None
    lowest_usd_foil: float | None = None
    scryfall_id: str | None = None
    image_uri: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    # Scryfall Tagger (V28): function root keys + top preview tags ({id,slug,label})
    functions: list[str] = field(default_factory=list)
    oracle_tags: list[dict] = field(default_factory=list)


@dataclass
class CompareResult:
    """Outcome of :func:`compare_commanders`: both commanders' identities plus
    the merged, bucketed, enriched card list."""
    name_a: str
    name_b: str | None
    slug_a: str
    slug_b: str | None
    cards: list[CompareCard] = field(default_factory=list)


@dataclass
class _CmdCard:
    """A single commander's deduped recommendation for one card (internal)."""
    name: str
    oracle_id: str | None
    slug: str
    tags: set[str]
    inclusion_pct: float | None
    num_decks: int | None
    synergy: float | None
    trend_zscore: float | None


def _dedupe_commander_cards(rows: Iterable) -> dict:
    """Collapse a commander's per-``(card, list_tag)`` rows into one entry per
    card, keyed by ``card_oracle_id`` (fallback ``card_slug`` when unresolved).

    A card appears in several lists (topcards AND creatures AND …); the card-level
    metrics (inclusion %, deck count) are identical across its lists, so we take
    the first non-null, union the ``list_tag``s as ``tags``, and keep the MAX
    synergy / trend across its rows. Accepts either ``EnrichedCardRow`` objects
    (fresh sync) or sqlite rows (cached read) — the card-identity columns are named
    differently between the two (``oracle_id``/``slug``/``name`` vs the
    ``card_``-prefixed table columns), so those are read via the key maps below;
    the metric columns share names."""
    def _get(r, attr):
        if hasattr(r, "keys"):          # sqlite Row (cached read)
            try:
                return r[attr]
            except (KeyError, IndexError):
                return None
        return getattr(r, attr, None)   # EnrichedCardRow (fresh sync)

    is_db = (lambda r: hasattr(r, "keys"))
    by_card: dict = {}
    for r in rows:
        oid = _get(r, "card_oracle_id" if is_db(r) else "oracle_id")
        slug = _get(r, "card_slug" if is_db(r) else "slug")
        name = _get(r, "card_name" if is_db(r) else "name")
        key = oid or f"slug:{slug}"
        tag = _get(r, "list_tag")
        pct = _get(r, "inclusion_pct")
        num = _get(r, "num_decks")
        syn = _get(r, "synergy")
        trend = _get(r, "trend_zscore")
        cur = by_card.get(key)
        if cur is None:
            by_card[key] = _CmdCard(
                name=name, oracle_id=oid, slug=slug,
                tags={tag} if tag else set(),
                inclusion_pct=pct, num_decks=num, synergy=syn, trend_zscore=trend,
            )
        else:
            if tag:
                cur.tags.add(tag)
            if cur.inclusion_pct is None and pct is not None:
                cur.inclusion_pct = pct
            if cur.num_decks is None and num is not None:
                cur.num_decks = num
            if syn is not None and (cur.synergy is None or syn > cur.synergy):
                cur.synergy = syn
            if trend is not None and (cur.trend_zscore is None or trend > cur.trend_zscore):
                cur.trend_zscore = trend
    return by_card


def _commander_card_entries(ref: str) -> tuple[str, str, dict]:
    """Resolve a commander ref, ensure its page is cached (sync if absent), and
    return ``(oracle_name, slug, {card_key: _CmdCard})``.

    Reads the cached ``edhrec_commander_cards`` rows when the commander page is
    already present (no network); otherwise runs ``sync_commander`` once. Raises
    :class:`EdhrecError` if the ref isn't commander-eligible or EDHREC has no page."""
    name, card = resolve_oracle_card(ref)
    if card is not None and not legality.is_commander_eligible(card):
        raise EdhrecError(f"{name!r} is not commander-eligible — no commander page to compare.")
    slug = slugify(name)
    cmd_cached, _ = _cached_slugs()
    if slug in cmd_cached:
        with db.connect() as conn:
            rows = conn.execute(
                """
                SELECT card_oracle_id, card_slug, card_name, list_tag,
                       num_decks, potential_decks, inclusion_pct, synergy, trend_zscore
                FROM edhrec_commander_cards WHERE commander_slug = ?
                """,
                (slug,),
            ).fetchall()
        if rows:
            # Prefer the stored header name if present (nicer casing).
            with db.connect() as conn:
                hdr = conn.execute(
                    "SELECT commander_name FROM edhrec_commander_cards "
                    "WHERE commander_slug = ? LIMIT 1", (slug,)
                ).fetchone()
            display = hdr[0] if hdr and hdr[0] else name
            return display, slug, _dedupe_commander_cards(rows)
    # Not cached (or cache empty) — sync once.
    res = sync_commander(name)
    return res.name, res.slug, _dedupe_commander_cards(res.rows)


def compare_commanders(ref_a: str, ref_b: str | None = None) -> CompareResult:
    """Compare the recommended-card rankings of two commanders (workflow D).

    Each commander's FULL recommendation set (every ``list_tag``) is read from the
    cache (synced on demand if absent), deduped per commander to one entry per
    card. The union is partitioned into ``a_only`` / ``both`` / ``b_only`` buckets
    keyed on ``card_oracle_id`` (fallback slug); ``both`` cards carry each side's
    inclusion % + deck count and a ``delta`` = ``abs(a_pct - b_pct)``. Every card
    is enriched in ONE batched ``sets.lowest_price_by_oracle`` call (type / mana /
    lowest USD + a representative printing's image + Scryfall link), and ONE
    batched ``scryfall_tags.card_summaries`` call (Tagger function roots + top
    preview tags; empty when the tag cache was never synced).
    """
    name_a, slug_a, a_cards = _commander_card_entries(ref_a)
    # One commander (Explore's single view): every card lands in a_only.
    name_b, slug_b, b_cards = _commander_card_entries(ref_b) if ref_b else (None, None, {})

    keys = list(dict.fromkeys([*a_cards.keys(), *b_cards.keys()]))
    cards: list[CompareCard] = []
    for key in keys:
        a = a_cards.get(key)
        b = b_cards.get(key)
        src = a or b
        if a and b:
            bucket = "both"
            delta = (abs(a.inclusion_pct - b.inclusion_pct)
                     if a.inclusion_pct is not None and b.inclusion_pct is not None else None)
        elif a:
            bucket, delta = "a_only", None
        else:
            bucket, delta = "b_only", None
        tags = sorted(((a.tags if a else set()) | (b.tags if b else set())))
        cards.append(CompareCard(
            name=src.name, oracle_id=src.oracle_id, slug=src.slug, bucket=bucket,
            tags=tags,
            a_pct=a.inclusion_pct if a else None,
            b_pct=b.inclusion_pct if b else None,
            a_decks=a.num_decks if a else None,
            b_decks=b.num_decks if b else None,
            delta=delta,
            synergy_a=a.synergy if a else None,
            synergy_b=b.synergy if b else None,
            trend_a=a.trend_zscore if a else None,
            trend_b=b.trend_zscore if b else None,
        ))

    # Enrich all cards in ONE batched call (incl. representative printing image).
    # The displayed printing (image/link) is the chronologically-first STANDARD
    # printing — not the cheapest one, which is often a random showcase/borderless
    # reprint. The floor price stays the cheapest across all printings.
    oids = [c.oracle_id for c in cards if c.oracle_id]
    meta = sets.lowest_price_by_oracle(oids)
    display = sets.standard_printing_by_oracle(oids)
    by_oid: dict[str, list[CompareCard]] = {}
    for c in cards:
        if c.oracle_id:
            by_oid.setdefault(c.oracle_id, []).append(c)
    for c in cards:
        m = meta.get(c.oracle_id or "")
        if not m:
            continue
        c.type_line = m.get("type_line")
        c.cmc = m.get("cmc")
        c.mana_cost = m.get("mana_cost")
        _ci = m.get("color_identity")
        c.color_identity = json.loads(_ci) if _ci else []
        c.rarity = m.get("rarity")
        c.lowest_usd = m.get("lowest_usd")
        c.lowest_usd_foil = m.get("lowest_usd_foil")
        p = display.get(c.oracle_id or "") or m
        c.scryfall_id = p.get("scryfall_id")
        c.image_uri = p.get("image_uri")
        c.set_code = p.get("set_code")
        c.collector_number = p.get("collector_number")

    # Scryfall Tagger functions + preview tags — also ONE batched lookup.
    for oid, summ in scryfall_tags.card_summaries(oids).items():
        for c in by_oid.get(oid, ()):
            c.functions = list(summ.functions)
            c.oracle_tags = [{"id": t.id, "slug": t.slug, "label": t.label}
                             for t in summ.tags]

    return CompareResult(name_a=name_a, name_b=name_b, slug_a=slug_a, slug_b=slug_b, cards=cards)

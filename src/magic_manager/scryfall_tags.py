"""Scryfall Tagger tags — a rebuildable local cache: oracle (function) tags (V28)
and art tags (V30, same hierarchy table, ``type``-discriminated; see :data:`KINDS`).

Source: Scryfall's OFFICIAL ``oracle_tags`` bulk file (``GET /bulk-data`` →
``data.scryfall.io``), fetched through the sanctioned ``scryfall.sh bulk``
wrapper (daily file, 24h listing cache). Never the tagger site or its GraphQL.

Tags are card-level metadata at ORACLE grain: one tag carries ``id`` (UUID — the
stable key; slugs/labels can be renamed), ``slug``, ``label``, the hierarchy
(``parent_ids``/``child_ids``, e.g. mana-rock ⊂ ramp), and ``taggings[]`` of
``{oracle_id, weight}``. ``sync`` fully re-derives ``scryfall_tags`` +
``card_oracle_tags`` from the file (idempotent).

On top of the raw tags sit curated FUNCTION roots (``config/function_tags.toml``:
Ramp, Card draw, Removal, …). A card's functions = every root whose subtree tags
it (:func:`roll_up`). :func:`card_summaries` is the ONE batched lookup consumers
(e.g. ``edhrec.compare_commanders``) call for functions + top preview tags.
"""
from __future__ import annotations

import gzip
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence

from . import config, db, scryfall

_CHUNK = 900  # stay under SQLite's host-parameter limit


@dataclass(frozen=True)
class Kind:
    """One flavour of Scryfall tag bulk file. Both share the tag hierarchy table
    (``scryfall_tags``, discriminated by ``type``) and the file format; they differ
    in the bulk type, the tagging grain/table, and the settings key."""
    name: str
    bulk_type: str
    tag_type: str          # scryfall_tags.type
    table: str             # tagging table
    key_col: str           # grain column in ``table`` / key inside ``taggings[]``
    settings_key: str


KINDS: dict[str, Kind] = {
    "oracle": Kind("oracle", "oracle_tags", "oracle", "card_oracle_tags",
                   "oracle_id", "scryfall_tags.source"),
    "art": Kind("art", "art_tags", "illustration", "illustration_art_tags",
                "illustration_id", "scryfall_tags.art_source"),
}
BULK_TYPE = KINDS["oracle"].bulk_type  # back-compat


def kind_of(kind: str) -> Kind:
    try:
        return KINDS[kind]
    except KeyError:
        raise ValueError(f"unknown tag kind {kind!r} (expected one of {', '.join(KINDS)})") from None


# Higher = stronger. Tagger publishes very_strong / strong / median / weak.
WEIGHT_RANK = {"very_strong": 3, "strong": 2, "median": 1, "weak": 0}


@dataclass(frozen=True)
class Tag:
    id: str
    slug: str
    label: str
    weight: str | None = None


@dataclass(frozen=True)
class FunctionRoot:
    """A curated function root resolved against the local tag hierarchy:
    ``tag_ids`` is the root tag(s) PLUS every descendant."""
    key: str
    label: str
    tag_ids: frozenset[str]


@dataclass
class SyncResult:
    source: str
    tags: int
    taggings: int
    skipped: bool = False
    updated_at: str | None = None


@dataclass
class CardTagSummary:
    functions: list[str] = field(default_factory=list)   # root keys, config order
    tags: list[Tag] = field(default_factory=list)        # top preview tags


# ---------- sync ----------

def _bulk_timestamp(path: Path) -> str | None:
    """``oracle_tags--oracle-tags-20261004090034.jsonl.gz`` → ISO-8601 UTC."""
    m = re.search(r"(\d{14})", path.name)
    if not m:
        return None
    return datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(
        tzinfo=timezone.utc).isoformat(timespec="seconds")


def load_bulk(path: Path) -> list[dict]:
    """Parse a bulk tags file: gzip'd JSONL (current format), plain JSONL, or a
    JSON array (Scryfall's legacy ``download_uri`` shape)."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        text = f.read()
    stripped = text.lstrip()
    if stripped.startswith("["):
        return list(json.loads(stripped))
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def ingest(rows: Iterable[dict], *, source: str, updated_at: str | None,
           conn: sqlite3.Connection | None = None, kind: str = "oracle") -> tuple[int, int]:
    """Fully replace ONE kind's tags + taggings from parsed bulk ``rows`` in ONE
    transaction (the other kind's rows are untouched). Returns
    ``(n_tags, n_taggings)``. Re-running with the same rows is a no-op in effect
    (rebuildable cache)."""
    k = kind_of(kind)
    tag_rows: list[tuple] = []
    tagging_rows: dict[tuple[str, str], str | None] = {}
    for t in rows:
        if t.get("object", "tag") != "tag" or not t.get("id"):
            continue
        tid = t["id"]
        tag_rows.append((
            tid, t.get("slug") or "", t.get("label") or t.get("slug") or "",
            k.tag_type,
            json.dumps(t.get("parent_ids") or []), json.dumps(t.get("child_ids") or []),
            updated_at,
        ))
        for tg in t.get("taggings") or []:
            key = tg.get(k.key_col)
            if key:
                tagging_rows[(key, tid)] = tg.get("weight")
    with db.transaction(conn) as c:
        c.execute(f"DELETE FROM {k.table}")
        c.execute("DELETE FROM scryfall_tags WHERE type = ?", (k.tag_type,))
        c.executemany(
            "INSERT INTO scryfall_tags (id, slug, label, type, parent_ids, child_ids, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", tag_rows)
        c.executemany(
            f"INSERT INTO {k.table} ({k.key_col}, tag_id, weight) VALUES (?, ?, ?)",
            [(o, t, w) for (o, t), w in tagging_rows.items()])
        c.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                  "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                  (k.settings_key, source))
    return len(tag_rows), len(tagging_rows)


def _counts(conn: sqlite3.Connection, kind: str = "oracle") -> tuple[int, int]:
    k = kind_of(kind)
    return (conn.execute("SELECT COUNT(*) FROM scryfall_tags WHERE type = ?",
                         (k.tag_type,)).fetchone()[0],
            conn.execute(f"SELECT COUNT(*) FROM {k.table}").fetchone()[0])


def sync(*, refresh: bool = False, kind: str = "oracle",
         progress: Callable[[str], None] | None = None) -> SyncResult:
    """Download (≤ once a day, via the wrapper's cache) the kind's bulk file and
    re-derive its local tag tables. When the local tables already hold this exact
    daily file, skip the rewrite unless ``refresh``."""
    k = kind_of(kind)
    say = progress or (lambda _m: None)
    say(f"Resolving Scryfall {k.bulk_type} bulk file…")
    path = scryfall.bulk_file(k.bulk_type, refresh=refresh)
    updated_at = _bulk_timestamp(path)
    with db.connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?",
                           (k.settings_key,)).fetchone()
        if not refresh and row and row[0] == path.name:
            n_tags, n_taggings = _counts(conn, kind)
            if n_tags:
                say("Already current.")
                return SyncResult(path.name, n_tags, n_taggings, skipped=True,
                                  updated_at=updated_at)
    say(f"Parsing {path.name}…")
    rows = load_bulk(path)
    say(f"Writing {len(rows)} tags…")
    with db.connect() as conn:
        n_tags, n_taggings = ingest(rows, source=path.name, updated_at=updated_at,
                                    conn=conn, kind=kind)
    return SyncResult(path.name, n_tags, n_taggings, updated_at=updated_at)


def sync_kinds(kinds: Iterable[str] = tuple(KINDS), *, refresh: bool = False,
               progress: Callable[[str], None] | None = None) -> dict[str, SyncResult]:
    """Sync several kinds (default: all) → ``{kind: SyncResult}``."""
    return {name: sync(refresh=refresh, kind=name, progress=progress) for name in kinds}


# ---------- hierarchy ----------

@dataclass
class _Hierarchy:
    by_id: dict[str, tuple[str, str, list[str]]]   # id -> (slug, label, child_ids)
    by_slug: dict[str, str]                        # slug -> id

    def subtree(self, tag_id: str) -> set[str]:
        """``tag_id`` plus every descendant (cycle-safe)."""
        out: set[str] = set()
        stack = [tag_id]
        while stack:
            t = stack.pop()
            if t in out or t not in self.by_id:
                continue
            out.add(t)
            stack.extend(self.by_id[t][2])
        return out


def _hierarchy(conn: sqlite3.Connection, kind: str = "oracle") -> _Hierarchy:
    """Load one kind's tag graph (~4.5k / ~11.6k rows — cheap); kinds never mix. Edges come from BOTH
    ``child_ids`` and the inverse of ``parent_ids`` so a one-sided edge upstream
    still rolls up."""
    by_id: dict[str, tuple[str, str, list[str]]] = {}
    by_slug: dict[str, str] = {}
    parents: list[tuple[str, list[str]]] = []
    for r in conn.execute("SELECT id, slug, label, child_ids, parent_ids FROM scryfall_tags WHERE type = ?",
                          (kind_of(kind).tag_type,)):
        by_id[r[0]] = (r[1], r[2] or r[1], list(json.loads(r[3] or "[]")))
        by_slug[r[1]] = r[0]
        parents.append((r[0], json.loads(r[4] or "[]")))
    for child, pids in parents:
        for p in pids:
            if p in by_id and child not in by_id[p][2]:
                by_id[p][2].append(child)
    return _Hierarchy(by_id, by_slug)


def descendants(tag_id: str, *, kind: str = "oracle",
                conn: sqlite3.Connection | None = None) -> set[str]:
    """Every tag UUID strictly below ``tag_id`` in the ``kind`` hierarchy."""
    with db.transaction(conn) as c:
        return _hierarchy(c, kind).subtree(tag_id) - {tag_id}


def _resolve_ref(h: _Hierarchy, ref: dict) -> str | None:
    """A config tag ref ``{id, slug}`` → local UUID (id first; slug fallback)."""
    if ref.get("id") and ref["id"] in h.by_id:
        return ref["id"]
    return h.by_slug.get(ref.get("slug") or "")


def function_roots(*, conn: sqlite3.Connection | None = None,
                   _h: _Hierarchy | None = None) -> list[FunctionRoot]:
    """The configured function roots resolved to subtree tag-id sets, in config
    order. A root whose tags are all absent locally resolves to an empty set."""
    cfg = config.function_tags()
    with db.transaction(conn) as c:
        h = _h or _hierarchy(c)
    out = []
    for r in cfg["roots"]:
        ids: set[str] = set()
        for ref in r["tags"]:
            tid = _resolve_ref(h, ref)
            if tid:
                ids |= h.subtree(tid)
        out.append(FunctionRoot(r["key"], r["label"], frozenset(ids)))
    return out


# ---------- batched lookups ----------

def _taggings(c: sqlite3.Connection, oracle_ids: Sequence[str]) -> dict[str, list[tuple[str, str | None]]]:
    out: dict[str, list[tuple[str, str | None]]] = {}
    ids = list(dict.fromkeys(o for o in oracle_ids if o))
    for i in range(0, len(ids), _CHUNK):
        chunk = ids[i:i + _CHUNK]
        q = ("SELECT oracle_id, tag_id, weight FROM card_oracle_tags "
             f"WHERE oracle_id IN ({','.join('?' * len(chunk))})")
        for oid, tid, w in c.execute(q, chunk):
            out.setdefault(oid, []).append((tid, w))
    return out


def tags_for_oracles(oracle_ids: Iterable[str], *,
                     conn: sqlite3.Connection | None = None) -> dict[str, list[Tag]]:
    """``{oracle_id: [Tag…]}`` for every tagged id (strongest weight first, then
    label). Untagged ids are absent. One query per 900 ids."""
    with db.transaction(conn) as c:
        h = _hierarchy(c)
        raw = _taggings(c, list(oracle_ids))
    out: dict[str, list[Tag]] = {}
    for oid, pairs in raw.items():
        tags = [Tag(tid, h.by_id[tid][0], h.by_id[tid][1], w)
                for tid, w in pairs if tid in h.by_id]
        tags.sort(key=lambda t: (-WEIGHT_RANK.get(t.weight or "", 1), t.label))
        out[oid] = tags
    return out


def roll_up(oracle_ids: Iterable[str], roots: Sequence[FunctionRoot] | None = None, *,
            conn: sqlite3.Connection | None = None) -> dict[str, list[str]]:
    """``{oracle_id: [root_key…]}`` — each card's function roots (config order)
    via the tag hierarchy. Cards with no function are absent."""
    with db.transaction(conn) as c:
        roots = roots if roots is not None else function_roots(conn=c)
        raw = _taggings(c, list(oracle_ids))
    out: dict[str, list[str]] = {}
    for oid, pairs in raw.items():
        tids = {t for t, _ in pairs}
        keys = [r.key for r in roots if r.tag_ids & tids]
        if keys:
            out[oid] = keys
    return out


def card_summaries(oracle_ids: Iterable[str], *,
                   conn: sqlite3.Connection | None = None,
                   limit: int | None = None) -> dict[str, CardTagSummary]:
    """ONE batched lookup → ``{oracle_id: CardTagSummary(functions, tags)}``.

    ``functions`` = rolled-up root keys; ``tags`` = the top
    ``preview_limit`` tags for a card preview: strongest weight first, then tags
    inside a function subtree, then label — skipping structural/meta subtrees
    (``preview_exclude``) unless the tag is ALSO inside a function subtree (e.g.
    mana-rock-with-set-s-mechanic sits under both mana-rock and a meta root).
    Ids with neither are absent."""
    cfg = config.function_tags()
    with db.transaction(conn) as c:
        h = _hierarchy(c)
        roots = function_roots(conn=c, _h=h)
        raw = _taggings(c, list(oracle_ids))
    excluded: set[str] = set()
    for slug in cfg["preview_exclude"]:
        tid = h.by_slug.get(slug)
        if tid:
            excluded |= h.subtree(tid)
    functional = frozenset().union(*(r.tag_ids for r in roots)) if roots else frozenset()
    limit = max(0, cfg["preview_limit"] if limit is None else limit)
    out: dict[str, CardTagSummary] = {}
    for oid, pairs in raw.items():
        tids = {t for t, _ in pairs}
        funcs = [r.key for r in roots if r.tag_ids & tids]
        cands = [(tid, w) for tid, w in pairs
                 if tid in h.by_id and (tid not in excluded or tid in functional)]
        cands.sort(key=lambda p: (-WEIGHT_RANK.get(p[1] or "", 1),
                                  p[0] not in functional, h.by_id[p[0]][1]))
        tags = [Tag(tid, h.by_id[tid][0], h.by_id[tid][1], w) for tid, w in cands[:limit]]
        if funcs or tags:
            out[oid] = CardTagSummary(funcs, tags)
    return out


def status(*, kind: str = "oracle", conn: sqlite3.Connection | None = None) -> dict:
    """``{source, tags, taggings}`` for the local cache (source None = never synced)."""
    with db.transaction(conn) as c:
        row = c.execute("SELECT value FROM settings WHERE key = ?",
                        (kind_of(kind).settings_key,)).fetchone()
        n_tags, n_taggings = _counts(c, kind)
    return {"source": row[0] if row else None, "tags": n_tags, "taggings": n_taggings}

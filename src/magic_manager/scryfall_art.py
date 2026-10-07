"""Scryfall art tags (V30): which PRINTINGS carry a given piece of artwork.

Art tags come from Scryfall's official ``art_tags`` bulk file and are keyed on
``illustration_id`` (one artwork, shared by every printing that reuses it) —
ingested by :mod:`magic_manager.scryfall_tags` (``kind="art"``). This module adds
the printing → illustration link (``cards.illustration_id``, projected on sync and
backfilled from the ``default_cards`` bulk file) and the ONE engine query the
future "deck with dragon art" feature consumes: :func:`printings_with_art`.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Callable, Iterable, Sequence

from . import db, scryfall, scryfall_tags
from .scryfall_tags import WEIGHT_RANK, _CHUNK
from .selectors import _is_digital_only

KIND = "art"
_BATCH = 2000


# ---------- printing → illustration backfill ----------

def backfill_illustration_ids(*, refresh: bool = False,
                              progress: Callable[[str], None] | None = None) -> int:
    """Fill NULL ``cards.illustration_id`` from Scryfall's ``default_cards`` bulk
    file (gzip'd JSONL — streamed one card per line, never fully loaded). Only rows
    whose value is NULL are touched; returns rows updated."""
    import gzip

    say = progress or (lambda _m: None)
    say("Resolving Scryfall default_cards bulk file…")
    path = scryfall.bulk_file("default_cards", refresh=refresh)
    opener = gzip.open if path.suffix == ".gz" else open
    sql = "UPDATE cards SET illustration_id = ? WHERE scryfall_id = ? AND illustration_id IS NULL"
    updated = seen = 0
    batch: list[tuple[str, str]] = []
    with db.connect() as conn:
        def flush() -> None:
            nonlocal updated
            before = conn.total_changes
            conn.executemany(sql, batch)
            updated += conn.total_changes - before
            batch.clear()

        say(f"Streaming {path.name}…")
        with opener(path, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip().rstrip(",")
                if not line.startswith("{"):
                    continue  # '[' / ']' of a legacy JSON-array file
                card = json.loads(line)
                seen += 1
                ill = db.card_illustration_id(card)
                if ill and card.get("id"):
                    batch.append((ill, card["id"]))
                if len(batch) >= _BATCH:
                    flush()
        flush()
        conn.commit()
    say(f"Scanned {seen} cards; filled {updated} rows.")
    return updated


# ---------- tag lookup ----------

def _tag_rows(c: sqlite3.Connection) -> list[tuple[str, str, str]]:
    return [(r[0], r[1], r[2] or r[1]) for r in c.execute(
        "SELECT id, slug, label FROM scryfall_tags WHERE type = ?",
        (scryfall_tags.kind_of(KIND).tag_type,))]


def resolve_tag(ref: str, *, conn: sqlite3.Connection | None = None) -> tuple[str, str] | None:
    """An art tag by UUID, slug, or label (case-insensitive) → ``(id, label)``."""
    ref = (ref or "").strip()
    if not ref:
        return None
    low = ref.lower()
    with db.transaction(conn) as c:
        rows = _tag_rows(c)
    for tid, slug, label in rows:
        if tid == ref:
            return tid, label
    for tid, slug, label in rows:
        if slug.lower() == low:
            return tid, label
    for tid, slug, label in rows:
        if label.lower() == low:
            return tid, label
    return None


def art_tag_search(q: str, limit: int = 20, *,
                   conn: sqlite3.Connection | None = None) -> list[dict]:
    """Art tags whose label or slug contains ``q`` →
    ``[{id, label, slug, illustrations}]``, exact matches first then most
    illustrations. ``illustrations`` = distinct artworks tagged DIRECTLY."""
    needle = (q or "").strip().lower()
    if not needle:
        return []
    with db.transaction(conn) as c:
        counts = dict(c.execute(
            "SELECT tag_id, COUNT(*) FROM illustration_art_tags GROUP BY tag_id"))
        rows = _tag_rows(c)
    out = []
    for tid, slug, label in rows:
        if needle in label.lower() or needle in slug.lower():
            out.append({"id": tid, "label": label, "slug": slug,
                        "illustrations": counts.get(tid, 0),
                        "_exact": needle in (label.lower(), slug.lower())})
    out.sort(key=lambda t: (not t["_exact"], -t["illustrations"], t["label"]))
    return [{k: v for k, v in t.items() if k != "_exact"} for t in out[:max(0, limit)]]


# ---------- engine query ----------

def _chunks(seq: Sequence, n: int = _CHUNK):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _owned_qty(c: sqlite3.Connection, sids: Sequence[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for chunk in _chunks(list(sids)):
        q = ("SELECT scryfall_id, SUM(quantity) FROM inventory "
             f"WHERE scryfall_id IN ({','.join('?' * len(chunk))}) GROUP BY scryfall_id")
        out.update({sid: n for sid, n in c.execute(q, chunk)})
    return out


def printings_with_art(tag_ref: str, *, oracle_ids: Iterable[str] | None = None,
                       owned_only: bool = False, include_descendants: bool = True,
                       conn: sqlite3.Connection | None = None) -> list[dict]:
    """Printings (local ``cards``) whose illustration carries the art tag — or, by
    default, any DESCENDANT tag (e.g. ``dragon`` rolls up wyrm/drake/…). ``tag_ref``
    is a label, slug, or UUID. ``oracle_ids`` restricts to printings of those cards;
    ``owned_only`` to printings with inventory qty > 0. Tokens and digital-only
    printings are excluded. Each row: scryfall_id, oracle_id, name, set_code,
    collector_number, illustration_id, tags (matched labels), weight (strongest
    matched), owned (qty). Raises ``LookupError`` for an unknown tag."""
    oracle_filter = {o for o in oracle_ids} if oracle_ids is not None else None
    with db.transaction(conn) as c:
        tag = resolve_tag(tag_ref, conn=c)
        if tag is None:
            raise LookupError(f"no art tag matches {tag_ref!r}")
        tag_ids = {tag[0]}
        if include_descendants:
            tag_ids |= scryfall_tags.descendants(tag[0], kind=KIND, conn=c)
        labels = {tid: lab for tid, _s, lab in _tag_rows(c)}
        found: dict[str, dict] = {}
        for chunk in _chunks(sorted(tag_ids)):
            q = ("SELECT c.scryfall_id, c.oracle_id, c.name, c.set_code, c.collector_number, "
                 "c.illustration_id, c.is_token, c.promo_types, c.security_stamp, "
                 "t.tag_id, t.weight "
                 "FROM illustration_art_tags t JOIN cards c ON c.illustration_id = t.illustration_id "
                 f"WHERE t.tag_id IN ({','.join('?' * len(chunk))})")
            for r in c.execute(q, chunk):
                if r["is_token"] or (oracle_filter is not None and r["oracle_id"] not in oracle_filter):
                    continue
                if _is_digital_only(dict(r)):
                    continue
                row = found.setdefault(r["scryfall_id"], {
                    "scryfall_id": r["scryfall_id"], "oracle_id": r["oracle_id"],
                    "name": r["name"], "set_code": r["set_code"],
                    "collector_number": r["collector_number"],
                    "illustration_id": r["illustration_id"], "tags": [], "weight": None})
                row["tags"].append(labels.get(r["tag_id"], r["tag_id"]))
                if WEIGHT_RANK.get(r["weight"] or "", 1) > WEIGHT_RANK.get(row["weight"] or "", -1):
                    row["weight"] = r["weight"]
        owned = _owned_qty(c, list(found))
    rows = []
    for row in found.values():
        row["tags"] = sorted(set(row["tags"]))
        row["owned"] = owned.get(row["scryfall_id"], 0)
        if owned_only and not row["owned"]:
            continue
        rows.append(row)
    rows.sort(key=lambda r: (r["name"], r["set_code"], r["collector_number"]))
    return rows


def art_tags_for_printings(scryfall_ids: Iterable[str], *,
                           conn: sqlite3.Connection | None = None) -> dict[str, list[str]]:
    """``{scryfall_id: [art tag label…]}`` (DIRECT tags, label order) for printings
    that have any. One batched query per 900 ids."""
    ids = list(dict.fromkeys(s for s in scryfall_ids if s))
    out: dict[str, list[str]] = {}
    with db.transaction(conn) as c:
        for chunk in _chunks(ids):
            q = ("SELECT c.scryfall_id, COALESCE(NULLIF(s.label, ''), s.slug) "
                 "FROM cards c JOIN illustration_art_tags t ON t.illustration_id = c.illustration_id "
                 "JOIN scryfall_tags s ON s.id = t.tag_id "
                 f"WHERE c.scryfall_id IN ({','.join('?' * len(chunk))})")
            for sid, label in c.execute(q, chunk):
                out.setdefault(sid, []).append(label)
    return {sid: sorted(set(labels)) for sid, labels in out.items()}


def art_tags_for_illustrations(illustration_ids: Iterable[str], *, limit: int = 8,
                               conn: sqlite3.Connection | None = None) -> dict[str, list[dict]]:
    """``{illustration_id: [{slug, label}…]}`` — each artwork's DIRECT art tags,
    strongest weight first then label, at most ``limit``. Keyed on the artwork, so
    it works for printings not in the local catalog (e.g. a random Scryfall card)."""
    ids = list(dict.fromkeys(i for i in illustration_ids if i))
    found: dict[str, list[tuple[int, str, str]]] = {}
    with db.transaction(conn) as c:
        for chunk in _chunks(ids):
            q = ("SELECT t.illustration_id, s.slug, COALESCE(NULLIF(s.label, ''), s.slug), t.weight "
                 "FROM illustration_art_tags t JOIN scryfall_tags s ON s.id = t.tag_id "
                 f"WHERE t.illustration_id IN ({','.join('?' * len(chunk))})")
            for ill, slug, label, weight in c.execute(q, chunk):
                found.setdefault(ill, []).append((-WEIGHT_RANK.get(weight or "", 1), label, slug))
    return {ill: [{"slug": s, "label": lab} for _w, lab, s in sorted(set(rows))[:limit]]
            for ill, rows in found.items()}

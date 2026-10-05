"""Where owned copies came from, and where they are now — read off the V19 ledger.

Every inventory write is a signed delta on one ``ingest_events`` row, so the net
balance each event still holds for a ``(scryfall_id, finish)`` is the number of
copies acquired that way (trueup re-attribution moves copies between events
net-zero, so balances stay exact). Each event classifies into a *source*:

* a **product** — a ``precon`` event (``precon:<fileName>`` from ``import_precon``,
  ``trueup:<fileName>`` from product-coverage). Its kind (playable ``deck`` vs
  card ``pool``) and name come from the ``decks`` rows sharing that fileName;
* **singles** — checklists, intake, ad-hoc adds, block/collection imports
  (``backfill:checklist`` reconstructed archived checklists, so it counts too);
* **unknown** — the generic best-effort buckets (``backfill:precon``,
  ``unattributed-backfill``, ``migration-backfill``).

Acquisition is history: a later removal is its own (negative) event, so the
sources of a printing can sum past what is owned today. Callers show them as
"acquired from", and only for printings still owned.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import db

SINGLES_KEY = "singles"
UNKNOWN_KEY = "unknown"
_UNKNOWN_LABELS = {"backfill:precon", "backfill:unattributed"}
_UNKNOWN_METHODS = {"unattributed-backfill", "migration-backfill"}
_PRODUCT_PREFIXES = ("precon:", "trueup:")


@dataclass(frozen=True)
class Source:
    key: str                   # "singles" | "unknown" | "product:<fileName>"
    kind: str                  # "singles" | "unknown" | "deck" | "pool"
    label: str
    set_code: str | None = None   # products: the fileName's set suffix (lowercase)


@dataclass
class CardSource:
    source: Source
    finish: str
    copies: int
    acquisitions: int = 1   # distinct ingest events (e.g. two Jumpstart packs of the same theme bought separately)


@dataclass
class DeckPledge:
    slug: str
    name: str
    finish: str
    count: int


@dataclass
class Holdings:
    scryfall_id: str
    owned: dict[str, int] = field(default_factory=dict)      # finish -> copies
    pledged: dict[str, int] = field(default_factory=dict)    # finish -> copies pledged to built decks
    free: dict[str, int] = field(default_factory=dict)       # finish -> owned - pledged (>= 0)
    decks: list[DeckPledge] = field(default_factory=list)
    sources: list[CardSource] = field(default_factory=list)
    other_printings_owned: int = 0                            # same oracle, other printings, all finishes


def _pretty_file_name(file_name: str) -> str:
    """``AragornAtHelmSDeep_LTC`` → ``Aragorn At Helm S Deep (LTC)`` — a fallback
    for products with no deck row (e.g. a rowless deconstructed import)."""
    stem, _, code = file_name.rpartition("_")
    if not stem:
        stem, code = file_name, ""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", stem)
    return f"{words} ({code})" if code else words


def _product_file_name(method: str, label: str | None, source_path: str | None) -> str | None:
    if method != "precon" or label in _UNKNOWN_LABELS:
        return None
    for p in _PRODUCT_PREFIXES:
        if label and label.startswith(p):
            return label[len(p):] or None
    return source_path or None


def _classify(method: str, label: str | None, source_path: str | None,
              products: dict[str, tuple[str, str]]) -> Source:
    if method in _UNKNOWN_METHODS or label in _UNKNOWN_LABELS:
        return Source(UNKNOWN_KEY, "unknown", "Unknown origin")
    fn = _product_file_name(method, label, source_path)
    if fn is None:
        return Source(SINGLES_KEY, "singles", "Singles")
    kind, name = products.get(fn, ("deck", _pretty_file_name(fn)))
    code = fn.rpartition("_")[2].lower() if "_" in fn else None
    return Source(f"product:{fn}", kind, name, code)


def _products(conn) -> dict[str, tuple[str, str]]:
    """fileName → (kind, name) from the deck rows that carry it."""
    return {
        r[0]: (r[1] or "deck", r[2]) for r in conn.execute(
            "SELECT source_precon_file_name, MAX(kind), MIN(name) FROM decks "
            "WHERE source_precon_file_name IS NOT NULL GROUP BY source_precon_file_name")
    }


def card_sources(scryfall_ids, *, conn=None) -> dict[str, list[CardSource]]:
    """Batched: per printing, the copies acquired from each source, per finish
    (only positive event balances; largest first)."""
    ids = list(dict.fromkeys(scryfall_ids))

    def _q(c) -> dict[str, list[CardSource]]:
        products = _products(c)
        agg: dict[str, dict[tuple[Source, str], int]] = {}
        events: dict[tuple[str, Source, str], set[int]] = {}
        for i in range(0, len(ids), 500):
            part = ids[i:i + 500]
            ph = ",".join("?" * len(part))
            for sid, fin, method, label, path, q, iid in c.execute(
                f"""
                SELECT v.scryfall_id, v.finish, e.method, e.label, e.source_path, SUM(v.delta) AS q, v.ingest_id
                FROM inventory_events v JOIN ingest_events e ON e.ingest_id = v.ingest_id
                WHERE v.scryfall_id IN ({ph})
                GROUP BY v.scryfall_id, v.finish, v.ingest_id
                HAVING q > 0
                """, part,
            ):
                src = _classify(method, label, path, products)
                d = agg.setdefault(sid, {})
                d[(src, fin)] = d.get((src, fin), 0) + q
                events.setdefault((sid, src, fin), set()).add(iid)
        return {
            sid: sorted((CardSource(s, f, n, len(events[(sid, s, f)])) for (s, f), n in d.items()),
                        key=lambda cs: (-cs.copies, cs.source.label, cs.finish))
            for sid, d in agg.items()
        }

    if conn is not None:
        return _q(conn)
    with db.connect() as c:
        return _q(c)


def card_holdings(scryfall_id: str) -> Holdings:
    """One printing's ownership picture: per-finish owned / pledged / free, which
    built decks hold its pledged copies, where its copies came from, and how many
    copies of the same card you own in other printings."""
    h = Holdings(scryfall_id=scryfall_id)
    with db.connect() as conn:
        for fin, q in conn.execute(
            "SELECT finish, quantity FROM inventory WHERE scryfall_id = ? AND quantity > 0", (scryfall_id,)
        ):
            h.owned[fin] = q
        for slug, name, fin, n in conn.execute(
            """
            SELECT d.slug, d.name, a.finish, a.count FROM deck_assignments a
            JOIN decks d ON d.deck_id = a.deck_id
            WHERE a.scryfall_id = ? ORDER BY a.count DESC, d.name
            """, (scryfall_id,),
        ):
            h.decks.append(DeckPledge(slug, name, fin, n))
            h.pledged[fin] = h.pledged.get(fin, 0) + n
        h.free = {f: max(0, q - h.pledged.get(f, 0)) for f, q in h.owned.items()}
        if h.owned:
            h.sources = card_sources([scryfall_id], conn=conn).get(scryfall_id, [])
        row = conn.execute(
            """
            SELECT COALESCE(SUM(i.quantity), 0) FROM inventory i
            JOIN cards c ON c.scryfall_id = i.scryfall_id
            WHERE c.oracle_id = (SELECT oracle_id FROM cards WHERE scryfall_id = ?)
              AND i.scryfall_id <> ?
            """, (scryfall_id, scryfall_id),
        ).fetchone()
        h.other_printings_owned = row[0] if row else 0
    return h

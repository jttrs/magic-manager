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
* a **purchase** — a store order read by the browser companion (V34 ``purchase``
  events, labelled ``purchase:<store>:<order id>``);
* **unknown** — the generic best-effort buckets (``backfill:precon``,
  ``unattributed-backfill``, ``migration-backfill``).

A later removal is its own (negative) event; ``card_sources`` nets it with the
same in-order ledger walk purchase history uses (``_held``), so the sources of
a printing sum to what is owned today.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Literal

from . import db

SINGLES_KEY = "singles"
UNKNOWN_KEY = "unknown"
_UNKNOWN_LABELS = {"backfill:precon", "backfill:unattributed"}
_UNKNOWN_METHODS = {"unattributed-backfill", "migration-backfill"}
_PRODUCT_PREFIXES = ("precon:", "trueup:")


@dataclass(frozen=True)
class Source:
    key: str                   # "singles" | "unknown" | "product:<fileName>" | "purchase:<store>:<order id>"
    kind: str                  # "singles" | "unknown" | "deck" | "pool" | "purchase"
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
    # A bare MTGJSON fileName — not a checklist path (pre-V19 jumpstart/precon checklist ingests).
    if source_path and "/" not in source_path and "." not in source_path:
        return source_path
    return None


_STORE_NAMES = {"manapool": "Mana Pool", "tcgplayer": "TCGplayer", "cardkingdom": "Card Kingdom"}


def _purchase_title(label: str | None) -> str:
    _, store, order = (label or "purchase::").split(":", 2)
    return f"{_STORE_NAMES.get(store, store or 'Store')} order #{order}" if order else "Store order"


def _classify(method: str, label: str | None, source_path: str | None,
              products: dict[str, tuple[str, str]]) -> Source:
    if method == "purchase":
        return Source(label or "purchase", "purchase", _purchase_title(label))
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
    """Batched: per printing, the copies each source still accounts for, per finish
    (largest first). Removals are netted by ``_held`` like purchase history, so
    per finish the copies sum to what is owned today and a source whose copies
    are all gone drops out."""
    ids = list(dict.fromkeys(scryfall_ids))

    def _q(c) -> dict[str, list[CardSource]]:
        products = _products(c)
        held = {k: n for k, n in _held(c, ids).items() if n > 0}
        meta: dict[int, tuple] = {}
        iids = list({iid for iid, _, _ in held})
        for i in range(0, len(iids), 500):
            part = iids[i:i + 500]
            for iid, method, label, path in c.execute(
                f"SELECT ingest_id, method, label, source_path FROM ingest_events "
                f"WHERE ingest_id IN ({','.join('?' * len(part))})", part,
            ):
                meta[iid] = (method, label, path)
        agg: dict[str, dict[tuple[Source, str], int]] = {}
        events: dict[tuple[str, Source, str], set[int]] = {}
        for (iid, sid, fin), q in held.items():
            src = _classify(*meta[iid], products)
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


# ---------- purchase history: one entry per ingest event ----------
#
# The acquisition timeline read straight off the ledger. Each ``ingest_events``
# row is one entry; its ``inventory_events`` give copies in / out and the balance
# it still holds per printing (what that acquisition accounts for today), valued
# at local prices. Honest about what the ledger can't know: pre-ledger ingests
# (before V19) carry no deltas — their copies live in the reconstructed buckets —
# and product-coverage (``trueup:``) entries are dated when they were IDENTIFIED,
# not when bought. A removal is its own (negative) event, so "held" nets removals
# against the copies held when the removal was written, newest acquisition first
# (LIFO, walking the ledger rows in order): per printing-finish, the held copies
# across all entries always sum to what is owned today.

HistoryKind = Literal["deck", "pool", "singles", "checklist", "unknown", "move", "purchase", "revert"]

_SINGLES_TITLES = {
    "adhoc": "Added by hand", "intake": "Scan session", "import-block": "Imported list",
    "collection-import": "Collection import", "collection-export": "Collection export",
}
_WEB_TITLES = {"search": "Added from search", "paste": "Pasted list", "deck": "Added a deck's cards"}
_UNKNOWN_DETAIL = {
    "backfill:precon": "Reconstructed from precon decklists — which product is not known",
    "backfill:unattributed": "Residual of the reconstruction — source not known",
}


@dataclass
class HistoryEntry:
    ingest_id: int
    at: str
    method: str
    kind: HistoryKind
    title: str
    detail: str | None = None    # file name, product fileName, raw label…
    dated: str = "acquired"      # acquired | identified (product coverage) | reconstructed (V19 backfill)
    ledgered: bool = True        # False: pre-ledger ingest, copies counted in a reconstructed bucket
    copies_in: int = 0
    copies_out: int = 0
    held: int = 0                # copies this event still accounts for (removals netted newest-first)
    printings: int = 0           # printings with held copies
    value_usd: float = 0.0       # held copies at today's local prices
    lines: int = 0               # checklist rows / deck-move lines touched (from the ingest row)
    product: str | None = None   # MTGJSON fileName
    set_code: str | None = None
    deck_slug: str | None = None
    purchase_id: int | None = None   # purchase entries: the stored order
    paid_usd: float | None = None    # purchase entries: card prices paid (lines with a price today, like value_usd)
    revertible: bool = False         # its kind can be reverted (ingest.not_revertible_reason) and it hasn't been
    reverted_by: int | None = None   # the revert event that undid it (V35)
    reverts: int | None = None       # revert entries: the event they undid


@dataclass
class HistoryLine:
    scryfall_id: str
    finish: str
    copies_in: int
    copies_out: int
    held: int
    unit_usd: float | None


@dataclass
class History:
    entries: list[HistoryEntry]
    prices_as_of: str | None = None
    stale_sets: list[str] = field(default_factory=list)


def _unit_usd(p: dict | None, finish: str) -> float | None:
    if not p:
        return None
    v = p.get("usd_foil") if finish == "foil" else p.get("usd")
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _set_label(code: str, names: dict[str, str]) -> str:
    return names.get(code.lower()) or code.upper()


def _describe(e, products: dict[str, tuple[str, str]], deck_names: dict[str, str],
              product_slugs: dict[str, str], set_names: dict[str, str]) -> HistoryEntry:
    iid, at, method, label, path, status, rows_added, rows_updated, mode, reverts = e
    label = label or ""
    base = os.path.basename(path) if path and "/" in path else None
    h = HistoryEntry(ingest_id=iid, at=at, method=method, kind="singles", title="", lines=(rows_added or 0) + (rows_updated or 0))
    if status == "backfill":
        h.dated = "reconstructed"
    if method == "revert":
        h.kind, h.title, h.reverts = "revert", "Reverted an import", reverts
        return h
    from .ingest import not_revertible_reason
    h.revertible = not_revertible_reason(method, mode, label or None, status) is None
    if method in ("deck-assign", "deck-unassign"):
        slug = label.split(":", 1)[1] if ":" in label else (path or "").removeprefix("deck:")
        h.kind, h.deck_slug = "move", slug or None
        name = deck_names.get(slug, slug or "a deck")
        h.title = f"Built {name}" if method == "deck-assign" else f"Broke down {name}"
        return h
    src = _classify(method, label, path, products)
    if src.kind == "purchase":
        h.kind, h.title, h.detail = "purchase", src.label, None
        return h
    if src.kind == "unknown":
        h.kind, h.title = "unknown", "Provenance unknown"
        h.detail = _UNKNOWN_DETAIL.get(label, label or None)
        return h
    if src.key.startswith("product:"):
        fn = src.key.removeprefix("product:")
        h.kind, h.title, h.product, h.set_code = src.kind, src.label, fn, src.set_code
        h.detail = fn
        h.deck_slug = product_slugs.get(fn) if src.kind == "deck" else None
        if label.startswith("trueup:"):
            h.dated = "identified"
        return h
    if label == "backfill:checklist":
        h.kind, h.title = "checklist", "Checklists before the ledger"
        h.detail = "Reconstructed from archived checklists"
        return h
    if method in ("checklist", "precon"):     # checklist ingests (incl. pre-ledger jumpstart/precon sheets)
        h.kind = "checklist"
        kind, _, code = label.partition(":")
        if kind == "set" and code:
            h.title, h.set_code = f"Checklist · {_set_label(code, set_names)}", code.lower()
        elif kind == "jumpstart" and code:
            h.title, h.set_code = f"Jumpstart packs · {_set_label(code, set_names)}", code.lower()
        elif kind == "precon":
            h.title = "Precon checklist"
        else:
            h.title = "Checklist"
        h.detail = base or path or (label or None)
        return h
    if label.startswith("web:"):
        source, _, rest = label.removeprefix("web:").partition(" · ")
        h.title, h.detail = _WEB_TITLES.get(source, "Added cards"), rest or None
        return h
    h.title = _SINGLES_TITLES.get(method, "Added cards")
    h.detail = label or None
    return h


def _balances(conn, ingest_id: int | None = None):
    """``(ingest_id, sid, finish, in, out, balance)`` per event and printing-finish."""
    where, args = ("WHERE ingest_id = ?", (ingest_id,)) if ingest_id is not None else ("", ())
    return conn.execute(
        f"""
        SELECT ingest_id, scryfall_id, finish,
               SUM(CASE WHEN delta > 0 THEN delta ELSE 0 END),
               SUM(CASE WHEN delta < 0 THEN -delta ELSE 0 END),
               SUM(delta)
        FROM inventory_events {where}
        GROUP BY ingest_id, scryfall_id, finish
        """, args,
    ).fetchall()


def _held(conn, sids=None) -> dict[tuple[int, str, str], int]:
    """``(ingest_id, sid, finish) -> held``: the copies each event still accounts for,
    from a walk of the ledger rows in the order they were written. A negative row
    first takes the event's OWN held copies (a re-attribution moving them, or an
    event undoing itself); only the part that takes the event's own balance below
    zero is a removal, drawn from the copies held at that moment, most recently
    acquired first. A re-attribution from a raw balance larger than what the event
    still held moves copies already removed; that shortfall is taken off the
    transfer's target (the next positive row), and a final newest-first netting is
    the safety net, so per printing-finish the held copies sum to the owned quantity. Walking rows (not per-event sums ordered by id) keeps a
    removal from landing on copies re-attributed after it (a purchase match or a
    trueup), which would make the source look as if it still held them."""
    rows: list = []
    q = "SELECT event_id, ingest_id, scryfall_id, finish, delta FROM inventory_events {}"
    if sids is None:
        rows = conn.execute(q.format("")).fetchall()
    else:
        ids = list(dict.fromkeys(sids))
        for i in range(0, len(ids), 500):
            part = ids[i:i + 500]
            rows += conn.execute(q.format(f"WHERE scryfall_id IN ({','.join('?' * len(part))})"), part).fetchall()
    rows.sort(key=lambda r: r[0])
    # A revert (V35) takes its copies back from the event it reverts, not from
    # whichever acquisition happens to be newest.
    reverts = dict(conn.execute(
        "SELECT ingest_id, reverts_ingest_id FROM ingest_events WHERE reverts_ingest_id IS NOT NULL"))
    by_key: dict[tuple[str, str], dict[int, int]] = {}
    raw: dict[tuple[int, str, str], int] = {}
    total: dict[tuple[str, str], int] = {}
    owed: dict[tuple[str, str], int] = {}   # copies a transfer moved out but no longer held
    for _eid, iid, sid, fin, delta in rows:
        held = by_key.setdefault((sid, fin), {})
        before = raw.get((iid, sid, fin), 0)
        raw[(iid, sid, fin)] = before + delta
        total[(sid, fin)] = total.get((sid, fin), 0) + delta
        if delta > 0:
            # A re-attribution writes +take right after -take: the copies it moved but
            # its source no longer held were already removed, so they aren't held here.
            absorb = min(delta, owed.get((sid, fin), 0))
            owed[(sid, fin)] = owed.get((sid, fin), 0) - absorb
            held[iid] = held.pop(iid, 0) + delta - absorb   # re-insert: now the most recent acquisition
            continue
        need = -delta
        src = reverts.get(iid, iid)
        own = min(need, held.get(src, 0))
        if own:
            held[src] -= own
            need -= own
        # Only the part that takes the event below zero is a removal of someone else's copies;
        # the rest moved copies already removed elsewhere (owed to the next acquisition).
        removal = min(need, max(0, -(before + delta)) - max(0, -before))
        owed[(sid, fin)] = owed.get((sid, fin), 0) + need - removal
        need = removal
        for other in reversed(list(held)):
            if need <= 0:
                break
            take = min(need, held[other])
            held[other] -= take
            need -= take
        held.setdefault(iid, 0)
    out: dict[tuple[int, str, str], int] = {}
    for (sid, fin), held in by_key.items():
        excess = sum(held.values()) - max(total[(sid, fin)], 0)
        for iid in reversed(list(held)):
            if excess <= 0:
                break
            take = min(excess, held[iid])
            held[iid] -= take
            excess -= take
        for iid, n in held.items():
            out[(iid, sid, fin)] = n
    return out


def _priced(conn, sids) -> tuple[dict[str, dict], list[str]]:
    from . import sets as sets_mod
    stale: list[str] = []
    return sets_mod.priced_map(sids, conn=conn, warn=stale.extend), stale


def _event_rows(conn, ingest_id: int | None = None):
    where, args = ("AND ingest_id = ?", (ingest_id,)) if ingest_id is not None else ("", ())
    return conn.execute(
        f"SELECT ingest_id, at, method, label, source_path, status, rows_added, rows_updated, "
        f"mode, reverts_ingest_id FROM ingest_events WHERE status <> 'failed' {where} ORDER BY at DESC, ingest_id DESC", args,
    ).fetchall()


def _context(conn):
    from .sets import set_names
    products = _products(conn)
    deck_names = {s: n for s, n in conn.execute("SELECT slug, name FROM decks")}
    product_slugs = {
        fn: slug for fn, slug in conn.execute(
            "SELECT source_precon_file_name, MIN(slug) FROM decks "
            "WHERE source_precon_file_name IS NOT NULL AND kind = 'deck' GROUP BY source_precon_file_name")
    }
    return products, deck_names, product_slugs, set_names()


def _fill(h: HistoryEntry, rows, held: dict[tuple[int, str, str], int], prices: dict[str, dict]) -> None:
    h.ledgered = bool(rows) or h.kind == "move"
    for iid, sid, fin, cin, cout, _bal in rows:
        h.copies_in += cin
        h.copies_out += cout
        n = held.get((iid, sid, fin), 0)
        if n > 0:
            h.held += n
            h.printings += 1
            h.value_usd += n * (_unit_usd(prices.get(sid), fin) or 0.0)
    h.value_usd = round(h.value_usd, 2)


def _as_of(prices: dict[str, dict]) -> str | None:
    dates = [p.get("prices_updated_at") for p in prices.values() if p.get("prices_updated_at")]
    return max(dates)[:10] if dates else None


def _attach_purchases(conn, entries: list[HistoryEntry]) -> None:
    """Purchase entries carry their stored order and what you paid for the
    copies they still hold (the per-line unit price × held copies)."""
    ids = [h.ingest_id for h in entries if h.kind == "purchase"]
    if not ids:
        return
    ph = ",".join("?" * len(ids))
    pid = {r[0]: r[1] for r in conn.execute(f"SELECT ingest_id, purchase_id FROM purchases WHERE ingest_id IN ({ph})", ids)}
    unit: dict[tuple[int, str, str], int] = {}
    for iid, sid, fin, cents, qty in conn.execute(
        f"""SELECT p.ingest_id, l.scryfall_id, l.finish, SUM(l.unit_price_cents * (l.matched + l.added)),
                   SUM(l.matched + l.added)
            FROM purchase_lines l JOIN purchases p ON p.purchase_id = l.purchase_id
            WHERE p.ingest_id IN ({ph}) AND l.scryfall_id IS NOT NULL AND l.unit_price_cents IS NOT NULL
            GROUP BY p.ingest_id, l.scryfall_id, l.finish""", ids):
        if qty:
            unit[(iid, sid, fin)] = cents / qty
    held = _held(conn, {k[1] for k in unit})
    for h in entries:
        if h.kind != "purchase":
            continue
        h.purchase_id = pid.get(h.ingest_id)
        h.paid_usd = round(sum(c * held.get(k, 0) for k, c in unit.items() if k[0] == h.ingest_id) / 100, 2)


def _link_reverts(conn, entries: list[HistoryEntry]) -> None:
    """Mark reverted entries (and drop their Revert offer); a revert entry's detail
    names what it undid."""
    by = {r[0]: r[1] for r in conn.execute(
        "SELECT reverts_ingest_id, ingest_id FROM ingest_events WHERE reverts_ingest_id IS NOT NULL")}
    titles: dict[int, str] = {}
    want = [h.reverts for h in entries if h.reverts is not None]
    if want:
        ctx = _context(conn)
        for e in conn.execute(
            f"SELECT ingest_id, at, method, label, source_path, status, rows_added, rows_updated, mode, "
            f"reverts_ingest_id FROM ingest_events WHERE ingest_id IN ({','.join('?' * len(want))})", want,
        ):
            o = _describe(e, *ctx)
            titles[o.ingest_id] = o.title + (f" · {o.detail}" if o.detail else "")
    for h in entries:
        h.reverted_by = by.get(h.ingest_id)
        if h.reverted_by is not None:
            h.revertible = False
        if h.reverts is not None:
            h.detail = titles.get(h.reverts)


def history(*, conn=None) -> History:
    """Every (non-failed) ingest event, newest first, with copies in/out, the copies
    it still accounts for and their value at local prices (never a network fetch
    for prices — stale sets are reported, not refreshed)."""
    def _q(c) -> History:
        ctx = _context(c)
        by_event: dict[int, list] = {}
        for row in _balances(c):
            by_event.setdefault(row[0], []).append(row)
        held = _held(c)
        prices, stale = _priced(c, {sid for (_i, sid, _f), n in held.items() if n > 0})
        entries = []
        for e in _event_rows(c):
            h = _describe(e, *ctx)
            _fill(h, by_event.get(h.ingest_id, []), held, prices)
            entries.append(h)
        _attach_purchases(c, entries)
        _link_reverts(c, entries)
        return History(entries, _as_of(prices), sorted(set(stale)))

    if conn is not None:
        return _q(conn)
    with db.connect() as c:
        return _q(c)


def history_event(ingest_id: int) -> tuple[HistoryEntry, list[HistoryLine]]:
    """One entry plus its cards: every printing-finish the event moved, with copies
    in / out / still held and today's unit price; most valuable held first.
    Raises ``LookupError`` for an unknown (or failed) ingest."""
    with db.connect() as c:
        rows = _event_rows(c, ingest_id)
        if not rows:
            raise LookupError(f"no ingest event {ingest_id}")
        bal = _balances(c, ingest_id)
        held = _held(c, {r[1] for r in bal})
        prices, _ = _priced(c, {r[1] for r in bal})
        h = _describe(rows[0], *_context(c))
        _fill(h, bal, held, prices)
        _attach_purchases(c, [h])
        _link_reverts(c, [h])
    lines = [HistoryLine(sid, fin, cin, cout, held.get((i, sid, fin), 0), _unit_usd(prices.get(sid), fin))
             for i, sid, fin, cin, cout, _b in bal]
    lines.sort(key=lambda ln: (-(max(ln.held, 0) * (ln.unit_usd or 0)), -ln.held, ln.scryfall_id))
    return h, lines

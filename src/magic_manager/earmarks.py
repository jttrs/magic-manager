"""Earmarked sealed products and single cards — a cross-storefront watchlist.

CRUD plus the single-card identity checkpoint (``resolve_single``).

Two tables (V12, V31):
  - ``earmarked_products`` — one row per watched item. ``kind`` (V31) is
    ``'sealed'`` (MTGJSON sealed-product identity: ``set_code`` + ``product_name``,
    ``product_uuid`` when known; facts pulled from ``mtgjson.sealed_products``)
    or ``'single'`` (one card printing keyed by ``set_code`` + ``collector_number``
    + ``finish``, with its ``scryfall_id`` for exact-finish pricing).
  - ``earmark_links`` — one row per storefront URL, joined to a product. The
    same product on three stores → one product row + three link rows, so the
    review collates them.

**What is (and isn't) stored here.** Only the NON-DERIVABLE facts live in the DB:
the store URL and a *snapshot* of its asking price + when it was captured (the
whole point of an earmark, and not recomputable). Market / intrinsic value is
deliberately NOT stored — ``scripts/review_earmarks.py`` recomputes it live via
the ``sealed`` engine so there is one source of price truth (DRY).

Identity validation is enforced by the CLI ``add`` command: sealed products via
``sealed.identify_product`` (does it resolve in MTGJSON?), singles via
``resolve_single`` below (does the printing exist, in that finish, under that name?).
V32 adds ``earmark_prices`` — the price history of each link: one row per
observation (the asking-price snapshot taken when you earmark, and every Deals
read of that URL). V33 adds ``earmark_targets`` — an optional price target per product
(a price, or a percentage under its market price; see :func:`set_target`, :func:`target_threshold`).
The identity checkpoint is :func:`resolve_identity`, shared by the CLI and the web.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.parse import urlparse

from . import db, scryfall


# ---------- row shapes ----------

@dataclass
class EarmarkLink:
    link_id: int
    product_id: int
    store_url: str
    store_name: str | None
    asking_price: float | None
    currency: str
    captured_at: str
    notes: str | None


@dataclass
class EarmarkProduct:
    product_id: int
    set_code: str
    product_uuid: str | None
    product_name: str
    category: str | None
    subtype: str | None
    release_date: str | None
    card_count: int | None
    notes: str | None
    earmarked_at: str
    kind: str = "sealed"
    scryfall_id: str | None = None
    collector_number: str | None = None
    finish: str | None = None
    links: list[EarmarkLink] = field(default_factory=list)

    @property
    def best_asking(self) -> float | None:
        """The cheapest asking price across this product's storefront links
        (``None`` if no link has a price)."""
        prices = [l.asking_price for l in self.links if l.asking_price is not None]
        return min(prices) if prices else None


# ---------- helpers ----------

def store_name_from_url(url: str) -> str | None:
    """Derive a human store label from a URL host (``www.`` stripped).
    Returns ``None`` for an unparseable URL."""
    try:
        host = urlparse(url).netloc.lower()
    except (ValueError, AttributeError):
        return None
    if not host:
        return None
    return host[4:] if host.startswith("www.") else host


def resolve_single(set_code: str, collector_number: str, finish: str = "nonfoil",
                   *, name: str | None = None) -> dict:
    """Validate a proposed single-card printing → canonical identity dict.

    The deterministic identity checkpoint for a single (sibling of
    ``sealed.identify_product``): the AGENT proposes set + collector number +
    finish (+ the card name from the store title); this confirms the printing
    exists, offers that finish, and — when ``name`` is given — really is that
    card (store titles often mislabel set/CN). Local ``cards`` first, Scryfall
    ``/cards/collection`` fill (upserted) on a miss. Raises ``LookupError``."""
    set_code = set_code.lower()
    cn = str(collector_number).strip()
    sql = ("SELECT scryfall_id, name, flavor_name, collector_number, finishes, rarity, "
           "released_at FROM cards WHERE set_code = ? AND lower(collector_number) = lower(?)")
    with db.connect() as conn:
        row = conn.execute(sql, (set_code, cn)).fetchone()
        if row is None:
            found, _ = scryfall.collection([{"set": set_code, "collector_number": cn}])
            if found:
                db.upsert_card(conn, found[0])
                conn.commit()
            row = conn.execute(sql, (set_code, cn)).fetchone()
    tag = f"{set_code.upper()} #{cn}"
    if row is None:
        raise LookupError(f"no printing {tag}")
    try:
        available = json.loads(row["finishes"] or "[]")
    except (ValueError, TypeError):
        available = []
    # cards stores only prices_usd / prices_usd_foil (usd_etched is dropped at projection),
    # so an etched-only printing could never be priced by the review.
    if finish not in available:
        if finish == "foil" and "etched" in available:
            raise LookupError(f"{tag} ({row['name']}) is etched-only; etched prices aren't "
                              f"tracked locally, so it can't be earmarked")
        raise LookupError(f"{tag} ({row['name']}) has no {finish} finish; "
                          f"available: {', '.join(available) or 'unknown'}")
    card_name = row["name"]
    if name is not None:
        accepted = {card_name.lower(), card_name.split(" // ")[0].lower()}
        if row["flavor_name"]:
            accepted.add(row["flavor_name"].lower())
        if name.strip().lower() not in accepted:
            raise LookupError(f"{tag} is {card_name!r}, not {name!r} — the store's "
                              f"set/CN may be wrong; verify by name + image")
    cn = row["collector_number"]
    return {
        "kind": "single", "set_code": set_code,
        "name": f"{card_name} (#{cn}, {finish})", "card_name": card_name,
        "scryfall_id": row["scryfall_id"], "collector_number": cn, "finish": finish,
        "category": "single", "subtype": row["rarity"] or None,
        "release_date": row["released_at"] or None,
    }


# ---------- reads ----------

def earmark_list() -> list[EarmarkProduct]:
    """Every earmarked product with its storefront links attached.

    Products sort by ``earmarked_at`` desc (newest first); each product's links
    sort by ``asking_price`` asc (cheapest first, NULLs last)."""
    with db.connect() as conn:
        prods = conn.execute(
            "SELECT * FROM earmarked_products ORDER BY earmarked_at DESC, product_id DESC"
        ).fetchall()
        links = conn.execute("SELECT * FROM earmark_links").fetchall()
    by_product: dict[int, list[EarmarkLink]] = {}
    for r in links:
        by_product.setdefault(r["product_id"], []).append(EarmarkLink(
            link_id=r["link_id"], product_id=r["product_id"], store_url=r["store_url"],
            store_name=r["store_name"], asking_price=r["asking_price"],
            currency=r["currency"], captured_at=r["captured_at"], notes=r["notes"],
        ))
    out: list[EarmarkProduct] = []
    for p in prods:
        plinks = by_product.get(p["product_id"], [])
        plinks.sort(key=lambda l: (l.asking_price is None, l.asking_price or 0.0))
        out.append(EarmarkProduct(
            product_id=p["product_id"], set_code=p["set_code"],
            product_uuid=p["product_uuid"], product_name=p["product_name"],
            category=p["category"], subtype=p["subtype"],
            release_date=p["release_date"], card_count=p["card_count"],
            notes=p["notes"], earmarked_at=p["earmarked_at"],
            kind=p["kind"], scryfall_id=p["scryfall_id"],
            collector_number=p["collector_number"], finish=p["finish"],
            links=plinks,
        ))
    return out


# ---------- writes ----------

def earmark_add(
    set_code: str,
    product_name: str,
    store_url: str,
    *,
    product_uuid: str | None = None,
    category: str | None = None,
    subtype: str | None = None,
    release_date: str | None = None,
    card_count: int | None = None,
    store_name: str | None = None,
    asking_price: float | None = None,
    currency: str = "USD",
    product_notes: str | None = None,
    link_notes: str | None = None,
    kind: str = "sealed",
    scryfall_id: str | None = None,
    collector_number: str | None = None,
    finish: str | None = None,
    conn=None,
) -> dict:
    """Upsert a product (sealed: by ``set_code`` + ``product_name``; single: by
    ``set_code`` + ``collector_number`` + ``finish``) and one storefront
    link (by ``store_url``) in one atomic transaction.

    Product-level fields (category/subtype/…) are refreshed on re-add so a later
    earmark can fill in metadata an earlier one lacked. Adding a second store for
    an existing product just inserts a new link. Re-adding the same ``store_url``
    updates that link's asking-price snapshot + ``captured_at``.

    Returns ``{"product_action": "inserted"|"updated", "link_action":
    "inserted"|"updated", "product_id": int, "link_id": int}``.
    """
    set_code = set_code.lower()
    if kind not in ("sealed", "single"):
        raise ValueError(f"kind must be 'sealed' or 'single', got {kind!r}")
    if kind == "single":
        if not collector_number:
            raise ValueError("a single earmark requires a collector_number")
        if finish not in ("nonfoil", "foil"):
            raise ValueError(f"a single earmark requires finish nonfoil|foil, got {finish!r}")
    if store_name is None:
        store_name = store_name_from_url(store_url)
    now = db._utcnow_iso()
    with db.transaction(conn) as conn:
        if kind == "single":
            existing = conn.execute(
                "SELECT product_id FROM earmarked_products WHERE kind = 'single' "
                "AND set_code = ? AND collector_number = ? AND finish = ?",
                (set_code, collector_number, finish),
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT product_id FROM earmarked_products WHERE set_code = ? AND product_name = ?",
                (set_code, product_name),
            ).fetchone()
        if existing is None:
            cur = conn.execute(
                "INSERT INTO earmarked_products (set_code, product_uuid, product_name, "
                "category, subtype, release_date, card_count, notes, earmarked_at, "
                "kind, scryfall_id, collector_number, finish) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (set_code, product_uuid, product_name, category, subtype,
                 release_date, card_count, product_notes, now,
                 kind, scryfall_id, collector_number, finish),
            )
            product_id = cur.lastrowid
            product_action = "inserted"
        else:
            product_id = existing["product_id"]
            # Refresh metadata (coalesce: keep old value if new one is None).
            conn.execute(
                "UPDATE earmarked_products SET "
                "product_uuid = COALESCE(?, product_uuid), "
                "category = COALESCE(?, category), "
                "subtype = COALESCE(?, subtype), "
                "release_date = COALESCE(?, release_date), "
                "card_count = COALESCE(?, card_count), "
                "notes = COALESCE(?, notes), "
                "scryfall_id = COALESCE(?, scryfall_id) "
                "WHERE product_id = ?",
                (product_uuid, category, subtype, release_date, card_count,
                 product_notes, scryfall_id, product_id),
            )
            product_action = "updated"

        link = conn.execute(
            "SELECT link_id FROM earmark_links WHERE store_url = ?", (store_url,)
        ).fetchone()
        if link is None:
            cur = conn.execute(
                "INSERT INTO earmark_links (product_id, store_url, store_name, "
                "asking_price, currency, captured_at, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (product_id, store_url, store_name, asking_price, currency, now, link_notes),
            )
            link_id = cur.lastrowid
            link_action = "inserted"
        else:
            link_id = link["link_id"]
            # Re-point to this product (in case identity was corrected) and
            # refresh the asking-price snapshot + capture time.
            conn.execute(
                "UPDATE earmark_links SET product_id = ?, store_name = COALESCE(?, store_name), "
                "asking_price = ?, currency = ?, captured_at = ?, "
                "notes = COALESCE(?, notes) WHERE link_id = ?",
                (product_id, store_name, asking_price, currency, now, link_notes, link_id),
            )
            link_action = "updated"
        if asking_price is not None:
            record_price(link_id, asking_price, currency=currency, source="snapshot", at=now, conn=conn)
    return {"product_action": product_action, "link_action": link_action,
            "product_id": product_id, "link_id": link_id}


# ---------- price history (V32) ----------

def record_price(link_id: int, price: float | None, *, currency: str = "USD", available: bool | None = None,
                 source: str = "read", at: str | None = None, conn=None) -> None:
    """Append one price observation for a link."""
    with db.transaction(conn) as conn:
        conn.execute(
            "INSERT INTO earmark_prices (link_id, price, currency, available, read_at, source) VALUES (?, ?, ?, ?, ?, ?)",
            (link_id, price, currency, None if available is None else int(bool(available)), at or db._utcnow_iso(), source))


def record_reads(rows: list[dict], *, conn=None) -> int:
    """Record every read row whose URL is an earmarked link; returns how many."""
    urls = [r["url"] for r in rows if r.get("price") is not None]
    if not urls:
        return 0
    now = db._utcnow_iso()
    with db.transaction(conn) as conn:
        ids = {r[0]: r[1] for r in conn.execute(
            f"SELECT store_url, link_id FROM earmark_links WHERE store_url IN ({','.join('?' * len(urls))})", urls)}
        n = 0
        for r in rows:
            if r["url"] in ids and r.get("price") is not None:
                record_price(ids[r["url"]], r["price"], currency=r.get("currency") or "USD",
                             available=r.get("available"), at=now, conn=conn)
                n += 1
    return n


def price_history(link_ids: list[int]) -> dict[int, list[dict]]:
    """``link_id → [{price, currency, available, read_at, source}]`` oldest first."""
    if not link_ids:
        return {}
    out: dict[int, list[dict]] = {}
    with db.connect() as conn:
        for r in conn.execute(
            f"SELECT link_id, price, currency, available, read_at, source FROM earmark_prices "
            f"WHERE link_id IN ({','.join('?' * len(link_ids))}) ORDER BY read_at, price_id", link_ids):
            out.setdefault(r["link_id"], []).append({
                "price": r["price"], "currency": r["currency"],
                "available": None if r["available"] is None else bool(r["available"]),
                "read_at": r["read_at"], "source": r["source"]})
    return out


# ---------- price targets (V33) ----------

TARGET_MODES = ("price", "pct_under")


def set_target(product_id: int, mode: str, value: float, *, conn=None) -> dict:
    """Set (replace) a watched product's price target: ``price`` (USD) or
    ``pct_under`` (percent under its market price, 0–100). Raises ``ValueError``
    on a bad mode/value, ``LookupError`` when the product isn't watched."""
    if mode not in TARGET_MODES:
        raise ValueError(f"target mode must be one of {', '.join(TARGET_MODES)}")
    value = round(float(value or 0), 2)  # validate what is stored: 99.996 → 100.0 / 0.004 → 0.0 would trip the CHECK
    if value <= 0 or (mode == "pct_under" and value >= 100):
        raise ValueError("a price target must be above $0" if mode == "price" else "a percentage must be between 0 and 100")
    with db.transaction(conn) as conn:
        if conn.execute("SELECT 1 FROM earmarked_products WHERE product_id = ?", (product_id,)).fetchone() is None:
            raise LookupError(f"no watched product {product_id}")
        conn.execute(
            "INSERT INTO earmark_targets (product_id, mode, value, set_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(product_id) DO UPDATE SET mode = excluded.mode, value = excluded.value, set_at = excluded.set_at",
            (product_id, mode, value, db._utcnow_iso()))
    return targets([product_id])[product_id]


def clear_target(product_id: int, *, conn=None) -> bool:
    with db.transaction(conn) as conn:
        return conn.execute("DELETE FROM earmark_targets WHERE product_id = ?", (product_id,)).rowcount > 0


def targets(product_ids: list[int] | None = None) -> dict[int, dict]:
    """``product_id → {mode, value, set_at}`` (all targets, or just these products)."""
    sql = "SELECT product_id, mode, value, set_at FROM earmark_targets"
    args: list = []
    if product_ids is not None:
        if not product_ids:
            return {}
        sql += f" WHERE product_id IN ({','.join('?' * len(product_ids))})"
        args = list(product_ids)
    with db.connect() as conn:
        return {r[0]: {"mode": r[1], "value": r[2], "set_at": r[3]} for r in conn.execute(sql, args)}


def target_threshold(target: dict | None, market: float | None) -> float | None:
    """The price at or under which a target is met (``None`` when it can't be
    known yet: no target, or a percentage target without a market price)."""
    if not target:
        return None
    if target["mode"] == "price":
        return target["value"]
    return None if market is None else round(market * (1 - target["value"] / 100), 2)


# ---------- identity ----------

def resolve_identity(set_code: str, name: str | None, *,
                     collector_number: str | None = None, finish: str = "nonfoil") -> dict:
    """Validate a proposed sealed-product / Secret Lair drop / single-card identity → canonical dict.

    With ``collector_number`` it is a SINGLE printing (checked first, so ``sld`` +
    a collector number is a Secret Lair single, not a drop): :func:`resolve_single`
    verifies the printing, finish and (if given) ``name``.

    The single deterministic checkpoint shared by ``mm resolve-product``,
    ``mm earmark add`` and the web's *Watch*. Raises ``LookupError`` on no or an
    ambiguous match. Returns ``{kind, set_code, name, uuid?, category?, subtype?,
    release_date?, card_count?}`` (``kind`` = ``"sld"`` | ``"sealed"`` | ``"single"``).

    Secret Lair drops resolve through the engine that PRICES them
    (``sld.identify_drop``); store names carry a ``Secret Lair x`` scaffold + a
    finish marker the bare drop name lacks, so the input is normalized + stripped
    before matching. The finish is kept separately — inferred from the ORIGINAL
    name into ``subtype`` and appended to the canonical name (" (Foil Edition)")
    — so the two editions of one drop stay distinct earmarks."""
    from . import sealed, sld
    if collector_number:
        return resolve_single(set_code, collector_number, finish, name=name)
    if set_code.lower() == "sld":
        raw = name or ""
        drop = sld.identify_drop(sld.strip_finish_marker(sld.normalize_name(raw)))
        edition = sld.edition_from_name(raw)
        canonical = drop["name"] + (" (Foil Edition)" if edition == "foil" else "")
        return {"kind": "sld", "set_code": "sld", "name": canonical,
                "subtype": edition, "category": "secret_lair",
                "release_date": drop.get("release_date")}
    product = sealed.identify_product(set_code, name)
    return {
        "kind": "sealed", "set_code": set_code.lower(), "name": product["name"],
        "uuid": product.get("uuid"), "category": product.get("category"),
        "subtype": product.get("subtype"),
        "release_date": product.get("releaseDate"),
        "card_count": product.get("cardCount"),
    }


def earmark_remove_link(store_url: str, *, conn=None) -> dict:
    """Remove one storefront link. The product row survives (other links may
    reference it). Returns ``{"removed": bool}``."""
    with db.transaction(conn) as conn:
        cur = conn.execute("DELETE FROM earmark_links WHERE store_url = ?", (store_url,))
        return {"removed": cur.rowcount > 0}


def earmark_remove_product(set_code: str, product_name: str, *, conn=None) -> dict:
    """Remove a product and (via ON DELETE CASCADE) all its links. Returns
    ``{"removed": bool}``."""
    set_code = set_code.lower()
    with db.transaction(conn) as conn:
        cur = conn.execute(
            "DELETE FROM earmarked_products WHERE set_code = ? AND product_name = ?",
            (set_code, product_name),
        )
        return {"removed": cur.rowcount > 0}

"""Earmarked sealed products — a cross-storefront watchlist. CRUD only.

Two tables (V12):
  - ``earmarked_products`` — one row per MTGJSON sealed-product identity
    (``set_code`` + ``product_name``, ``product_uuid`` when known). High-level
    facts pulled from ``mtgjson.sealed_products`` at earmark time.
  - ``earmark_links`` — one row per storefront URL, joined to a product. The
    same product on three stores → one product row + three link rows, so the
    review collates them.

**What is (and isn't) stored here.** Only the NON-DERIVABLE facts live in the DB:
the store URL and a *snapshot* of its asking price + when it was captured (the
whole point of an earmark, and not recomputable). Market / intrinsic value is
deliberately NOT stored — ``scripts/review_earmarks.py`` recomputes it live via
the ``sealed`` engine so there is one source of price truth (DRY).

This module is pure CRUD; identity validation (does the product resolve in
MTGJSON?) is enforced by the CLI ``add`` command via ``sealed.identify_product``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from . import db


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
            notes=p["notes"], earmarked_at=p["earmarked_at"], links=plinks,
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
    conn=None,
) -> dict:
    """Upsert a product (by ``set_code`` + ``product_name``) and one storefront
    link (by ``store_url``) in one atomic transaction.

    Product-level fields (category/subtype/…) are refreshed on re-add so a later
    earmark can fill in metadata an earlier one lacked. Adding a second store for
    an existing product just inserts a new link. Re-adding the same ``store_url``
    updates that link's asking-price snapshot + ``captured_at``.

    Returns ``{"product_action": "inserted"|"updated", "link_action":
    "inserted"|"updated", "product_id": int, "link_id": int}``.
    """
    set_code = set_code.lower()
    if store_name is None:
        store_name = store_name_from_url(store_url)
    now = db._utcnow_iso()
    with db.transaction(conn) as conn:
        existing = conn.execute(
            "SELECT product_id FROM earmarked_products WHERE set_code = ? AND product_name = ?",
            (set_code, product_name),
        ).fetchone()
        if existing is None:
            cur = conn.execute(
                "INSERT INTO earmarked_products (set_code, product_uuid, product_name, "
                "category, subtype, release_date, card_count, notes, earmarked_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (set_code, product_uuid, product_name, category, subtype,
                 release_date, card_count, product_notes, now),
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
                "notes = COALESCE(?, notes) "
                "WHERE product_id = ?",
                (product_uuid, category, subtype, release_date, card_count,
                 product_notes, product_id),
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
    return {"product_action": product_action, "link_action": link_action,
            "product_id": product_id, "link_id": link_id}


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

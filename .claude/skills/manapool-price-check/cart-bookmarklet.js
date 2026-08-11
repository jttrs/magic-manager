/*
 * Mana Pool cart exporter — bookmarklet (tier-1 cart fetch).
 *
 * WHAT IT DOES
 *   Run this while viewing https://manapool.com/cart (logged in). It reuses your
 *   live Supabase session token to read your cart server-side (the RLS-scoped
 *   `cart_items` table), enriches each line into price/seller/product, ALSO
 *   scrapes the rendered card name/set/finish from the page, and copies a
 *   normalized JSON array to your clipboard. Paste that into:
 *       pbpaste | uv run python scripts/manapool_cart.py --file -
 *   (or straight into scripts/manapool_price_check.py).
 *
 * WHY A BOOKMARKLET
 *   The cart isn't in Mana Pool's sanctioned API. This runs inside your own
 *   authenticated tab, so it needs no stored credentials and rides whatever
 *   auth the page already holds. Robust to backend changes since it uses the
 *   same calls the site itself makes.
 *
 * INSTALL
 *   Create a new bookmark; set its URL to the minified `javascript:` one-liner
 *   in cart-bookmarklet.min.txt (generated from this file). Click it on the
 *   cart page.
 *
 * SECURITY
 *   Reads your session token from the page only to authenticate the read; the
 *   token is never displayed or stored by this script — only the resulting cart
 *   JSON goes to your clipboard.
 */
(async () => {
  const SB = "https://sb-api.manapool.com";
  const APIKEY = "sb_publishable_mwzveHhY-M-t19HCwYC1lw_pRUJyYZP";
  const PROJECT_REF = "hjcswxouetokzgwaavis";
  const INV_SELECT =
    "inventoryId:id,priceCents:adjusted_price_cents_new,sellerId:seller_id," +
    "quantityAvailable:live_quantity," +
    "product:products!inner(id,type," +
    "single:products_mtg_single(cardId:card_id,languageId:language_id," +
    "conditionId:condition_id,finishId:finish_id,uniqueProductId:unique_product_id))";

  // ---- find the session JWT the page holds (supabase-ssr: cookie or localStorage) ----
  function decodeMaybeBase64(v) {
    if (!v) return null;
    if (v.startsWith("base64-")) v = v.slice(7);
    try { return JSON.parse(v); } catch (e) {}
    try { return JSON.parse(atob(v)); } catch (e) {}
    return null;
  }
  function findToken() {
    const keyRe = new RegExp("sb-" + PROJECT_REF + "-auth-token");
    // localStorage (may be plain or chunked .0/.1)
    const lsKeys = Object.keys(localStorage).filter((k) => keyRe.test(k));
    if (lsKeys.length) {
      // reassemble chunks in order
      const base = lsKeys.filter((k) => !/\.\d+$/.test(k));
      let raw = null;
      if (base.length) raw = localStorage.getItem(base[0]);
      else {
        const chunks = lsKeys.filter((k) => /\.\d+$/.test(k))
          .sort((a, b) => (+a.split(".").pop()) - (+b.split(".").pop()));
        raw = chunks.map((k) => localStorage.getItem(k)).join("");
      }
      const obj = decodeMaybeBase64(raw);
      if (obj && obj.access_token) return obj.access_token;
    }
    // cookies (chunked .0/.1 common with supabase-ssr)
    const cookies = Object.fromEntries(document.cookie.split("; ").map((c) => {
      const i = c.indexOf("="); return [c.slice(0, i), decodeURIComponent(c.slice(i + 1))];
    }));
    const ckKeys = Object.keys(cookies).filter((k) => keyRe.test(k))
      .sort((a, b) => (+(a.split(".").pop()) || 0) - (+(b.split(".").pop()) || 0));
    if (ckKeys.length) {
      const raw = ckKeys.map((k) => cookies[k]).join("");
      const obj = decodeMaybeBase64(raw);
      if (obj && obj.access_token) return obj.access_token;
    }
    return null;
  }

  const jwt = findToken();
  if (!jwt) {
    alert("MP cart export: couldn't find your session token. Make sure you're logged in on manapool.com and on the cart page, then retry.");
    return;
  }
  const auth = { apikey: APIKEY, Authorization: "Bearer " + jwt };

  try {
    // 1. authoritative cart (server-side, RLS-scoped)
    const cart = await fetch(SB + "/rest/v1/cart_items?select=*", { headers: auth }).then((r) => r.json());
    if (!Array.isArray(cart) || !cart.length) {
      alert("MP cart export: cart_items came back empty. Is your cart empty?");
      return;
    }
    // discover the inventory-id column
    const invField = ["inventory_id", "inventoryId", "listing_id", "listingId", "id"]
      .find((k) => k in cart[0]) ||
      Object.keys(cart[0]).find((k) => /(_id|Id)$/.test(k) && typeof cart[0][k] === "string" && cart[0][k].length === 36);
    const qtyField = ["quantity", "qty", "count"].find((k) => k in cart[0]);
    const invIds = cart.map((r) => r[invField]).filter(Boolean);
    const qtyByInv = {};
    cart.forEach((r) => { qtyByInv[r[invField]] = qtyField ? (r[qtyField] || 1) : 1; });

    // 2. enrich inventoryIds -> price/seller/product (batches of 100)
    const enriched = [];
    for (let i = 0; i < invIds.length; i += 100) {
      const idList = invIds.slice(i, i + 100).join(",");
      const qs = new URLSearchParams({ select: INV_SELECT }).toString() + "&id=in.(" + idList + ")";
      const rows = await fetch(SB + "/rest/v1/inventory?" + qs, { headers: auth }).then((r) => r.json());
      if (Array.isArray(rows)) enriched.push(...rows);
    }

    // 3. best-effort: scrape rendered card name/set from the cart DOM, keyed loosely by order.
    // Cart rows render the card name in a link to /card/<set>/<num>/<slug>. Harvest those.
    const domCards = Array.from(document.querySelectorAll('a[href*="/card/"]')).map((a) => {
      const m = a.getAttribute("href").match(/\/card\/([a-z0-9]+)\/([^/]+)/i);
      return m ? { set: m[1], number: m[2], name: (a.textContent || "").trim() } : null;
    }).filter(Boolean);

    // 4. normalize (attach DOM name/set by cardId order-agnostic best match on index)
    const items = enriched.map((r, idx) => {
      const single = (r.product && r.product.single) || {};
      const dom = domCards[idx] || {};
      return {
        inventory_id: r.inventoryId,
        price_cents: r.priceCents,
        seller_id: r.sellerId,
        quantity: qtyByInv[r.inventoryId] || 1,
        card_id: single.cardId,
        condition_id: single.conditionId,
        finish_id: single.finishId,
        unique_product_id: single.uniqueProductId,
        name: dom.name || null,
        set: dom.set || null,
        number: dom.number || null,
      };
    });

    const payload = JSON.stringify({ source: "manapool-cart-bookmarklet", count: items.length, items }, null, 2);
    await navigator.clipboard.writeText(payload);
    alert("MP cart export: copied " + items.length + " line items to clipboard.\nNow run:\n  pbpaste | uv run python scripts/manapool_cart.py --file -");
  } catch (e) {
    alert("MP cart export failed: " + e.message + "\n(Backend may have changed, or session expired — reload the cart page and retry.)");
  }
})();

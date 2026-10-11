// magic-manager companion — order history reads (Mana Pool, TCGplayer, Card Kingdom).
//
// Runs in the worker. Opens ONE background tab of its own on the store's order
// pages (never one of your tabs), reads them with the store's reader file, and
// closes it. Two requests:
//  * order_list — every order on your order history pages: number, date, total.
//    The page links the companion follows stay here; they are not sent.
//  * orders     — the orders you ticked in the app, with their lines.
// Reads only; never submits a form or changes anything on the store.

import { MAX_ORDER_PAGES, MAX_ORDERS_PER_READ, ORDER_STORES } from './protocol.js';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function ORDER_FEATURES(has) {
  return {
    orders_tcgplayer: await has(ORDER_STORES.tcgplayer.origins),
    orders_cardkingdom: await has(ORDER_STORES.cardkingdom.origins),
  };
}

const READ = {
  manapool: { list: () => readManaPoolOrderList(document), detail: () => readManaPoolOrder(document), show: () => ({ ok: manaPoolShowItems(document) }) }, // eslint-disable-line no-undef
  tcgplayer: { list: () => readTcgplayerOrders(document) }, // eslint-disable-line no-undef
  cardkingdom: { list: () => readCardKingdomOrderList(document), detail: () => readCardKingdomInvoice(document) }, // eslint-disable-line no-undef
};

/** The store's own pages only: same origin, a relative path or a same-origin URL. */
function sameStoreUrl(store, href) {
  try {
    const u = new URL(href, store.origin);
    return u.origin === store.origin ? u.href : null;
  } catch { return null; }
}

async function withOwnTab(url, fn) {
  const tab = await chrome.tabs.create({ url, active: false });
  try { return await fn(tab); } finally { chrome.tabs.remove(tab.id).catch(() => {}); }
}

async function go(tab, url, h) {
  await chrome.tabs.update(tab.id, { url });
  await sleep(300);
  return h.loaded(tab.id, 25_000);
}

/** Inject + call a reader until it reads (pages render after load), up to `ms`. */
async function poll(tab, store, fn, h, ms = 10_000) {
  const end = Date.now() + ms;
  let out;
  for (;;) {
    try {
      out = await h.inject(tab.id, store.reader, fn);
    } catch {
      return { ok: false, code: 'orders.not_scriptable' };
    }
    if (out?.ok || out?.code === 'orders.sign_in' || Date.now() > end) return out || { ok: false, code: 'orders.page_changed' };
    await sleep(500);
  }
}

async function listPages(key, tab, h) {
  const store = ORDER_STORES[key];
  const orders = [];
  const warnings = [];
  const seen = new Set();
  let range = null;
  let pages = 0;
  let url = store.list;
  for (;;) {
    pages += 1;
    if (pages > 1 && !await go(tab, url, h)) return { ok: false, code: 'orders.load_timeout' };
    const out = await poll(tab, store, READ[key].list, h);
    if (!out.ok) {
      if (pages > 1 && out.code === 'orders.none') break;
      return out;
    }
    range = out.range ?? range;
    warnings.push(...(out.warnings || []));
    for (const o of out.orders) if (!seen.has(o.order_id)) { seen.add(o.order_id); orders.push(o); }
    const next = out.next && sameStoreUrl(store, out.next);
    if (!next || next === url || pages >= MAX_ORDER_PAGES) {
      if (next && pages >= MAX_ORDER_PAGES) warnings.push({ code: 'orders.too_many_pages', pages });
      break;
    }
    url = next;
  }
  return { ok: true, orders, warnings, range, pages };
}

function storeOrFail(params) {
  const key = String(params.store || '');
  return Object.hasOwn(ORDER_STORES, key) ? key : null;
}

export async function readOrderList(params, h) {
  const key = storeOrFail(params);
  if (!key) return h.fail('request.invalid', { detail: 'unknown store' });
  const store = ORDER_STORES[key];
  if (!await chrome.permissions.contains({ origins: store.origins })) return h.fail(key === 'manapool' ? 'permission.manapool_missing' : 'permission.orders_off');
  return withOwnTab(store.list, async (tab) => {
    if (!await h.loaded(tab.id, 25_000)) return h.fail('orders.load_timeout');
    const out = await listPages(key, tab, h);
    if (!out.ok) return h.fail(out.code || 'orders.page_changed', { warnings: out.warnings || [] });
    return { ok: true, data: {
      store: key, range: out.range, pages: out.pages, warnings: out.warnings,
      orders: out.orders.map((o) => ({ order_id: o.order_id, ordered_at: o.ordered_at, total: o.total ?? null, lines: o.lines ? o.lines.length : null })),
    } };
  });
}

export async function readOrders(params, h) {
  const key = storeOrFail(params);
  const ids = Array.isArray(params.ids) ? params.ids.filter((x) => typeof x === 'string' && /^[A-Za-z0-9-]{1,64}$/.test(x)) : [];
  if (!key || !ids.length || ids.length > MAX_ORDERS_PER_READ || ids.length !== params.ids.length) return h.fail('request.invalid', { detail: 'store and 1–100 order numbers' });
  const store = ORDER_STORES[key];
  if (!await chrome.permissions.contains({ origins: store.origins })) return h.fail(key === 'manapool' ? 'permission.manapool_missing' : 'permission.orders_off');
  return withOwnTab(store.list, async (tab) => {
    if (!await h.loaded(tab.id, 25_000)) return h.fail('orders.load_timeout');
    const list = await listPages(key, tab, h);
    if (!list.ok) return h.fail(list.code || 'orders.page_changed', { warnings: list.warnings || [] });
    const byId = new Map(list.orders.map((o) => [o.order_id, o]));
    const warnings = [...list.warnings];
    const orders = [];
    for (const id of ids) {
      const head = byId.get(id);
      if (!head) { warnings.push({ code: 'orders.not_found', order: id }); continue; }
      if (!READ[key].detail) {
        // TCGplayer lists every order's items inline.
        const { path: _p, ...o } = head; // eslint-disable-line no-unused-vars
        orders.push(o);
        continue;
      }
      const url = sameStoreUrl(store, head.path);
      if (!url || !await go(tab, url, h)) { warnings.push({ code: 'orders.load_timeout', order: id }); continue; }
      if (READ[key].show) await poll(tab, store, READ[key].show, h, 8_000);
      const out = await poll(tab, store, READ[key].detail, h);
      if (!out?.ok) { warnings.push({ code: out?.code || 'orders.page_changed', order: id }); continue; }
      warnings.push(...(out.warnings || []).map((w) => ({ ...w, order: id })));
      orders.push({ ...out.order, order_id: id, ordered_at: head.ordered_at, total: out.order.total ?? head.total ?? null });
    }
    if (!orders.length) return h.fail('orders.not_found', { warnings });
    return { ok: true, data: { store: key, orders, warnings } };
  });
}

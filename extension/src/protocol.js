// Shared constants and validators for the extension's own pages and worker.
// (Content scripts can't import modules, so bridge.js repeats CHANNEL.)

import { STORES } from './stores.js';

export const CHANNEL = 'magic-manager/companion';
export const KINDS = ['cart', 'tabs', 'moxfield', 'order_list', 'orders', 'watched', 'archidekt', 'moxfield_collection', 'moxfield_binders'];
export const APPROVAL_TTL_MS = 5 * 60 * 1000;
export const MAX_PAYLOAD_BYTES = 2_000_000;
/** A whole Moxfield collection runs to tens of thousands of lines (≤ 60,000 printings, ~120 bytes
 *  each; long names make it more) — what is sent, as JSON. */
export const MAX_COLLECTION_BYTES = 24_000_000;
export const maxPayload = (kind) => (kind === 'moxfield_collection' ? MAX_COLLECTION_BYTES : MAX_PAYLOAD_BYTES);
/** Chrome's session storage holds 10 MB and counts objects at their in-memory size (a 40,000-line
 *  collection as objects is over the limit at ~5 MB of JSON). So a waiting read is held packed —
 *  gzipped JSON in one string — and must fit in this. */
export const SESSION_BUDGET_BYTES = 8_000_000;

/** A read's data → one gzipped, base64 string (what the pending request holds until you decide). */
export async function packData(data) {
  const gz = await new Response(new Blob([JSON.stringify(data)]).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer();
  const bytes = new Uint8Array(gz);
  let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}

/** The data a packed string holds (see packData). */
export async function unpackData(packed) {
  const bin = atob(packed);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return JSON.parse(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text());
}

/** UTF-8 size of a value as JSON (what the cap measures). */
export const jsonBytes = (data) => new TextEncoder().encode(JSON.stringify(data)).length;
/** Most watched store pages one Watching read may open + read. */
export const MAX_WATCHED = 50;

export const MANAPOOL_CART_URL = 'https://manapool.com/cart';
export const MANAPOOL_ORIGINS = ['https://manapool.com/*'];
// Other carts (opt-in via Allow access): the cart page’s own host only.
export const TCGPLAYER_CART_ORIGINS = ['https://www.tcgplayer.com/*'];
export const CARDKINGDOM_CART_ORIGINS = ['https://www.cardkingdom.com/*'];
export const CART_STORES = {
  manapool: {
    name: 'Mana Pool', url: MANAPOOL_CART_URL, matches: ['https://manapool.com/cart*'], origins: MANAPOOL_ORIGINS,
    reader: 'src/readers/manapool-cart.js', fn: 'readManaPoolCart', permission: 'permission.manapool_missing',
  },
  tcgplayer: {
    name: 'TCGplayer', url: 'https://www.tcgplayer.com/cart', matches: ['https://www.tcgplayer.com/cart*'], origins: TCGPLAYER_CART_ORIGINS,
    reader: 'src/readers/tcgplayer-cart.js', fn: 'readTcgplayerCart', permission: 'permission.tcgplayer_cart_off',
  },
  cardkingdom: {
    name: 'Card Kingdom', url: 'https://www.cardkingdom.com/cart', matches: ['https://www.cardkingdom.com/cart*'], origins: CARDKINGDOM_CART_ORIGINS,
    reader: 'src/readers/cardkingdom-cart.js', fn: 'readCardKingdomCart', permission: 'permission.cardkingdom_cart_off',
  },
};
export const MOXFIELD_ORIGINS = ['https://moxfield.com/*', 'https://*.moxfield.com/*'];
export const MOXFIELD_TABS = ['https://moxfield.com/*', 'https://www.moxfield.com/*'];
// Archidekt decks (opt-in): the deck page itself, read with your own session.
export const ARCHIDEKT_ORIGINS = ['https://archidekt.com/*', 'https://www.archidekt.com/*'];
export const ARCHIDEKT_DECK = /^https:\/\/(?:www\.)?archidekt\.com\/decks\/(\d{1,12})(?:[/?#-]|$)/;
// Moxfield collection / binder share links.
export const MOXFIELD_COLLECTION = /^https:\/\/(?:www\.)?moxfield\.com\/collection\/([A-Za-z0-9_-]{4,64})(?:[/?#]|$)/;
export const MOXFIELD_BINDER = /^https:\/\/(?:www\.)?moxfield\.com\/binders\/([A-Za-z0-9_-]{4,64})(?:[/?#]|$)/;
// Order history (purchases). Mana Pool needs no extra permission (install-time);
// TCGplayer + Card Kingdom are part of the optional Allow access grant.
export const TCGPLAYER_ORDER_ORIGINS = ['https://store.tcgplayer.com/*'];
export const CARDKINGDOM_ORDER_ORIGINS = ['https://www.cardkingdom.com/*'];
export const ORDER_ORIGINS = [...TCGPLAYER_ORDER_ORIGINS, ...CARDKINGDOM_ORDER_ORIGINS];
export const ORDER_STORES = {
  manapool: {
    name: 'Mana Pool', origins: MANAPOOL_ORIGINS, list: 'https://manapool.com/settings/orders',
    reader: 'src/readers/manapool-orders.js', origin: 'https://manapool.com',
  },
  tcgplayer: {
    name: 'TCGplayer', origins: TCGPLAYER_ORDER_ORIGINS, list: 'https://store.tcgplayer.com/myaccount/orderhistory',
    reader: 'src/readers/tcgplayer-orders.js', origin: 'https://store.tcgplayer.com',
  },
  cardkingdom: {
    name: 'Card Kingdom', origins: CARDKINGDOM_ORDER_ORIGINS, list: 'https://www.cardkingdom.com/myaccount/order_history',
    reader: 'src/readers/cardkingdom-orders.js', origin: 'https://www.cardkingdom.com',
  },
};
export const MAX_ORDER_PAGES = 30;
export const MAX_ORDERS_PER_READ = 100;
export const MOXFIELD_DECK = /^https:\/\/(?:www\.)?moxfield\.com\/decks\/([A-Za-z0-9_-]{4,64})(?:[/?#]|$)/;

/** Chrome match patterns for every Deals store (bare host + subdomains). */
export const STORE_ORIGINS = STORES.flatMap((s) => s.hosts.flatMap((h) => [`https://${h}/*`, `https://*.${h}/*`]));

/** Every optional site the readers use — what the one "Allow access" switch asks Chrome for
 *  (owner, 2026-10-11: one grant instead of a switch per feature). The paired app address is
 *  separate (pairing), and Mana Pool is install-time. */
export const ALL_ACCESS_ORIGINS = [...new Set([
  ...TCGPLAYER_CART_ORIGINS, ...CARDKINGDOM_CART_ORIGINS, ...STORE_ORIGINS, ...MOXFIELD_ORIGINS,
  ...ARCHIDEKT_ORIGINS, ...ORDER_ORIGINS,
])];

/** The bridge content script, registered for the paired app address only (bridge.js re-checks the
 *  exact origin). Chrome drops dynamically registered scripts when the extension is reloaded or
 *  updated, so the worker re-registers it (background.js ensureBridge). */
export const BRIDGE_ID = 'mm-bridge';
export function bridgeScript(pattern) {
  return { id: BRIDGE_ID, matches: [pattern], js: ['src/bridge.js'], runAt: 'document_start', allFrames: false, persistAcrossSessions: true };
}

/** The store a hostname belongs to, if any. */
export function storeOf(hostname) {
  const h = String(hostname || '').toLowerCase().replace(/^www\./, '');
  return STORES.find((s) => s.hosts.some((x) => h === x || h.endsWith(`.${x}`))) || null;
}

/**
 * The app address the user typed, as a bare origin — or an error string.
 * http only on this computer (localhost / 127.0.0.1); anything else must be
 * https on a Tailscale name (*.ts.net) — the hosts this build may be paired with.
 */
export function parseAppOrigin(input) {
  let u;
  try { u = new URL(String(input || '').trim()); } catch { return { error: 'Enter the address you open the app at, like http://localhost:8766.' }; }
  if (u.username || u.password) return { error: 'The address must not contain a user name or password.' };
  if (u.pathname !== '/' || u.search || u.hash) return { error: 'Enter just the address (no path), like http://localhost:8766.' };
  const local = u.hostname === 'localhost' || u.hostname === '127.0.0.1';
  if (u.protocol === 'http:' && !local) return { error: 'Plain http is only allowed for this computer (localhost). Use https.' };
  if (u.protocol !== 'http:' && u.protocol !== 'https:') return { error: 'The address must start with http:// or https://.' };
  if (!local && !/\.ts\.net$/i.test(u.hostname)) return { error: 'This build can pair with this computer (localhost) or your Tailscale address (…ts.net) only.' };
  return { origin: u.origin, pattern: `${u.protocol}//${u.hostname}/*` };
}

/** Small, total summaries for the approval window. */
export function summarize(kind, data) {
  if (kind === 'cart') {
    const items = data.items || [];
    const copies = items.reduce((n, i) => n + (i.quantity || 0), 0);
    const total = items.reduce((n, i) => n + (i.price || 0) * (i.quantity || 0), 0);
    return `${CART_STORES[data.store]?.name || 'Mana Pool'} cart · ${items.length} lines · ${copies} items · $${total.toFixed(2)}`;
  }
  if (kind === 'tabs') {
    const pages = Object.keys(data.pages || {}).length;
    return `${(data.tabs || []).length} store tabs${pages ? ` · ${pages} page readings` : ''}`;
  }
  if (kind === 'watched') {
    const urls = data.urls || [];
    if (!data.pages) {
      const toOpen = urls.filter((u) => !u.open).length;
      return `${urls.length} watched store pages${toOpen ? ` · ${toOpen} to open in a background tab` : ''}`;
    }
    return `${Object.keys(data.pages).length} of ${urls.length} watched store pages read`;
  }
  if (kind === 'moxfield') {
    const n = Object.values(data.deck?.boards || {}).reduce((t, b) => t + Object.values(b.cards || {}).reduce((s, c) => s + (c.quantity || 0), 0), 0);
    return `${data.deck?.name || 'Deck'} · ${n} cards`;
  }
  if (kind === 'archidekt') {
    const n = (data.deck?.cards || []).reduce((t, c) => t + (c.quantity || 0), 0);
    return `${data.deck?.name || 'Deck'} · ${n} cards`;
  }
  if (kind === 'moxfield_binders') return `${(data.binders || []).length} Moxfield binders`;
  if (kind === 'moxfield_collection') {
    const c = data.collection || {};
    const lines = c.lines || [];
    const copies = lines.reduce((t, l) => t + (l.quantity || 0), 0);
    const what = c.scope === 'binder' ? `Moxfield binder${c.name ? ` “${c.name}”` : ''}` : c.id ? 'Moxfield collection (shared link)' : 'Your Moxfield collection';
    return `${what} · ${lines.length} printings · ${copies} cards`;
  }
  if (kind === 'order_list') {
    const n = (data.orders || []).length;
    return `${n} ${ORDER_STORES[data.store]?.name || ''} orders`.replace('  ', ' ');
  }
  if (kind === 'orders') {
    const orders = data.orders || [];
    const lines = orders.reduce((t, o) => t + (o.lines || []).length, 0);
    const paid = orders.reduce((t, o) => t + (o.lines || []).reduce((s, l) => s + (l.price || 0) * (l.quantity || 0), 0), 0);
    return `${orders.length} ${ORDER_STORES[data.store]?.name || ''} orders · ${lines} lines · $${paid.toFixed(2)} in items`;
  }
  return '';
}

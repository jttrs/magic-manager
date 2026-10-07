// Shared constants and validators for the extension's own pages and worker.
// (Content scripts can't import modules, so bridge.js repeats CHANNEL.)

import { STORES } from './stores.js';

export const CHANNEL = 'magic-manager/companion';
export const KINDS = ['cart', 'tabs', 'moxfield'];
export const APPROVAL_TTL_MS = 5 * 60 * 1000;
export const MAX_PAYLOAD_BYTES = 2_000_000;

export const MANAPOOL_CART_URL = 'https://manapool.com/cart';
export const MANAPOOL_ORIGINS = ['https://manapool.com/*'];
export const MOXFIELD_ORIGINS = ['https://moxfield.com/*', 'https://*.moxfield.com/*'];
export const MOXFIELD_DECK = /^https:\/\/(?:www\.)?moxfield\.com\/decks\/([A-Za-z0-9_-]{4,64})(?:[/?#]|$)/;

/** Chrome match patterns for every Deals store (bare host + subdomains). */
export const STORE_ORIGINS = STORES.flatMap((s) => s.hosts.flatMap((h) => [`https://${h}/*`, `https://*.${h}/*`]));

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
  try { u = new URL(String(input || '').trim()); } catch { return { error: 'Enter the address you open the app at, like http://localhost:8765.' }; }
  if (u.username || u.password) return { error: 'The address must not contain a user name or password.' };
  if (u.pathname !== '/' || u.search || u.hash) return { error: 'Enter just the address (no path), like http://localhost:8765.' };
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
    return `${items.length} cart lines · ${copies} cards · $${total.toFixed(2)}`;
  }
  if (kind === 'tabs') {
    const pages = Object.keys(data.pages || {}).length;
    return `${(data.tabs || []).length} store tabs${pages ? ` · ${pages} page readings` : ''}`;
  }
  if (kind === 'moxfield') {
    const n = Object.values(data.deck?.boards || {}).reduce((t, b) => t + Object.values(b.cards || {}).reduce((s, c) => s + (c.quantity || 0), 0), 0);
    return `${data.deck?.name || 'Deck'} · ${n} cards`;
  }
  return '';
}

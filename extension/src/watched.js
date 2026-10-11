// magic-manager companion — read your WATCHED open-tab store pages (Deals → Watching).
//
// Two steps, both in the companion's own approval window
// (docs/browser-companion-security.md):
//  1. plan: the app names the watched links; only https product pages of a
//     catalogued `rendered` store are kept (re-checked here — the app's list is
//     never trusted). Nothing is opened yet: you see the list, and which pages
//     would open in a background tab, and press "Read these pages".
//  2. read: each page is read with the same reader as the open-tab Deals read
//     (readers/store-page.js) — from your tab when it's open, else from a tab
//     opened inactive and ALWAYS closed afterwards (never one of yours). At most
//     3 at a time. Then you see exactly what would be sent and press Send.

import { MAX_WATCHED, storeOf } from './protocol.js';

const PARALLEL = 3;
const LOAD_TIMEOUT_MS = 20_000;
const RENDER_WAIT_MS = 8_000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** The watched link as an https product page of a catalogued open-tab store, or null. */
export function watchedPage(raw) {
  let u;
  try { u = new URL(String(raw || '')); } catch { return null; }
  if (u.protocol !== 'https:' || u.username || u.password || u.port) return null;
  const store = storeOf(u.hostname);
  if (!store || store.mode !== 'rendered' || !new RegExp(store.product_path).test(u.pathname)) return null;
  return { url: u.href, store: store.name };
}

async function openTabs() {
  const out = new Map();
  for (const t of await chrome.tabs.query({})) {
    if (t.url && !t.incognito && !t.discarded && !out.has(t.url)) out.set(t.url, t.id);
  }
  return out;
}

/** Step 1 — validate the app's list; no tab is opened or read. */
export async function planWatched(params, fail, storeOrigins) {
  if (!Array.isArray(params.urls) || params.urls.length > MAX_WATCHED) return fail('request.invalid');
  if (!await chrome.permissions.contains({ origins: storeOrigins })) return fail('permission.deals_off');
  const seen = new Set();
  const pages = params.urls.map(watchedPage).filter((p) => p && !seen.has(p.url) && seen.add(p.url));
  if (!pages.length) return fail('watched.none');
  const open = await openTabs();
  return { ok: true, data: { urls: pages.map((p) => ({ ...p, open: open.has(p.url) })) } };
}

/** A page's price signals have rendered (or there's nothing more to wait for). */
const rendered = (p) => Boolean(p && (p.ld.length || /price/i.test(p.head) || /\$\s?\d/.test(p.text)));

async function readOne(entry, open, { inject, loaded }) {
  const read = (tabId) => inject(tabId, 'src/readers/store-page.js', () => readStorePage(document)); // eslint-disable-line no-undef
  const mine = open.get(entry.url);
  if (mine != null) {
    try {
      const now = await chrome.tabs.get(mine);   // still showing that page (not navigated away)?
      if (now.url !== entry.url) throw new Error('moved');
      return { page: await read(mine), opened: false };
    } catch { return { warning: 'tabs.page_unreadable', opened: false }; }
  }
  let tab = null;
  try {
    tab = await chrome.tabs.create({ url: entry.url, active: false });
    if (!await loaded(tab.id, LOAD_TIMEOUT_MS)) return { warning: 'watched.load_timeout', opened: true };
    const end = Date.now() + RENDER_WAIT_MS;
    let page = null;
    for (;;) {
      try { page = await read(tab.id); } catch { page = null; }
      if (rendered(page) || Date.now() > end) break;
      await sleep(500);
    }
    return page ? { page, opened: true } : { warning: 'tabs.page_unreadable', opened: true };
  } catch {
    return { warning: 'tabs.page_unreadable', opened: true };
  } finally {
    if (tab) chrome.tabs.remove(tab.id).catch(() => {});
  }
}

/** Step 2 — after you approved the list: read each page (≤ PARALLEL at once).
 *  ``deps.alive()`` false (you pressed Don't read / closed the window) stops opening more. */
export async function readWatched(plan, deps) {
  const urls = plan.urls.map((e) => watchedPage(e.url)).filter(Boolean).slice(0, MAX_WATCHED);
  const open = await openTabs();
  const results = new Array(urls.length);
  let next = 0;
  const worker = async () => {
    while (next < urls.length) {
      const i = next++;
      results[i] = await deps.alive() ? await readOne(urls[i], open, deps) : { warning: 'tabs.page_unreadable', opened: false };
    }
  };
  await Promise.all(Array.from({ length: Math.min(PARALLEL, urls.length) }, worker));
  const pages = {};
  const warnings = [];
  const out = urls.map((e, i) => {
    const r = results[i];
    if (r.page) pages[e.url] = r.page;
    else warnings.push({ code: r.warning, url: e.url });
    return { ...e, open: !r.opened };
  });
  return { urls: out, pages, warnings };
}

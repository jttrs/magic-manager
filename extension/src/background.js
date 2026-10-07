// magic-manager companion — background service worker.
//
// The only place requests are handled. Rules (docs/browser-companion-security.md):
//  * a request is accepted ONLY from the bridge running in the top frame of a tab
//    whose origin is the app address you paired (checked here, not trusted from
//    the page); no other website can reach this worker (no externally_connectable);
//  * the read happens in your browser and stays here until you press Send in the
//    companion's own approval window; one request at a time; nothing is stored
//    beyond the pending request (session memory, cleared on decision);
//  * reads are page/tab reads only — no cookies, storage, tokens or writes to any site.

import { STORES } from './stores.js';
import {
  APPROVAL_TTL_MS, KINDS, MANAPOOL_CART_URL, MANAPOOL_ORIGINS, MAX_PAYLOAD_BYTES, MOXFIELD_DECK,
  MOXFIELD_ORIGINS, STORE_ORIGINS, storeOf, summarize,
} from './protocol.js';

const SELF = chrome.runtime.getURL('');
const CATALOG = fetch(chrome.runtime.getURL('errors.json')).then((r) => r.json()).then((j) => j.codes);

async function fail(code, extra = {}) {
  const c = (await CATALOG)[code] || {};
  return { ok: false, code, message: c.message || code, fix: c.fix ?? null, ...extra };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function appOrigin() {
  const { appOrigin: o } = await chrome.storage.local.get('appOrigin');
  return typeof o === 'string' ? o : null;
}

async function features() {
  const has = (origins) => chrome.permissions.contains({ origins }).catch(() => false);
  return { cart: await has(MANAPOOL_ORIGINS), deals: await has(STORE_ORIGINS), moxfield: await has(MOXFIELD_ORIGINS) };
}

chrome.action.onClicked.addListener(() => chrome.runtime.openOptionsPage());

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  route(msg, sender).then(sendResponse, async (e) => sendResponse(await fail('request.invalid', { detail: String(e?.message || e).slice(0, 200) })));
  return true;
});

async function route(msg, sender) {
  if (sender.id !== chrome.runtime.id || !msg || typeof msg !== 'object') return undefined;
  // The extension's own pages first: the approval window is itself a tab.
  if (typeof sender.url === 'string' && sender.url.startsWith(SELF) && sender.origin === SELF.slice(0, -1)) return fromOwnPage(msg);
  if (sender.tab) return fromApp(msg, sender);
  return undefined;
}

// ---------- requests from the app (via bridge.js) ----------

async function fromApp(msg, sender) {
  const pinned = await appOrigin();
  if (!pinned || sender.frameId !== 0 || sender.origin !== pinned || !sameOrigin(sender.tab.url, pinned)) return undefined;
  if (msg.type === 'hello') return { ok: true, version: chrome.runtime.getManifest().version, features: await features() };
  if (msg.type !== 'request') return undefined;
  if (typeof msg.id !== 'string' || !/^[A-Za-z0-9_-]{8,64}$/.test(msg.id) || !KINDS.includes(msg.kind)) return fail('request.invalid');
  const params = msg.params && typeof msg.params === 'object' ? msg.params : {};

  const busy = await pendingRequest();
  if (busy) {
    if (Date.now() - busy.created < APPROVAL_TTL_MS) {
      if (busy.windowId != null) chrome.windows.update(busy.windowId, { focused: true }).catch(() => {});
      return fail('request.busy');
    }
    await finish(busy, await fail('request.expired'));
  }

  const read = await READERS[msg.kind](params);
  if (!read.ok) return read;
  if (JSON.stringify(read.data).length > MAX_PAYLOAD_BYTES) return fail('request.invalid', { detail: 'too large' });

  const pending = { id: msg.id, kind: msg.kind, tabId: sender.tab.id, origin: pinned, data: read.data,
    summary: summarize(msg.kind, read.data), created: Date.now(), windowId: null };
  await chrome.storage.session.set({ pending });
  const win = await chrome.windows.create({ url: chrome.runtime.getURL('src/approve.html'), type: 'popup', width: 620, height: 720, focused: true });
  pending.windowId = win.id;
  await chrome.storage.session.set({ pending });
  return { ok: true, status: 'awaiting_approval', summary: pending.summary };
}

function sameOrigin(url, origin) {
  try { return new URL(url).origin === origin; } catch { return false; }
}

async function pendingRequest() {
  const { pending } = await chrome.storage.session.get('pending');
  return pending || null;
}

/** Deliver a result to the requesting app tab — only if it is still on the app. */
async function finish(pending, result) {
  await chrome.storage.session.remove('pending');
  if (pending.windowId != null) chrome.windows.remove(pending.windowId).catch(() => {});
  let tab;
  try { tab = await chrome.tabs.get(pending.tabId); } catch { return false; }
  if (!sameOrigin(tab.url, pending.origin) || pending.origin !== await appOrigin()) return false;
  await chrome.tabs.sendMessage(pending.tabId, { type: 'result', id: pending.id, kind: pending.kind, ...result }, { frameId: 0 }).catch(() => {});
  return true;
}

// ---------- messages from the approval / options pages ----------

async function fromOwnPage(msg) {
  if (msg.type === 'decision') {
    const pending = await pendingRequest();
    if (!pending || pending.id !== msg.id) return { ok: false };
    if (msg.approve === true && Date.now() - pending.created < APPROVAL_TTL_MS) {
      const sent = await finish(pending, { ok: true, data: pending.data });
      return sent ? { ok: true } : fail('request.tab_moved');
    }
    await finish(pending, await fail(msg.approve === false ? 'request.denied' : 'request.expired'));
    return { ok: true };
  }
  if (msg.type === 'features') return { ok: true, features: await features() };
  return undefined;
}

chrome.windows.onRemoved.addListener(async (windowId) => {
  const pending = await pendingRequest();
  if (pending && pending.windowId === windowId) await finish({ ...pending, windowId: null }, await fail('request.expired'));
});

// ---------- readers ----------

const READERS = { cart: readCart, tabs: readTabs, moxfield: readMoxfield };

/** Wait until a tab we opened has loaded (or give up). */
async function loaded(tabId, timeoutMs) {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    const tab = await chrome.tabs.get(tabId).catch(() => null);
    if (!tab) return false;
    if (tab.status === 'complete') return true;
    await sleep(250);
  }
  return false;
}

async function inject(tabId, file, func, args = []) {
  await chrome.scripting.executeScript({ target: { tabId, frameIds: [0] }, files: [file] });
  const [res] = await chrome.scripting.executeScript({ target: { tabId, frameIds: [0] }, func, args });
  return res?.result;
}

async function withTab(url, matches, fn) {
  const existing = (await chrome.tabs.query({ url: matches })).find((t) => !t.incognito && !t.discarded);
  const tab = existing || await chrome.tabs.create({ url, active: false });
  try {
    return await fn(tab, !existing);
  } finally {
    if (!existing) chrome.tabs.remove(tab.id).catch(() => {});
  }
}

async function readCart() {
  if (!await chrome.permissions.contains({ origins: MANAPOOL_ORIGINS })) return fail('permission.manapool_missing');
  return withTab(MANAPOOL_CART_URL, ['https://manapool.com/cart*'], async (tab, opened) => {
    if (opened && !await loaded(tab.id, 20_000)) return fail('cart.load_timeout');
    // The cart renders after load: give rows up to 8 s to appear.
    const end = Date.now() + 8_000;
    let out;
    for (;;) {
      try {
        out = await inject(tab.id, 'src/readers/manapool-cart.js', () => readManaPoolCart(document)); // eslint-disable-line no-undef
      } catch {
        return fail('cart.not_scriptable');
      }
      if (out?.ok || Date.now() > end) break;
      await sleep(500);
    }
    if (!out) return fail('cart.page_changed');
    if (!out.ok) return fail(out.code, { warnings: out.warnings || [] });
    return { ok: true, data: { items: out.items, warnings: out.warnings || [], source: 'extension' } };
  });
}

async function readTabs() {
  if (!await chrome.permissions.contains({ origins: STORE_ORIGINS })) return fail('permission.deals_off');
  const all = await chrome.tabs.query({});
  const windows = [...new Set(all.map((t) => t.windowId))];
  const tabs = [];
  const pages = {};
  const warnings = [];
  const seen = new Set();
  for (const t of all) {
    if (!t.url || t.incognito || seen.has(t.url)) continue;
    let u;
    try { u = new URL(t.url); } catch { continue; }
    if (u.protocol !== 'https:') continue;
    const store = storeOf(u.hostname);
    if (!store) continue;
    seen.add(t.url);
    tabs.push({ url: t.url, title: (t.title || '').slice(0, 500), window: windows.indexOf(t.windowId) + 1 });
    if (store.mode !== 'rendered' || !new RegExp(store.product_path).test(u.pathname)) continue;
    try {
      if (t.discarded) throw new Error('discarded');
      const page = await inject(t.id, 'src/readers/store-page.js', () => readStorePage(document)); // eslint-disable-line no-undef
      if (page) pages[t.url] = page;
    } catch {
      warnings.push({ code: 'tabs.page_unreadable', url: t.url });
    }
  }
  if (!tabs.length) return fail('tabs.none');
  return { ok: true, data: { tabs, pages, warnings, stores: STORES.length } };
}

async function readMoxfield(params) {
  const m = MOXFIELD_DECK.exec(String(params.url || ''));
  if (!m) return fail('moxfield.bad_url');
  if (!await chrome.permissions.contains({ origins: MOXFIELD_ORIGINS })) return fail('permission.moxfield_off');
  const id = m[1];
  return withTab(`https://moxfield.com/decks/${id}`, ['https://moxfield.com/*', 'https://www.moxfield.com/*'], async (tab, opened) => {
    if (opened && !await loaded(tab.id, 20_000)) return fail('moxfield.load_timeout');
    let out;
    try {
      out = await inject(tab.id, 'src/readers/moxfield-deck.js', (deckId) => readMoxfieldDeck(deckId), [id]); // eslint-disable-line no-undef
    } catch {
      return fail('moxfield.blocked');
    }
    if (!out?.ok) return fail(out?.code || 'moxfield.changed', out?.status ? { status: out.status } : {});
    return { ok: true, data: { url: `https://moxfield.com/decks/${id}`, deck: out.deck } };
  });
}

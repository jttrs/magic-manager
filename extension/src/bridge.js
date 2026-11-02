// magic-manager companion — the bridge between the app page and the companion.
//
// Registered ONLY for the app address you paired (see options), and it checks
// again here: it does nothing unless this page's origin is exactly that address.
// It relays the app's requests to the companion's worker and the results back
// to this same page (window.postMessage pinned to this page's origin). It reads
// nothing from the page. A classic content script: no modules.

(() => {
  'use strict';
  const CHANNEL = 'magic-manager/companion';
  // One live bridge per page. The worker also injects one into app tabs already open after an
  // update or a pairing; a bridge left over from a reloaded extension is dead (its runtime has no
  // id) and steps aside — and goes silent itself, so the app never gets an answer from it.
  const rt = chrome.runtime;
  const alive = () => { try { return Boolean(rt && rt.id); } catch { return false; } };
  const prev = globalThis.__mmCompanionBridge;
  if (prev && prev.alive()) return;
  globalThis.__mmCompanionBridge = { alive };
  let paired = null;

  const post = (m) => window.postMessage(Object.assign({}, m, { channel: CHANNEL, from: 'companion' }), location.origin);
  const ask = (m) => new Promise((resolve) => {
    try {
      rt.sendMessage(m, (r) => { void rt.lastError; resolve(r || null); });
    } catch {
      resolve(null);
    }
  });

  async function isPaired() {
    if (paired === null) {
      const { appOrigin } = await chrome.storage.local.get('appOrigin');
      paired = appOrigin === location.origin && window.top === window;
    }
    return paired;
  }

  async function hello() {
    if (!alive() || !await isPaired()) return;
    const r = await ask({ type: 'hello' });
    if (r && r.ok) post({ type: 'hello', version: String(r.version), features: r.features });
  }

  window.addEventListener('message', async (ev) => {
    if (ev.source !== window || ev.origin !== location.origin || !alive()) return;
    const d = ev.data;
    if (!d || typeof d !== 'object' || d.channel !== CHANNEL || d.from !== 'app') return;
    if (!await isPaired()) return;
    if (d.type === 'ping') { hello(); return; }
    if (d.type !== 'request' || typeof d.id !== 'string' || d.id.length > 64) return;
    const p = d.params && typeof d.params === 'object' ? d.params : {};
    // Only these, typed and capped: a deck url; an order-history store + order numbers;
    // watched store pages (the worker re-checks each one and caps the count); which Moxfield
    // collection read (your whole collection / one of your binders by id).
    const params = {
      url: typeof p.url === 'string' ? p.url.slice(0, 500) : undefined,
      store: typeof p.store === 'string' ? p.store.slice(0, 20) : undefined,
      what: typeof p.what === 'string' ? p.what.slice(0, 20) : undefined,
      binder: typeof p.binder === 'string' ? p.binder.slice(0, 64) : undefined,
      urls: Array.isArray(p.urls) ? p.urls.slice(0, 51).filter((u) => typeof u === 'string').map((u) => u.slice(0, 2000)) : undefined,
      ids: Array.isArray(p.ids) ? p.ids.slice(0, 100).filter((x) => typeof x === 'string').map((x) => x.slice(0, 64)) : undefined,
    };
    const r = await ask({ type: 'request', id: d.id, kind: String(d.kind), params });
    post(Object.assign({}, r || { ok: false, code: 'companion.timeout' }, { type: 'ack', id: d.id }));
  });

  // Unpaired or re-paired with another address: this page re-checks (and goes silent if it no
  // longer matches). The worker checks the exact origin of every message regardless.
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && 'appOrigin' in changes) paired = null;
  });

  chrome.runtime.onMessage.addListener((m, sender) => {
    if (sender.id !== chrome.runtime.id || sender.tab) return;
    if (m && m.type === 'result' && typeof m.id === 'string') post(m);
  });

  hello();
})();

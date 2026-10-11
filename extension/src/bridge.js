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
  let paired = null;

  const post = (m) => window.postMessage(Object.assign({}, m, { channel: CHANNEL, from: 'companion' }), location.origin);
  const ask = (m) => new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(m, (r) => { void chrome.runtime.lastError; resolve(r || null); });
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
    if (!await isPaired()) return;
    const r = await ask({ type: 'hello' });
    if (r && r.ok) post({ type: 'hello', version: String(r.version), features: r.features });
  }

  window.addEventListener('message', async (ev) => {
    if (ev.source !== window || ev.origin !== location.origin) return;
    const d = ev.data;
    if (!d || typeof d !== 'object' || d.channel !== CHANNEL || d.from !== 'app') return;
    if (!await isPaired()) return;
    if (d.type === 'ping') { hello(); return; }
    if (d.type !== 'request' || typeof d.id !== 'string' || d.id.length > 64) return;
    const p = d.params && typeof d.params === 'object' ? d.params : {};
    // Only these, typed and capped: a deck url; an order-history store + order numbers.
    const params = {
      url: typeof p.url === 'string' ? p.url.slice(0, 500) : undefined,
      store: typeof p.store === 'string' ? p.store.slice(0, 20) : undefined,
      ids: Array.isArray(p.ids) ? p.ids.slice(0, 100).filter((x) => typeof x === 'string').map((x) => x.slice(0, 64)) : undefined,
    };
    const r = await ask({ type: 'request', id: d.id, kind: String(d.kind), params });
    post(Object.assign({}, r || { ok: false, code: 'companion.timeout' }, { type: 'ack', id: d.id }));
  });

  chrome.runtime.onMessage.addListener((m, sender) => {
    if (sender.id !== chrome.runtime.id || sender.tab) return;
    if (m && m.type === 'result' && typeof m.id === 'string') post(m);
  });

  hello();
})();

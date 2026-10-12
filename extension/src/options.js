// The companion's settings: pair with ONE app address and switch features on
// (each asks Chrome for just its sites, at that moment).

import { STORES } from './stores.js';
import { ARCHIDEKT_ORIGINS, CART_STORES, MOXFIELD_ORIGINS, ORDER_ORIGINS, STORE_ORIGINS, MANAPOOL_ORIGINS, parseAppOrigin } from './protocol.js';

const $ = (id) => document.getElementById(id);
const BRIDGE = 'mm-bridge';
const granted = { deals: false, moxfield: false, archidekt: false, orders: false, 'cart-tcgplayer': false, 'cart-cardkingdom': false };
const GROUPS = {
  deals: STORE_ORIGINS, moxfield: MOXFIELD_ORIGINS, archidekt: ARCHIDEKT_ORIGINS, orders: ORDER_ORIGINS,
  'cart-tcgplayer': CART_STORES.tcgplayer.origins, 'cart-cardkingdom': CART_STORES.cardkingdom.origins,
};

/** The pairing line: text pieces, the origin set in its own span (never parsed as HTML). */
function status(parts, cls = 'ok') {
  const el = $('pair-status');
  el.replaceChildren(...[].concat(parts).map((p) => {
    if (typeof p === 'string') return document.createTextNode(p);
    const span = document.createElement('span');
    span.className = 'origin';
    span.textContent = p.origin;
    return span;
  }));
  el.className = cls;
}

/** "just now" / "4 min ago" / "3 h ago" / a date. */
function ago(ms, now = Date.now()) {
  const s = Math.max(0, Math.round((now - ms) / 1000));
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `on ${new Date(ms).toLocaleDateString()}`;
}

/** Paired? And has that exact address said hello since? (A wrong address never does.) */
async function showPairing() {
  const { appOrigin, lastHello } = await chrome.storage.local.get(['appOrigin', 'lastHello']);
  $('unpair').disabled = !appOrigin;
  if (!appOrigin) return status('Not paired: no app can reach the companion.', 'muted');
  if (lastHello?.origin === appOrigin) return status(['Paired with ', { origin: appOrigin }, `. The app last checked in ${ago(lastHello.at)}.`]);
  return status(['Paired with ', { origin: appOrigin }, ', but the app hasn’t checked in yet. Open the app at exactly this address and reload its tab. If the app runs at a different address, pair with that one instead.'], 'warn');
}

async function refresh() {
  $('version').textContent = chrome.runtime.getManifest().version;
  $('store-count').textContent = String(STORES.length);
  await showPairing();
  const has = (origins) => chrome.permissions.contains({ origins });
  const cart = await has(MANAPOOL_ORIGINS);
  $('cart-state').dataset.on = String(cart);
  $('cart-state').querySelector('.state').textContent = cart ? 'Always on' : 'Blocked in Chrome’s site access';
  for (const [key, origins] of Object.entries(GROUPS)) {
    granted[key] = await has(origins);
    $(key).setAttribute('aria-checked', String(granted[key]));
    $(key).querySelector('.state').textContent = granted[key] ? 'On' : 'Off';
  }
}

let pairing = false;

async function pair() {
  if (pairing) return;
  pairing = true;
  try {
    await pairWith(parseAppOrigin($('origin').value));
  } finally {
    pairing = false;
  }
}

async function pairWith(parsed) {
  if (parsed.error) return status(parsed.error, 'error');
  // First await in the click handler, so Chrome still sees the user's click.
  const granted = await chrome.permissions.request({ origins: [parsed.pattern] });
  const { appOrigin: before } = await chrome.storage.local.get('appOrigin');
  if (!granted) return status('Chrome permission was not given, so the companion is not paired.', 'error');
  await chrome.scripting.unregisterContentScripts({ ids: [BRIDGE] }).catch(() => {});
  await chrome.scripting.registerContentScripts([{
    id: BRIDGE, matches: [parsed.pattern], js: ['src/bridge.js'], runAt: 'document_start', allFrames: false, persistAcrossSessions: true,
  }]);
  await chrome.storage.local.remove('lastHello');
  await chrome.storage.local.set({ appOrigin: parsed.origin });
  if (before && before !== parsed.origin) {
    const old = parseAppOrigin(before);
    if (old.pattern && old.pattern !== parsed.pattern) await chrome.permissions.remove({ origins: [old.pattern] }).catch(() => {});
  }
  $('origin').value = parsed.origin;
  await refresh();
}

async function unpair() {
  const { appOrigin } = await chrome.storage.local.get('appOrigin');
  await chrome.scripting.unregisterContentScripts({ ids: [BRIDGE] }).catch(() => {});
  await chrome.storage.local.remove(['appOrigin', 'lastHello']);
  const p = appOrigin && parseAppOrigin(appOrigin);
  if (p?.pattern) await chrome.permissions.remove({ origins: [p.pattern] }).catch(() => {});
  await refresh();
}

/** Switches with a permission change in flight: a second click waits for the first to land. */
const busy = new Set();

async function toggle(key, origins) {
  if (busy.has(key)) return;
  busy.add(key);
  // request() must be the first await so Chrome still sees the click.
  try {
    await flip(key, origins);
    await refresh();   // still busy until `granted` is fresh
  } finally {
    busy.delete(key);
  }
}

async function flip(key, origins) {
  if (granted[key]) {
    // Keep a site another switched-on feature still needs (Card Kingdom is in three).
    const shared = new Set(Object.entries(GROUPS).filter(([k]) => k !== key && granted[k]).flatMap(([, o]) => o));
    const drop = origins.filter((o) => !shared.has(o));
    if (drop.length) await chrome.permissions.remove({ origins: drop });
  } else await chrome.permissions.request({ origins });
}

$('pair').addEventListener('click', pair);
$('unpair').addEventListener('click', unpair);
for (const [key, origins] of Object.entries(GROUPS)) $(key).addEventListener('click', () => toggle(key, origins));
// The app checking in (or a pairing change) updates the line while this page is open.
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && ('lastHello' in changes || 'appOrigin' in changes)) showPairing();
});
chrome.storage.local.get('appOrigin').then(({ appOrigin }) => { $('origin').value = appOrigin || ''; });
refresh();

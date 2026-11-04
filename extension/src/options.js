// The companion's settings: pair with ONE app address, and ONE "Allow access" switch that
// asks Chrome for every site the readers use at once (owner, 2026-10-11).

import { STORES } from './stores.js';
import { ALL_ACCESS_ORIGINS, MANAPOOL_ORIGINS, parseAppOrigin } from './protocol.js';

const $ = (id) => document.getElementById(id);
let access = false;
const CATALOG = fetch(chrome.runtime.getURL('errors.json')).then((r) => r.json()).then((j) => j.codes).catch(() => ({}));

/** A pairing failure: its catalogued message and fix (extension/errors.json), as an error line. */
async function refuse(code) {
  const c = (await CATALOG)[code] || {};
  status([c.message || code, c.fix ? ` ${c.fix}` : ''].join(''), 'error');
  $('pair-status').dataset.code = code;
}

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
  delete el.dataset.code;
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
  access = await has(ALL_ACCESS_ORIGINS);
  // Some sites allowed but not all (an older version's per-feature switches, or a store added
  // since): Off, and switching on asks for the rest.
  const some = !access && (await Promise.all(ALL_ACCESS_ORIGINS.map((o) => has([o])))).some(Boolean);
  $('access').setAttribute('aria-checked', String(access));
  $('access').querySelector('.state').textContent = access ? 'On' : 'Off';
  $('access-partial').hidden = !some;
}

/** Ask the worker to (un)register the bridge for the paired address and reach open app tabs. */
const syncBridge = () => chrome.runtime.sendMessage({ type: 'bridge' }).catch(() => null);

let pairing = false;
// While true, the pairing line keeps a pairing error on screen, so storage changes don't redraw over it (cleared by the next Pair/Unpair).
let holdError = false;

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
  if (parsed.code) return refuse(parsed.code);
  // First await in the click handler, so Chrome still sees the user's click. Exactly this one
  // origin's pattern is asked for (the manifest's any-https entry is only the pool it comes from).
  const granted = await chrome.permissions.request({ origins: [parsed.pattern] }).catch(() => false);
  holdError = false;   // a new attempt clears any held error
  const { appOrigin: before, lastHello: prevHello } = await chrome.storage.local.get(['appOrigin', 'lastHello']);
  if (!granted) return refuse('pair.permission_denied');
  const old = before ? parseAppOrigin(before) : null;
  if (before !== parsed.origin) {
    await chrome.storage.local.remove('lastHello');
    await chrome.storage.local.set({ appOrigin: parsed.origin });
  }
  const bridged = await syncBridge();
  if (!bridged?.ok) {
    // Restore the pairing from before the click: a prior pairing stays paired and working, and
    // with none the page is unpaired. The error stays on screen until the next Pair/Unpair.
    holdError = true;
    if (before) await chrome.storage.local.set({ appOrigin: before, ...(prevHello ? { lastHello: prevHello } : {}) });
    else await chrome.storage.local.remove(['appOrigin', 'lastHello']);
    if (parsed.pattern !== old?.pattern) await chrome.permissions.remove({ origins: [parsed.pattern] }).catch(() => {});
    await syncBridge();   // the worker re-registers the prior bridge, or none
    $('unpair').disabled = !before;   // held error: the button must still match the restored pairing
    return refuse('pair.bridge_failed');
  }
  if (old?.pattern && old.pattern !== parsed.pattern) await chrome.permissions.remove({ origins: [old.pattern] }).catch(() => {});
  $('origin').value = parsed.origin;
  await refresh();
}

async function unpair() {
  if (pairing) return;   // a pair attempt in flight finishes (and restores) first
  holdError = false;
  const { appOrigin } = await chrome.storage.local.get('appOrigin');
  await chrome.storage.local.remove(['appOrigin', 'lastHello']);
  await syncBridge();   // no paired address: the worker unregisters the bridge
  const p = appOrigin && parseAppOrigin(appOrigin);
  if (p?.pattern) await chrome.permissions.remove({ origins: [p.pattern] }).catch(() => {});
  await refresh();
}

/** A permission change in flight: a second click waits for the first to land. */
let busy = false;

async function toggleAccess() {
  if (busy) return;
  busy = true;
  try {
    // request() must be the first await so Chrome still sees the click.
    if (access) await chrome.permissions.remove({ origins: ALL_ACCESS_ORIGINS }).catch(() => false);
    else await chrome.permissions.request({ origins: ALL_ACCESS_ORIGINS }).catch(() => false);
    await refresh();   // still busy until `access` is fresh
  } finally {
    busy = false;
  }
}

$('pair').addEventListener('click', pair);
$('unpair').addEventListener('click', unpair);
$('access').addEventListener('click', toggleAccess);
// The app checking in (or a pairing change) updates the line while this page is open.
chrome.storage.onChanged.addListener((changes, area) => {
  if (holdError) return;
  if (area === 'local' && ('lastHello' in changes || 'appOrigin' in changes)) showPairing();
});
chrome.storage.local.get('appOrigin').then(({ appOrigin }) => { $('origin').value = appOrigin || ''; });
refresh();

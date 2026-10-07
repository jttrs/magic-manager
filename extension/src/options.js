// The companion's settings: pair with ONE app address and switch features on
// (each asks Chrome for just its sites, at that moment).

import { STORES } from './stores.js';
import { MOXFIELD_ORIGINS, STORE_ORIGINS, MANAPOOL_ORIGINS, parseAppOrigin } from './protocol.js';

const $ = (id) => document.getElementById(id);
const BRIDGE = 'mm-bridge';
const granted = { deals: false, moxfield: false };

async function status(text, isError = false) {
  $('pair-status').textContent = text;
  $('pair-status').className = isError ? 'error' : 'ok';
}

async function refresh() {
  $('version').textContent = chrome.runtime.getManifest().version;
  $('store-count').textContent = String(STORES.length);
  const { appOrigin } = await chrome.storage.local.get('appOrigin');
  $('origin').value = appOrigin || 'http://localhost:8765';
  $('unpair').disabled = !appOrigin;
  if (appOrigin) await status(`Paired with ${appOrigin}. Reload the app tab once so it notices.`);
  const has = (origins) => chrome.permissions.contains({ origins });
  $('cart-state').textContent = await has(MANAPOOL_ORIGINS) ? 'On' : 'Blocked in Chrome site access';
  granted.deals = await has(STORE_ORIGINS);
  granted.moxfield = await has(MOXFIELD_ORIGINS);
  $('deals').textContent = granted.deals ? 'Switch off' : 'Switch on';
  $('moxfield').textContent = granted.moxfield ? 'Switch off' : 'Switch on';
}

async function pair() {
  const parsed = parseAppOrigin($('origin').value);
  if (parsed.error) return status(parsed.error, true);
  // First await in the click handler, so Chrome still sees the user's click.
  const granted = await chrome.permissions.request({ origins: [parsed.pattern] });
  const { appOrigin: before } = await chrome.storage.local.get('appOrigin');
  if (!granted) return status('Chrome permission was not given, so the companion is not paired.', true);
  await chrome.scripting.unregisterContentScripts({ ids: [BRIDGE] }).catch(() => {});
  await chrome.scripting.registerContentScripts([{
    id: BRIDGE, matches: [parsed.pattern], js: ['src/bridge.js'], runAt: 'document_start', allFrames: false, persistAcrossSessions: true,
  }]);
  await chrome.storage.local.set({ appOrigin: parsed.origin });
  if (before && before !== parsed.origin) {
    const old = parseAppOrigin(before);
    if (old.pattern && old.pattern !== parsed.pattern) await chrome.permissions.remove({ origins: [old.pattern] }).catch(() => {});
  }
  await refresh();
}

async function unpair() {
  const { appOrigin } = await chrome.storage.local.get('appOrigin');
  await chrome.scripting.unregisterContentScripts({ ids: [BRIDGE] }).catch(() => {});
  await chrome.storage.local.remove('appOrigin');
  const p = appOrigin && parseAppOrigin(appOrigin);
  if (p?.pattern) await chrome.permissions.remove({ origins: [p.pattern] }).catch(() => {});
  await status('Unpaired. No app can reach the companion now.');
  await refresh();
}

async function toggle(key, origins) {
  // request() must be the first await so Chrome still sees the click.
  if (granted[key]) await chrome.permissions.remove({ origins });
  else await chrome.permissions.request({ origins });
  await refresh();
}

$('pair').addEventListener('click', pair);
$('unpair').addEventListener('click', unpair);
$('deals').addEventListener('click', () => toggle('deals', STORE_ORIGINS));
$('moxfield').addEventListener('click', () => toggle('moxfield', MOXFIELD_ORIGINS));
refresh();

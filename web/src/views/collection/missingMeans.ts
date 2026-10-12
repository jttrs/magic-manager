// "Missing means" — a Collection preference (Settings → Collection), not a
// filter: it changes what a gap IS, so it persists in this browser rather than
// riding each URL. `printing` = every exact printing you don't have (the
// collector's view, default); `card` = only cards you own in no printing at all
// (the deck builder's view).
import { useSyncExternalStore } from 'react';

export type MissingMeans = 'printing' | 'card';
const KEY = 'mm.collection.missingMeans';
const listeners = new Set<() => void>();
/** Fallback when storage is blocked: the choice lasts until reload. */
let memory: MissingMeans = 'printing';

function read(): MissingMeans {
  try {
    return localStorage.getItem(KEY) === 'card' ? 'card' : 'printing';
  } catch {
    return memory;
  }
}

function subscribe(l: () => void) {
  listeners.add(l);
  const onStorage = (e: StorageEvent) => { if (e.key === KEY) l(); };
  window.addEventListener('storage', onStorage);
  return () => { listeners.delete(l); window.removeEventListener('storage', onStorage); };
}

export function setMissingMeans(v: MissingMeans): void {
  memory = v;
  try {
    if (v === 'card') localStorage.setItem(KEY, v);
    else localStorage.removeItem(KEY);
  } catch { /* storage blocked: `memory` holds it */ }
  for (const l of listeners) l();
}

export function useMissingMeans(): MissingMeans {
  return useSyncExternalStore(subscribe, read, () => 'printing');
}

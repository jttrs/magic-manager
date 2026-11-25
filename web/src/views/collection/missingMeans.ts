// "Missing means" — a Collection preference (Settings → Collection), not a
// filter: it changes what a gap IS, so it persists in this browser rather than
// riding each URL. `printing` = every exact printing you don't have (the
// collector's view, default); `card` = only cards you own in no printing at all
// (the deck builder's view).
import { createLocalPref } from '../../app/localPref';

export type MissingMeans = 'printing' | 'card';

// Only the non-default choice is stored, so choosing "printing" clears the key.
const pref = createLocalPref<MissingMeans>({
  key: 'mm.collection.missingMeans',
  parse: (raw) => (raw === 'card' ? 'card' : 'printing'),
  serialize: (v) => (v === 'card' ? v : null),
});

export const readMissingMeans = pref.get;
export const setMissingMeans = pref.set;
export const useMissingMeans = pref.use;

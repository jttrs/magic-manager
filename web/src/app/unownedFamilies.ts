// "Include families you don't own" in the Collection's Set families picker: it changes what the
// picker OFFERS, not what the sheet shows, so it persists in this browser rather than in the URL.
import { createLocalPref } from './localPref';

const pref = createLocalPref<boolean>({
  key: 'mm.collection.unownedFamilies',
  parse: (raw) => raw === '1',
  serialize: (v) => (v ? '1' : null),
});

export const setUnownedFamilies = pref.set;
export const useUnownedFamilies = pref.use;

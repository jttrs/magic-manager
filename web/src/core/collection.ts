// Collection view derivations: which printings show under the active filters,
// what counts as "missing", and which finish a buy-list line should name.
import type { CollectionCardOut } from './api';

export type MissingBasis = 'either' | 'nonfoil' | 'foil';
type Layer = 'show' | 'hide';
type ChaseLayer = 'show' | 'hide' | 'only';

export type CollectionFilters = {
  show: readonly ('owned' | 'missing')[];
  basis: MissingBasis;
  bulk: Layer;
  treatments: Layer;
  chase: ChaseLayer;
  q: string;
};

const ownedOf = (c: CollectionCardOut, f: 'nonfoil' | 'foil') => c.owned[f] ?? 0;
const ownedTotal = (c: CollectionCardOut) => Object.values(c.owned).reduce((s, n) => s + n, 0);

/** A printing is missing when you own none of it (either), or none of the
 *  requested finish — only counted when that finish actually exists. */
export function isMissing(c: CollectionCardOut, basis: MissingBasis): boolean {
  if (basis === 'either') return ownedTotal(c) === 0;
  return c.finishes.includes(basis) && ownedOf(c, basis) === 0;
}

export function filterCollection(cards: readonly CollectionCardOut[], f: CollectionFilters): CollectionCardOut[] {
  const q = f.q.trim().toLowerCase();
  const wantOwned = f.show.includes('owned');
  const wantMissing = f.show.includes('missing');
  return cards.filter((c) => {
    if (q && !c.name.toLowerCase().includes(q)) return false;
    if (f.bulk === 'hide' && c.is_bulk) return false;
    if (f.treatments === 'hide' && !c.standard_frame) return false;
    if (f.chase === 'hide' && c.is_chase) return false;
    if (f.chase === 'only' && !c.is_chase) return false;
    return (wantOwned && ownedTotal(c) > 0) || (wantMissing && isMissing(c, f.basis));
  });
}

/** Finish a buy line should name for a missing printing under the basis. */
export function buyFinish(c: CollectionCardOut, basis: MissingBasis): 'nonfoil' | 'foil' {
  if (basis !== 'either') return basis;
  return c.finishes.includes('nonfoil') ? 'nonfoil' : 'foil';
}

export type CollectionStats = { printings: number; owned: number; copies: number; missing: number; missingUsd: number };

export function collectionStats(cards: readonly CollectionCardOut[], basis: MissingBasis): CollectionStats {
  let owned = 0, copies = 0, missing = 0, missingUsd = 0;
  for (const c of cards) {
    const n = ownedTotal(c);
    if (n > 0) { owned++; copies += n; }
    if (isMissing(c, basis)) {
      missing++;
      missingUsd += (buyFinish(c, basis) === 'foil' ? c.price_usd_foil : c.price_usd) ?? 0;
    }
  }
  return { printings: cards.length, owned, copies, missing, missingUsd };
}

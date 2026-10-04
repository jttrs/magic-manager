// Collection view derivations: which printings show under the active filters,
// what counts as "missing", and which finish a buy-list line should name.
import type { CollectionCardOut } from './api';

export type MissingBasis = 'either' | 'nonfoil' | 'foil';

export type CollectionFilters = {
  show: readonly ('owned' | 'missing')[];
  basis: MissingBasis;
  /** Card-type traits the user unchecked (see TRAITS); a card with ANY excluded trait is hidden. */
  exclude: readonly string[];
  q: string;
};

type TraitGroup = 'Rarity' | 'Treatment' | 'Chase';
type TraitDef = { key: string; label: string; group: TraitGroup };

/** Every filterable card-type trait, in display order. Keys are URL-stable. */
export const TRAITS: readonly TraitDef[] = [
  { key: 'rarity:mythic', label: 'Mythic', group: 'Rarity' },
  { key: 'rarity:rare', label: 'Rare', group: 'Rarity' },
  { key: 'rarity:uncommon', label: 'Uncommon', group: 'Rarity' },
  { key: 'rarity:common', label: 'Common', group: 'Rarity' },
  { key: 'rarity:special', label: 'Special / bonus', group: 'Rarity' },
  { key: 'treat:std', label: 'Standard frame', group: 'Treatment' },
  { key: 'treat:b', label: 'Borderless', group: 'Treatment' },
  { key: 'treat:shw', label: 'Showcase', group: 'Treatment' },
  { key: 'treat:ext', label: 'Extended art', group: 'Treatment' },
  { key: 'treat:fa', label: 'Full art', group: 'Treatment' },
  { key: 'treat:sm', label: 'Reskin', group: 'Treatment' },
  { key: 'treat:ff', label: 'Fancy foil / etched', group: 'Treatment' },
  { key: 'treat:other', label: 'Other frame (gold/silver border…)', group: 'Treatment' },
  { key: 'chase:yes', label: 'Chase', group: 'Chase' },
  { key: 'chase:no', label: 'Not chase', group: 'Chase' },
];

/** The trait keys a printing carries (one rarity, ≥1 treatment, one chase key). */
export function traitsOf(c: CollectionCardOut): string[] {
  const rarity = ['mythic', 'rare', 'uncommon', 'common'].includes(c.rarity) ? c.rarity : 'special';
  const codes = c.treatment ? c.treatment.split('|') : [];
  const treat = c.standard_frame && !codes.length ? ['treat:std'] : codes.length ? codes.map((t) => `treat:${t}`) : ['treat:other'];
  return [`rarity:${rarity}`, ...treat, c.is_chase ? 'chase:yes' : 'chase:no'];
}

/** Count of cards carrying each trait (for picker counts). */
export function traitCounts(cards: readonly CollectionCardOut[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const c of cards) for (const t of new Set(traitsOf(c))) m.set(t, (m.get(t) ?? 0) + 1);
  return m;
}

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
  const excluded = new Set(f.exclude);
  return cards.filter((c) => {
    if (q && !c.name.toLowerCase().includes(q)) return false;
    if (excluded.size && traitsOf(c).some((t) => excluded.has(t))) return false;
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

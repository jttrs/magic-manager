// Collection view derivations: which printings show under the active filters,
// what counts as "missing", and which finish a buy-list line should name.
import type { CollectionCardOut } from './api';
import { facetCounts, passes, type Facets } from './facets';

export type CollectionFilters = {
  show: readonly ('owned' | 'missing')[];
  /** Card-type traits the user unchecked (see TRAITS). Finish traits OR together
   *  (a printing shows while any of its finishes is checked, and owned/missing
   *  are judged on the checked finishes); any other excluded trait hides it. */
  exclude: readonly string[];
  q: string;
  /** Missing printings only of cards you own in no printing anywhere. */
  gaps?: boolean;
  /** Scryfall Tagger function roots to keep (OR); empty = no function filter. */
  fn?: readonly string[];
  /** Only printings of cards you earmarked. */
  em?: boolean;
};

/** `fn` key for printings no function root covers. */
export const NO_FUNCTION = '_none';

const fnKeys = (c: CollectionCardOut): string[] => (c.functions?.length ? c.functions : [NO_FUNCTION]);

export type TraitGroup = 'Rarity' | 'Finish' | 'Treatment' | 'Chase';
type TraitDef = { key: string; label: string; group: TraitGroup };

/** Every filterable card-type trait, in display order (Rarity · Finish · Treatment · Chase). Keys are URL-stable. */
export const TRAITS: readonly TraitDef[] = [
  { key: 'rarity:mythic', label: 'Mythic', group: 'Rarity' },
  { key: 'rarity:rare', label: 'Rare', group: 'Rarity' },
  { key: 'rarity:uncommon', label: 'Uncommon', group: 'Rarity' },
  { key: 'rarity:common', label: 'Common', group: 'Rarity' },
  { key: 'rarity:special', label: 'Special / bonus', group: 'Rarity' },
  { key: 'finish:nonfoil', label: 'Nonfoil', group: 'Finish' },
  { key: 'finish:foil', label: 'Foil', group: 'Finish' },
  { key: 'finish:fancy', label: 'Fancy foil (surge, etched…)', group: 'Finish' },
  { key: 'treat:std', label: 'Standard frame', group: 'Treatment' },
  { key: 'treat:b', label: 'Borderless', group: 'Treatment' },
  { key: 'treat:shw', label: 'Showcase', group: 'Treatment' },
  { key: 'treat:ext', label: 'Extended art', group: 'Treatment' },
  { key: 'treat:fa', label: 'Full art', group: 'Treatment' },
  { key: 'treat:sm', label: 'Reskin', group: 'Treatment' },
  { key: 'treat:other', label: 'Other frame (gold/silver border…)', group: 'Treatment' },
  { key: 'chase:yes', label: 'Chase', group: 'Chase' },
  { key: 'chase:no', label: 'Not chase', group: 'Chase' },
];

type InvFinish = 'nonfoil' | 'foil';
type FinishTrait = { trait: string; inv: InvFinish };

const isFancy = (c: CollectionCardOut) => (c.treatment ? c.treatment.split('|') : []).includes('ff');

/** A printing's finishes as picker traits. Its foil is "fancy" (surge, etched,
 *  galaxy…) when the treatment carries `ff`; inventory files both as foil. */
function finishTraits(c: CollectionCardOut): FinishTrait[] {
  return c.finishes.map((f) =>
    f === 'nonfoil' ? { trait: 'finish:nonfoil', inv: 'nonfoil' } : { trait: isFancy(c) ? 'finish:fancy' : 'finish:foil', inv: 'foil' },
  );
}

/** Inventory finishes of `c` whose finish trait is still checked. */
function allowedFinishes(c: CollectionCardOut, excluded: ReadonlySet<string>): InvFinish[] {
  return finishTraits(c).filter((f) => !excluded.has(f.trait)).map((f) => f.inv);
}

/** Non-finish trait keys a printing carries (one rarity, ≥1 treatment, one chase key). */
export function traitsOf(c: CollectionCardOut): string[] {
  const rarity = ['mythic', 'rare', 'uncommon', 'common'].includes(c.rarity) ? c.rarity : 'special';
  const all = c.treatment ? c.treatment.split('|') : [];
  const codes = all.filter((t) => t !== 'ff');
  const treat = codes.length ? codes.map((t) => `treat:${t}`) : c.standard_frame || all.length ? ['treat:std'] : ['treat:other'];
  return [`rarity:${rarity}`, ...treat, c.is_chase ? 'chase:yes' : 'chase:no'];
}

const ownedIn = (c: CollectionCardOut, fins: readonly InvFinish[]) =>
  [...new Set(fins)].reduce((s, f) => s + (c.owned[f] ?? 0), 0);

/** A printing is missing when you own none of it in any checked finish. */
export function isMissing(c: CollectionCardOut, exclude: readonly string[]): boolean {
  const fins = allowedFinishes(c, new Set(exclude));
  return fins.length > 0 && ownedIn(c, fins) === 0;
}

/** Copies held in the checked finishes. */
function ownedCopies(c: CollectionCardOut, exclude: readonly string[]): number {
  return ownedIn(c, allowedFinishes(c, new Set(exclude)));
}

type CollectionFacet = 'em' | 'q' | 'fn' | 'rarity' | 'treatment' | 'chase' | 'finish' | 'show';

const FACET_GROUP: Record<'rarity' | 'treatment' | 'chase', TraitGroup> = { rarity: 'Rarity', treatment: 'Treatment', chase: 'Chase' };

/** One predicate per collection filter (see `core/facets`). Each trait group hides a
 *  printing that carries one of ITS excluded traits; together they equal "any excluded trait". */
/** Where a printing lands for the Show filter, judged on its checked finishes: owned,
 *  missing, or neither (no checked finish; or, counting gaps, owned in another printing). */
function showState(c: CollectionCardOut, excluded: ReadonlySet<string>, gaps?: boolean): 'owned' | 'missing' | null {
  const fins = allowedFinishes(c, excluded);
  if (!fins.length) return null;
  if (ownedIn(c, fins) > 0) return 'owned';
  return gaps && (c.card_owned ?? 0) > 0 ? null : 'missing';
}

function collectionFacets(f: CollectionFilters): Facets<CollectionCardOut, CollectionFacet> {
  const q = f.q.trim().toLowerCase();
  const wantOwned = f.show.includes('owned');
  const wantMissing = f.show.includes('missing');
  const excluded = new Set(f.exclude);
  const fn = new Set(f.fn ?? []);
  const groupKeep = (g: TraitGroup) => {
    const keys = new Set(traitsIn(g).map((t) => t.key));
    const ex = new Set([...excluded].filter((k) => keys.has(k)));
    return (c: CollectionCardOut) => !ex.size || !traitsOf(c).some((t) => ex.has(t));
  };
  const rarity = groupKeep(FACET_GROUP.rarity), treatment = groupKeep(FACET_GROUP.treatment), chase = groupKeep(FACET_GROUP.chase);
  return {
    em: (c) => !f.em || !!c.earmarked,
    q: (c) => !q || c.name.toLowerCase().includes(q),
    fn: (c) => !fn.size || fnKeys(c).some((k) => fn.has(k)),
    rarity, treatment, chase,
    finish: (c) => allowedFinishes(c, excluded).length > 0,
    show: (c) => {
      const st = showState(c, excluded, f.gaps);
      return (wantOwned && st === 'owned') || (wantMissing && st === 'missing');
    },
  };
}

export function filterCollection(cards: readonly CollectionCardOut[], f: CollectionFilters): CollectionCardOut[] {
  const facets = collectionFacets(f);
  return cards.filter((c) => passes(c, facets));
}

export type CollectionCounts = {
  show: { owned: number; missing: number };
  /** Every trait key (rarity, finish, treatment, chase), each group counted under the other filters. */
  traits: Map<string, number>;
  fn: Map<string, number>;
};

/** Option counts for every collection control, each under every OTHER filter. */
export function collectionCounts(cards: readonly CollectionCardOut[], f: CollectionFilters): CollectionCounts {
  const facets = collectionFacets(f);
  const excluded = new Set(f.exclude);
  const show = { owned: 0, missing: 0 };
  for (const c of cards) {
    if (!passes(c, facets, 'show')) continue;
    const st = showState(c, excluded, f.gaps);
    if (st) show[st]++;
  }
  // Each trait option is counted with only ITS OWN exclusion lifted: the printings that
  // would show if you ticked it (for a checked option, exactly the ones shown). Lifting
  // a whole group would miscount multi-valued groups (Finish, Treatment) — and Show
  // judges owned/missing on the checked finishes, so other finish exclusions must stay.
  const traits = new Map<string, number>();
  for (const t of TRAITS) {
    const facetsT = collectionFacets({ ...f, exclude: f.exclude.filter((k) => k !== t.key) });
    const carries = t.group === 'Finish'
      ? (c: CollectionCardOut) => finishTraits(c).some((x) => x.trait === t.key)
      : (c: CollectionCardOut) => traitsOf(c).includes(t.key);
    let n = 0;
    for (const c of cards) if (carries(c) && passes(c, facetsT)) n++;
    if (n) traits.set(t.key, n);
  }
  return {
    show,
    traits,
    fn: facetCounts(cards, facets, 'fn', fnKeys),
  };
}

/** Σ market price of a buy list (each printing at the finish its line names). */
export function buyTotal(cards: readonly CollectionCardOut[], exclude: readonly string[]): number {
  return cards.reduce((s, c) => s + ((buyFinish(c, exclude) === 'foil' ? c.price_usd_foil : c.price_usd) ?? 0), 0);
}

/** Finish a buy line names for a missing printing: nonfoil when it's checked, else foil. */
export function buyFinish(c: CollectionCardOut, exclude: readonly string[]): InvFinish {
  const fins = allowedFinishes(c, new Set(exclude));
  return fins.includes('nonfoil') || !fins.length && c.finishes.includes('nonfoil') ? 'nonfoil' : 'foil';
}

export type CollectionStats = {
  printings: number; owned: number; copies: number; missing: number; missingUsd: number;
  /** Missing printings with no price (counted as $0 in missingUsd, so it's a lower bound). */
  missingUnpriced: number;
  /** Distinct missing cards (by oracle) and Σ each one's cheapest missing printing shown. */
  missingCards: number; missingCardsUsd: number;
  /** Missing cards with no priced printing (counted as $0 in missingCardsUsd). */
  missingCardsUnpriced: number;
};

export function collectionStats(cards: readonly CollectionCardOut[], exclude: readonly string[]): CollectionStats {
  let owned = 0, copies = 0, missing = 0, missingUsd = 0, missingUnpriced = 0;
  // Per card: its cheapest PRICED missing printing (null while all are unpriced).
  const cheapest = new Map<string, number | null>();
  for (const c of cards) {
    const n = ownedCopies(c, exclude);
    if (n > 0) { owned++; copies += n; }
    if (isMissing(c, exclude)) {
      missing++;
      const p = (buyFinish(c, exclude) === 'foil' ? c.price_usd_foil : c.price_usd) ?? null;
      missingUsd += p ?? 0;
      if (p == null) missingUnpriced++;
      const k = c.oracle_id ?? c.scryfall_id;
      const prev = cheapest.get(k) ?? null;
      cheapest.set(k, p == null ? prev : Math.min(prev ?? Infinity, p));
    }
  }
  const missingCardsUsd = [...cheapest.values()].reduce<number>((s, p) => s + (p ?? 0), 0);
  const missingCardsUnpriced = [...cheapest.values()].filter((p) => p == null).length;
  return { printings: cards.length, owned, copies, missing, missingUsd, missingUnpriced, missingCards: cheapest.size, missingCardsUsd, missingCardsUnpriced };
}

/** Trait keys of one group. */
export const traitsIn = (group: TraitGroup) => TRAITS.filter((t) => t.group === group);

/** Replace a group's exclusions so exactly `included` of its keys stay checked. */
export function setGroupIncluded(exclude: readonly string[], group: TraitGroup, included: readonly string[]): string[] {
  const keys = traitsIn(group).map((t) => t.key);
  return [...exclude.filter((k) => !keys.includes(k)), ...keys.filter((k) => !included.includes(k))];
}

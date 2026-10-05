// Collection view derivations: which printings show under the active filters,
// what counts as "missing", and which finish a buy-list line should name.
import type { CollectionCardOut, SourceOut } from './api';

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
  /** Acquisition sources to keep (OR): `kind:<deck|pool|singles|unknown>` or a
   *  SourceOut key. Only owned printings have sources, so any value hides missing. */
  src?: readonly string[];
};

/** Kind of each source key, from the payload's source catalog. */
export const sourceKinds = (sources: readonly SourceOut[] = []): ReadonlyMap<string, string> =>
  new Map(sources.map((s) => [s.key, s.kind]));

/** Does a printing match the active source selection (`kind:*` or exact key)? */
function sourceMatch(c: CollectionCardOut, src: ReadonlySet<string>, kinds: ReadonlyMap<string, string>): boolean {
  return (c.sources ?? []).some((k) => src.has(k) || src.has(`kind:${kinds.get(k)}`));
}

/** `fn` key for printings no function root covers. */
export const NO_FUNCTION = '_none';

const fnKeys = (c: CollectionCardOut): string[] => (c.functions?.length ? c.functions : [NO_FUNCTION]);

/** Cards per function root (incl. NO_FUNCTION); a multi-role card counts in each. */
export function functionCounts(cards: readonly CollectionCardOut[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const c of cards) for (const k of fnKeys(c)) m.set(k, (m.get(k) ?? 0) + 1);
  return m;
}

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

/** Count of cards carrying each trait (for picker counts). */
export function traitCounts(cards: readonly CollectionCardOut[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const c of cards) {
    for (const t of new Set([...finishTraits(c).map((f) => f.trait), ...traitsOf(c)])) m.set(t, (m.get(t) ?? 0) + 1);
  }
  return m;
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

export function filterCollection(cards: readonly CollectionCardOut[], f: CollectionFilters, kinds: ReadonlyMap<string, string> = new Map()): CollectionCardOut[] {
  const q = f.q.trim().toLowerCase();
  const wantOwned = f.show.includes('owned');
  const wantMissing = f.show.includes('missing');
  const excluded = new Set(f.exclude);
  const fn = new Set(f.fn ?? []);
  const src = new Set(f.src ?? []);
  return cards.filter((c) => {
    if (src.size && !sourceMatch(c, src, kinds)) return false;
    if (q && !c.name.toLowerCase().includes(q)) return false;
    if (fn.size && !fnKeys(c).some((k) => fn.has(k))) return false;
    if (excluded.size && traitsOf(c).some((t) => excluded.has(t))) return false;
    const fins = allowedFinishes(c, excluded);
    if (!fins.length) return false;
    const n = ownedIn(c, fins);
    return (wantOwned && n > 0) || (wantMissing && n === 0 && !(f.gaps && (c.card_owned ?? 0) > 0));
  });
}

/** Finish a buy line names for a missing printing: nonfoil when it's checked, else foil. */
export function buyFinish(c: CollectionCardOut, exclude: readonly string[]): InvFinish {
  const fins = allowedFinishes(c, new Set(exclude));
  return fins.includes('nonfoil') || !fins.length && c.finishes.includes('nonfoil') ? 'nonfoil' : 'foil';
}

export type CollectionStats = {
  printings: number; owned: number; copies: number; missing: number; missingUsd: number;
  /** Distinct missing cards (by oracle) and Σ each one's cheapest missing printing shown. */
  missingCards: number; missingCardsUsd: number;
};

export function collectionStats(cards: readonly CollectionCardOut[], exclude: readonly string[]): CollectionStats {
  let owned = 0, copies = 0, missing = 0, missingUsd = 0;
  const cheapest = new Map<string, number>();
  for (const c of cards) {
    const n = ownedCopies(c, exclude);
    if (n > 0) { owned++; copies += n; }
    if (isMissing(c, exclude)) {
      missing++;
      const p = (buyFinish(c, exclude) === 'foil' ? c.price_usd_foil : c.price_usd) ?? 0;
      missingUsd += p;
      const k = c.oracle_id ?? c.scryfall_id;
      cheapest.set(k, Math.min(cheapest.get(k) ?? Infinity, p));
    }
  }
  const missingCardsUsd = [...cheapest.values()].reduce((s, p) => s + p, 0);
  return { printings: cards.length, owned, copies, missing, missingUsd, missingCards: cheapest.size, missingCardsUsd };
}

/** Trait keys of one group. */
export const traitsIn = (group: TraitGroup) => TRAITS.filter((t) => t.group === group);

/** Replace a group's exclusions so exactly `included` of its keys stay checked. */
export function setGroupIncluded(exclude: readonly string[], group: TraitGroup, included: readonly string[]): string[] {
  const keys = traitsIn(group).map((t) => t.key);
  return [...exclude.filter((k) => !keys.includes(k)), ...keys.filter((k) => !included.includes(k))];
}

const KIND_LABEL: Record<string, string> = {
  pool: 'Any card pool', deck: 'Any precon deck', singles: 'Singles', unknown: 'Unknown origin',
};
const KIND_ORDER = ['pool', 'deck', 'singles', 'unknown'];
const PRODUCT_GROUP: Record<string, string> = { pool: 'Card pools', deck: 'Precon decks' };

/** "Acquired from" picker options: one per kind present, then every pool and
 *  precon deck product by name (· SET), with owned-printing counts. */
export function sourceOptions(cards: readonly CollectionCardOut[], sources: readonly SourceOut[]) {
  const kinds = sourceKinds(sources);
  const byKind = new Map<string, number>();
  for (const c of cards) for (const k of new Set((c.sources ?? []).map((s) => kinds.get(s) ?? ''))) if (k) byKind.set(k, (byKind.get(k) ?? 0) + 1);
  const kindOpts = KIND_ORDER.filter((k) => byKind.has(k)).map((k) => ({ value: `kind:${k}`, label: KIND_LABEL[k], count: byKind.get(k), group: 'By kind' }));
  const products = sources
    .filter((s) => s.kind in PRODUCT_GROUP)
    .sort((a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind) || a.label.localeCompare(b.label))
    .map((s) => ({ value: s.key, label: s.set_code ? `${s.label} · ${s.set_code.toUpperCase()}` : s.label, count: s.printings, group: PRODUCT_GROUP[s.kind] }));
  return [...kindOpts, ...products];
}

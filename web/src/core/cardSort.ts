// Card sort keys shared by every card view (Collection, Decks, Commanders).
import type { GuideCard } from './guideCard';
import { colorSection, colorRank, RARITY_NAME, RARITY_RANK, TYPE_GROUPS } from './cardFacts';
import type { SortPreset, SortRegistry } from './sort';

/** The card's FAMILY release date with the family code appended as a hidden
 *  tie-break, so two families released the same day (C21/STX) never interleave.
 *  Views without family facts fall back to the printing's own date. */
const familyRelease = (c: GuideCard) => (c.familyReleased ? `${c.familyReleased}|${c.family ?? ''}` : c.released);

const ownedTotal = (c: GuideCard) => (c.owned ? (c.owned.nonfoil ?? 0) + (c.owned.foil ?? 0) : null);

export const CARD_SORT = {
  set: { label: 'Set name', get: (c) => c.setName ?? c.setCode, defaultDir: 'asc', section: (c) => c.setName ?? c.setCode ?? '—' },
  cn: { label: 'Collector #', get: (c) => c.cn, defaultDir: 'asc' },
  rarity: { label: 'Rarity', get: (c) => (c.rarity ? RARITY_RANK[c.rarity] ?? 0 : null), defaultDir: 'desc', section: (c) => (c.rarity ? RARITY_NAME[c.rarity] ?? c.rarity : 'Unknown') },
  name: { label: 'Name', get: (c) => c.name, defaultDir: 'asc', section: (c) => c.name.charAt(0).toUpperCase() },
  color: { label: 'Color', get: (c) => colorRank(c.colors), defaultDir: 'asc', section: (c) => colorSection(c.colors) },
  mv: { label: 'Mana value', get: (c) => c.cmc, defaultDir: 'asc', section: (c) => (c.cmc == null ? 'No mana value' : `Mana value ${c.cmc}`) },
  type: { label: 'Type', get: (c) => TYPE_GROUPS.indexOf(c.typeGroup as (typeof TYPE_GROUPS)[number]), defaultDir: 'asc', section: (c) => c.typeGroup },
  price: { label: 'Price', get: (c) => c.price, defaultDir: 'desc' },
  owned: { label: 'Copies owned', get: ownedTotal, defaultDir: 'desc', section: (c) => ((ownedTotal(c) ?? 0) > 0 ? 'Owned' : 'Missing') },
  released: { label: 'Release date', get: familyRelease, defaultDir: 'desc', section: (c) => (c.familyReleased ?? c.released)?.slice(0, 4) ?? 'Undated' },
  printed: { label: 'Printing date', get: (c) => c.released, defaultDir: 'asc', section: (c) => c.released?.slice(0, 4) ?? 'Undated' },
} satisfies SortRegistry<GuideCard>;

export type CardSortKey = keyof typeof CARD_SORT;

export const CARD_SORT_PRESETS: SortPreset<CardSortKey>[] = [
  { label: 'Release › Set name › Number', rules: [{ key: 'released', dir: 'desc' }, { key: 'set', dir: 'asc' }, { key: 'cn', dir: 'asc' }] },
  { label: 'Set name › Number', rules: [{ key: 'set', dir: 'asc' }, { key: 'cn', dir: 'asc' }] },
  { label: 'Set name › Rarity › Number', rules: [{ key: 'set', dir: 'asc' }, { key: 'rarity', dir: 'desc' }, { key: 'cn', dir: 'asc' }] },
  { label: 'Color › Mana value › Name', rules: [{ key: 'color', dir: 'asc' }, { key: 'mv', dir: 'asc' }, { key: 'name', dir: 'asc' }] },
  { label: 'Type › Name', rules: [{ key: 'type', dir: 'asc' }, { key: 'name', dir: 'asc' }] },
  { label: 'Price, high first', rules: [{ key: 'price', dir: 'desc' }, { key: 'name', dir: 'asc' }] },
  { label: 'Rarity › Price', rules: [{ key: 'rarity', dir: 'desc' }, { key: 'price', dir: 'desc' }] },
];

// Pure view-model derivations for the commander compare view.
import type { CompareCardOut } from './api';
import { colorRank, TYPE_GROUPS, typeGroup } from './cardFacts';
import type { Bucket } from './search';
import type { SortPreset, SortRegistry } from './sort';

export type CompareCard = CompareCardOut;

export function bucketCards(cards: CompareCard[]): Record<Bucket, CompareCard[]> {
  const out: Record<Bucket, CompareCard[]> = { a_only: [], both: [], b_only: [] };
  for (const c of cards) out[c.bucket as Bucket]?.push(c);
  return out;
}

export function matches(c: CompareCard, q: string, tags: readonly string[]): boolean {
  if (q && !c.name.toLowerCase().includes(q.toLowerCase())) return false;
  if (tags.length) {
    const want = new Set(tags);
    if (!c.tags.some((t) => want.has(t))) return false;
  }
  return true;
}

/** The inclusion % that ranks a card within its own bucket. */
export function bucketInclusion(c: CompareCard): number {
  if (c.bucket === 'a_only') return c.a_pct ?? -1;
  if (c.bucket === 'b_only') return c.b_pct ?? -1;
  return Math.max(c.a_pct ?? -1, c.b_pct ?? -1);
}

const maxOf = (a: number | null | undefined, b: number | null | undefined) =>
  a == null && b == null ? null : Math.max(a ?? -Infinity, b ?? -Infinity);

export const COMPARE_SORT = {
  inclusion: { label: 'Inclusion %', get: (c) => (bucketInclusion(c) >= 0 ? bucketInclusion(c) : null), defaultDir: 'desc' },
  synergy: { label: 'Synergy', get: (c) => maxOf(c.synergy_a, c.synergy_b), defaultDir: 'desc' },
  delta: { label: 'Inclusion gap', get: (c) => c.delta, defaultDir: 'desc' },
  price: { label: 'Price', get: (c) => c.lowest_usd, defaultDir: 'desc' },
  name: { label: 'Name', get: (c) => c.name, defaultDir: 'asc' },
  mv: { label: 'Mana value', get: (c) => c.cmc, defaultDir: 'asc' },
  color: { label: 'Color', get: (c) => colorRank(c.color_identity ?? []), defaultDir: 'asc' },
  type: { label: 'Type', get: (c) => TYPE_GROUPS.indexOf(typeGroup(c.type_line) as (typeof TYPE_GROUPS)[number]), defaultDir: 'asc' },
} satisfies SortRegistry<CompareCard>;

export type CompareSortKey = keyof typeof COMPARE_SORT;

export const COMPARE_SORT_PRESETS: SortPreset<CompareSortKey>[] = [
  { label: 'Inclusion, high first', rules: [{ key: 'inclusion', dir: 'desc' }, { key: 'name', dir: 'asc' }] },
  { label: 'Synergy, high first', rules: [{ key: 'synergy', dir: 'desc' }, { key: 'inclusion', dir: 'desc' }] },
  { label: 'Biggest inclusion gap', rules: [{ key: 'delta', dir: 'desc' }, { key: 'inclusion', dir: 'desc' }] },
  { label: 'Mana value › Inclusion', rules: [{ key: 'mv', dir: 'asc' }, { key: 'inclusion', dir: 'desc' }] },
  { label: 'Price, low first', rules: [{ key: 'price', dir: 'asc' }, { key: 'inclusion', dir: 'desc' }] },
];

/** Tag → count across the given cards, most common first. */
export function tagCounts(cards: CompareCard[]): Array<[string, number]> {
  const m = new Map<string, number>();
  for (const c of cards) for (const t of c.tags) m.set(t, (m.get(t) ?? 0) + 1);
  return [...m].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

/** EDHREC list tags are slugs ("manaartifacts"); give them readable labels. */
const TAG_LABELS: Record<string, string> = {
  topcards: 'Top cards', highsynergycards: 'High synergy', newcards: 'New cards',
  creatures: 'Creatures', instants: 'Instants', sorceries: 'Sorceries',
  utilityartifacts: 'Utility artifacts', manaartifacts: 'Mana artifacts',
  enchantments: 'Enchantments', planeswalkers: 'Planeswalkers', battles: 'Battles',
  utilitylands: 'Utility lands', lands: 'Lands', gamechangers: 'Game changers',
};
export const tagLabel = (t: string): string =>
  TAG_LABELS[t] ?? t.replace(/[-_]/g, ' ').replace(/^\w/, (s) => s.toUpperCase());

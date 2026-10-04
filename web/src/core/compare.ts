// Pure view-model derivations for the commander compare view.
import type { CompareCardOut } from './api';
import type { Bucket, CompareSort } from './search';

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

const num = (v: number | null | undefined, missing = -Infinity) => (v == null ? missing : v);

export function sortCards(cards: CompareCard[], sort: CompareSort): CompareCard[] {
  const by: Record<CompareSort, (x: CompareCard, y: CompareCard) => number> = {
    inclusion: (x, y) => bucketInclusion(y) - bucketInclusion(x),
    delta: (x, y) => num(y.delta) - num(x.delta),
    synergy: (x, y) =>
      Math.max(num(y.synergy_a), num(y.synergy_b)) - Math.max(num(x.synergy_a), num(x.synergy_b)),
    price: (x, y) => num(y.lowest_usd) - num(x.lowest_usd),
    name: (x, y) => x.name.localeCompare(y.name),
    mv: (x, y) => num(x.cmc, Infinity) - num(y.cmc, Infinity),
  };
  return [...cards].sort((x, y) => by[sort](x, y) || x.name.localeCompare(y.name));
}

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

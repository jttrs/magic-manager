import { describe, expect, it } from 'vitest';
import { facetCounts, passes, type Facets } from './facets';

type Card = { name: string; rarity: string; fns: string[] };
const cards: Card[] = [
  { name: 'A', rarity: 'rare', fns: ['ramp', 'draw'] },
  { name: 'B', rarity: 'rare', fns: ['removal'] },
  { name: 'C', rarity: 'common', fns: ['ramp'] },
];
const facetsFor = (rarity: string[], fn: string[]): Facets<Card, 'rarity' | 'fn'> => ({
  rarity: (c) => !rarity.length || rarity.includes(c.rarity),
  fn: (c) => !fn.length || c.fns.some((f) => fn.includes(f)),
});

describe('facets', () => {
  it('passes every facet, or every facet but one', () => {
    const f = facetsFor(['common'], ['removal']);
    expect(cards.filter((c) => passes(c, f)).map((c) => c.name)).toEqual([]);
    expect(cards.filter((c) => passes(c, f, 'fn')).map((c) => c.name)).toEqual(['C']);
  });

  it('counts a filter under the others, never under itself', () => {
    const f = facetsFor(['common'], ['ramp']);
    // rarity counts ignore the rarity choice but respect fn=ramp: A (rare), C (common)
    expect(facetCounts(cards, f, 'rarity', (c) => c.rarity)).toEqual(new Map([['rare', 1], ['common', 1]]));
    // fn counts ignore fn but respect rarity=common: only C
    expect(facetCounts(cards, f, 'fn', (c) => c.fns)).toEqual(new Map([['ramp', 1]]));
  });

  it('tallies a multi-valued key once per item', () => {
    const f = facetsFor([], []);
    expect(facetCounts(cards, f, 'fn', (c) => [...c.fns, ...c.fns]).get('ramp')).toBe(2);
  });
});

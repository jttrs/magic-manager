import { describe, expect, it } from 'vitest';
import { fromCardDiff, fromCompare, groupCards, rarityLetter, typeGroup, exportLines } from './guideCard';
import { sortCards, matches, bucketCards, tagLabel } from './compare';
import { filterTiles, sortTiles } from './cardDiff';
import { compareSearch, cardDiffSearch } from './search';
import type { CardDiffTile, CompareCardOut } from './api';

const cmp = (o: Partial<CompareCardOut>): CompareCardOut => ({
  name: 'X', oracle_id: 'o', slug: 'x', bucket: 'a_only', tags: [], a_pct: null, b_pct: null,
  a_decks: null, b_decks: null, delta: null, synergy_a: null, synergy_b: null, trend_a: null,
  trend_b: null, type_line: null, cmc: null, mana_cost: null, color_identity: null, rarity: null,
  lowest_usd: null, lowest_usd_foil: null, scryfall_id: null, image_uri: null, set_code: null,
  collector_number: null, scryfall_url: null, ...o,
});
const tile = (o: Partial<CardDiffTile>): CardDiffTile => ({
  key: 'sid|1', family: 'fin', pools: ['printing'], name: 'Y', set_code: 'FIN', collector_number: '1',
  rarity: 'rare', finish: 'nonfoil', usd: 1, image_uri: null, scryfall_url: null,
  manapool_line: '', tcgplayer_line: '', ...o,
});

describe('typeGroup', () => {
  it('classifies by front face, creature first', () => {
    expect(typeGroup('Artifact Creature — Golem')).toBe('Creatures');
    expect(typeGroup('Legendary Planeswalker — Tifa')).toBe('Planeswalkers');
    expect(typeGroup('Instant // Sorcery')).toBe('Instants');
    expect(typeGroup('Land — Forest')).toBe('Lands');
    expect(typeGroup(null)).toBe('Other');
  });
});

describe('mappers', () => {
  it('compare: inclusion is the bucket metric; both carries bars', () => {
    const a = fromCompare(cmp({ bucket: 'a_only', a_pct: 61, set_code: 'fin' }));
    expect(a.pct).toBe(61);
    expect(a.bars).toBeNull();
    expect(a.setCode).toBe('FIN');
    const b = fromCompare(cmp({ bucket: 'both', a_pct: 40, b_pct: 70 }));
    expect(b.pct).toBe(70);
    expect(b.bars).toEqual({ a: 40, b: 70 });
  });
  it('card-diff: pools become stamps; exact-printing lines preserved', () => {
    const g = fromCardDiff(tile({ pools: ['printing', 'variant-chase'], manapool_line: '1 Y [FIN] 1' }));
    expect(g.stamps).toEqual(['P', 'V']);
    expect(g.lines.manapool).toBe('1 Y [FIN] 1');
    expect(g.key).toBe('fin|sid|1');
  });
  it('rarity letters', () => {
    expect(rarityLetter('mythic')).toBe('M');
    expect(rarityLetter(null)).toBe('');
  });
});

describe('groupCards', () => {
  it('orders groups by the given order, keeps item order', () => {
    const cards = ['Lands', 'Creatures', 'Lands'].map((group, i) => ({ ...fromCompare(cmp({})), key: String(i), group }));
    const g = groupCards(cards, ['Creatures', 'Lands']);
    expect(g.map((x) => x.key)).toEqual(['Creatures', 'Lands']);
    expect(g[1].items.map((c) => c.key)).toEqual(['0', '2']);
  });
  it('export lines skip blanks', () => {
    expect(exportLines([fromCompare(cmp({ name: 'Sol Ring' }))], 'plain')).toBe('1 Sol Ring');
  });
});

describe('compare derivations', () => {
  const cards = [
    cmp({ name: 'B', bucket: 'a_only', a_pct: 10, tags: ['creatures'] }),
    cmp({ name: 'A', bucket: 'a_only', a_pct: 90, lowest_usd: 1 }),
    cmp({ name: 'C', bucket: 'both', a_pct: 20, b_pct: 50, delta: 30 }),
  ];
  it('sorts by inclusion desc, ties by name', () => {
    expect(sortCards(cards, 'inclusion').map((c) => c.name)).toEqual(['A', 'C', 'B']);
    expect(sortCards(cards, 'name').map((c) => c.name)).toEqual(['A', 'B', 'C']);
  });
  it('filters by query and tag', () => {
    expect(cards.filter((c) => matches(c, 'b', [])).map((c) => c.name)).toEqual(['B']);
    expect(cards.filter((c) => matches(c, '', ['creatures'])).map((c) => c.name)).toEqual(['B']);
  });
  it('buckets', () => {
    const b = bucketCards(cards);
    expect([b.a_only.length, b.both.length, b.b_only.length]).toEqual([2, 1, 0]);
  });
  it('tag labels', () => {
    expect(tagLabel('manaartifacts')).toBe('Mana artifacts');
    expect(tagLabel('some-new_tag')).toBe('Some new tag');
  });
});

describe('card-diff derivations', () => {
  const tiles = [
    tile({ name: 'Zed', collector_number: '10', usd: 5, pools: ['functional'] }),
    tile({ name: 'Amy', collector_number: '2', usd: null }),
    tile({ name: 'Bo', collector_number: '2a', usd: 9 }),
  ];
  it('collector-number sort is numeric then suffix', () => {
    expect(sortTiles(tiles, 'cn').map((t) => t.collector_number)).toEqual(['2', '2a', '10']);
  });
  it('value sort puts unpriced last', () => {
    expect(sortTiles(tiles, 'value').map((t) => t.name)).toEqual(['Bo', 'Zed', 'Amy']);
  });
  it('pool filter keeps tiles in any shown pool', () => {
    expect(filterTiles(tiles, '', ['functional']).map((t) => t.name)).toEqual(['Zed']);
  });
});

describe('URL schemas', () => {
  it('compare: defaults + coercion of single values', () => {
    const s = compareSearch.parse({ a: 'Tifa', show: 'both', tags: 'creatures', sort: 'bogus' });
    expect(s.show).toEqual(['both']);
    expect(s.tags).toEqual(['creatures']);
    expect(s.sort).toBe('inclusion');
  });
  it('card-diff: defaults', () => {
    const s = cardDiffSearch.parse({});
    expect(s.show).toEqual(['printing', 'functional', 'variant-chase']);
    expect(s.chase).toBe('exclude');
  });
});

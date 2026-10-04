import { describe, expect, it } from 'vitest';
import type { CollectionCardOut, CompareCardOut } from './api';
import { CARD_SORT } from './cardSort';
import { colorRank, typeGroup } from './cardFacts';
import { buyFinish, collectionStats, filterCollection, isMissing, traitCounts, traitsOf, type CollectionFilters } from './collection';
import { bucketCards, COMPARE_SORT, matches, tagLabel } from './compare';
import { exportLines, fromCollection, fromCompare, groupCards, rarityLetter, treatmentLabels } from './guideCard';
import { collectionSearch, compareSearch } from './search';
import { composeSort, decodeSort, encodeSort, leadSection, sortBy } from './sort';

const cmp = (o: Partial<CompareCardOut>): CompareCardOut => ({
  name: 'X', oracle_id: 'o', slug: 'x', bucket: 'a_only', tags: [], a_pct: null, b_pct: null,
  a_decks: null, b_decks: null, delta: null, synergy_a: null, synergy_b: null, trend_a: null,
  trend_b: null, type_line: null, cmc: null, mana_cost: null, color_identity: null, rarity: null,
  lowest_usd: null, lowest_usd_foil: null, scryfall_id: null, image_uri: null, set_code: null,
  collector_number: null, scryfall_url: null, ...o,
});
const card = (o: Partial<CollectionCardOut>): CollectionCardOut => ({
  scryfall_id: 'id', oracle_id: 'o', name: 'Y', family: 'fin', set_code: 'fin', collector_number: '1',
  rarity: 'rare', type_line: 'Creature — Moogle', cmc: 2, color_identity: ['W'], released_at: '2025-06-13',
  finishes: ['nonfoil', 'foil'], owned: {}, pledged: {}, price_usd: 1, price_usd_foil: 3, image_uri: null,
  scryfall_url: null, treatment: '', standard_frame: true, is_bulk: false, is_chase: false, ...o,
});
const ALL: CollectionFilters = { show: ['owned', 'missing'], basis: 'either', exclude: [], q: '' };

describe('card facts', () => {
  it('type groups by front face, creature first', () => {
    expect(typeGroup('Artifact Creature — Golem')).toBe('Creatures');
    expect(typeGroup('Instant // Sorcery')).toBe('Instants');
    expect(typeGroup(null)).toBe('Other');
  });
  it('color order: WUBRG mono, then multicolor, then colorless', () => {
    expect(['G', 'W'].map((c) => colorRank([c]))).toEqual([4, 0]);
    expect(colorRank(['W', 'U'])).toBeGreaterThan(colorRank(['G']));
    expect(colorRank([])).toBeGreaterThan(colorRank(['W', 'U', 'B']));
  });
  it('labels', () => {
    expect(rarityLetter('mythic')).toBe('M');
    expect(treatmentLabels('b|ext')).toEqual(['Borderless', 'Ext. art']);
    expect(tagLabel('manaartifacts')).toBe('Mana artifacts');
  });
});

describe('sort rules', () => {
  const reg = { n: { label: 'N', get: (x: { n: number | null; s: string }) => x.n, defaultDir: 'desc' as const }, s: { label: 'S', get: (x: { n: number | null; s: string }) => x.s, defaultDir: 'asc' as const } };
  const items = [{ n: 1, s: 'b' }, { n: null, s: 'a' }, { n: 2, s: 'c' }, { n: 1, s: 'a' }];
  it('composes levels; nulls last in both directions', () => {
    expect(sortBy(items, [{ key: 'n', dir: 'desc' }, { key: 's', dir: 'asc' }], reg).map((x) => `${x.n}${x.s}`)).toEqual(['2c', '1a', '1b', 'nulla']);
    expect(sortBy(items, [{ key: 'n', dir: 'asc' }], reg).at(-1)!.n).toBeNull();
  });
  it('URL codec round-trips, omits default directions, drops junk and dupes', () => {
    const rules = [{ key: 'n' as const, dir: 'asc' as const }, { key: 's' as const, dir: 'asc' as const }];
    expect(encodeSort(rules, reg)).toBe('n:asc,s');
    expect(decodeSort('n:asc,s', reg)).toEqual(rules);
    expect(decodeSort('bogus,s,s,n:sideways', reg)).toEqual([{ key: 's', dir: 'asc' }, { key: 'n', dir: 'desc' }]);
  });
  it('collector numbers sort numerically with suffixes', () => {
    const cards = ['10', '2a', '2'].map((cn) => fromCollection(card({ scryfall_id: cn, collector_number: cn }), false));
    expect(sortBy(cards, [{ key: 'cn', dir: 'asc' }], CARD_SORT).map((c) => c.cn)).toEqual(['2', '2a', '10']);
  });
  it('rarity sorts mythic first by default and leads sections', () => {
    const cards = ['common', 'mythic', 'rare'].map((r) => fromCollection(card({ scryfall_id: r, rarity: r }), false));
    const rules = decodeSort('rarity', CARD_SORT);
    expect(sortBy(cards, rules, CARD_SORT).map((c) => c.rarity)).toEqual(['mythic', 'rare', 'common']);
    expect(leadSection(rules, CARD_SORT)!(cards[0])).toBe('Common');
    expect(leadSection(decodeSort('price', CARD_SORT), CARD_SORT)).toBeNull();
  });
  it('compare registry ranks by bucket inclusion', () => {
    const cs = [cmp({ name: 'B', a_pct: 10 }), cmp({ name: 'A', a_pct: 90 }), cmp({ name: 'C', bucket: 'both', a_pct: 20, b_pct: 50 })];
    expect([...cs].sort(composeSort(decodeSort('inclusion,name', COMPARE_SORT), COMPARE_SORT)).map((c) => c.name)).toEqual(['A', 'C', 'B']);
  });
});

describe('collection filters', () => {
  const owned = card({ scryfall_id: 'own', owned: { nonfoil: 2 } });
  const missing = card({ scryfall_id: 'miss' });
  const bulk = card({ scryfall_id: 'bulk', is_bulk: true, rarity: 'common' });
  const treated = card({ scryfall_id: 'tr', standard_frame: false, treatment: 'b' });
  const chase = card({ scryfall_id: 'ch', is_chase: true });
  const all = [owned, missing, bulk, treated, chase];
  const ids = (f: Partial<CollectionFilters>) => filterCollection(all, { ...ALL, ...f }).map((c) => c.scryfall_id);

  it('missing basis', () => {
    expect(isMissing(owned, 'either')).toBe(false);
    expect(isMissing(owned, 'foil')).toBe(true);
    expect(isMissing(card({ finishes: ['nonfoil'] }), 'foil')).toBe(false);
  });
  it('show owned / missing', () => {
    expect(ids({ show: ['owned'] })).toEqual(['own']);
    expect(ids({ show: ['missing'] })).toEqual(['miss', 'bulk', 'tr', 'ch']);
    expect(ids({ show: [] })).toEqual([]);
  });
  it('card-type traits', () => {
    expect(traitsOf(treated)).toEqual(['rarity:rare', 'treat:b', 'chase:no']);
    expect(traitsOf(card({ standard_frame: false, treatment: '' }))).toContain('treat:other');
    expect(traitsOf(card({ treatment: 'b|ext', standard_frame: false }))).toEqual(['rarity:rare', 'treat:b', 'treat:ext', 'chase:no']);
    expect(traitCounts(all).get('rarity:rare')).toBe(4);
  });
  it('unchecked traits hide any card carrying them', () => {
    expect(ids({ exclude: ['rarity:common'] })).not.toContain('bulk');
    expect(ids({ exclude: ['treat:b'] })).not.toContain('tr');
    expect(ids({ exclude: ['chase:no'] })).toEqual(['ch']);
    expect(ids({ exclude: ['chase:yes'] })).not.toContain('ch');
    expect(ids({ q: 'nope' })).toEqual([]);
  });
  it('buy finish + stats', () => {
    expect(buyFinish(card({ finishes: ['foil'] }), 'either')).toBe('foil');
    expect(buyFinish(missing, 'either')).toBe('nonfoil');
    expect(collectionStats([owned, missing], 'either')).toEqual({ printings: 2, owned: 1, copies: 2, missing: 1, missingUsd: 1 });
  });
  it('collection mapper carries counts, missing mark and tags', () => {
    const g = fromCollection(card({ owned: { foil: 1 }, is_chase: true, treatment: 'shw' }), true);
    expect(g.owned).toEqual({ foil: 1 });
    expect(g.missing).toBe(true);
    expect(g.tags).toEqual(['Chase', 'Showcase']);
    expect(g.setCode).toBe('FIN');
  });
});

describe('compare + grouping', () => {
  it('mapper + buckets + filters', () => {
    const both = fromCompare(cmp({ bucket: 'both', a_pct: 40, b_pct: 70, set_code: 'fin' }));
    expect(both.pct).toBe(70);
    expect(both.bars).toEqual({ a: 40, b: 70 });
    const cards = [cmp({ name: 'B', tags: ['creatures'] }), cmp({ name: 'C', bucket: 'both' })];
    expect(bucketCards(cards).both).toHaveLength(1);
    expect(cards.filter((c) => matches(c, '', ['creatures'])).map((c) => c.name)).toEqual(['B']);
    expect(exportLines([fromCompare(cmp({ name: 'Sol Ring' }))], 'plain')).toBe('1 Sol Ring');
  });
  it('groupCards keeps order', () => {
    const cs = ['Lands', 'Creatures', 'Lands'].map((group, i) => ({ ...fromCompare(cmp({})), key: String(i), group }));
    const g = groupCards(cs, ['Creatures', 'Lands']);
    expect(g.map((x) => x.key)).toEqual(['Creatures', 'Lands']);
    expect(g[1].items.map((c) => c.key)).toEqual(['0', '2']);
  });
});

describe('URL schemas', () => {
  it('compare defaults', () => {
    const s = compareSearch.parse({ a: 'Tifa', show: 'both', tags: 'creatures' });
    expect(s.show).toEqual(['both']);
    expect(s.sort).toBe('inclusion,name');
  });
  it('collection defaults + coercion', () => {
    const s = collectionSearch.parse({ families: 'fin', exclude: 'rarity:common' });
    expect(s.exclude).toEqual(['rarity:common']);
    const d = collectionSearch.parse({});
    expect(s.families).toEqual(['fin']);
    expect(s.show).toEqual(['owned', 'missing']);
    expect(d.exclude).toEqual([]);
    expect(s.sort).toBe('set,cn');
  });
});

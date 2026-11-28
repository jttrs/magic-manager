import { describe, expect, it } from 'vitest';
import type { CollectionCardOut } from './api';
import { collectionCounts, filterCollection, traitsOf, type CollectionFilters } from './collection';

const card = (o: Partial<CollectionCardOut>): CollectionCardOut => ({
  scryfall_id: 'id', oracle_id: 'o', name: 'Y', family: 'fin', set_code: 'fin', collector_number: '1',
  rarity: 'rare', type_line: null, cmc: null, color_identity: [], released_at: null,
  finishes: ['nonfoil'], owned: {}, pledged: {}, price_usd: null, price_usd_foil: null, image_uri: null,
  scryfall_url: null, treatment: '', standard_frame: true, is_bulk: false, is_chase: false, ...o,
});

const cards = [
  card({ scryfall_id: 'a', rarity: 'rare', owned: { nonfoil: 1 }, functions: ['ramp'] }),
  card({ scryfall_id: 'b', rarity: 'common', functions: ['ramp'] }),
  card({ scryfall_id: 'c', rarity: 'mythic', treatment: 'b', is_chase: true, functions: ['draw'] }),
  card({ scryfall_id: 'd', rarity: 'uncommon', finishes: ['nonfoil', 'foil'], owned: { foil: 1 } }),
];
const ALL: CollectionFilters = { show: ['owned', 'missing'], exclude: [], q: '' };

describe('collection facet counts', () => {
  it('Owned/Missing never read 0 for the switched-off option', () => {
    const counts = collectionCounts(cards, { ...ALL, show: ['owned'] });
    expect(counts.show).toEqual({ owned: 2, missing: 2 });
    expect(filterCollection(cards, { ...ALL, show: ['owned'] })).toHaveLength(2);
  });
  it('an unchecked finish still counts the printings it would bring back', () => {
    // only `d` has foil; with foil unchecked and only owned shown, `d` is owned in foil only
    const counts = collectionCounts(cards, { ...ALL, show: ['owned'], exclude: ['finish:foil'] });
    expect(counts.traits.get('finish:foil')).toBe(1);
    // a CHECKED finish counts exactly what is shown: `d` (owned in foil only) is hidden
    const shown = filterCollection(cards, { ...ALL, show: ['owned'], exclude: ['finish:foil'] });
    expect(shown.map((c) => c.scryfall_id)).toEqual(['a']);
    expect(counts.traits.get('finish:nonfoil')).toBe(1);
  });
  it('a multi-treatment printing hidden by one treatment is not counted under another', () => {
    const both = [card({ scryfall_id: 'x', treatment: 'b|shw' }), card({ scryfall_id: 'y', treatment: 'shw' })];
    const counts = collectionCounts(both, { ...ALL, exclude: ['treat:b'] });
    expect(filterCollection(both, { ...ALL, exclude: ['treat:b'] }).map((c) => c.scryfall_id)).toEqual(['y']);
    expect(counts.traits.get('treat:shw')).toBe(1);
    expect(counts.traits.get('treat:b')).toBe(1);
  });
  it('rarity counts respect a function filter but ignore the rarity exclusion', () => {
    const counts = collectionCounts(cards, { ...ALL, fn: ['ramp'], exclude: ['rarity:rare'] });
    expect(counts.traits.get('rarity:rare')).toBe(1);
    expect(counts.traits.get('rarity:common')).toBe(1);
    expect(counts.traits.get('rarity:mythic')).toBeUndefined();
    // another group's exclusion does apply
    const noChase = collectionCounts(cards, { ...ALL, exclude: ['chase:yes'] });
    expect(noChase.traits.get('rarity:mythic')).toBeUndefined();
    expect(noChase.traits.get('chase:yes')).toBe(1);
  });
  it('function counts ignore the function filter', () => {
    const counts = collectionCounts(cards, { ...ALL, fn: ['draw'], q: 'y' });
    expect(counts.fn.get('ramp')).toBe(2);
  });
  it('filters like the old rule for a mixed exclude list', () => {
    const exclude = ['rarity:common', 'treat:b', 'finish:foil'];
    const old = cards.filter((c) => {
      if (traitsOf(c).some((t) => exclude.includes(t))) return false;
      const fins = c.finishes.filter((f) => !(f === 'foil' && exclude.includes('finish:foil')));
      return fins.length > 0;
    });
    expect(filterCollection(cards, { ...ALL, exclude }).map((c) => c.scryfall_id)).toEqual(old.map((c) => c.scryfall_id));
  });
});

describe('card-tag filter', () => {
  const tagged = cards.map((c, i) => ({ ...c, oracle_id: `o${i}` }));
  it('keeps only cards whose oracle id carries a chosen tag; absent = no tag filter; empty = nothing', () => {
    expect(filterCollection(tagged, { ...ALL, otIds: new Set(['o0', 'o2']) }).map((c) => c.scryfall_id)).toEqual(['a', 'c']);
    expect(filterCollection(tagged, { ...ALL })).toHaveLength(4);
    expect(filterCollection(tagged, { ...ALL, otIds: new Set() })).toHaveLength(0);
  });
  it('functions and tags are one picker: a card matches ANY chosen function or tag', () => {
    // o3 is d (no function); ramp keeps a and b
    expect(filterCollection(tagged, { ...ALL, fn: ['ramp'], otIds: new Set(['o3']) }).map((c) => c.scryfall_id)).toEqual(['a', 'b', 'd']);
    // a chosen tag still resolving (empty set) narrows nothing beyond the chosen functions
    expect(filterCollection(tagged, { ...ALL, fn: ['draw'], otIds: new Set() }).map((c) => c.scryfall_id)).toEqual(['c']);
  });
  it('function counts lift the whole picker (functions and tags), so a chosen tag never zeroes them', () => {
    expect(collectionCounts(tagged, { ...ALL, otIds: new Set(['o3']) }).fn.get('ramp')).toBe(2);
    // ...but other filters still apply
    expect(collectionCounts(tagged, { ...ALL, otIds: new Set(['o3']), exclude: ['rarity:common'] }).fn.get('ramp')).toBe(1);
  });
});

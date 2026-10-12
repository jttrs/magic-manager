import { describe, expect, it } from 'vitest';
import type { DeckCardOut, PrintingOut, RecipeOut } from './api';
import { coverage, DECK_SECTIONS, deckGuideGroups, deckReviewLines, deckSection, filterRecipes, fromDeckCard, groupRecipes, jumpstartSet, optionCounts, ownershipLabel, recipeFileName, recipeSummary, unreadInSet, type RecipeFilters } from './decks';
import { decksSearch } from './search';

const recipe = (o: Partial<RecipeOut>): RecipeOut => ({
  key: 's', slug: 's', slugs: ['s'], file_name: 'S_FIC', name: 'Deck', kind: 'precon', deck_type: 'Commander', product_type: 'Commander Deck', source: 'Commander Deck', author: null,
  set_code: 'fic', set_name: 'Final Fantasy Commander', released: '2025-06-13', built: 1, loose: 0, ownership: 'built', pledged_pct: 100, read: true,
  cards: 100, value_usd: 50, image_uri: null, color: 'WU', have: 90, short: 10, status: 'far', ...o,
});
const printing = (o: Partial<PrintingOut> = {}): PrintingOut => ({
  scryfall_id: 'p', oracle_id: 'o', name: 'Card', set_code: 'fic', set_name: null, collector_number: '1', rarity: 'rare',
  finishes: ['nonfoil', 'foil'], treatment: '', image_uri: null, price_usd: 1, price_usd_foil: 2, released_at: null, owned: {}, ...o,
});
const card = (o: Partial<DeckCardOut> & { p?: Partial<PrintingOut> } = {}): DeckCardOut => ({
  printing: printing(o.p), board: 'main', finish: 'nonfoil', count: 1, type_line: 'Creature — Moogle', cmc: 2, color_identity: ['W'],
  pledged_here: 0, free: 0, ...o,
});

describe('recipe list', () => {
  const rs = [
    recipe({ key: 'a', name: 'Counter Blitz' }),
    recipe({ key: 'fn:Angels1_J25', slug: null, slugs: [], file_name: 'Angels1_J25', name: 'Angels (1)', kind: 'jumpstart', deck_type: 'Jumpstart', set_code: 'j25', set_name: 'Foundations Jumpstart', released: '2024-11-15', built: 0, ownership: 'none', color: 'W', have: 20, short: 0, status: 'build' }),
    recipe({ key: 'fn:Angels2_J25', slug: null, slugs: [], file_name: 'Angels2_J25', name: 'Angels (2)', kind: 'jumpstart', deck_type: 'Jumpstart', set_code: 'j25', set_name: 'Foundations Jumpstart', released: '2024-11-15', built: 0, ownership: 'none', read: false, cards: null, value_usd: null, color: null, have: null, short: null, status: null }),
    recipe({ key: 'p2', name: 'Pirates', kind: 'jumpstart', deck_type: 'Jumpstart', set_code: 'j25', set_name: 'Foundations Jumpstart', released: '2024-11-15', built: 0, loose: 2, ownership: 'loose', color: 'U', have: 18, short: 2, status: 'close' }),
    recipe({ key: 'mine', file_name: null, name: 'Mine', kind: 'custom', set_code: null, set_name: null, released: null, source: null, author: 'me', built: 0, loose: 1, ownership: 'loose', color: 'B' }),
  ];
  const f = (o: Partial<RecipeFilters>): string[] => filterRecipes(rs, { q: '', kinds: [], own: ['built', 'loose', 'none'], cover: 'any', types: [], sets: [], ...o }).map((r) => r.key);

  it('defaults to what you own, every kind, every type', () => {
    const d = decksSearch.parse({});
    expect([d.own, d.kinds, d.types, d.sets, d.cover, d.group, d.view]).toEqual([['built', 'loose'], [], [], [], 'any', 'set', 'grid']);
    expect(decksSearch.parse({ group: 'origin' }).group).toBe('kind');
    expect(f({ own: ['built', 'loose'] })).toEqual(['a', 'p2', 'mine']);
  });
  it('filters by kind, ownership, free-card cover, type, set and text', () => {
    expect(f({ kinds: ['jumpstart'] })).toEqual(['fn:Angels1_J25', 'fn:Angels2_J25', 'p2']);
    expect(f({ own: ['none'] })).toEqual(['fn:Angels1_J25', 'fn:Angels2_J25']);
    expect(f({ cover: 'build' })).toEqual(['fn:Angels1_J25']);
    expect(f({ cover: 'close' })).toEqual(['fn:Angels1_J25', 'p2']);
    expect(f({ types: ['Commander'] })).toEqual(['a', 'mine']);
    expect(f({ sets: ['j25'] })).toEqual(['fn:Angels1_J25', 'fn:Angels2_J25', 'p2']);
    expect(f({ q: 'me' })).toEqual(['mine']);
    expect(f({ q: 'jumpstart' })).toEqual(['fn:Angels1_J25', 'fn:Angels2_J25', 'p2']);
  });
  it('counts each option under the other filters', () => {
    const c = optionCounts(rs, { q: '', kinds: ['jumpstart'], own: ['built', 'loose'], cover: 'any', types: [], sets: [] });
    expect(c.own).toEqual([{ value: 'built', label: 'Built', count: 0 }, { value: 'loose', label: 'Loose', count: 1 }, { value: 'none', label: 'None', count: 2 }]);
    expect(c.kinds.map((k) => k.count)).toEqual([1, 1, 0, 1]);
    expect(c.sets.map((s) => s.label)).toEqual(['Foundations Jumpstart · J25']);
    expect(c.cover).toEqual({ any: null, build: 0, close: 1 });
  });
  it('groups newest set/year first, kinds and ownership in a fixed order, colour with unread last', () => {
    expect(groupRecipes(rs, 'set').map((g) => g.label)).toEqual(['Final Fantasy Commander', 'Foundations Jumpstart', 'No set']);
    expect(groupRecipes(rs, 'year').map((g) => g.label)).toEqual(['2025', '2024', 'Undated']);
    expect(groupRecipes(rs, 'kind').map((g) => g.label)).toEqual(['Precon', 'Jumpstart', 'Custom']);
    expect(groupRecipes(rs, 'state').map((g) => g.label)).toEqual(['Built', 'Loose', 'Not owned']);
    expect(groupRecipes(rs, 'color').map((g) => [g.label, g.ready])).toEqual([['White', 1], ['Blue', 0], ['Black', 0], ['Multicolour', 0], ['Not read yet', 0]]);
  });
  it('marks ownership and free-card cover', () => {
    expect(rs.map(ownershipLabel)).toEqual(['×1 built', 'not owned', 'not owned', '2 loose', 'not built']);
    expect(rs.map(coverage)).toEqual(['', 'All 20 free', '', '2 short', '90 of 100 free']);
    expect(coverage(recipe({ built: 0, have: 9, short: 11, status: 'far' }))).toBe('9 of 20 free');
    expect(recipeSummary(rs)).toBe('5 recipes · 1 built · 1 ready from free cards');
  });
  it('knows the one Jumpstart set in view and what is unread in it', () => {
    expect(jumpstartSet(rs, { sets: ['j25'] })).toBe('j25');
    expect(jumpstartSet(rs, { sets: ['fic'] })).toBeNull();
    expect(jumpstartSet(rs, { sets: [] })).toBeNull();
    expect(unreadInSet(rs, { sets: ['j25'] })).toBe(1);
    expect(recipeFileName('fn:Angels1_J25')).toBe('Angels1_J25');
    expect(recipeFileName('my-deck')).toBeUndefined();
  });
});

describe('deck inspector', () => {
  it('sections: board first, then type; ordered like a decklist', () => {
    expect(deckSection({ board: 'commander', type_line: 'Legendary Creature' })).toBe('Commander');
    expect(deckSection({ board: 'main', type_line: 'Instant' })).toBe('Instants');
    expect(deckSection({ board: 'token', type_line: 'Token Creature' })).toBe('Tokens');
    const groups = deckGuideGroups([card({ board: 'token' }), card({ type_line: 'Basic Land — Plains', count: 8 }), card({ board: 'commander' })]);
    expect(groups.map((g) => g.label)).toEqual(['Commander', 'Lands · 8', 'Tokens']);
    expect(DECK_SECTIONS.indexOf('Commander')).toBe(0);
  });
  it('card facts: in-deck count, pledged, free, missing when unowned', () => {
    const g = fromDeckCard(card({ count: 2, pledged_here: 1, free: 3, finish: 'foil', p: { owned: { foil: 4 } } }));
    expect(g.tags.slice(0, 2)).toEqual(['×2 in deck', '1 pledged']);
    expect(g.note).toBe('3 free to use');
    expect(g.price).toBe(2);
    expect(g.missing).toBe(false);
    expect(fromDeckCard(card()).missing).toBe(true);
  });
  it('catalog recipe cards: missing and noted by free copies', () => {
    expect([fromDeckCard(card({ count: 2, free: 2 }), true).missing, fromDeckCard(card({ count: 2, free: 2 }), true).note]).toEqual([false, '2 free']);
    expect(fromDeckCard(card({ count: 2, free: 1 }), true).note).toBe('1 of 2 free');
    expect(fromDeckCard(card({ count: 1, free: 0 }), true)).toMatchObject({ missing: true, note: 'None free' });
  });
  it('review lines: exact printings, tokens out, marked subset, either → nonfoil', () => {
    const cs = [card({ count: 3, finish: 'either' }), card({ board: 'token', p: { scryfall_id: 't' } }), card({ p: { scryfall_id: 'q' } })];
    const all = deckReviewLines(cs);
    expect(all.map((l) => [l.chosen, l.qty, l.finish, l.status])).toEqual([['p', 3, 'nonfoil', 'exact'], ['q', 1, 'nonfoil', 'exact']]);
    expect(deckReviewLines(cs, new Set([fromDeckCard(cs[2]).key])).map((l) => l.chosen)).toEqual(['q']);
  });
});

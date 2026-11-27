import { describe, expect, it } from 'vitest';
import type { DeckCardOut, PrintingOut, RecipeOut } from './api';
import { coverage, readiness, deckStatus, DECK_SECTIONS, deckGuideGroups, deckReviewLines, deckSection, deckTypeCounts, effectiveTypes, filterRecipes, fromDeckCard, groupRecipes, jumpstartSet, optionCounts, ownershipLabel, recipeFileName, typesToSearch, unreadInSet, type RecipeFilters } from './decks';
import { decksSearch, legacyDecksSearch } from './search';

const recipe = (o: Partial<RecipeOut>): RecipeOut => ({
  key: 's', slug: 's', slugs: ['s'], file_name: 'S_FIC', name: 'Deck', origin: 'precon', deck_type: 'Commander', product_type: 'Commander Deck', source: 'Commander Deck', author: null,
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
    recipe({ key: 'fn:Angels1_J25', slug: null, slugs: [], file_name: 'Angels1_J25', name: 'Angels (1)', origin: 'precon', deck_type: 'Jumpstart', set_code: 'j25', set_name: 'Foundations Jumpstart', released: '2024-11-15', built: 0, ownership: 'none', color: 'W', have: 20, short: 0, status: 'build' }),
    recipe({ key: 'fn:Angels2_J25', slug: null, slugs: [], file_name: 'Angels2_J25', name: 'Angels (2)', origin: 'precon', deck_type: 'Jumpstart', set_code: 'j25', set_name: 'Foundations Jumpstart', released: '2024-11-15', built: 0, ownership: 'none', read: false, cards: null, value_usd: null, color: null, have: null, short: null, status: null }),
    recipe({ key: 'p2', name: 'Pirates', origin: 'precon', deck_type: 'Jumpstart', set_code: 'j25', set_name: 'Foundations Jumpstart', released: '2024-11-15', built: 0, loose: 2, ownership: 'loose', color: 'U', have: 18, short: 2, status: 'close' }),
    recipe({ key: 'mine', file_name: null, name: 'Mine', origin: 'custom', set_code: null, set_name: null, released: null, source: null, author: 'me', built: 0, loose: 1, ownership: 'loose', color: 'B' }),
  ];
  const f = (o: Partial<RecipeFilters>): string[] => filterRecipes(rs, { q: '', origins: [], status: ['built', 'buildable', 'unbuilt'], types: ['all'], sets: [], ...o }).map((r) => r.key);

  it('maps legacy own/cover links to a decklist status', () => {
    expect(legacyDecksSearch({ own: ['built', 'loose'] })).toEqual({ status: ['built', 'buildable', 'unbuilt'] });
    expect(legacyDecksSearch({ own: 'none' })).toEqual({ status: ['buildable', 'unbuilt'] });
    expect(legacyDecksSearch({ cover: 'build' })).toEqual({ status: ['buildable'] });
    expect(legacyDecksSearch({ cover: 'close', own: ['built'] })).toEqual({ status: ['buildable'] });
    expect(legacyDecksSearch({ status: ['built'], own: ['none'] })).toEqual({ status: ['built'] });
    expect(legacyDecksSearch({ own: ['built'] })).toEqual({ status: ['built'] });
    expect(legacyDecksSearch({ q: 'x' })).toEqual({ q: 'x' });
  });
  it('defaults to built decks, every source, the default deck type', () => {
    const d = decksSearch.parse({});
    expect([d.status, d.origins, d.types, d.sets, d.group, d.view]).toEqual([['built'], [], [], [], 'set', 'grid']);
    expect(decksSearch.parse({ group: 'origin' }).group).toBe('kind');
    expect(f({ status: ['built'] })).toEqual(['a']);
  });
  it('filters by source, decklist status, type, set and text', () => {
    expect(f({ origins: ['custom'] })).toEqual(['mine']);
    expect(f({ types: ['Jumpstart'] })).toEqual(['fn:Angels1_J25', 'fn:Angels2_J25', 'p2']);
    expect(f({ status: ['unbuilt'] })).toEqual(['fn:Angels2_J25', 'mine']);
    expect(f({ status: ['buildable'] })).toEqual(['fn:Angels1_J25', 'p2']);
    expect(filterRecipes(rs, { q: '', origins: [], status: ['buildable'], types: ['all'], sets: [] }, 0).map((r) => r.key)).toEqual(['fn:Angels1_J25']);
    expect(f({ types: ['Commander'] })).toEqual(['a', 'mine']);
    expect(f({ sets: ['j25'] })).toEqual(['fn:Angels1_J25', 'fn:Angels2_J25', 'p2']);
    expect(f({ q: 'me' })).toEqual(['mine']);
    expect(f({ q: 'jumpstart' })).toEqual(['fn:Angels1_J25', 'fn:Angels2_J25', 'p2']);
  });
  it('counts each option under the other filters', () => {
    const c = optionCounts(rs, { q: '', origins: ['precon'], status: ['built', 'buildable'], types: ['all'], sets: [] });
    expect(c.status).toEqual([{ value: 'built', label: 'Built', count: 1 }, { value: 'buildable', label: 'Buildable', count: 2 }, { value: 'unbuilt', label: 'Unbuilt', count: 1 }]);
    expect(c.origins.map((k) => k.count)).toEqual([3, 0, 0]);
    expect(c.sets.map((s) => s.label)).toEqual(['Final Fantasy Commander · FIC', 'Foundations Jumpstart · J25']);
  });
  it('groups newest set/year first, kinds and status in a fixed order, colour with unread last', () => {
    expect(groupRecipes(rs, 'set').map((g) => g.label)).toEqual(['Final Fantasy Commander', 'Foundations Jumpstart', 'No set']);
    expect(groupRecipes(rs, 'year').map((g) => g.label)).toEqual(['2025', '2024', 'Undated']);
    expect(groupRecipes(rs, 'kind').map((g) => g.label)).toEqual(['Wizards', 'Custom']);
    expect(groupRecipes(rs, 'state').map((g) => g.label)).toEqual(['Built', 'Buildable', 'Unbuilt']);
    expect(groupRecipes(rs, 'color').map((g) => [g.label, g.ready])).toEqual([['White', 1], ['Blue', 0], ['Black', 0], ['Multicolor', 0], ['Not read yet', 0]]);
  });
  it('marks ownership, unused-card cover and decklist status', () => {
    expect(rs.map(ownershipLabel)).toEqual(['×1 built', 'not owned', 'not owned', '2 loose', 'not built']);
    expect(rs.map(coverage)).toEqual(['', 'All 20 unused', '', '2 short', '90 of 100 unused']);
    expect(coverage(recipe({ built: 0, have: 9, short: 11, status: 'far' }))).toBe('9 of 20 unused');
    // The badge follows the user's threshold, not the server's status.
    expect(coverage(recipe({ built: 0, have: 17, short: 3, status: 'far' }))).toBe('3 short');
    expect(coverage(recipe({ built: 0, have: 17, short: 3, status: 'close' }), 2)).toBe('17 of 20 unused');
    expect(readiness(recipe({ short: 0 }))).toBe('ready');
    expect(readiness(recipe({ short: 5 }), 5)).toBe('close');
    expect(readiness(recipe({ read: false, short: null }))).toBeNull();
    expect(rs.map((r) => deckStatus(r))).toEqual(['built', 'buildable', 'unbuilt', 'buildable', 'unbuilt']);
  });
  it('leaves the deck type to the default until a set or type is chosen', () => {
    expect(effectiveTypes({ types: [], sets: [] })).toEqual(['Commander']);
    expect(effectiveTypes({ types: [], sets: ['j25'] })).toBeNull();
    expect(effectiveTypes({ types: ['all'], sets: [] })).toBeNull();
    expect(effectiveTypes({ types: ['all', 'Commander'], sets: [] })).toBeNull();
  });
  it("'Show all' never becomes a deck type option", () => {
    const rs = [recipe({ deck_type: 'Commander' }), recipe({ key: 'j', deck_type: 'Jumpstart' })];
    const f: RecipeFilters = { ...decksSearch.parse({}), types: ['all'] };
    expect(optionCounts(rs, f).types.map((t) => t.value).sort()).toEqual(['Commander', 'Jumpstart']);
  });
  it('old kinds= links keep every deck type', () => {
    expect(legacyDecksSearch({ kinds: ['import'] })).toEqual({ origins: ['import'], types: ['all'] });
    expect(legacyDecksSearch({ kinds: 'jumpstart' })).toEqual({ types: ['Jumpstart'] });
    expect(legacyDecksSearch({ kinds: ['custom'], source: ['precon'] })).toEqual({ origins: ['precon'], types: ['all'] });
    expect(legacyDecksSearch({ kinds: [] })).toEqual({});
    expect(legacyDecksSearch({ kinds: ['precon', 'jumpstart'] })).toEqual({ origins: ['precon'], types: ['all'] });
    expect(legacyDecksSearch({ kinds: ['import', 'jumpstart'] })).toEqual({ origins: ['import', 'precon'], types: ['all'] });
  });
  it('a Jumpstart-only set stays pickable under the Commander default', () => {
    const two = [recipe({ set_code: 'fic', deck_type: 'Commander' }), recipe({ key: 'j', set_code: 'j25', deck_type: 'Jumpstart' })];
    const f: RecipeFilters = { ...decksSearch.parse({}), status: ['built', 'buildable', 'unbuilt'] };
    expect(optionCounts(two, f).sets.map((x) => x.value).sort()).toEqual(['fic', 'j25']);
    expect(effectiveTypes({ types: ['Commander', 'Planeswalker'], sets: [] })).toEqual(['Commander', 'Planeswalker']);
    expect(effectiveTypes({ types: ['Commander', 'Planeswalker'], sets: ['fic'] })).toEqual(['Commander', 'Planeswalker']);
    expect(typesToSearch([])).toEqual(['all']);
    expect(typesToSearch(['Commander'])).toEqual(['Commander']);
    expect(filterRecipes(rs, { q: '', origins: [], status: ['built', 'buildable', 'unbuilt'], types: [], sets: [] }).map((r) => r.key)).toEqual(['a', 'mine']);
  });
  it('maps the old source= key to origins', () => {
    expect(legacyDecksSearch({ source: ['custom'] })).toEqual({ origins: ['custom'] });
    expect(legacyDecksSearch({ source: ['custom'], origins: ['import'] })).toEqual({ origins: ['import'] });
  });
  it('counts deck types, most decks first then by name', () => {
    expect(deckTypeCounts([{ deck_type: 'Pauper' }, { deck_type: 'Commander' }, { deck_type: 'Brawl' }, { deck_type: 'Commander' }])).toEqual([
      { value: 'Commander', label: 'Commander', count: 2 }, { value: 'Brawl', label: 'Brawl', count: 1 }, { value: 'Pauper', label: 'Pauper', count: 1 },
    ]);
  });
  it('maps old kinds= links to source and the Jumpstart deck type', () => {
    expect(legacyDecksSearch({ kinds: ['precon', 'jumpstart'], q: 'x' })).toEqual({ origins: ['precon'], types: ['all'], q: 'x' });
    expect(legacyDecksSearch({ kinds: ['jumpstart'], types: ['Commander'] })).toEqual({ types: ['Commander', 'Jumpstart'] });
    expect(legacyDecksSearch({ kinds: ['custom', 'import'] })).toEqual({ origins: ['custom', 'import'], types: ['all'] });
    expect(legacyDecksSearch({ q: 'x' })).toEqual({ q: 'x' });
    expect(decksSearch.parse(legacyDecksSearch({ kinds: ['jumpstart'] }))).toMatchObject({ origins: [], types: ['Jumpstart'] });
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
  it('card facts: in-deck count, pledged, unused, missing when unowned', () => {
    const g = fromDeckCard(card({ count: 2, pledged_here: 1, free: 3, finish: 'foil', p: { owned: { foil: 4 } } }));
    expect(g.tags.slice(0, 2)).toEqual(['×2 in deck', '1 pledged']);
    expect(g.note).toBe('3 unused');
    expect(g.price).toBe(2);
    expect(g.missing).toBe(false);
    expect(fromDeckCard(card()).missing).toBe(true);
  });
  it('catalog recipe cards: missing and noted by unused copies', () => {
    expect([fromDeckCard(card({ count: 2, free: 2 }), true).missing, fromDeckCard(card({ count: 2, free: 2 }), true).note]).toEqual([false, '2 unused']);
    expect(fromDeckCard(card({ count: 2, free: 1 }), true).note).toBe('1 of 2 unused');
    expect(fromDeckCard(card({ count: 1, free: 0 }), true)).toMatchObject({ missing: true, note: 'None unused' });
  });
  it('review lines: exact printings, tokens out, marked subset, either → nonfoil', () => {
    const cs = [card({ count: 3, finish: 'either' }), card({ board: 'token', p: { scryfall_id: 't' } }), card({ p: { scryfall_id: 'q' } })];
    const all = deckReviewLines(cs);
    expect(all.map((l) => [l.chosen, l.qty, l.finish, l.status])).toEqual([['p', 3, 'nonfoil', 'exact'], ['q', 1, 'nonfoil', 'exact']]);
    expect(deckReviewLines(cs, new Set([fromDeckCard(cs[2]).key])).map((l) => l.chosen)).toEqual(['q']);
  });
});

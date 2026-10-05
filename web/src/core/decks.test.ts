import { describe, expect, it } from 'vitest';
import type { DeckCardOut, DeckSummaryOut, PrintingOut } from './api';
import { DECK_SECTIONS, deckGuideGroups, deckReviewLines, deckSection, deckTypeCounts, filterDecks, fromDeckCard, groupDecks } from './decks';

const deck = (o: Partial<DeckSummaryOut>): DeckSummaryOut => ({
  slug: 's', name: 'Deck', format: 'commander', deck_type: 'Commander', state: 'built', built: 1, slugs: ['s'], origin: 'precon', source: 'Commander Deck', author: null,
  set_code: 'fic', set_name: 'Final Fantasy Commander', released: '2025-06-13', cards: 100, value_usd: 50, pledged_pct: 100, image_uri: null, ...o,
});
const printing = (o: Partial<PrintingOut> = {}): PrintingOut => ({
  scryfall_id: 'p', oracle_id: 'o', name: 'Card', set_code: 'fic', set_name: null, collector_number: '1', rarity: 'rare',
  finishes: ['nonfoil', 'foil'], treatment: '', image_uri: null, price_usd: 1, price_usd_foil: 2, released_at: null, owned: {}, ...o,
});
const card = (o: Partial<DeckCardOut> & { p?: Partial<PrintingOut> } = {}): DeckCardOut => ({
  printing: printing(o.p), board: 'main', finish: 'nonfoil', count: 1, type_line: 'Creature — Moogle', cmc: 2, color_identity: ['W'],
  pledged_here: 0, free: 0, ...o,
});

describe('deck list', () => {
  const ds = [
    deck({ slug: 'a', name: 'Counter Blitz' }),
    deck({ slug: 'b', name: 'Goblins', state: 'deconstructed', built: 0, set_code: 'blb', set_name: 'Bloomburrow', released: '2024-08-02', format: 'jumpstart', deck_type: 'Jumpstart', origin: 'precon' }),
    deck({ slug: 'c', name: 'Mine', origin: 'custom', set_code: null, set_name: null, released: null, source: null, author: 'me' }),
  ];
  it('filters by built and free text (name, set, author)', () => {
    expect(filterDecks(ds, { q: '', builtOnly: true }).map((d) => d.slug)).toEqual(['a', 'c']);
    expect(filterDecks(ds, { q: 'bloom' }).map((d) => d.slug)).toEqual(['b']);
    expect(filterDecks(ds, { q: 'me', builtOnly: true }).map((d) => d.slug)).toEqual(['c']);
    expect(filterDecks(ds, { q: '', types: ['Jumpstart'] }).map((d) => d.slug)).toEqual(['b']);
    expect(deckTypeCounts(ds)).toEqual([{ value: 'Commander', label: 'Commander', count: 2 }, { value: 'Jumpstart', label: 'Jumpstart', count: 1 }]);
  });
  it('groups newest set/year first, unknowns last', () => {
    expect(groupDecks(ds, 'set').map((g) => g.label)).toEqual(['Final Fantasy Commander', 'Bloomburrow', 'No set']);
    expect(groupDecks(ds, 'year').map((g) => g.label)).toEqual(['2025', '2024', 'Undated']);
    expect(groupDecks(ds, 'state').map((g) => g.label)).toEqual(['Built', 'Not built']);
    expect(groupDecks(ds, 'type').map((g) => g.label)).toEqual(['Commander', 'Jumpstart']);
    expect(groupDecks(ds, 'origin').map((g) => g.label)).toEqual(['Preconstructed', 'Built by hand']);
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
  it('review lines: exact printings, tokens out, marked subset, either → nonfoil', () => {
    const cs = [card({ count: 3, finish: 'either' }), card({ board: 'token', p: { scryfall_id: 't' } }), card({ p: { scryfall_id: 'q' } })];
    const all = deckReviewLines(cs);
    expect(all.map((l) => [l.chosen, l.qty, l.finish, l.status])).toEqual([['p', 3, 'nonfoil', 'exact'], ['q', 1, 'nonfoil', 'exact']]);
    expect(deckReviewLines(cs, new Set([fromDeckCard(cs[2]).key])).map((l) => l.chosen)).toEqual(['q']);
  });
});

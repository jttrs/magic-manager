import { describe, expect, it } from 'vitest';
import type { CompareCardOut, FunctionRootOut } from './api';
import { compareSections, hasFunctionData, NO_FUNCTION } from './groupBy';
import { compareSearch } from './search';

const cmp = (o: Partial<CompareCardOut>): CompareCardOut => ({
  name: 'X', oracle_id: 'o', slug: 'x', bucket: 'a_only', tags: [], a_pct: null, b_pct: null,
  a_decks: null, b_decks: null, delta: null, synergy_a: null, synergy_b: null, trend_a: null,
  trend_b: null, type_line: null, cmc: null, mana_cost: null, color_identity: null, rarity: null,
  lowest_usd: null, lowest_usd_foil: null, scryfall_id: null, image_uri: null, set_code: null,
  collector_number: null, scryfall_url: null, functions: [], oracle_tags: [], ...o,
});
const roots: FunctionRootOut[] = [
  { key: 'ramp', label: 'Ramp' }, { key: 'removal', label: 'Removal' },
  { key: 'board-wipe', label: 'Board wipe' }, { key: 'lifegain', label: 'Lifegain' },
];

const cards = [
  cmp({ name: 'Wrath', oracle_id: 'w', type_line: 'Sorcery', functions: ['removal', 'board-wipe'] }),
  cmp({ name: 'Sol Ring', oracle_id: 's', type_line: 'Artifact', functions: ['ramp'],
    oracle_tags: [{ id: 't1', slug: 'mana-rock', label: 'mana rock' }] }),
  cmp({ name: 'Bear', oracle_id: 'b', type_line: 'Creature — Bear' }),
  cmp({ name: 'Swords', oracle_id: 'p', type_line: 'Instant', functions: ['removal', 'lifegain'] }),
];

describe('compareSections', () => {
  it('lists mode keeps the EDHREC type groups', () => {
    expect(compareSections(cards, 'lists', roots).map((g) => g.key)).toEqual(['Creatures', 'Instants', 'Sorceries', 'Artifacts']);
  });

  it('function mode orders groups by root config, untagged last', () => {
    const g = compareSections(cards, 'function', roots);
    expect(g.map((x) => x.key)).toEqual(['ramp', 'removal', 'board-wipe', 'lifegain', NO_FUNCTION]);
    expect(g.map((x) => x.label)).toEqual(['Ramp', 'Removal', 'Board wipe', 'Lifegain', 'No tagged function']);
  });

  it('a multi-function card appears under each function with an also-note, input order preserved', () => {
    const g = Object.fromEntries(compareSections(cards, 'function', roots).map((x) => [x.key, x.items]));
    expect(g.removal.map((c) => c.name)).toEqual(['Wrath', 'Swords']);
    expect(g.removal[0].note).toBe('also: Board wipe');
    expect(g['board-wipe'][0].note).toBe('also: Removal');
    expect(g.lifegain[0].note).toBe('also: Removal');
    expect(g.ramp[0].note).toBeNull();
    expect(g[NO_FUNCTION].map((c) => c.name)).toEqual(['Bear']);
    // same selection key across groups so marking is per card, not per appearance
    expect(g.removal[0].key).toBe(g['board-wipe'][0].key);
  });

  it('maps function keys and tags to display labels on the guide card', () => {
    const sol = compareSections(cards, 'function', roots)[0].items[0];
    expect(sol.functions).toEqual(['Ramp']);
    expect(sol.oracleTags).toEqual(['mana rock']);
  });

  it('detects whether tags were synced', () => {
    expect(hasFunctionData(cards)).toBe(true);
    expect(hasFunctionData([cmp({})])).toBe(false);
  });
});

describe('compareSearch.groupBy', () => {
  it('defaults to lists and rejects junk', () => {
    expect(compareSearch.parse({}).groupBy).toBe('lists');
    expect(compareSearch.parse({ groupBy: 'function' }).groupBy).toBe('function');
    expect(compareSearch.parse({ groupBy: 'nope' }).groupBy).toBe('lists');
  });
});

describe('collection function filter', () => {
  it('keeps cards in any chosen function; _none matches untagged', async () => {
    const { filterCollection, functionCounts, NO_FUNCTION: NONE } = await import('./collection');
    const card = (id: string, functions: string[]) => ({
      scryfall_id: id, oracle_id: id, name: id, family: 'f', set_code: 'f', collector_number: '1', rarity: 'rare',
      type_line: null, cmc: null, color_identity: [], released_at: null, finishes: ['nonfoil'], owned: {}, pledged: {},
      price_usd: null, price_usd_foil: null, image_uri: null, scryfall_url: null, treatment: '', standard_frame: true,
      is_bulk: false, is_chase: false, functions,
    });
    const cards = [card('a', ['ramp', 'removal']), card('b', ['draw']), card('c', [])];
    const base = { show: ['owned', 'missing'] as const, exclude: [], q: '' };
    const ids = (fn: string[]) => filterCollection(cards, { ...base, show: [...base.show], fn }).map((c) => c.scryfall_id);
    expect(ids([])).toEqual(['a', 'b', 'c']);
    expect(ids(['removal'])).toEqual(['a']);
    expect(ids(['draw', NONE])).toEqual(['b', 'c']);
    expect(Object.fromEntries(functionCounts(cards))).toEqual({ ramp: 1, removal: 1, draw: 1, [NONE]: 1 });
  });
});

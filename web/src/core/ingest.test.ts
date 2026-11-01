import { describe, expect, it } from 'vitest';
import type { PrintingOut, ResolvedLineOut } from './api';
import { commitItems, deckFacts, fitFinish, fromResolved, productOwned, readDeckQuery, reviewStats, sourceLine, stagePrinting, updateLine } from './ingest';

const p = (o: Partial<PrintingOut>): PrintingOut => ({
  scryfall_id: 'p1', oracle_id: 'o', name: 'Sol Ring', set_code: 'cmm', set_name: 'Commander Masters',
  collector_number: '1', rarity: 'uncommon', finishes: ['nonfoil', 'foil'], treatment: '', image_uri: null,
  price_usd: 1, price_usd_foil: 2, released_at: '2023-08-04', owned: {}, ...o,
});
const line = (o: Partial<ResolvedLineOut>): ResolvedLineOut => ({
  line: 1, raw: '1 Sol Ring', qty: 1, name: 'Sol Ring', finish: 'nonfoil', section: 'mainboard',
  status: 'exact', candidates: [p({})], chosen: 'p1', note: null, ...o,
});

describe('add-cards review model', () => {
  it('fits a finish to the printing', () => {
    expect(fitFinish(p({ finishes: ['foil'] }), 'nonfoil')).toBe('foil');
    expect(fitFinish(p({}), 'foil')).toBe('foil');
    expect(fitFinish(undefined, 'foil')).toBe('foil');
  });
  it('unresolved lines start excluded and never commit', () => {
    const ls = fromResolved([line({}), line({ status: 'unresolved', candidates: [], chosen: null })]);
    expect(ls[1].include).toBe(false);
    expect(commitItems(ls)).toEqual([{ scryfall_id: 'p1', finish: 'nonfoil', qty: 1 }]);
    expect(reviewStats(ls)).toMatchObject({ copies: 1, unresolved: 1 });
  });
  it('switching printing re-fits the finish; qty clamps', () => {
    const ls = fromResolved([line({ status: 'ambiguous', finish: 'foil', candidates: [p({}), p({ scryfall_id: 'p2', finishes: ['nonfoil'] })] })]);
    const next = updateLine(ls, ls[0].key, { chosen: 'p2' });
    expect(next[0].finish).toBe('nonfoil');
    expect(updateLine(next, ls[0].key, { qty: 0 })[0].qty).toBe(1);
  });
  it('search staging bumps the same printing; commit merges duplicates', () => {
    let ls = stagePrinting([], p({}));
    ls = stagePrinting(ls, p({}));
    ls = stagePrinting(ls, p({}), 'foil');
    expect(ls.map((l) => [l.finish, l.qty])).toEqual([['nonfoil', 2], ['foil', 1]]);
    const dup = [...fromResolved([line({ qty: 2 })]), ...fromResolved([line({ qty: 3 })], 'b')];
    expect(commitItems(dup)).toEqual([{ scryfall_id: 'p1', finish: 'nonfoil', qty: 5 }]);
  });
});

describe('sourceLine', () => {
  const l = (raw: string, name: string, note: string | null = null, status: 'exact' | 'ambiguous' | 'unresolved' = 'exact') => ({ raw, name, note, status });
  it('drops a source line that only repeats count, name, set and number', () => {
    expect(sourceLine(l('1 Insist', 'Insist'))).toBeNull();
    expect(sourceLine(l('4x Lightning Bolt (M10) 146', 'Lightning Bolt'))).toBeNull();
    expect(sourceLine(l('1 Sol Ring [CMM] 410 *F*', 'Sol Ring'))).toBeNull();
    expect(sourceLine(l('1 Fable of the Mirror-Breaker', 'Fable of the Mirror-Breaker // Reflection of Kiki-Jiki'))).toBeNull();
    expect(sourceLine(l('1 insist', 'Insist'))).toBeNull();
  });
  it('keeps what adds information: notes, misspellings, flavor names, search set names', () => {
    expect(sourceLine(l('1 Notacard', 'Notacard', "No card named 'Notacard'"))).toBe("No card named 'Notacard'");
    expect(sourceLine(l('1 Lightnig Bolt', 'Lightning Bolt'))).toBe('1 Lightnig Bolt');
    expect(sourceLine(l('Commander Masters', 'Sol Ring'))).toBe('Commander Masters');
    expect(sourceLine(l('1 Sol Ring (XYZ) 999', 'Sol Ring', null, 'ambiguous'))).toBe('1 Sol Ring (XYZ) 999');
    expect(sourceLine(l('1 Sol Ring', 'Sol Ring', null, 'ambiguous'))).toBeNull();
  });
});

describe('add decklist or product: one field', () => {
  it('a supported deck link is a deck; other links are not; text searches', () => {
    expect(readDeckQuery(' https://archidekt.com/decks/123 ')).toEqual({ kind: 'deck', url: 'https://archidekt.com/decks/123', site: 'Archidekt' });
    expect(readDeckQuery('www.moxfield.com/decks/AbCd1234')).toEqual({ kind: 'deck', url: 'https://www.moxfield.com/decks/AbCd1234', site: 'Moxfield' });
    expect(readDeckQuery('https://example.com/decks/1')).toEqual({ kind: 'link' });
    expect(readDeckQuery('Final Fantasy')).toEqual({ kind: 'search', q: 'Final Fantasy' });
    expect(readDeckQuery('fic')).toEqual({ kind: 'search', q: 'fic' });
    expect(readDeckQuery('')).toEqual({ kind: 'search', q: '' });
  });
  it('ownership hint drops zeros and says broken down, never loose', () => {
    expect(productOwned(0, 0)).toBeNull();
    expect(productOwned(1, 0)).toBe('you own 1 built');
    expect(productOwned(1, 2)).toBe('you own 1 built · 2 broken down');
    expect(productOwned(0, 3)).toBe('you own 3 broken down');
  });
  it('a read deck says how many cards, whose, and where from', () => {
    const r = { lines: [line({ qty: 99 }), line({ qty: 1 })], deck: { source: 'moxfield', id: 'x', name: 'G', author: 'goblinfan', cards: [] } };
    expect(deckFacts(r, 'Moxfield')).toBe('100 cards · by goblinfan · Moxfield');
    expect(deckFacts({ lines: [line({})], deck: null }, 'Scryfall')).toBe('1 card · Scryfall');
  });
});

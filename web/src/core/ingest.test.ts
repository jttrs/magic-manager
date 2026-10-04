import { describe, expect, it } from 'vitest';
import type { PrintingOut, ResolvedLineOut } from './api';
import { commitItems, fitFinish, fromResolved, reviewStats, stagePrinting, updateLine } from './ingest';

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

import { describe, expect, it } from 'vitest';
import type { ProductCostOut, SldDropOut } from './api';
import { marketSearch } from './search';
import { fmtDay } from './format';
import { basisColumn, dropBase, filterSortDrops, oldestPricesAt, splitBonus, sldGap, sldKey, sldRows, watchKey, type SldFilters } from './secretLair';

const cost = (p: Partial<ProductCostOut>): ProductCostOut => ({ kind: 'sld', set_code: 'sld', name: 'x', ...p }) as ProductCostOut;

const drops: SldDropOut[] = [
  { name: 'Both', release_date: '2026-09-01', editions: [{ finish: 'nonfoil', sealed_name: 'SLD Both', tcgplayer_url: 'https://t/1' }, { finish: 'foil', sealed_name: 'SLD Both Foil', tcgplayer_url: null }] },
  { name: 'Foil only', release_date: '2026-08-01', editions: [{ finish: 'foil', sealed_name: null, tcgplayer_url: null }] },
  { name: 'Alpha', release_date: '2026-07-01', editions: [{ finish: 'nonfoil' }] },
];

describe('secret lair view-model', () => {
  it('picks the chosen edition, else the only one', () => {
    const rows = sldRows(drops, 'nonfoil');
    expect(rows.map((r) => [r.name, r.finish, r.otherEdition])).toEqual([['Both', 'nonfoil', false], ['Foil only', 'foil', true], ['Alpha', 'nonfoil', false]]);
    expect(rows[0].tcgplayer_url).toBe('https://t/1');
    expect(sldRows(drops, 'foil')[0].key).toBe(sldKey('Both', 'foil'));
  });

  it('a foil-only drop matches its watched entry, which comes back without the suffix', () => {
    expect(dropBase('Alien Auroras Galaxy Foil Edition')).toBe('Alien Auroras Galaxy');
    expect(dropBase('Foil Edition Fans')).toBe('Foil Edition Fans');
    expect(watchKey('Alien Auroras Galaxy Foil Edition', 'foil')).toBe(watchKey('Alien Auroras Galaxy', 'foil'));
    expect(watchKey('Both', 'foil')).not.toBe(watchKey('Both', 'nonfoil'));
  });

  it('gap is sealed minus cards, negative when sealed is cheaper', () => {
    expect(sldGap(cost({ market: 40, exact: 50, floor: 20 }), 'exact')).toEqual({ usd: -10, pct: -20 });
    expect(sldGap(cost({ market: 40, exact: 50, floor: 20 }), 'floor')).toEqual({ usd: 20, pct: 100 });
    expect(sldGap(cost({ market: null, exact: 50 }), 'exact')).toBeNull();
    expect(sldGap(cost({ market: 40, exact: 0 }), 'exact')).toBeNull();
    expect(sldGap(undefined, 'exact')).toBeNull();
  });

  it('filters by name and discount, sorts with unpriced last', () => {
    const rows = sldRows(drops, 'nonfoil');
    const costs = new Map<string, ProductCostOut | undefined>([
      [rows[0].key, cost({ market: 30, exact: 60 })], // −50%
      [rows[1].key, cost({ market: 55, exact: 50 })], // +10%
      [rows[2].key, cost({ market: null, exact: 10 })],
    ]);
    const o: SldFilters = { q: '', minOff: 0, basis: 'exact', sort: 'gap_pct' };
    expect(filterSortDrops(rows, costs, o).map((r) => r.name)).toEqual(['Both', 'Foil only', 'Alpha']);
    expect(filterSortDrops(rows, costs, { ...o, minOff: 20 }).map((r) => r.name)).toEqual(['Both']);
    expect(filterSortDrops(rows, costs, { ...o, q: 'alp' }).map((r) => r.name)).toEqual(['Alpha']);
    expect(filterSortDrops(rows, costs, { ...o, sort: 'price' }).map((r) => r.name)).toEqual(['Both', 'Foil only', 'Alpha']);
    expect(filterSortDrops(rows, costs, { ...o, sort: 'release' }).map((r) => r.name)).toEqual(['Both', 'Foil only', 'Alpha']);
    expect(filterSortDrops(rows, costs, { ...o, sort: 'name' }).map((r) => r.name)).toEqual(['Alpha', 'Both', 'Foil only']);
  });

  it('URL state defaults and rejects junk', () => {
    const s = marketSearch.parse({ subject: 'sld' });
    expect([s.subject, s.edition, s.sldN, s.sbasis, s.ssort]).toEqual(['sld', 'nonfoil', 30, 'exact', 'gap_pct']);
    const bad = marketSearch.parse({ subject: 'sld', edition: 'etched', sldN: 9999, ssort: 'x' });
    expect([bad.edition, bad.sldN, bad.ssort]).toEqual(['nonfoil', 30, 'gap_pct']);
  });
});

describe('secret lair columns + freshness', () => {
  it('marks a value column only when the gap is measured against one', () => {
    expect(basisColumn('exact')).toBe('exact');
    expect(basisColumn('floor')).toBe('floor');
    expect(basisColumn('market')).toBeNull();
  });

  it('finds the oldest prices_at', () => {
    expect(oldestPricesAt([cost({ prices_at: '2026-11-14T08:00:00' }), undefined, cost({ prices_at: '2026-11-12T08:00:00' }), cost({})])).toBe('2026-11-12T08:00:00');
    expect(oldestPricesAt([cost({})])).toBeNull();
  });

  it('splits bonus lines apart from the guaranteed cards', () => {
    const l = (name: string, bonus: 'named' | 'possible' | null) => ({ name, bonus }) as never;
    const s = splitBonus([l('A', null), l('B', 'named'), l('C', 'possible')]);
    expect([s.cards.length, s.named.length, s.possible.length]).toEqual([1, 1, 1]);
    expect(splitBonus(undefined).cards).toEqual([]);
  });

  it('formats the stamped day', () => {
    expect(fmtDay('2026-11-12T23:30:00')).toBe(fmtDay('2026-11-12'));
    expect(fmtDay(null)).toBe('—');
  });
});

import { describe, expect, it } from 'vitest';
import type { ProductCostOut } from './api';
import { filterSortProducts, inStockBest, newlyMetFrom, targetMet, targetPriceOf, targetText, type DealFilters, type DealProduct, type Offer } from './deals';
import { historyChart } from './priceHistory';

const offer = (o: Partial<Offer>): Offer => ({ url: 'https://a.example/x', store: 'A', price: 80, available: true, ...o });
const prod = (o: Partial<DealProduct>): DealProduct => {
  const offers = o.offers ?? [offer({})];
  return { key: 'k', kind: 'sealed', set_code: 'c18', name: 'Deck', finish: null, category: 'deck', type: 'deck', offers, best: offers[0] ?? null, watching: true, productId: 1, target: null, targetPrice: null, ...o };
};
const cost = (market: number | null) => ({ market }) as ProductCostOut;
const T = (mode: 'price' | 'pct_under', value: number) => ({ mode, value, set_at: '2026-10-01' });

describe('price targets', () => {
  it('uses the server price, else works out a % target from the sealed price', () => {
    expect(targetPriceOf(prod({ target: T('price', 70), targetPrice: 70 }), undefined)).toBe(70);
    expect(targetPriceOf(prod({ target: T('pct_under', 10) }), cost(80))).toBe(72);
    expect(targetPriceOf(prod({ target: T('pct_under', 10) }), undefined)).toBeNull();
    expect(targetPriceOf(prod({}), cost(80))).toBeNull();
  });
  it('is met only by an in-stock price at or under it', () => {
    const offers = [offer({ price: 75 }), offer({ url: 'b', price: 60, available: false })];
    const p = prod({ offers, target: T('price', 75), targetPrice: 75 });
    expect(inStockBest(p)?.price).toBe(75);
    expect(targetMet(p, undefined)).toBe(true);
    expect(targetMet({ ...p, targetPrice: 74.99 }, undefined)).toBe(false);
    expect(targetMet(prod({ offers: [offer({ available: false, price: 1 })], targetPrice: 70, target: T('price', 70) }), undefined)).toBe(false);
    expect(targetMet(prod({}), undefined)).toBeNull();
  });
  it('describes the target the way it was set', () => {
    expect(targetText(T('price', 72), 'sealed')).toBe('$72.00');
    expect(targetText(T('pct_under', 12.5), 'sealed')).toBe('12.5% under the sealed price');
    expect(targetText(T('pct_under', 10), 'single')).toBe('10% under the printing’s price');
  });
  it('filters to products at or under target', () => {
    const f: DealFilters = { q: '', stores: [], types: [], minOff: 0, basis: 'market', sort: 'name', inStock: false, atTarget: true };
    const hit = prod({ key: 'hit', name: 'Hit', target: T('price', 90), targetPrice: 90 });
    const miss = prod({ key: 'miss', name: 'Miss', target: T('price', 50), targetPrice: 50 });
    const none = prod({ key: 'none', name: 'None' });
    expect(filterSortProducts([hit, miss, none], new Map(), f).map((p) => p.key)).toEqual(['hit']);
    expect(filterSortProducts([hit, miss, none], new Map(), { ...f, atTarget: false })).toHaveLength(3);
  });
  it('reads the newly_met artifact', () => {
    const m = { product_id: 1, name: 'Deck', price: 70, store: 'A', url: 'u', target_price: 72 };
    expect(newlyMetFrom([{ label: 'watchlist', data: [] }, { label: 'newly_met', data: [m] }])).toEqual([m]);
    expect(newlyMetFrom(undefined)).toEqual([]);
  });
});

describe('price history chart', () => {
  const a = offer({ store: 'Alpha', url: 'https://a.example/x', price: 70, history: [{ price: 80, at: '2026-10-01T12:00:00Z' }, { price: 70, at: '2026-10-05T12:00:00Z' }] });
  const b = offer({ store: 'Beta', url: 'https://b.example/x', price: 75, history: [{ price: 90, at: '2026-10-03T12:00:00Z' }, { price: 75, at: '2026-10-09T12:00:00Z' }] });

  it('needs two readings', () => {
    expect(historyChart([offer({ history: [{ price: 80, at: '2026-10-01T12:00:00Z' }] })])).toBeNull();
    expect(historyChart([offer({ history: [] })])).toBeNull();
  });
  it('draws a step line per store across the whole time range, cheapest today solid', () => {
    const c = historyChart([a, b], 72)!;
    expect(c.series.map((s) => [s.store, s.style])).toEqual([['Alpha', 0], ['Beta', 1]]);
    const [sa, sb] = c.series;
    expect(sa.points[0].x).toBe(0);
    expect(sb.points[1].x).toBe(100);
    expect(sa.path.endsWith('H100')).toBe(true);           // the latest price holds to the latest reading
    expect(sa.path).toMatch(/^M0 [\d.]+ H50 V[\d.]+ H100$/);
    expect(sa.points[1].y).toBeGreaterThan(sb.points[0].y);  // $70 sits below $90
    expect([sa.first, sa.low, sa.high, sa.now]).toEqual([80, 70, 80, 70]);
  });
  it('fits the target in the axis and lists every reading newest first', () => {
    const c = historyChart([a, b], 60)!;
    expect(c.lo).toBeLessThan(60);
    expect(c.targetY).not.toBeNull();
    expect(c.rows.map((r) => r.price)).toEqual([75, 70, 90, 80]);
    expect(c.summary).toBe('Prices at 2 stores from Oct 1 to Oct 9; lowest $70.00 at Alpha on Oct 5. Target $60.00.');
  });
});

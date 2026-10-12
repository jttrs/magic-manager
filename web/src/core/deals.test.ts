import { describe, expect, it } from 'vitest';
import type { ProductCostOut } from './api';
import { browserReadUrls, MAX_BROWSER_READS, basisValue, deltaLabel, filterSortProducts, gapOf, pagesFresh, pricesFrom, productsFromTabs, productsFromWatched, productType, readAge, sharedErrors, stockLabel, trendLabel, watchlistErrors, type DealFilters, type DealProduct, type PriceRow } from './deals';

type WatchStore = Parameters<typeof trendLabel>[0];

const row = (p: Partial<PriceRow>): PriceRow => ({ url: 'u', vendor: 'v', price: 1, currency: 'USD', available: true, title: 't', signal: 'meta', error: null, candidates: [], note: '', partial: false, ...p });

describe('deals view-model', () => {
  it('keys the job artifact by URL', () => {
    const m = pricesFrom([{ label: 'prices', data: [row({ url: 'a' }), row({ url: 'b', price: 2 })] }]);
    expect(m.get('b')?.price).toBe(2);
    expect(pricesFrom(undefined).size).toBe(0);
  });
  it('lifts repeated and setup errors to one shared note', () => {
    const js = 'Chrome blocks reading open tabs. Turn on … Allow JavaScript from Apple Events …';
    expect(sharedErrors([row({ error: js }), row({ error: 'Tab closed' }), row({ error: 'x' }), row({ error: 'x' })])).toEqual([js, 'x']);
  });
  it('labels stock, blank when the page does not say', () => {
    expect([stockLabel(row({})), stockLabel(row({ available: false })), stockLabel(row({ available: null })), stockLabel(undefined)]).toEqual(['In stock', 'Sold out', '', '']);
  });
  it('labels the gap to market and ranks the best deals', () => {
    expect(deltaLabel(row({ delta: -2.93, pct: -1.9 }))).toEqual({ text: '$2.93 under market (−2%)', tone: 'good' });
    expect(deltaLabel(row({ delta: 6.99, pct: 13.2 }))).toEqual({ text: '$6.99 over market (+13%)', tone: 'bad' });
    expect(deltaLabel(row({ delta: null }))).toBeNull();
    expect(deltaLabel(row({ delta: -0.41, pct: -0.4 }))?.text).toBe('$0.41 under market');
  });

  it('lists the watched open-tab store links for the companion, deduped and capped', () => {
    const store = (url: string, read_in_browser: boolean) => ({ url, read_in_browser }) as unknown as WatchStore;
    const w = (stores: WatchStore[]) => ({ stores }) as unknown as Parameters<typeof browserReadUrls>[0][number];
    expect(browserReadUrls([w([store('https://a/1', true), store('https://shop/2', false)]), w([store('https://a/1', true)])]))
      .toEqual({ urls: ['https://a/1'], skipped: 0 });
    const many = Array.from({ length: MAX_BROWSER_READS + 3 }, (_, i) => store(`https://a/${i}`, true));
    expect(browserReadUrls([w(many)]).skipped).toBe(3);
    expect(browserReadUrls([])).toEqual({ urls: [], skipped: 0 });
  });

  it('reads the watchlist errors artifact', () => {
    expect(watchlistErrors([{ label: 'watchlist', data: [] }, { label: 'errors', data: [row({ error: 'gone' })] }])[0].error).toBe('gone');
    expect(watchlistErrors(undefined)).toEqual([]);
  });
  it('labels a store\'s price trend and how old its reading is', () => {
    const s = (p: Partial<WatchStore>): WatchStore => ({ url: 'u', store: 'S', price: 55, available: true, read_at: '2026-09-10T12:00:00', read: true, first_price: 60, first_at: '2026-09-05T12:00:00', change: -5, history: [{ price: 60, at: 'a' }, { price: 55, at: 'b' }], ...p });
    expect(trendLabel(s({}))).toEqual({ text: '↓ $5.00 since Sep 5', tone: 'good' });
    expect(trendLabel(s({ change: 2 }))?.tone).toBe('bad');
    expect(trendLabel(s({ change: 0 }))?.text).toBe('no change since Sep 5');
    expect(trendLabel(s({ history: [{ price: 60, at: 'a' }] }))).toBeNull();
    const now = new Date('2026-09-14T09:00:00');
    expect(readAge(s({}), now)).toBe('read 4 days ago');
    expect(readAge(s({ read_at: '2026-09-13T23:00:00' }), now)).toBe('read yesterday');
    expect(readAge(s({ read_at: '2026-09-14T01:00:00' }), now)).toBe('read today');
    expect(readAge(s({ read: false }), now)).toBe('saved Sep 10');
    expect(now.getHours()).toBe(9);
  });
});

const m = (name: string, set = 'hob') => ({ kind: 'sealed' as const, set_code: set, name, scryfall_id: null, finish: null, price: null });
const cost = (p: Partial<ProductCostOut>): ProductCostOut => ({ kind: 'sealed', set_code: 'hob', name: 'X', market: 100, exact: 120, floor: 80, ...p });
const prod = (name: string, price: number | null, over: Partial<DealProduct> = {}): DealProduct => {
  const best = price == null ? null : { url: name, store: 'A', price, available: true };
  return { key: name, kind: 'sealed', set_code: 'hob', name, finish: null, category: null, type: 'deck', offers: best ? [best] : [], best, watching: false, ...over };
};
const F: DealFilters = { q: '', stores: [], types: [], minOff: 0, basis: 'market', sort: 'name', inStock: false };

describe('deal products', () => {
  it('maps category to product type', () => {
    expect([productType('sld', null), productType('single', null), productType('sealed', 'deck_box'), productType('sealed', 'booster_case'), productType('sealed', 'bundle'), productType('sealed', 'box_set'), productType('sealed', 'x'), productType('sealed', null)])
      .toEqual(['secret_lair', 'single', 'deck', 'booster', 'bundle', 'box_set', 'other', 'other']);
  });
  it('groups the same product across stores into one product; the rest needs a look', () => {
    const rows = [
      row({ url: 'a', price: 120, kind: 'sealed', status: 'matched', match: m('Box'), watching: true }),
      row({ url: 'b', price: 110, kind: 'sealed', status: 'confirmed', match: m('Box') }),
      row({ url: 'c', price: 90, available: false, kind: 'sealed', status: 'matched', match: m('Box') }),
      row({ url: 'd', kind: 'single', status: 'ambiguous', match: null }),
      row({ url: 'e', kind: 'other_game', status: 'skipped', match: null }),
      row({ url: 'f', kind: 'sealed', status: 'matched', match: m('Box 2'), error: 'boom' }),
    ];
    const { products, needsLook } = productsFromTabs(new Map(rows.map((r) => [r.url, r])), new Map([['a', 'Alpha'], ['b', 'Beta'], ['c', 'Gamma']]));
    expect(products).toHaveLength(1);
    expect(products[0].offers.map((o) => o.store)).toEqual(['Beta', 'Alpha', 'Gamma']);
    expect(products[0].best?.price).toBe(110);
    expect(products[0].watching).toBe(true);
    expect(needsLook.map((r) => r.url)).toEqual(['d', 'e', 'f']);
  });
  it('builds watched products with age, trend and errors', () => {
    const st = { url: 'u', store: 'S', price: 55, available: true, read_at: '2026-09-10T12:00:00', read: true, first_price: 60, first_at: '2026-09-05T12:00:00', change: -5, history: [{ price: 60, at: 'a' }, { price: 55, at: 'b' }] };
    const [p] = productsFromWatched([{ product_id: 1, set_code: 'c13', name: 'N', kind: 'sealed', category: 'deck', release_date: null, best_price: 55, best_store: 'S', best_url: 'u', stores: [st, { ...st, url: 'v', price: null }] }], [row({ url: 'v', error: 'bad' })]);
    expect(p.type).toBe('deck');
    expect(p.watching).toBe(true);
    expect(p.best?.price).toBe(55);
    expect(p.offers[1].error).toBe('bad');
    expect(p.offers[0].trend?.tone).toBe('good');
  });
  it('computes the gap against each basis, singles included', () => {
    const p = prod('A', 80);
    const c = cost({});
    expect(gapOf(p, c, 'market')).toEqual({ usd: -20, pct: -20 });
    expect(gapOf(p, c, 'exact')?.pct).toBeCloseTo(-33.33, 1);
    expect(gapOf(p, c, 'floor')).toEqual({ usd: 0, pct: 0 });
    expect(gapOf(p, undefined, 'market')).toBeNull();
    expect(gapOf(prod('B', null), c, 'market')).toBeNull();
    expect(gapOf(p, cost({ market: 0 }), 'market')).toBeNull();
    const s = prod('S', 8, { kind: 'single', singleMarket: 10 });
    expect(basisValue(s, undefined, 'market')).toBe(10);
    expect(gapOf(s, undefined, 'exact')?.pct).toBeCloseTo(-20);
    expect(gapOf(s, undefined, 'floor')).toBeNull();
  });
  it('filters by name or set, store, type, discount and stock', () => {
    const a = prod('Alpha Box', 80, { offers: [{ url: 'a', store: 'X', price: 80, available: true }], best: { url: 'a', store: 'X', price: 80, available: true } });
    const b = prod('Beta Deck', 100, { set_code: 'zzz', type: 'bundle', offers: [{ url: 'b', store: 'Y', price: 100, available: false }], best: { url: 'b', store: 'Y', price: 100, available: false } });
    const c = prod('Gamma', null, { type: 'single' });
    const costs = new Map([['Alpha Box', cost({})], ['Beta Deck', cost({})]]);
    const run = (o: Partial<DealFilters>) => filterSortProducts([a, b, c], costs, { ...F, ...o }).map((p) => p.name);
    expect(run({})).toEqual(['Alpha Box', 'Beta Deck', 'Gamma']);
    expect(run({ q: 'ZZZ' })).toEqual(['Beta Deck']);
    expect(run({ q: 'alpha' })).toEqual(['Alpha Box']);
    expect(run({ stores: ['Y'] })).toEqual(['Beta Deck']);
    expect(run({ types: ['single', 'bundle'] })).toEqual(['Beta Deck', 'Gamma']);
    expect(run({ minOff: 20 })).toEqual(['Alpha Box']);
    expect(run({ minOff: 30 })).toEqual([]);
    expect(run({ inStock: true })).toEqual(['Alpha Box']);
  });
  it('sorts with unknowns last and ties by name', () => {
    const a = prod('A', 80), b = prod('B', 50), c = prod('C', 90), d = prod('D', null);
    const costs = new Map([['A', cost({ market: 100, exact: 200, floor: 50 })], ['B', cost({ market: 100, exact: 100, floor: 60 })], ['C', cost({ market: 100, exact: 90, floor: 70 })]]);
    const run = (sort: DealFilters['sort']) => filterSortProducts([d, c, b, a], costs, { ...F, sort }).map((p) => p.name);
    expect(run('gap_pct')).toEqual(['B', 'A', 'C', 'D']);
    expect(run('gap_usd')).toEqual(['B', 'A', 'C', 'D']);
    expect(run('price')).toEqual(['B', 'A', 'C', 'D']);
    expect(run('market')).toEqual(['A', 'B', 'C', 'D']);
    expect(run('exact')).toEqual(['A', 'B', 'C', 'D']);
    expect(run('floor')).toEqual(['C', 'B', 'A', 'D']);
    expect(run('name')).toEqual(['A', 'B', 'C', 'D']);
  });
});

describe('pagesFresh', () => {
  it('trusts a reading for two minutes, never a missing or future one', () => {
    const now = 1_000_000;
    expect(pagesFresh(now - 119_000, now)).toBe(true);
    expect(pagesFresh(now - 120_000, now)).toBe(true);
    expect(pagesFresh(now - 121_000, now)).toBe(false);
    expect(pagesFresh(null, now)).toBe(false);
    expect(pagesFresh(undefined, now)).toBe(false);
    expect(pagesFresh(now + 5_000, now)).toBe(false);
  });
});

import { describe, expect, it } from 'vitest';
import { bestDeals, canWatch, deltaLabel, pricesFrom, readAge, sharedErrors, stockLabel, trendLabel, watchlistFrom, type PriceRow, type WatchStore } from './deals';

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
    const rows = [row({ url: 'a', delta: -1, pct: -5 }), row({ url: 'b', delta: -9, pct: -30 }), row({ url: 'c', delta: 3, pct: 4 }), row({ url: 'd', delta: -5, pct: -40, available: false })];
    expect(bestDeals(rows).map((r) => r.url)).toEqual(['b', 'a']);
  });

  it('watches matched sealed products and Secret Lair drops, not singles or unknowns', () => {
    const m = { kind: 'sealed' as const, set_code: 'hob', name: 'X', scryfall_id: null, finish: null, price: null };
    expect(canWatch(row({ kind: 'sealed', status: 'matched', match: m }))).toBe(true);
    expect(canWatch(row({ kind: 'sld', status: 'confirmed', match: { ...m, kind: 'sld' } }))).toBe(true);
    expect(canWatch(row({ kind: 'single', status: 'matched', match: { ...m, kind: 'single' } }))).toBe(false);
    expect(canWatch(row({ kind: 'sealed', status: 'ambiguous', match: null }))).toBe(false);
  });
  it('reads the watchlist artifacts', () => {
    const w = watchlistFrom([{ label: 'watchlist', data: [{ name: 'A' }] }, { label: 'errors', data: [row({ error: 'gone' })] }]);
    expect(w.watched.map((x) => x.name)).toEqual(['A']);
    expect(w.errors[0].error).toBe('gone');
    expect(watchlistFrom(undefined)).toEqual({ watched: [], errors: [] });
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

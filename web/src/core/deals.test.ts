import { describe, expect, it } from 'vitest';
import { bestDeals, deltaLabel, pricesFrom, sharedErrors, stockLabel, type PriceRow } from './deals';

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
});

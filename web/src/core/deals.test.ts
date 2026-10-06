import { describe, expect, it } from 'vitest';
import { pricesFrom, sharedErrors, stockLabel, type PriceRow } from './deals';

const row = (p: Partial<PriceRow>): PriceRow => ({ url: 'u', vendor: 'v', price: 1, currency: 'USD', available: true, title: 't', signal: 'meta', error: null, ...p });

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
});

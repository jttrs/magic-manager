import { describe, expect, it } from 'vitest';
import type { PurchaseOut, ReviewLineOut } from './api';
import { chunk, clampDecision, decisionsBody, decisionTotals, defaultDecisions, listStatus, STATUS_LABEL, subtotalGap, valuation } from './purchases';

const line = (o: Partial<ReviewLineOut>): ReviewLineOut => ({
  line_no: 1, kind: 'single', name: 'Sol Ring', set_name: 'Commander', condition: 'NM', finish: 'nonfoil',
  printing: { scryfall_id: 'x' } as ReviewLineOut['printing'], quantity: 3, unit_usd: 2, today_usd: 3,
  matched: 0, added: 0, remaining: 3, owned: 2, matchable: 2, ...o,
});
const purchase = (o: Partial<PurchaseOut>): PurchaseOut => ({
  purchase_id: 1, store: 'manapool', store_name: 'Mana Pool', order_id: 'A1', ordered_at: '2026-01-01', read_at: '2026-01-02',
  lines: 1, copies: 1, assigned: 0, assignable: 1, unresolved: 0, status: 'new', paid_usd: 10, worth_usd: 12, compared_paid_usd: 10, gain_usd: 2, ...o,
});

describe('purchases view-model', () => {
  it('labels statuses in plain words', () => {
    expect(STATUS_LABEL).toEqual({ new: 'Not added yet', partial: 'Partly added', done: 'In your collection', nothing: 'Recorded only' });
  });

  it('listStatus matches store + order id, else unread', () => {
    const ps = [purchase({ status: 'partial' })];
    expect(listStatus('A1', 'manapool', ps)).toBe('partial');
    expect(listStatus('A1', 'tcgplayer', ps)).toBe('unread');
    expect(listStatus('B2', 'manapool', ps)).toBe('unread');
  });

  it('defaultDecisions: match mode pairs with owned copies, add mode brings everything in; skips unassignable lines', () => {
    const lines = [line({}), line({ line_no: 2, kind: 'sealed' }), line({ line_no: 3, printing: null }), line({ line_no: 4, remaining: 0 }), line({ line_no: 5, matchable: 9, remaining: 4 })];
    expect(defaultDecisions(lines, 'match')).toEqual({ 1: { match: 2, add: 0 }, 5: { match: 4, add: 0 } });
    expect(defaultDecisions(lines, 'add')).toEqual({ 1: { match: 0, add: 3 }, 5: { match: 0, add: 4 } });
  });

  it('clampDecision keeps match ≤ min(remaining, matchable) and add ≤ what is left', () => {
    const l = line({});
    expect(clampDecision(l, { match: 5, add: 5 })).toEqual({ match: 2, add: 1 });
    expect(clampDecision(l, { match: -1, add: 9 })).toEqual({ match: 0, add: 3 });
    expect(clampDecision(l, { match: Number.NaN, add: 1.9 })).toEqual({ match: 0, add: 1 });
  });

  it('decisionsBody drops zero rows; decisionTotals sums copies and what was paid', () => {
    const lines = [line({}), line({ line_no: 2, unit_usd: 1.5 })];
    const d = { 1: { match: 2, add: 1 }, 2: { match: 0, add: 0 } };
    expect(decisionsBody(d)).toEqual([{ line_no: 1, match: 2, add: 1 }]);
    expect(decisionTotals(lines, d)).toEqual({ matched: 2, added: 1, paid: 6 });
  });

  it('chunk splits into batches', () => {
    expect(chunk([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]]);
    expect(chunk([], 100)).toEqual([]);
  });

  it('subtotalGap: null when equal (within a cent) or unknown, else paid − subtotal', () => {
    expect(subtotalGap(purchase({ paid_usd: 3305.32, subtotal_usd: 3189.82 }))).toBe(115.5);
    expect(subtotalGap(purchase({ paid_usd: 10, subtotal_usd: 10.004 }))).toBeNull();
    expect(subtotalGap(purchase({ paid_usd: 10, subtotal_usd: null }))).toBeNull();
    expect(subtotalGap(purchase({ paid_usd: 10 }))).toBeNull();
  });
});

describe('valuation', () => {
  const v = (paid_usd: number, compared_paid_usd: number) => valuation({ paid_usd, compared_paid_usd, worth_usd: 145.3, gain_usd: 25.02 });
  it('shows nothing when no line has a price today', () => expect(v(375, 0)).toEqual({ kind: 'none' }));
  it('is partial when some paid lines are unvalued', () => expect(v(495.28, 120.28)).toEqual({ kind: 'partial', worth: 145.3, gain: 25.02, comparedPaid: 120.28 }));
  it('is full when every paid line is valued (within a cent)', () => {
    expect(v(120.28, 120.28).kind).toBe('full');
    expect(v(120.284, 120.28).kind).toBe('full');
  });
});

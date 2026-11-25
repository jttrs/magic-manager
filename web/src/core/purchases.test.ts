import { describe, expect, it } from 'vitest';
import type { PurchaseOut, ReviewLineOut } from './api';
import { addableCopies, addableOwnedLines, chunk, isAddable, listStatus, roiSummary, STATUS_LABEL, subtotalGap, valuation } from './purchases';

const line = (o: Partial<ReviewLineOut>): ReviewLineOut => ({
  line_no: 1, kind: 'single', name: 'Sol Ring', set_name: 'Commander', condition: 'NM', finish: 'nonfoil',
  printing: { scryfall_id: 'x' } as ReviewLineOut['printing'], quantity: 3, unit_usd: 2, today_usd: 3,
  matched: 0, added: 0, remaining: 3, owned: 2, ...o,
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

  it('adds only single lines with a known printing and copies left', () => {
    const lines = [line({}), line({ line_no: 2, kind: 'sealed' }), line({ line_no: 3, printing: null }), line({ line_no: 4, remaining: 0 }), line({ line_no: 5, remaining: 4 })];
    expect(lines.map(isAddable)).toEqual([true, false, false, false, true]);
    expect(addableCopies(lines)).toBe(7);
    expect(addableCopies([])).toBe(0);
    expect(addableOwnedLines([...lines.map((l) => ({ ...l, owned: 0 })), { ...lines[4], owned: 2 }, { ...lines[1], owned: 3 }, { ...lines[3], owned: 1 }])).toBe(1);
  });

  it('roiSummary signs the gain: + only when positive', () => {
    const t = { orders: 3, paid_usd: 100, collection_value_usd: 130.5, gain_usd: 30.5 };
    expect(roiSummary(t)).toMatchObject({ paid: 100, orders: 3, value: 130.5, sign: '+', gain: 30.5 });
    expect(roiSummary({ ...t, collection_value_usd: 80, gain_usd: -20 })).toMatchObject({ sign: '−', gain: 20 });
    expect(roiSummary({ ...t, collection_value_usd: 100, gain_usd: 0 }).sign).toBe('');
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

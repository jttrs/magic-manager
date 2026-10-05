import { describe, expect, it } from 'vitest';
import { confirmed, productMeta, scanFrom, type CoverageProduct } from './trueup';

const p = (fileName: string, o: Partial<CoverageProduct> = {}): CoverageProduct => ({ fileName, name: fileName, type: 'Box Set', code: 'hob', release_date: '2026-08-14', recipe_qty: 6, usd: 10, ...o });

describe('product coverage review', () => {
  it('reads the scan artifact and labels products', () => {
    const scan = { ready: [p('A')], conflicts: [], applied: false, registered: 0, reattributed: 0 };
    expect(scanFrom([{ label: 'other', data: 1 }, { label: 'scan', data: scan }])).toBe(scan);
    expect(scanFrom(undefined)).toBeNull();
    expect(productMeta(p('A'))).toBe('Box Set · HOB · 2026');
    expect(productMeta(p('A', { type: null, release_date: null }))).toBe('HOB');
  });

  it('records only the products not marked not-mine', () => {
    const scan = { ready: [p('A'), p('B')], conflicts: [], applied: false, registered: 0, reattributed: 0 };
    expect(confirmed(scan, new Set(['B'])).map((x) => x.fileName)).toEqual(['A']);
  });
});

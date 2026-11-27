import { describe, expect, it } from 'vitest';
import { addDays, daysBetween, histogram, presetOf, presetRange, rangeLabel } from './dateRange';

describe('date range', () => {
  it('steps days in UTC', () => {
    expect(addDays('2026-02-28', 1)).toBe('2026-03-01');
    expect(daysBetween('2026-01-01', '2026-12-31')).toBe(364);
  });

  it('maps presets both ways', () => {
    expect(presetRange('30d', '2026-11-26')).toEqual({ from: '2026-10-28' });
    expect(presetRange('year', '2026-11-26')).toEqual({ from: '2026-01-01' });
    expect(presetOf(undefined, undefined, '2026-11-26')).toBe('all');
    expect(presetOf('2026-08-29', undefined, '2026-11-26')).toBe('90d');
    expect(presetOf('2026-08-01', '2026-09-01', '2026-11-26')).toBe('custom');
  });

  it('bins weekly under a year, monthly over', () => {
    const w = histogram(['2026-09-01', '2026-09-02', '2026-09-20'], '2026-09-01', '2026-09-30');
    expect(w.map((b) => b.count)).toEqual([2, 0, 1, 0, 0]);
    const m = histogram(['2025-01-15', '2026-06-02'], '2025-01-10', '2026-06-30');
    expect(m[0]).toMatchObject({ start: '2025-01-10', count: 1 });
    expect(m.at(-1)).toMatchObject({ start: '2026-06-01', count: 1 });
  });

  it('says the range in words', () => {
    expect(rangeLabel(undefined, undefined)).toBe('All time');
    expect(rangeLabel('2026-08-14', undefined)).toMatch(/^Since /);
  });
});

import { describe, expect, it } from 'vitest';
import { sortShort, sortSummary } from './sort';

const keys = { set: { label: 'Set', defaultDir: 'asc' as const }, price: { label: 'Price', defaultDir: 'desc' as const }, cn: { label: '#', defaultDir: 'asc' as const } };

describe('sort labels', () => {
  it('summarizes the whole hierarchy, marking a flipped direction', () => {
    expect(sortSummary(keys, [{ key: 'set', dir: 'asc' }, { key: 'price', dir: 'asc' }, { key: 'cn', dir: 'asc' }])).toBe('Set › Price ↑ › #');
    expect(sortSummary(keys, [])).toBe('Unsorted');
  });
  it('shortens to the first level plus a count', () => {
    expect(sortShort(keys, [{ key: 'price', dir: 'desc' }])).toBe('Price');
    expect(sortShort(keys, [{ key: 'set', dir: 'desc' }, { key: 'cn', dir: 'asc' }])).toBe('Set ↓ +1');
  });
});

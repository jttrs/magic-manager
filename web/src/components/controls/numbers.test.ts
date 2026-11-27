import { describe, expect, it } from 'vitest';
import { clampWhole, parseWhole } from './numbers';

describe('NumberField parsing', () => {
  it('reads whole numbers only', () => {
    expect(parseWhole('5')).toBe(5);
    expect(parseWhole(' 12 ')).toBe(12);
    expect(parseWhole('')).toBeNull();
    expect(parseWhole('-')).toBeNull();
    expect(parseWhole('2.5')).toBeNull();
  });

  it('clamps on leave, and keeps the old value for an empty field', () => {
    expect(clampWhole('15', 1, 10, 3)).toBe(10);
    expect(clampWhole('0', 1, 10, 3)).toBe(1);
    expect(clampWhole('', 1, 10, 3)).toBe(3);
    expect(clampWhole('abc', 1, 10, 3)).toBe(3);
  });
});

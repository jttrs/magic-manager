import { describe, expect, it } from 'vitest';
import { changeLines, whenLabel } from './undo';

describe('restore point', () => {
  it('describes changes in plain words', () => {
    expect(changeLines({ copies: 3, printings: 0, decks: -1, built: 0, wishlist: 0, earmarks: 2 })).toEqual(['3 more copies', '1 fewer deck', '2 more earmarked products']);
    expect(changeLines({ copies: 0, printings: 0, decks: 0, built: 0, wishlist: 0, earmarks: 0 })).toEqual([]);
  });
  it('labels the time, with the date when not today', () => {
    const now = new Date('2026-10-05T18:00:00');
    expect(whenLabel(new Date('2026-10-05T15:02:00').toISOString(), now)).toBe('3:02 PM');
    expect(whenLabel(new Date('2026-10-04T15:02:00').toISOString(), now)).toBe('Oct 4, 3:02 PM');
  });
});

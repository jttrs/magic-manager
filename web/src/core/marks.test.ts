import { describe, expect, it } from 'vitest';
import { copyMarkedLabel, copyMarkedTip, markBadge } from './marks';

describe('copy marked', () => {
  it('asks you to mark cards when none are marked', () => {
    expect(copyMarkedLabel(0)).toBe('Mark cards to copy them as a list');
  });
  it('counts the marked cards', () => {
    expect(copyMarkedLabel(1)).toBe('Copy 1 marked card as a list');
    expect(copyMarkedLabel(7)).toBe('Copy 7 marked cards as a list');
    expect(copyMarkedLabel(2, 'deck')).toBe('Copy 2 marked decks as a list');
  });
  it('tooltip: copied, then building, then a failure, else the label', () => {
    const label = 'Copy 2 marked cards as a list';
    expect(copyMarkedTip({ copied: true, busy: false, failure: null, label })).toBe('Copied');
    expect(copyMarkedTip({ copied: false, busy: true, failure: null, label })).toBe('Building list…');
    expect(copyMarkedTip({ copied: false, busy: false, failure: 'Nothing to copy', label })).toBe('Nothing to copy');
    expect(copyMarkedTip({ copied: false, busy: false, failure: null, label })).toBe(label);
  });
  it('caps the badge', () => {
    expect(markBadge(7)).toBe('7');
    expect(markBadge(140)).toBe('99+');
  });
});

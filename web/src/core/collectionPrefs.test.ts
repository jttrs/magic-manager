import { describe, expect, it } from 'vitest';
import type { PrefOut } from './api';
import { canToggleOff, predict, toggleMulti } from './collectionPrefs';

const multi: PrefOut = {
  key: 'missing_rarities', title: 'T', about: 'A', kind: 'multi',
  choices: [{ value: 'rare', label: 'Rares' }, { value: 'mythic', label: 'Mythics' }, { value: 'common', label: 'Commons' }],
  value: ['rare', 'mythic'], default: ['rare', 'mythic'], changed: false,
};
const choice: PrefOut = {
  key: 'variant_prints', title: 'T', about: 'A', kind: 'choice',
  choices: [{ value: 'hide', label: 'Leave out' }, { value: 'show', label: 'Include' }],
  value: 'hide', default: 'hide', changed: false,
};

describe('predict', () => {
  it('marks a different choice changed and a reset unchanged', () => {
    const changed = predict(choice, 'show');
    expect(changed).toMatchObject({ value: 'show', changed: true });
    expect(predict(changed, null)).toMatchObject({ value: 'hide', changed: false });
  });
  it('compares a multi as a set', () => {
    expect(predict(multi, ['mythic', 'rare']).changed).toBe(false);
    expect(predict(multi, ['rare']).changed).toBe(true);
  });
});

describe('toggleMulti', () => {
  const order = ['rare', 'mythic', 'common'];
  it('adds in choices order', () => expect(toggleMulti(['mythic'], 'rare', order)).toEqual(['rare', 'mythic']));
  it('removes', () => expect(toggleMulti(['rare', 'common'], 'rare', order)).toEqual(['common']));
});

describe('canToggleOff', () => {
  it('keeps the last value of a required multi', () => {
    expect(canToggleOff({ key: 'missing_rarities', value: ['rare'] }, 'rare')).toBe(false);
    expect(canToggleOff({ key: 'missing_rarities', value: ['rare', 'mythic'] }, 'rare')).toBe(true);
  });
  it('lets set_types go empty', () => expect(canToggleOff({ key: 'set_types', value: ['core'] }, 'core')).toBe(true));
});

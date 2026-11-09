import { describe, expect, it } from 'vitest';
import type { FamilyRuleOut, PrefOut } from './api';
import { canToggleOff, familyOption, predict, predictRule, ruleCounts, toggleMulti } from './collectionPrefs';

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

const rule: FamilyRuleOut = {
  id: 'r', description: 'D', note: null, default: 'count', state: 'count', changed: false, prints: 10, owned: 2,
};

describe('predictRule', () => {
  it('marks a different state changed and null resets to the default', () => {
    const changed = predictRule(rule, 'hide');
    expect(changed).toMatchObject({ state: 'hide', changed: true });
    expect(predictRule(changed, null)).toMatchObject({ state: 'count', changed: false });
    expect(predictRule(changed, 'count')).toMatchObject({ state: 'count', changed: false });
  });
});

describe('ruleCounts', () => {
  it('words the counts', () => {
    expect(ruleCounts(rule)).toBe('10 prints · 2 you own');
    expect(ruleCounts({ prints: 1, owned: 0 })).toBe('1 print · 0 you own');
    expect(ruleCounts({ prints: 1, owned: null })).toBe('1 print');
    expect(ruleCounts({ prints: null, owned: null })).toBe('Not read yet');
  });
});

describe('familyOption', () => {
  it('hints what changed, else the rule count', () => {
    expect(familyOption({ code: 'fin', name: 'Final Fantasy', rules: 4, changed: 3 })).toEqual({ value: 'fin', label: 'Final Fantasy', hint: '3 changed' });
    expect(familyOption({ code: 'fin', name: 'F', rules: 2, changed: 0 }).hint).toBe('2 rules');
    expect(familyOption({ code: 'fin', name: 'F', rules: 1, changed: 0 }).hint).toBe('1 rule');
  });
});

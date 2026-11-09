import { describe, expect, it } from 'vitest';
import type { FamilyRuleOut, PrefOut, VariantKindOut } from './api';
import { canToggleOff, familyOption, kindValue, predict, predictKind, predictRule, ruleCounts, ruleNow, toggleMulti } from './collectionPrefs';

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
  id: 'r', description: 'D', note: null, default: 'count', state: null, source: 'shipped', effective: 'count',
  changed: false, prints: 10, owned: 2, also_hidden: 0,
};

describe('predictRule', () => {
  it('pins a state, and null goes back to Group', () => {
    const pinned = predictRule(rule, 'hide');
    expect(pinned).toMatchObject({ state: 'hide', effective: 'hide', source: 'rule', changed: true });
    expect(predictRule(pinned, null)).toMatchObject({ state: null, effective: 'count', source: 'shipped', changed: false });
    expect(predictRule(pinned, null, 'chase')).toMatchObject({ state: null, effective: 'chase', source: 'family', changed: false });
    expect(predictRule(rule, 'count')).toMatchObject({ state: 'count', source: 'rule', changed: true });
  });
});

describe('ruleNow', () => {
  it('words where the state comes from and what the variant settings hide', () => {
    expect(ruleNow({ effective: 'hide', source: 'shipped', also_hidden: 0 })).toBe('Now: Hide (shipped)');
    expect(ruleNow({ effective: 'count', source: 'family', also_hidden: 0 })).toBe('Now: Count (from All rules)');
    expect(ruleNow({ effective: 'chase', source: 'rule', also_hidden: 0 })).toBe('Now: Chase');
    expect(ruleNow({ effective: 'count', source: 'shipped', also_hidden: 80 })).toBe('Now: Count (shipped) · 80 hidden by Variant prints');
  });
});

describe('variant kinds', () => {
  const kind: VariantKindOut = { key: 'serialized', label: 'Serialized', state: null, effective: 'hide' };
  it('reads null as Group and predicts through the group', () => {
    expect(kindValue(kind)).toBe('group');
    expect(kindValue({ state: 'show' })).toBe('show');
    expect(predictKind(kind, 'show', 'hide')).toMatchObject({ state: 'show', effective: 'show' });
    expect(predictKind({ ...kind, state: 'show', effective: 'show' }, null, 'hide')).toMatchObject({ state: null, effective: 'hide' });
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

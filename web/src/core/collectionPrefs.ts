// "What counts" preferences view-model (framework-free): the optimistic row
// for a change, multi-choice toggling and the one "can't be empty" rule.
import type { FamilyRuleOut, PrefOut, RuleFamilyOut } from './api';

type Value = PrefOut['value'];

const asList = (v: Value): string[] => (Array.isArray(v) ? v : [v]);

/** Equal as values; a multi compares as a set (order doesn't matter). */
function sameValue(a: Value, b: Value): boolean {
  if (!Array.isArray(a) || !Array.isArray(b)) return a === b;
  return a.length === b.length && a.every((v) => b.includes(v));
}

/** The predicted row while the server answers; `null` resets to the default. */
export function predict(row: PrefOut, value: Value | null): PrefOut {
  if (value === null) return { ...row, value: row.default, changed: false };
  return { ...row, value, changed: !sameValue(value, row.default) };
}

/** Add or remove `v`, keeping the choices' order. */
export function toggleMulti(current: string[], v: string, choicesOrder: string[]): string[] {
  const on = new Set(current);
  if (on.has(v)) on.delete(v);
  else on.add(v);
  return choicesOrder.filter((c) => on.has(c));
}

/** May `v` be switched off? Only set_types may end up empty; every other multi keeps one. */
export function canToggleOff(row: Pick<PrefOut, 'key' | 'value'>, v: string): boolean {
  if (row.key === 'set_types') return true;
  const now = asList(row.value);
  return !(now.length === 1 && now[0] === v);
}

/** The predicted rule while the server answers; `null` resets to the default. */
export function predictRule(row: FamilyRuleOut, state: FamilyRuleOut['state'] | null): FamilyRuleOut {
  const next = state ?? row.default;
  return { ...row, state: next, changed: next !== row.default };
}

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** "10 prints · 2 you own" — or that it hasn't been read yet. */
export function ruleCounts(row: Pick<FamilyRuleOut, 'prints' | 'owned'>): string {
  if (row.prints === null) return 'Not read yet';
  const prints = plural(row.prints, 'print', 'prints');
  return row.owned === null ? prints : `${prints} · ${row.owned} you own`;
}

/** A family as a SearchSelect option; the hint says what is changed or how many rules. */
export function familyOption(f: RuleFamilyOut): { value: string; label: string; hint: string } {
  return { value: f.code, label: f.name, hint: f.changed > 0 ? `${f.changed} changed` : plural(f.rules, 'rule', 'rules') };
}

// "What counts" preferences view-model (framework-free): the optimistic row
// for a change, multi-choice toggling and the one "can't be empty" rule.
import type { FamilyRuleOut, PrefOut, RuleFamilyOut, VariantKindOut } from './api';

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

/** The predicted rule while the server answers; `null` is Group (follows All rules, else the shipped state). */
export function predictRule(row: FamilyRuleOut, state: FamilyRuleOut['state'], allRules: FamilyRulesAll = null): FamilyRuleOut {
  if (state) return { ...row, state, effective: state, source: 'rule', changed: true };
  if (allRules) return { ...row, state: null, effective: allRules, source: 'family', changed: false };
  return { ...row, state: null, effective: row.default, source: 'shipped', changed: false };
}

type FamilyRulesAll = FamilyRuleOut['default'] | null;

const label = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** "Now: Hide (shipped)" / "Now: Count (from All rules)" / "Now: Chase", plus how many prints the variant settings still hide. */
export function ruleNow(row: Pick<FamilyRuleOut, 'effective' | 'source' | 'also_hidden'>): string {
  const from = row.source === 'shipped' ? ' (shipped)' : row.source === 'family' ? ' (from All rules)' : '';
  const hidden = row.also_hidden > 0 ? ` · ${row.also_hidden} hidden by Variant prints` : '';
  return `Now: ${label(row.effective)}${from}${hidden}`;
}

/** A variant kind's control value: Group when it has no switch of its own. */
export const kindValue = (k: Pick<VariantKindOut, 'state'>): 'group' | 'hide' | 'show' => k.state ?? 'group';

/** The predicted kind while the server answers; `null` follows the group. */
export function predictKind(k: VariantKindOut, state: VariantKindOut['state'], group: 'hide' | 'show'): VariantKindOut {
  return { ...k, state, effective: state ?? group };
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

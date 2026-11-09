import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { familyRulesQuery, invalidateCounting, ruleFamiliesQuery, unwrap } from '../../app/queries';
import { putFamilyAll, putFamilyRule, type FamilyRuleOut, type FamilyRulesOut } from '../../core/api';
import { familyOption, predictRule, ruleCounts, ruleNow } from '../../core/collectionPrefs';
import { FailureNote } from '../companion/CompanionNotes';
import { SearchSelect } from '../SearchSelect';
import { SettingsChoice, SettingsRow } from './SettingsControls';

type State = NonNullable<FamilyRuleOut['state']>;
type RuleChoice = State | 'group';
type AllChoice = State | 'shipped';
type Change = { kind: 'rule'; ruleId: string; state: State | null } | { kind: 'all'; state: State | null };

const RULE_OPTIONS: { value: RuleChoice; label: string }[] = [
  { value: 'group', label: 'Group' },
  { value: 'count', label: 'Count' },
  { value: 'chase', label: 'Chase' },
  { value: 'hide', label: 'Hide' },
];
const ALL_OPTIONS: { value: AllChoice; label: string }[] = [
  { value: 'shipped', label: 'Shipped' },
  { value: 'count', label: 'Count' },
  { value: 'chase', label: 'Chase' },
  { value: 'hide', label: 'Hide' },
];

/** Settings → What counts → Family rules: pick a family, then set all its rules or each one. */
export default function FamilyRulesSettings() {
  const [code, setCode] = useState('');
  const families = useQuery(ruleFamiliesQuery());
  const options = useMemo(() => (families.data?.families ?? []).map(familyOption), [families.data]);

  return (
    <>
      <SettingsRow
        label="Family rules"
        description="Pick a family to change what its rules do. Group follows All rules, or the shipped setting. Count and Chase bring back, in Collection, prints the variant settings leave out."
        control={() => (
          <SearchSelect label="Family" hideLabel tone="paper" noun="family" nouns="families" value={code || undefined} onChange={setCode} options={options} />
        )}
      />
      {families.isError && <FailureNote error={families.error} />}
      {code && <FamilyRules key={code} code={code} />}
    </>
  );
}

function FamilyRules({ code }: { code: string }) {
  const qc = useQueryClient();
  const rules = useQuery(familyRulesQuery(code));
  const key = familyRulesQuery(code).queryKey;

  const change = useMutation({
    mutationFn: async (c: Change) => unwrap(c.kind === 'all'
      ? await putFamilyAll({ path: { anchor: code }, body: { state: c.state } })
      : await putFamilyRule({ path: { anchor: code, rule_id: c.ruleId }, body: { state: c.state } })),
    onMutate: async (c) => {
      await qc.cancelQueries({ queryKey: key, exact: true });
      const before = qc.getQueryData<FamilyRulesOut>(key);
      if (before) {
        qc.setQueryData<FamilyRulesOut>(key, c.kind === 'all'
          ? { ...before, all_rules: c.state, rules: before.rules.map((r) => (r.state === null ? predictRule(r, null, c.state) : r)) }
          : { ...before, rules: before.rules.map((r) => (r.id === c.ruleId ? predictRule(r, c.state, before.all_rules) : r)) });
      }
      return { before };
    },
    onError: (_e, _c, ctx) => { if (ctx?.before) qc.setQueryData(key, ctx.before); },
    onSuccess: (data) => qc.setQueryData<FamilyRulesOut>(key, data),
    onSettled: () => invalidateCounting(qc),
  });

  return (
    <div className="flex flex-col">
      {change.error && <FailureNote error={change.error} />}
      {rules.isError && <FailureNote error={rules.error} />}
      {rules.isPending && <p className="py-3 text-sm text-ink-muted">Loading…</p>}
      {rules.data && (
        <>
          <SettingsRow
            label="All rules in this family"
            description="What every rule below does unless you set it on its own."
            control={(ids) => (
              <SettingsChoice<AllChoice>
                {...ids}
                value={rules.data.all_rules ?? 'shipped'}
                options={ALL_OPTIONS}
                onChange={(v) => { if (!change.isPending) change.mutate({ kind: 'all', state: v === 'shipped' ? null : v }); }}
              />
            )}
          />
          <div className="ml-1 flex flex-col border-l border-rule pl-4">
            {rules.data.rules.map((row) => (
              <RuleRow key={row.id} row={row} busy={change.isPending} onChange={(state) => change.mutate({ kind: 'rule', ruleId: row.id, state })} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function RuleRow({ row, busy, onChange }: { row: FamilyRuleOut; busy: boolean; onChange: (state: State | null) => void }) {
  return (
    <SettingsRow
      label={row.description}
      description={
        <>
          {ruleCounts(row)}
          <br />
          {ruleNow(row)}
          {row.note && (
            <details className="mt-1">
              <summary className="cursor-pointer">Why</summary>
              <p className="mt-1 text-sm text-ink-muted">{row.note}</p>
            </details>
          )}
        </>
      }
      control={(ids) => (
        <SettingsChoice<RuleChoice>
          {...ids}
          value={row.state ?? 'group'}
          options={RULE_OPTIONS}
          onChange={(v) => { if (!busy) onChange(v === 'group' ? null : v); }}
        />
      )}
    />
  );
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { familyRulesQuery, ruleFamiliesQuery, unwrap } from '../../app/queries';
import { putFamilyRule, type FamilyRuleOut, type FamilyRulesOut } from '../../core/api';
import { familyOption, predictRule, ruleCounts } from '../../core/collectionPrefs';
import { FailureNote } from '../companion/CompanionNotes';
import { SearchSelect } from '../SearchSelect';
import { SettingsChoice, SettingsRow } from './SettingsControls';

type State = FamilyRuleOut['state'];
type Change = { ruleId: string; state: State | null };

const STATES: { value: State; label: string }[] = [
  { value: 'count', label: 'Count' },
  { value: 'chase', label: 'Chase' },
  { value: 'hide', label: 'Hide' },
];

/** Settings → What counts → Family rules: pick a family, then set each of its rules. */
export default function FamilyRulesSettings() {
  const [code, setCode] = useState('');
  const families = useQuery(ruleFamiliesQuery());
  const options = useMemo(() => (families.data?.families ?? []).map(familyOption), [families.data]);

  return (
    <>
      <SettingsRow
        label="Family rules"
        description="Pick a family to change what its individual rules do. Count ignores the rule, Chase keeps those prints but tags them, Hide removes them unless you own them."
        control={() => (
          <SearchSelect label="Family" hideLabel tone="paper" noun="family" nouns="families" value={code || undefined} onChange={setCode} options={options} />
        )}
      />
      {families.isError && <FailureNote error={families.error} />}
      {code && <FamilyRules code={code} />}
    </>
  );
}

function FamilyRules({ code }: { code: string }) {
  const qc = useQueryClient();
  const rules = useQuery(familyRulesQuery(code));
  const key = familyRulesQuery(code).queryKey;

  const change = useMutation({
    mutationFn: async (c: Change) => unwrap(await putFamilyRule({ path: { anchor: code, rule_id: c.ruleId }, body: { state: c.state } })),
    onMutate: async (c) => {
      await qc.cancelQueries({ queryKey: key });
      const before = qc.getQueryData<FamilyRulesOut>(key);
      if (before) qc.setQueryData<FamilyRulesOut>(key, { ...before, rules: before.rules.map((r) => (r.id === c.ruleId ? predictRule(r, c.state) : r)) });
      return { before };
    },
    onError: (_e, _c, ctx) => { if (ctx?.before) qc.setQueryData(key, ctx.before); },
    onSuccess: (data) => qc.setQueryData<FamilyRulesOut>(key, data),
    onSettled: () => Promise.all([['preferences', 'collection', 'families'], ['collection'], ['market'], ['jumpstart']].map((k) => qc.invalidateQueries({ queryKey: k }))),
  });

  return (
    <div className="flex flex-col">
      {change.error && <FailureNote error={change.error} />}
      {rules.isError && <FailureNote error={rules.error} />}
      {rules.isPending && <p className="py-3 text-sm text-ink-muted">Loading…</p>}
      {rules.data?.rules.map((row) => (
        <RuleRow key={row.id} row={row} busy={change.isPending} onChange={(state) => change.mutate({ ruleId: row.id, state })} />
      ))}
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
          {row.note && (
            <details className="mt-1">
              <summary className="cursor-pointer">Why</summary>
              <p className="mt-1 text-sm text-ink-muted">{row.note}</p>
            </details>
          )}
        </>
      }
      control={(ids) => (
        <div className="flex flex-col items-start gap-1 sm:items-end">
          <SettingsChoice<State>
            {...ids}
            value={row.state}
            options={STATES}
            onChange={(v) => { if (!busy) onChange(v); }}
          />
          {row.changed && (
            <button
              type="button"
              disabled={busy}
              aria-label={`Reset ${row.description} to its default`}
              onClick={() => onChange(null)}
              className="min-h-6 cursor-pointer text-sm text-ink-muted underline hover:text-ink disabled:cursor-not-allowed pointer-coarse:min-h-11"
            >
              Reset
            </button>
          )}
        </div>
      )}
    />
  );
}

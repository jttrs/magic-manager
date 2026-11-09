import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { Fragment, useMemo } from 'react';
import { collectionPrefsQuery, unwrap, variantKindsQuery } from '../../app/queries';
import { useSettingsSection } from '../../app/settings';
import { putPref, putVariantKind, type PrefOut, type PrefsOut, type VariantKindOut, type VariantKindsOut } from '../../core/api';
import { canToggleOff, kindValue, predict, predictKind, toggleMulti } from '../../core/collectionPrefs';
import { FailureNote } from '../companion/CompanionNotes';
import FamilyRulesSettings from './FamilyRulesSettings';
import { SettingsChoice, SettingsMultiChoice, SettingsRow } from './SettingsControls';

type Change = { key: string; value: string | string[] | null };
type KindChange = { kind: string; state: VariantKindOut['state'] };
type KindChoice = 'group' | 'hide' | 'show';

const KIND_OPTIONS: { value: KindChoice; label: string }[] = [
  { value: 'group', label: 'Group' },
  { value: 'hide', label: 'Leave out' },
  { value: 'show', label: 'Include' },
];

/** Everything a preference or variant-kind change can alter: re-read it all. */
const invalidateCounting = (qc: QueryClient) => Promise.all(
  [['collection'], ['market'], ['jumpstart'], ['preferences', 'collection', 'families'], variantKindsQuery().queryKey]
    .map((k) => qc.invalidateQueries({ queryKey: k })),
);

/** Settings → What counts: which printings count in Collection, missing lists and checklists. */
export function useCollectionPrefsSettings() {
  const section = useMemo(() => ({
    id: 'counting',
    title: 'What counts',
    order: 45,
    content: <CollectionPrefsSection />,
  }), []);
  useSettingsSection(section);
}

function CollectionPrefsSection() {
  const qc = useQueryClient();
  const prefs = useQuery(collectionPrefsQuery());
  const key = collectionPrefsQuery().queryKey;

  const change = useMutation({
    mutationFn: async (c: Change) => unwrap(await putPref({ path: { key: c.key }, body: { value: c.value } })),
    onMutate: async (c) => {
      await qc.cancelQueries({ queryKey: key, exact: true });
      const before = qc.getQueryData<PrefsOut>(key);
      if (before) qc.setQueryData<PrefsOut>(key, { prefs: before.prefs.map((r) => (r.key === c.key ? predict(r, c.value) : r)) });
      return { before };
    },
    onError: (_e, _c, ctx) => { if (ctx?.before) qc.setQueryData(key, ctx.before); },
    onSuccess: (data) => qc.setQueryData<PrefsOut>(key, data),
    onSettled: () => invalidateCounting(qc),
  });

  const kinds = useQuery(variantKindsQuery());
  const kindsKey = variantKindsQuery().queryKey;
  const group = prefs.data?.prefs.find((r) => r.key === 'variant_prints')?.value === 'show' ? 'show' : 'hide';
  const changeKind = useMutation({
    mutationFn: async (c: KindChange) => unwrap(await putVariantKind({ path: { kind: c.kind }, body: { state: c.state } })),
    onMutate: async (c) => {
      await qc.cancelQueries({ queryKey: kindsKey, exact: true });
      const before = qc.getQueryData<VariantKindsOut>(kindsKey);
      if (before) qc.setQueryData<VariantKindsOut>(kindsKey, { kinds: before.kinds.map((k) => (k.key === c.kind ? predictKind(k, c.state, group) : k)) });
      return { before };
    },
    onError: (_e, _c, ctx) => { if (ctx?.before) qc.setQueryData(kindsKey, ctx.before); },
    onSuccess: (data) => qc.setQueryData<VariantKindsOut>(kindsKey, data),
    onSettled: () => invalidateCounting(qc),
  });

  const byFamily = prefs.data?.prefs.find((r) => r.key === 'by_family')?.value === 'on';

  return (
    <div className="flex flex-col">
      <p className="mb-1 text-sm text-ink-muted">Choose which printings count in Collection, missing lists and checklists. Only your own collection is affected.</p>
      {(change.error || changeKind.error) && <FailureNote error={change.error ?? changeKind.error} />}
      {prefs.isError && <FailureNote error={prefs.error} />}
      {prefs.isPending && <p className="py-3 text-sm text-ink-muted">Loading…</p>}
      {prefs.data?.prefs.map((row) => (
        <Fragment key={row.key}>
          <PrefRow row={row} busy={change.isPending} onChange={(value) => change.mutate({ key: row.key, value })} />
          {row.key === 'variant_prints' && (
            <div className="ml-1 flex flex-col border-l border-rule pl-4">
              {kinds.isError && <FailureNote error={kinds.error} />}
              {kinds.data?.kinds.map((k) => (
                <SettingsRow
                  key={k.key}
                  label={k.label}
                  description={`Now: ${k.effective === 'hide' ? 'Left out' : 'Included'}`}
                  control={(ids) => (
                    <SettingsChoice<KindChoice>
                      {...ids}
                      value={kindValue(k)}
                      options={KIND_OPTIONS}
                      onChange={(v) => { if (!changeKind.isPending) changeKind.mutate({ kind: k.key, state: v === 'group' ? null : v }); }}
                    />
                  )}
                />
              ))}
            </div>
          )}
        </Fragment>
      ))}
      {byFamily && <FamilyRulesSettings />}
    </div>
  );
}

function PrefRow({ row, busy, onChange }: { row: PrefOut; busy: boolean; onChange: (value: string | string[] | null) => void }) {
  return (
    <SettingsRow
      label={row.title}
      description={row.about}
      control={(ids) => (
        <div className="flex flex-col items-start gap-1 sm:items-end">
          {row.kind === 'multi' ? (
            <SettingsMultiChoice<string>
              {...ids}
              value={Array.isArray(row.value) ? row.value : [row.value]}
              options={row.choices}
              disabledValues={busy ? row.choices.map((c) => c.value) : row.choices.filter((c) => !canToggleOff(row, c.value) && Array.isArray(row.value) && row.value.includes(c.value)).map((c) => c.value)}
              onChange={(next) => {
                const current = Array.isArray(row.value) ? row.value : [row.value];
                const flipped = [...next.filter((v) => !current.includes(v)), ...current.filter((v) => !next.includes(v))][0];
                if (flipped === undefined) return;
                onChange(toggleMulti(current, flipped, row.choices.map((c) => c.value)));
              }}
            />
          ) : (
            <SettingsChoice<string>
              {...ids}
              value={String(row.value)}
              options={row.choices}
              onChange={(v) => { if (!busy) onChange(v); }}
            />
          )}
          {row.changed && (
            <button
              type="button"
              disabled={busy}
              aria-label={`Reset ${row.title} to its default`}
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

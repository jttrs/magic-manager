import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import { collectionPrefsQuery, unwrap } from '../../app/queries';
import { useSettingsSection } from '../../app/settings';
import { putPref, type PrefOut, type PrefsOut } from '../../core/api';
import { canToggleOff, predict, toggleMulti } from '../../core/collectionPrefs';
import { FailureNote } from '../companion/CompanionNotes';
import { SettingsChoice, SettingsMultiChoice, SettingsRow } from './SettingsControls';

type Change = { key: string; value: string | string[] | null };

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
      await qc.cancelQueries({ queryKey: key });
      const before = qc.getQueryData<PrefsOut>(key);
      if (before) qc.setQueryData<PrefsOut>(key, { prefs: before.prefs.map((r) => (r.key === c.key ? predict(r, c.value) : r)) });
      return { before };
    },
    onError: (_e, _c, ctx) => { if (ctx?.before) qc.setQueryData(key, ctx.before); },
    onSuccess: (data) => qc.setQueryData<PrefsOut>(key, data),
    onSettled: () => Promise.all(['collection', 'market', 'jumpstart'].map((k) => qc.invalidateQueries({ queryKey: [k] }))),
  });

  return (
    <div className="flex flex-col">
      <p className="mb-1 text-sm text-ink-muted">Choose which printings count in Collection, missing lists and checklists. Only your own collection is affected.</p>
      {change.error && <FailureNote error={change.error} />}
      {prefs.isError && <FailureNote error={prefs.error} />}
      {prefs.isPending && <p className="py-3 text-sm text-ink-muted">Loading…</p>}
      {prefs.data?.prefs.map((row) => (
        <PrefRow key={row.key} row={row} busy={change.isPending} onChange={(value) => change.mutate({ key: row.key, value })} />
      ))}
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

import { useQueryClient } from '@tanstack/react-query';
import { useBlocker } from '@tanstack/react-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { unwrap } from '../../app/queries';
import { collectionChecklist, type ChecklistOut, type CollectionCardOut } from '../../core/api';
import { familyLabel, readDraft, setCell, summarize, toChanges, type Draft, type Finish } from '../../core/checklist';

const KEY = 'mm.collection.checklist';

/** The checklist draft: kept in this browser until Save or Discard, one save =
 *  one ledger event. Warns before leaving Collection with unsaved counts. */
export function useChecklist() {
  const qc = useQueryClient();
  const [draft, setDraft] = useState<Draft>(() => readDraft(localStorage.getItem(KEY)));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<ChecklistOut | null>(null);
  const summary = useMemo(() => summarize(draft), [draft]);
  const dirty = summary.cells > 0;

  useEffect(() => {
    if (Object.keys(draft).length) localStorage.setItem(KEY, JSON.stringify(draft));
    else localStorage.removeItem(KEY);
  }, [draft]);

  const set = useCallback((card: CollectionCardOut, finish: Finish, qty: number | null, family: string) => {
    setSaved(null);
    setDraft((d) => setCell(d, card, finish, qty, family));
  }, []);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const res = unwrap(await collectionChecklist({ body: { family: familyLabel(summary.families), changes: toChanges(draft) } }));
      setDraft({});
      setSaved(res);
      await Promise.all(['collection', 'holdings', 'undo', 'decks'].map((k) => qc.invalidateQueries({ queryKey: [k] })));
    } catch (e) {
      setError((e as Error).message);
      // A stale count means the collection moved: show the current numbers.
      void qc.invalidateQueries({ queryKey: ['collection'] });
    } finally {
      setSaving(false);
    }
  };

  const discard = () => {
    setDraft({});
    setError(null);
  };

  const blocker = useBlocker({
    shouldBlockFn: ({ next }) => dirty && !saving && next.pathname !== '/collection',
    enableBeforeUnload: () => dirty,
    withResolver: true,
  });

  return { draft, summary, dirty, set, save, saving, error, saved, discard, blocker };
}

export type Checklist = ReturnType<typeof useChecklist>;

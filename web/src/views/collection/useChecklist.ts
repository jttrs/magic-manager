import { apiErrorFrom } from '../../core/apiError';
import { useQueryClient } from '@tanstack/react-query';
import { useBlocker } from '@tanstack/react-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { collectionChecklist, type ChecklistOut, type CollectionCardOut } from '../../core/api';
import { cellKey, confirmMoved, dropSaved, familyLabel, readDraft, rebaseStale, setCell, summarize, toChanges, type Draft, type Finish, type StaleRow } from '../../core/checklist';

const KEY = 'mm.collection.checklist';

/** The 409 body for counts that moved since the draft started (sets.StaleCounts). */
type StaleDetail = { message: string; stale: StaleRow[] };
const isStale = (d: unknown): d is StaleDetail =>
  !!d && typeof d === 'object' && Array.isArray((d as StaleDetail).stale) && typeof (d as StaleDetail).message === 'string';

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

  /** Keep your count in a flagged cell (all flagged cells when no card is given). */
  const confirm = useCallback((card?: CollectionCardOut, finish?: Finish) => {
    setDraft((d) => confirmMoved(d, card && finish ? cellKey(card.scryfall_id, finish) : undefined));
  }, []);

  const refresh = () => Promise.all(['collection', 'holdings', 'undo', 'decks'].map((k) => qc.invalidateQueries({ queryKey: [k] })));

  const save = async () => {
    const sent = draft;
    setSaving(true);
    setError(null);
    try {
      const r = await collectionChecklist({ body: { family: familyLabel(summary.families), changes: toChanges(sent) } });
      if (r.error !== undefined || !r.data) {
        const detail = (r.error as { detail?: unknown } | undefined)?.detail;
        if (isStale(detail)) {
          // The collection moved: show its counts and flag the cells to recheck.
          await qc.invalidateQueries({ queryKey: ['collection'] });
          // ChecklistNotes explains the flagged cells (summary.moved).
          setDraft((d) => rebaseStale(d, detail.stale));
        } else {
          setError(apiErrorFrom(r.error, r.response).message);
        }
        return;
      }
      // Fresh counts first, so saved cells never flash their old value and an
      // edit made meanwhile starts from the right count.
      await refresh();
      setDraft((d) => dropSaved(d, sent));
      setSaved(r.data);
    } catch (e) {
      setError((e as Error).message);
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

  return { draft, summary, dirty, set, confirm, save, saving, error, saved, discard, blocker };
}

export type Checklist = ReturnType<typeof useChecklist>;

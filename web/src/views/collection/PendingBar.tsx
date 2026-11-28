import { useEffect, useState } from 'react';
import { Button } from '../../components/Button';
import type { ChecklistOut } from '../../core/api';
import { pendingBarLine } from '../../core/checklist';
import { fmtInt } from '../../core/format';
import { ChecklistActions } from './Checklist';
import type { Checklist } from './useChecklist';

/** How long the "Added 23 copies" line stays after a save. */
const SAVED_MS = 8000;

/** The foot of the Collection sheet while a draft exists (grid, list or count table): what the
 *  draft does in plain numbers, Review (only the staged cards), Discard and the one commit. */
export function PendingBar({ checklist: c, reviewing, reviewCount, onReviewing }: {
  checklist: Checklist;
  reviewing: boolean;
  /** Cards the review filter shows. */
  reviewCount: number;
  onReviewing: (on: boolean) => void;
}) {
  // The saved line goes after a few seconds (the next edit clears `saved` itself).
  const [gone, setGone] = useState<ChecklistOut | null>(null);
  useEffect(() => {
    if (!c.saved) return;
    const t = window.setTimeout(() => setGone(c.saved), SAVED_MS);
    return () => window.clearTimeout(t);
  }, [c.saved]);
  const showSaved = !c.dirty && c.saved != null && gone !== c.saved;
  if (!c.dirty && !showSaved) return null;
  return (
    <div className="mx-sheet flex flex-wrap items-center gap-x-4 gap-y-2 border-t-2 border-rule-strong bg-paper py-2">
      <p role="status" aria-live="polite" className="min-w-0 flex-1 text-sm tabular text-ink">
        {pendingBarLine(c.summary, c.saved)}
        {reviewing && c.dirty && (
          <>
            {' · '}Showing {fmtInt(reviewCount)} pending ·{' '}
            <Button tone="paper" emphasis="link" onClick={() => onReviewing(false)}>Show all</Button>
          </>
        )}
      </p>
      {c.dirty && (
        <div className="flex shrink-0 items-center gap-2">
          <Button tone="paper" emphasis="quiet" aria-pressed={reviewing} onClick={() => onReviewing(!reviewing)}>Review</Button>
          <ChecklistActions checklist={c} />
        </div>
      )}
    </div>
  );
}

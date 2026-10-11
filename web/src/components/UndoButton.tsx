import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { undoQuery, unwrap } from '../app/queries';
import { undoRestore } from '../core/api';
import { changeLines, detailLines, whenLabel } from '../core/undo';
import { ConfirmDialog } from './ConfirmDialog';
import { IconTooltip } from './IconTooltip';

/** The one restore point: a quiet header icon once one exists (taken before the
 *  first change of each session); confirming swaps your data with it. */
export function UndoButton() {
  const qc = useQueryClient();
  const q = useQuery(undoQuery());
  const [open, setOpen] = useState(false);
  const info = q.data;
  if (!info?.taken_at) return null;
  const when = whenLabel(info.taken_at);
  const lines = changeLines(info.changes);
  const details = detailLines(info.details);
  const label = `Restore point · ${when}`;
  return (
    <>
      <IconTooltip label={label}>
        <button
          type="button"
          aria-label={label}
          onClick={() => { void q.refetch(); setOpen(true); }}
          className="touch-hit grid size-8 cursor-pointer place-items-center rounded-sm text-on-chrome-muted transition-colors ease-guide hover:text-on-chrome"
        >
          <svg viewBox="0 0 16 16" aria-hidden="true" className="size-4">
            <path d="M3.5 6.5h6a3.5 3.5 0 0 1 0 7H6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M6 3.5 3 6.5l3 3" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </IconTooltip>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={`Restore your collection to ${when}?`}
        confirmLabel="Restore"
        onConfirm={async () => {
          if (!info.restorable) throw new Error('The app’s database changed shape since this restore point was taken, so it can’t be restored.');
          unwrap(await undoRestore());
          await qc.invalidateQueries();
        }}
      >
        <div className="flex flex-col gap-3 text-md leading-relaxed">
          <p>Taken {info.reason}. Restoring puts your cards, decks, wishlist, watchlist and the rest of your data back as they were then.</p>
          {lines.length > 0 && (
            <ul aria-label="What changes" className="flex list-disc flex-col gap-0.5 pl-5">
              {lines.map((l) => <li key={l}>{l}</li>)}
            </ul>
          )}
          {details.length > 0 ? (
            <div className="flex flex-col gap-1">
              <p className="text-sm text-ink-muted">{lines.length ? 'Also rolled back:' : 'Your counts look the same as then, but these are rolled back:'}</p>
              <ul aria-label="Also rolled back" className="flex list-disc flex-col gap-0.5 pl-5 text-sm text-ink-muted">
                {details.map((l) => <li key={l}>{l}</li>)}
              </ul>
            </div>
          ) : !lines.length && (
            <p className="text-ink-muted">Nothing has changed since then.</p>
          )}
          <p className="text-sm text-ink-muted">It swaps rather than discards: restore again to come back to now.</p>
        </div>
      </ConfirmDialog>
    </>
  );
}

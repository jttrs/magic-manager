import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Tooltip } from 'radix-ui';
import { useState } from 'react';
import { undoQuery, unwrap } from '../app/queries';
import { undoRestore } from '../core/api';
import { changeLines, whenLabel } from '../core/undo';
import { ConfirmDialog } from './ConfirmDialog';

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
  const label = `Restore point · ${when}`;
  return (
    <>
      <Tooltip.Provider delayDuration={200}>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <button
              type="button"
              aria-label={label}
              onClick={() => { void q.refetch(); setOpen(true); }}
              className="grid size-8 cursor-pointer place-items-center rounded-sm text-on-chrome-muted transition-colors ease-guide hover:text-on-chrome"
            >
              <svg viewBox="0 0 16 16" aria-hidden="true" className="size-4">
                <path d="M3.5 6.5h6a3.5 3.5 0 0 1 0 7H6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M6 3.5 3 6.5l3 3" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content side="bottom" sideOffset={6} collisionPadding={12} className="z-50 rounded-sm border border-chrome-line bg-chrome-raised px-2.5 py-1.5 text-sm text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]">
              {label}
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </Tooltip.Provider>
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
          <p>Taken {info.reason}. Restoring puts your cards, decks, wishlist and earmarks back as they were then.</p>
          {lines.length ? (
            <ul aria-label="What changes" className="flex list-disc flex-col gap-0.5 pl-5">
              {lines.map((l) => <li key={l}>{l}</li>)}
            </ul>
          ) : (
            <p className="text-ink-muted">Your collection and decks look the same as then — only details (edits, provenance) would change.</p>
          )}
          <p className="text-sm text-ink-muted">It swaps rather than discards: restore again to come back to now.</p>
        </div>
      </ConfirmDialog>
    </>
  );
}

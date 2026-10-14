import { IconTooltip } from './IconTooltip';
import { iconActionClass } from './iconActionClass';
import { useCopy, type GetText } from './useCopy';
import { CopyListMark } from './StoreMarks';
import { copyMarkedLabel, markBadge } from '../core/marks';

export type MarkedCopy = { count: number; getText: GetText; onClear?: () => void; noun?: string };

/**
 * Header action: copy the marked cards as a list. Lives in the main view's
 * header actions — never in the filter rail. Views don't mount it themselves:
 * pass `GuideSheet`'s `marked` prop and the sheet puts it last in the header's
 * action icons.
 *
 *   const { selected, toggle, clear } = useSelection('explore');
 *   const marked = cards.filter((c) => selected.has(c.key));
 *   <GuideSheet … marked={{ count: marked.length, getText: () => exportLines(marked, 'plain'), onClear: clear }}>
 *
 * - `count` 0 → disabled, tooltip "Mark cards to copy them as a list".
 * - `count` N → amber count badge; tooltip "Copy N marked cards as a list".
 * - After a copy the glyph swaps to a check and the tooltip reads "Copied";
 *   the result is announced politely (failures too).
 * - `onClear` adds a small "Clear marks" × beside it while anything is marked.
 */
export function CopyMarked({ count, getText, onClear, noun = 'card' }: MarkedCopy) {
  const { status, busy, done, copy } = useCopy();
  const none = count === 0;
  const label = copyMarkedLabel(count, noun);
  const copied = done === 'marked';
  const tip = copied ? 'Copied' : busy ? 'Building list…' : status && !status.startsWith('Copied') ? status : label;
  return (
    <span className="flex items-center">
      <IconTooltip label={tip}>
        <button
          type="button"
          aria-label={label}
          aria-disabled={none || busy != null || undefined}
          data-state={copied ? 'done' : 'idle'}
          onClick={() => !none && busy == null && void copy('marked', getText)}
          className={iconActionClass('paper')}
        >
          {copied ? (
            <svg viewBox="0 0 24 24" aria-hidden="true" className="size-[1.35rem]">
              <path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ) : (
            <CopyListMark className="size-[1.35rem]" />
          )}
          {!none && (
            <span aria-hidden="true" className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-pill bg-accent px-1 text-2xs font-bold leading-none tabular text-on-accent">
              {markBadge(count)}
            </span>
          )}
        </button>
      </IconTooltip>
      {onClear && !none && (
        <IconTooltip label="Clear marks">
          <button
            type="button"
            aria-label="Clear marks"
            onClick={onClear}
            className="touch-hit grid size-6 cursor-pointer place-items-center rounded-sm text-ink-muted transition-colors duration-150 ease-guide hover:bg-paper-sunk hover:text-ink focus-visible:bg-paper-sunk focus-visible:text-ink"
          >
            <svg viewBox="0 0 16 16" aria-hidden="true" className="size-3">
              <path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </button>
        </IconTooltip>
      )}
      <span aria-live="polite" className="sr-only">{status}</span>
    </span>
  );
}

import { useContext, useLayoutEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { SheetHeaderSlots } from './sheetHeaderSlots';
import { SheetSummarySlot } from './SheetSummary';
import { ApiError } from '../core/apiError';
import { CopyMarked, type MarkedCopy } from './CopyMarked';

/**
 * Paper sheet that hosts a view's content, under the view's header strip.
 *
 * Header contract (every view, every variant):
 * - `title` is NEVER printed. It stays the page's accessible `h1` (sr-only, inside
 *   the sheet): the active nav tab, the sub-nav strip and the body's own group
 *   heads already say where you are.
 * - `summary` — the meta line (counts, freshness, what's shown); `arrange` — how
 *   the cards are arranged (`components/ArrangeControls`); `actions` — the view's
 *   header action icons (`IconAction`s). `actionsLabel` names the actions as a
 *   labelled toolbar (pass bare icons, no wrapper). `marked` adds `CopyMarked`
 *   last in the actions. Main-view actions live here, never in the filter rail.
 * - Inside `ViewLayout` the first GuideSheet PORTALS these into the layout's
 *   strip (`SheetHeaderSlots`: stats | arrange | actions), next to the section
 *   tabs; the strip's `surface-chrome` remaps paper tokens so controls need no
 *   restyling. Live summaries (`SheetSummary`) land in the strip's stats section.
 *   Outside a layout (or a second sheet under one) the header prints in the
 *   sheet as a compact row; with nothing to show it takes no space.
 *
 * `nav` (tabs at the sheet's top edge) and `hideTitle` are legacy: section modes
 * now go in `ViewLayout`'s `subnav` slot, and every title is hidden.
 */
export function GuideSheet({ title, summary, actions, actionsLabel, marked, arrange, nav, children }: { title: ReactNode; summary?: ReactNode; actions?: ReactNode; actionsLabel?: string; marked?: MarkedCopy; /** How the cards are arranged (sort, group, grid/list): `components/ArrangeControls`. */ arrange?: ReactNode; nav?: ReactNode; /** @deprecated titles are never printed now */ hideTitle?: boolean; children: ReactNode }) {
  const hasActions = Boolean(actions) || marked != null;
  const bare = !summary && !hasActions && !arrange;
  const toolbar = actionsLabel != null || marked != null;
  const slots = useContext(SheetHeaderSlots);
  const [claimed, setClaimed] = useState(false);
  const [slot, setSlot] = useState<HTMLElement | null>(null);
  const owner = slots?.owner;
  // Layout effect: claim the strip before the first paint, so the header never flashes in-sheet.
  useLayoutEffect(() => {
    if (!owner || owner.current) return;
    const me = Symbol('sheet');
    owner.current = me;
    setClaimed(true);
    return () => {
      if (owner.current === me) owner.current = null;
      setClaimed(false);
    };
  }, [owner]);
  const inStrip = claimed && slots != null && slots.stats != null && slots.arrange != null && slots.actions != null;
  const arrangeNode = arrange ? <div role="group" aria-label="Arrange" className="flex items-center gap-1">{arrange}</div> : null;
  const actionsNode = hasActions ? (
    <div role={toolbar ? 'toolbar' : undefined} aria-label={toolbar ? (actionsLabel ?? 'Sheet actions') : undefined} className={`flex items-center ${toolbar ? 'gap-1' : 'gap-2'}`}>
      {actions}
      {marked && <CopyMarked {...marked} />}
    </div>
  ) : null;
  return (
    <div className="paper-grain flex h-full min-h-[70dvh] flex-col bg-paper text-ink">
      {nav}
      {inStrip ? (
        <>
          <h1 className="sr-only">{title}</h1>
          {summary && createPortal(<span title={typeof summary === 'string' ? summary : undefined}>{summary}</span>, slots.stats!)}
          {arrangeNode && createPortal(arrangeNode, slots.arrange!)}
          {actionsNode && createPortal(actionsNode, slots.actions!)}
        </>
      ) : bare ? (
        <h1 className="sr-only">{title}</h1>
      ) : (
        <div className="flex min-h-12 flex-wrap items-center gap-x-6 gap-y-2 px-sheet pt-2 pb-1">
          <div className="min-w-0">
            <h1 className="sr-only">{title}</h1>
            {summary && <p className="text-sm tabular text-ink-muted">{summary}</p>}
            <p ref={setSlot} className="text-sm tabular text-ink-muted empty:hidden" />
          </div>
          {(arrangeNode || actionsNode) && (
            <div className="ml-auto flex flex-wrap items-center justify-end gap-x-2 gap-y-1">
              {arrangeNode && <div className={hasActions ? 'border-r border-rule pr-2' : ''}>{arrangeNode}</div>}
              {actionsNode}
            </div>
          )}
        </div>
      )}
      <div className="min-h-0 flex-1"><SheetSummarySlot.Provider value={inStrip ? slots.stats : slot}>{children}</SheetSummarySlot.Provider></div>
    </div>
  );
}

export function EmptyNote({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="mx-auto mt-[12vh] max-w-[46ch] px-6 text-center">
      <p className="text-2xl voice-condensed font-bold text-ink">{title}</p>
      {children && <div className="mt-2 text-md leading-relaxed text-ink-muted">{children}</div>}
    </div>
  );
}

export function ErrorNote({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div role="alert" className="mx-auto mt-[12vh] max-w-[52ch] px-6 text-center">
      <p className="text-2xl voice-condensed font-bold text-danger">Couldn’t load this sheet</p>
      <p className="mt-2 text-md text-ink">{msg}</p>
      {error instanceof ApiError && error.ref && !msg.includes(error.ref) && (
        <p className="mt-1 text-sm tabular text-ink-muted">
          Ref <span className="select-all text-ink">{error.ref}</span>{error.code ? ` · ${error.code}` : ''}
        </p>
      )}
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-4 cursor-pointer rounded-sm border border-rule px-3 py-1.5 text-sm voice-semi text-ink hover:border-rule-strong">
          Try again
        </button>
      )}
    </div>
  );
}

/** Ruled skeleton: grey card blocks at the guide's aspect while data loads. */
export function GridSkeleton({ label }: { label: string }) {
  return (
    <div role="status" aria-live="polite" className="grid grid-cols-[repeat(auto-fill,minmax(7.5rem,1fr))] gap-3 px-sheet pt-4" aria-label={label}>
      <span className="sr-only">{label}</span>
      {Array.from({ length: 18 }, (_, i) => (
        <span key={i} className="aspect-[488/680] animate-pulse rounded-sm bg-paper-sunk" />
      ))}
    </div>
  );
}

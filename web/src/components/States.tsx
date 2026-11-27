import { useContext, useLayoutEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { SheetHeaderSlots } from './sheetHeaderSlots';
import { ApiError } from '../core/apiError';
import { Button } from './Button';
import { CopyMarked, type MarkedCopy } from './CopyMarked';

/**
 * Paper sheet that hosts a view's content, under the view's header strip.
 *
 * Header contract (every view, every variant):
 * - `title` is NEVER printed. It stays the page's accessible `h1` (sr-only, inside
 *   the sheet): the active nav tab, the sub-nav strip and the body's own group
 *   heads already say where you are.
 * - No summary / stats text (owner decision). `arrange` — how the cards are
 *   arranged (`components/ArrangeControls`); `buy` — the copy-a-list picker and cart
 *   check (`components/CopyListMenu`); `actions` — the view's header action icons
 *   (`IconAction`s). `actionsLabel` names the actions as a
 *   labelled toolbar (pass bare icons, no wrapper). `marked` adds `CopyMarked`
 *   last in the actions. Main-view actions live here, never in the filter rail.
 * - Inside `ViewLayout` the first GuideSheet PORTALS these into the layout's
 *   strip (`SheetHeaderSlots`: arrange | buy | actions), right of the section
 *   tabs; the strip's `surface-chrome` remaps paper tokens so controls need no
 *   restyling.
 *   Outside a layout (or a second sheet under one) the header prints in the
 *   sheet as a compact row; with nothing to show it takes no space.
 *
 * `nav` (tabs at the sheet's top edge) and `hideTitle` are legacy: section modes
 * now go in `ViewLayout`'s `subnav` slot, and every title is hidden.
 */
export function GuideSheet({ title, actions, actionsLabel, marked, arrange, buy, nav, children }: { title: ReactNode; actions?: ReactNode; actionsLabel?: string; marked?: MarkedCopy; /** How the cards are arranged (sort, group, grid/list): `components/ArrangeControls`. */ arrange?: ReactNode; /** Lists to copy for a store + cart check (`components/CopyListMenu`): their own group. */ buy?: ReactNode; nav?: ReactNode; /** @deprecated titles are never printed now */ hideTitle?: boolean; children: ReactNode }) {
  const hasActions = Boolean(actions) || marked != null;
  const bare = !hasActions && !arrange && !buy;
  const toolbar = actionsLabel != null || marked != null;
  const slots = useContext(SheetHeaderSlots);
  const [claimed, setClaimed] = useState(false);
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
  const inStrip = claimed && slots != null && slots.arrange != null && slots.buy != null && slots.actions != null;
  const arrangeNode = arrange ? <div role="group" aria-label="Arrange" className="flex items-center gap-1">{arrange}</div> : null;
  const buyNode = buy ? <div role="group" aria-label="Buy" className="flex items-center gap-1">{buy}</div> : null;
  const actionsNode = hasActions ? (
    <div role={toolbar ? 'toolbar' : undefined} aria-label={toolbar ? (actionsLabel ?? 'Sheet actions') : undefined} className={`flex items-center ${toolbar ? 'gap-1' : 'gap-2'}`}>
      {actions}
      {marked && <CopyMarked {...marked} />}
    </div>
  ) : null;
  const groups = [arrangeNode, buyNode, actionsNode].filter(Boolean);
  return (
    <div className="paper-grain flex h-full min-h-[70dvh] flex-col bg-paper text-ink">
      {nav}
      <h1 className="sr-only">{title}</h1>
      {inStrip ? (
        <>
          {arrangeNode && createPortal(arrangeNode, slots.arrange!)}
          {buyNode && createPortal(buyNode, slots.buy!)}
          {actionsNode && createPortal(actionsNode, slots.actions!)}
        </>
      ) : bare ? null : (
        <div className="flex min-h-12 flex-wrap items-center justify-end divide-x divide-rule px-sheet pt-2 pb-1">
          {groups.map((g, i) => <div key={i} className="px-2 last:pr-0">{g}</div>)}
        </div>
      )}
      <div className="min-h-0 flex-1">{children}</div>
    </div>
  );
}

export function EmptyNote({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="mx-auto mt-[12vh] max-w-measure-narrow px-6 text-center">
      <p className="text-2xl voice-condensed font-bold text-ink">{title}</p>
      {children && <div className="mt-2 text-md leading-relaxed text-ink-muted">{children}</div>}
    </div>
  );
}

export function ErrorNote({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div role="alert" className="mx-auto mt-[12vh] max-w-measure-narrow px-6 text-center">
      <p className="text-2xl voice-condensed font-bold text-danger">Couldn’t load this sheet</p>
      <p className="mt-2 text-md text-ink">{msg}</p>
      {error instanceof ApiError && error.ref && !msg.includes(error.ref) && (
        <p className="mt-1 text-sm tabular text-ink-muted">
          Ref <span className="select-all text-ink">{error.ref}</span>{error.code ? ` · ${error.code}` : ''}
        </p>
      )}
      {onRetry && (
        <Button tone="paper" onClick={onRetry} className="mt-4">
          Try again
        </Button>
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
        <span key={i} className="aspect-card animate-pulse rounded-sm bg-paper-sunk" />
      ))}
    </div>
  );
}

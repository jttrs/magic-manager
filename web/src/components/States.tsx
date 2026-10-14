import type { ReactNode } from 'react';
import { ApiError } from '../core/apiError';
import { CopyMarked, type MarkedCopy } from './CopyMarked';

/**
 * Paper sheet that hosts a view's content: a compact header line, then the body.
 *
 * Header contract (every view, every variant):
 * - `title` is NEVER printed. It stays the page's accessible `h1` (sr-only): the
 *   active nav tab, the sub-nav strip and the body's own group heads already say
 *   where you are, so a big title only repeated them. Where the body has a single
 *   group, that group's head is the visible title.
 * - `summary` — the meta line (counts, freshness, what's shown), left.
 * - `actions` — the view's header action icons (`IconAction`s: refresh, open in
 *   a vendor, surf…), right-aligned on the same line. Main-view actions live
 *   here, never in the filter rail. `actionsLabel` names the group: the sheet
 *   then renders it as a labelled toolbar (pass bare icons, no wrapper).
 * - `marked` — the view has markable cards: the sheet adds `CopyMarked` (copy
 *   the marked cards as a list, count badge, Clear marks) last in the actions.
 * - With neither summary nor actions the header takes no space at all.
 *
 * `nav` (tabs at the sheet's top edge) and `hideTitle` are legacy: section modes
 * now go in `ViewLayout`'s `subnav` slot, and every title is hidden. Both stay
 * accepted until each view adopts the strip.
 */
export function GuideSheet({ title, summary, actions, actionsLabel, marked, nav, children }: { title: ReactNode; summary?: ReactNode; actions?: ReactNode; actionsLabel?: string; marked?: MarkedCopy; nav?: ReactNode; /** @deprecated titles are never printed now */ hideTitle?: boolean; children: ReactNode }) {
  const hasActions = Boolean(actions) || marked != null;
  const bare = !summary && !hasActions;
  const toolbar = actionsLabel != null || marked != null;
  return (
    <div className="paper-grain flex h-full min-h-[70dvh] flex-col rounded-sm bg-paper text-ink shadow-[0_1px_0_var(--theme-chrome-line),0_18px_40px_-28px_var(--theme-scrim)]">
      {nav}
      {bare ? (
        <h1 className="sr-only">{title}</h1>
      ) : (
        <div className="flex min-h-12 flex-wrap items-center gap-x-6 gap-y-2 px-5 pt-2 pb-1">
          <div className="min-w-0">
            <h1 className="sr-only">{title}</h1>
            {summary && <p className="text-sm tabular text-ink-muted">{summary}</p>}
          </div>
          {hasActions && (
            <div role={toolbar ? 'toolbar' : undefined} aria-label={toolbar ? (actionsLabel ?? 'Sheet actions') : undefined} className={`ml-auto flex items-center ${toolbar ? 'gap-1' : 'gap-2'}`}>
              {actions}
              {marked && <CopyMarked {...marked} />}
            </div>
          )}
        </div>
      )}
      <div className="min-h-0 flex-1">{children}</div>
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
    <div role="status" aria-live="polite" className="grid grid-cols-[repeat(auto-fill,minmax(7.5rem,1fr))] gap-3 px-4 pt-4" aria-label={label}>
      <span className="sr-only">{label}</span>
      {Array.from({ length: 18 }, (_, i) => (
        <span key={i} className="aspect-[488/680] animate-pulse rounded-sm bg-paper-sunk" />
      ))}
    </div>
  );
}

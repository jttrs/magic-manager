import type { ReactNode } from 'react';

/** Paper sheet that hosts a view's content: title, summary line, then the body. */
export function GuideSheet({ title, summary, actions, nav, children }: { title: ReactNode; summary?: ReactNode; actions?: ReactNode; nav?: ReactNode; children: ReactNode }) {
  return (
    <div className="paper-grain flex h-full min-h-[70dvh] flex-col rounded-sm bg-paper text-ink shadow-[0_1px_0_var(--theme-chrome-line),0_18px_40px_-28px_var(--theme-scrim)]">
      {nav}
      <div className="flex flex-wrap items-end gap-x-6 gap-y-2 px-5 pt-4 pb-2">
        <div className="min-w-0">
          <h1 className="text-3xl voice-condensed font-bold leading-none tracking-[-0.01em] text-ink">{title}</h1>
          {summary && <p className="mt-1.5 text-sm tabular text-ink-muted">{summary}</p>}
        </div>
        {actions && <div className="ml-auto flex items-center gap-2">{actions}</div>}
      </div>
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

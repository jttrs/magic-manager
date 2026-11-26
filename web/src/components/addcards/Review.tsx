import type { ReactNode } from 'react';
import { fmtInt } from '../../core/format';
import type { ReviewStats } from '../../core/ingest';
import { Button } from '../Button';
import { Chevron } from '../icons/Chevron';

/** A read list under review: title, a way back, the reader's warnings, then the checklist. */
export function Review({ title, warnings, back, children }: { title: string; warnings: string[]; back: { label: string; onClick: () => void }; children: ReactNode }) {
  return (
    <section aria-label={title} className="flex min-h-0 flex-1 flex-col @container">
      <div className="flex items-baseline gap-4 border-b-2 border-rule-strong pb-1">
        <h3 className="text-lg voice-condensed font-bold uppercase">{title}</h3>
        <Button tone="paper" emphasis="link" onClick={back.onClick} className="self-center text-sm">
          <Chevron dir="left" className="mr-0.5 inline size-icon-xs align-text-bottom" />
          {back.label}
        </Button>
      </div>
      {warnings.length > 0 && (
        <details className="border-b border-rule py-1.5 text-sm text-ink-muted">
          <summary className="cursor-pointer">{fmtInt(warnings.length)} {warnings.length === 1 ? 'line needs' : 'lines need'} a look</summary>
          <ul className="mt-1 flex flex-col gap-0.5 text-xs">{warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </details>
      )}
      <div className="min-h-0 flex-1 overflow-y-auto pr-3 [scrollbar-gutter:stable]">{children}</div>
    </section>
  );
}

/** "12 copies · 2 best-guess printings to check · 1 not found" — the review footer's tally. */
export function ReviewTally({ stats }: { stats: ReviewStats }) {
  return (
    <p className="text-sm tabular text-ink-muted">
      <span className="text-ink">{fmtInt(stats.copies)} {stats.copies === 1 ? 'copy' : 'copies'}</span>
      {stats.picked > 0 && ` · ${fmtInt(stats.picked)} best-guess printings to check`}
      {stats.unresolved > 0 && <span className="text-danger"> · {fmtInt(stats.unresolved)} not found</span>}
      {stats.skipped > 0 && ` · ${fmtInt(stats.skipped)} left out`}
    </p>
  );
}

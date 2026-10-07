/** A job's thin amber progress rule with its current step (`Pricing 3 of 12 · <product>`). */
export function ProgressRule({ label, done, total, message, verb }: { label: string; done: number; total: number | null; message?: string; verb: string }) {
  const fmt = new Intl.NumberFormat();
  return (
    <div className="flex flex-col gap-1 pt-1" role="status" aria-live="polite">
      <div className="flex items-baseline gap-2 text-sm text-ink-muted">
        <span className="shrink-0 tabular">{total ? `${verb} ${fmt.format(Math.min(done + 1, total))} of ${fmt.format(total)}` : `${verb}…`}</span>
        {message && <span className="min-w-0 truncate">· {message}</span>}
      </div>
      <div className="h-[3px] overflow-hidden rounded-pill bg-paper-sunk" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={total ?? 0} aria-valuenow={done}>
        <div className="h-full rounded-pill bg-accent transition-[width] duration-300 ease-guide" style={{ width: total ? `${(done / total) * 100}%` : '4%' }} />
      </div>
    </div>
  );
}

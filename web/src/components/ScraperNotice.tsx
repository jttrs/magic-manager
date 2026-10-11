import { Tooltip } from 'radix-ui';
import { noticeFor, type ScraperHealth } from '../core/scraperHealth';

/**
 * Where a site read is offered and that read is flagged "temporarily down"
 * (docs/scraper-health.md): a ruled notice — what's down, why, since when, the
 * code to quote — that never blocks. A read that works clears the flag.
 */
export function ScraperNotice({ down, className = '' }: { down: readonly ScraperHealth[]; className?: string }) {
  if (!down.length) return null;
  return (
    <section role="status" aria-label="Temporarily down" className={`flex flex-col gap-2 border-y-2 border-rule-strong py-2 ${className}`}>
      {down.map((h) => {
        const n = noticeFor(h);
        return (
          <div key={h.key} className="flex flex-col gap-0.5">
            <p className="flex items-baseline gap-1.5 text-md voice-condensed font-bold text-danger">
              <DownGlyph />
              <span>{n.title}</span>
            </p>
            <p className="max-w-[68ch] text-sm leading-relaxed text-ink">{n.reason} You can still try — a read that works clears this.</p>
            <p className="text-xs tabular text-ink-muted">{n.meta}</p>
          </div>
        );
      })}
    </section>
  );
}

/** The compact form for a row (a store in Deals): a rust DOWN mark; the tooltip says the rest. */
export function ScraperDownMark({ health }: { health: ScraperHealth | undefined }) {
  if (health?.status !== 'down') return null;
  const n = noticeFor(health);
  return (
    <Tooltip.Provider delayDuration={120}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          {/* Focusable so the explanation is reachable by keyboard, like InfoTip. */}
          <span tabIndex={0} aria-label={n.tip} className="touch-hit inline-flex cursor-help items-center gap-1 text-xs voice-semi font-semibold uppercase tracking-[0.06em] text-danger">
            <DownGlyph />
            Down
          </span>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content side="top" sideOffset={6} collisionPadding={12} className="z-50 max-w-[20rem] rounded-sm border border-chrome-line bg-chrome-raised px-3 py-2 text-sm leading-snug text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]">
            <p className="font-semibold">{n.title}</p>
            <p>{n.reason} You can still try.</p>
            <p className="mt-1 text-xs tabular text-on-chrome-muted">{n.meta}</p>
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

/** A broken link: the read stopped connecting to the site's page. */
function DownGlyph() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className="size-3.5 shrink-0 translate-y-[1px] self-center">
      <path d="M6.6 9.4 5 11a2 2 0 0 1-2.9-2.9l1.6-1.6M9.4 6.6 11 5a2 2 0 0 1 2.9 2.9l-1.6 1.6M5.2 2.4l.5 1.7M2.4 5.2l1.7.5M10.8 13.6l-.5-1.7M13.6 10.8l-1.7-.5"
        fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

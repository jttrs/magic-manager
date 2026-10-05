import { Tooltip } from 'radix-ui';
import type { ReactNode } from 'react';

/** A small ⓘ that explains a term on hover or keyboard focus. */
export function InfoTip({ label, children, tone = 'chrome' }: { label: string; children: ReactNode; tone?: 'chrome' | 'paper' }) {
  return (
    <Tooltip.Provider delayDuration={120}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <button type="button" aria-label={label} className={`touch-hit grid size-5 cursor-help place-items-center rounded-pill ${tone === 'paper' ? 'text-ink-muted hover:text-accent-ink focus-visible:text-accent-ink' : 'text-on-chrome-muted hover:text-accent focus-visible:text-accent'}`}>
            <svg viewBox="0 0 16 16" aria-hidden="true" className="size-3.5">
              <circle cx="8" cy="8" r="6.4" fill="none" stroke="currentColor" strokeWidth="1.4" />
              <path d="M8 7.2v4M8 4.9v.1" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content side="right" sideOffset={6} collisionPadding={12} className="z-50 max-w-[18rem] rounded-sm border border-chrome-line bg-chrome-raised px-3 py-2 text-sm leading-snug text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]">
            {children}
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

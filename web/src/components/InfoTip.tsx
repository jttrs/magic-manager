import { Tooltip } from 'radix-ui';
import type { ReactNode } from 'react';
import { InfoMark } from './icons/marks';

/** A small ⓘ that explains a term on hover or keyboard focus. */
export function InfoTip({ label, children, tone = 'chrome' }: { label: string; children: ReactNode; tone?: 'chrome' | 'paper' }) {
  return (
    <Tooltip.Provider delayDuration={120}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <button type="button" aria-label={label} className={`touch-hit grid size-5 cursor-help place-items-center rounded-pill ${tone === 'paper' ? 'text-ink-muted hover:text-accent-ink focus-visible:text-accent-ink' : 'text-on-chrome-muted hover:text-accent focus-visible:text-accent'}`}>
            <InfoMark className="size-icon-xs" />
          </button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content side="right" sideOffset={6} collisionPadding={12} className="z-50 max-w-[18rem] rounded-sm border border-chrome-line bg-chrome-raised px-3 py-2 text-sm leading-snug text-on-chrome shadow-popover">
            {children}
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

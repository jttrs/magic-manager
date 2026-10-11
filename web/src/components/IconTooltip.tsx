import { Tooltip } from 'radix-ui';
import type { ReactNode } from 'react';

/** The words behind an icon-only control: wraps ONE trigger element (a button,
 *  a router Link, a Radix trigger) in the shared chrome tooltip. Used by
 *  `IconAction` and the masthead icons so the tooltip looks the same everywhere. */
export function IconTooltip({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content side="bottom" sideOffset={6} collisionPadding={12} className="z-50 max-w-[16rem] rounded-sm border border-chrome-line bg-chrome-raised px-2.5 py-1.5 text-sm leading-snug text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]">
            {label}
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

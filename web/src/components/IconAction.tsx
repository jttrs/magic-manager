import { Tooltip } from 'radix-ui';
import type { ComponentType, SVGProps } from 'react';

type Props = {
  /** Names the action; shown as the tooltip and used as the accessible name. */
  label: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  onClick: () => void;
  disabled?: boolean;
  /** Why it's disabled (replaces the tooltip text). */
  disabledReason?: string;
};

/**
 * An icon-only action on paper: the mark in amber ink, a quiet sunk fill on
 * hover/focus — no lift, no underline. The tooltip carries the words, so a row
 * of actions stays calm. DESIGN.md: secondary actions only; a flow's commit stays
 * a filled amber button.
 */
export function IconAction({ label, Icon, onClick, disabled = false, disabledReason }: Props) {
  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <button
            type="button"
            aria-label={label}
            aria-disabled={disabled || undefined}
            onClick={() => !disabled && onClick()}
            className="touch-hit grid size-9 cursor-pointer place-items-center rounded-sm text-accent-ink transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk aria-disabled:cursor-not-allowed aria-disabled:text-ink-muted aria-disabled:opacity-60 aria-disabled:hover:bg-transparent"
          >
            <Icon className="size-[1.35rem]" />
          </button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content side="bottom" sideOffset={6} collisionPadding={12} className="z-50 max-w-[16rem] rounded-sm border border-chrome-line bg-chrome-raised px-2.5 py-1.5 text-sm leading-snug text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]">
            {disabled && disabledReason ? disabledReason : label}
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

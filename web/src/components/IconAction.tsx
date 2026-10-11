import type { ComponentProps, ComponentType, MouseEvent, SVGProps } from 'react';
import { IconTooltip } from './IconTooltip';

type Props = Omit<ComponentProps<'button'>, 'onClick' | 'disabled'> & {
  /** Names the action; shown as the tooltip and used as the accessible name. */
  label: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  /** Optional when used as a Radix trigger (`asChild`), which supplies its own. */
  onClick?: (e: MouseEvent<HTMLButtonElement>) => void;
  disabled?: boolean;
  /** Why it's disabled (replaces the tooltip text). */
  disabledReason?: string;
};

/**
 * An icon-only action on paper: the mark in amber ink, a quiet sunk fill on
 * hover/focus — no lift, no underline (a pressed toggle adds an amber
 * underline). The tooltip carries the words, so a row of actions stays calm. DESIGN.md: secondary actions only; a flow's commit stays
 * a filled amber button.
 */
export function IconAction({ label, Icon, onClick, disabled = false, disabledReason, ...rest }: Props) {
  return (
    <IconTooltip label={disabled && disabledReason ? disabledReason : label}>
      <button
        type="button"
        {...rest}
        aria-label={label}
        aria-disabled={disabled || undefined}
        onClick={(e) => !disabled && onClick?.(e)}
        className="touch-hit grid size-9 cursor-pointer place-items-center rounded-sm text-accent-ink transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk aria-pressed:bg-paper-sunk aria-pressed:shadow-[inset_0_-2px_0_var(--theme-accent)] aria-disabled:cursor-not-allowed aria-disabled:text-ink-muted aria-disabled:opacity-60 aria-disabled:hover:bg-transparent"
      >
        <Icon className="size-[1.35rem]" />
      </button>
    </IconTooltip>
  );
}

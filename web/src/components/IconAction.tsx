import type { ComponentProps, ComponentType, MouseEvent, SVGProps } from 'react';
import { IconTooltip } from './IconTooltip';
import { iconActionClass, type IconTone } from './iconActionClass';

type Props = Omit<ComponentProps<'button'>, 'onClick' | 'disabled'> & {
  /** Names the action; shown as the tooltip and used as the accessible name. */
  label: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  /** Optional when used as a Radix trigger (`asChild`), which supplies its own. */
  onClick?: (e: MouseEvent<HTMLButtonElement>) => void;
  disabled?: boolean;
  /** Why it's disabled (replaces the tooltip text). */
  disabledReason?: string;
  /** `paper` (default): amber mark on a guide sheet. `chrome`: the masthead's quiet bone mark. */
  tone?: IconTone;
};

/**
 * An icon-only action on paper: the mark in amber ink, a quiet sunk fill on
 * hover/focus — no lift, no underline (a pressed toggle adds an amber
 * underline). The tooltip carries the words, so a row of actions stays calm. DESIGN.md: secondary actions only; a flow's commit stays
 * a filled amber button.
 */
export function IconAction({ label, Icon, onClick, disabled = false, disabledReason, tone = 'paper', ...rest }: Props) {
  return (
    <IconTooltip label={disabled && disabledReason ? disabledReason : label}>
      <button
        type="button"
        {...rest}
        aria-label={label}
        aria-disabled={disabled || undefined}
        onClick={(e) => !disabled && onClick?.(e)}
        className={iconActionClass(tone)}
      >
        <Icon className={tone === 'chrome' ? 'size-[1.125rem]' : 'size-[1.35rem]'} />
      </button>
    </IconTooltip>
  );
}

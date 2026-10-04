import type { ButtonHTMLAttributes } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { tone?: 'chrome' | 'paper'; emphasis?: 'primary' | 'quiet' };

/** The one button. On chrome it reads as a ruled outline; primary fills amber. */
export function Button({ tone = 'chrome', emphasis = 'quiet', className = '', type = 'button', ...rest }: Props) {
  const base =
    'inline-flex items-center justify-center gap-2 min-h-9 px-3 rounded-sm text-sm voice-semi font-medium ' +
    'transition-[background-color,color,border-color] ease-guide disabled:opacity-45 disabled:cursor-not-allowed ' +
    'border cursor-pointer select-none';
  const look =
    emphasis === 'primary'
      ? 'bg-accent text-on-accent border-accent hover:bg-highlight-solid'
      : tone === 'chrome'
        ? 'bg-transparent text-on-chrome border-chrome-line hover:border-on-chrome-muted hover:bg-chrome-raised'
        : 'bg-transparent text-ink border-rule hover:border-rule-strong hover:bg-paper-sunk';
  return <button type={type} className={`${base} ${look} ${className}`} {...rest} />;
}

export type ButtonEmphasis = 'primary' | 'quiet' | 'danger' | 'danger-solid';

/** The one button's classes — also for a link that must look like it (e.g. a sign-in redirect).
 *  `danger` (rust label, quiet) and `danger-solid` (the one filled rust commit) are for
 *  destroying the account only. */
export function buttonClass(tone: 'chrome' | 'paper' = 'chrome', emphasis: ButtonEmphasis = 'quiet'): string {
  const base =
    'inline-flex items-center justify-center gap-2 min-h-9 px-3 rounded-sm text-sm voice-semi font-medium ' +
    'transition-[background-color,color,border-color] ease-guide disabled:opacity-45 disabled:cursor-not-allowed ' +
    'border cursor-pointer select-none';
  const look =
    emphasis === 'primary'
      ? 'bg-accent text-on-accent border-accent hover:bg-highlight-solid'
      : emphasis === 'danger-solid'
        ? 'bg-danger text-paper border-danger enabled:hover:opacity-90'
        : emphasis === 'danger'
          ? 'bg-transparent text-danger border-rule hover:border-danger hover:bg-paper-sunk'
          : tone === 'chrome'
        ? 'bg-transparent text-on-chrome border-chrome-line hover:border-on-chrome-muted hover:bg-chrome-raised'
        : 'bg-transparent text-ink border-rule hover:border-rule-strong hover:bg-paper-sunk';
  return `${base} ${look}`;
}

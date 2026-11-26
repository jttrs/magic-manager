export type ButtonEmphasis = 'primary' | 'quiet' | 'danger' | 'danger-solid' | 'link' | 'nav';

/** The one button's classes — also for a link that must look like it (e.g. a sign-in redirect).
 *  `danger` (rust label, quiet) and `danger-solid` (the one filled rust commit) are for
 *  destroying the account only. `link` is a quiet inline text action ("Reset filters",
 *  "Clear", "See the revert") — underlined words, no box. */
export function buttonClass(tone: 'chrome' | 'paper' = 'chrome', emphasis: ButtonEmphasis = 'quiet'): string {
  if (emphasis === 'nav') {
    return (
      'inline cursor-pointer select-none bg-transparent p-0 voice-semi underline underline-offset-2 hover:decoration-2 ' +
      'disabled:cursor-not-allowed disabled:opacity-45 ' +
      (tone === 'chrome' ? 'text-accent' : 'text-accent-ink')
    );
  }
  if (emphasis === 'link') {
    return (
      'inline cursor-pointer select-none bg-transparent p-0 underline underline-offset-2 transition-colors ease-guide ' +
      'disabled:cursor-not-allowed disabled:opacity-45 ' +
      (tone === 'chrome' ? 'text-on-chrome-muted hover:text-on-chrome' : 'text-ink-muted hover:text-ink')
    );
  }
  const base =
    'inline-flex items-center justify-center gap-2 min-h-control px-3 rounded-sm text-sm voice-semi font-medium ' +
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

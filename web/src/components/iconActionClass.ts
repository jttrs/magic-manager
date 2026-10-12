// The icon-action box shared by `IconAction` and masthead icon links.
export type IconTone = 'paper' | 'chrome';

const TONE: Record<IconTone, string> = {
  paper: 'text-accent-ink hover:bg-paper-sunk focus-visible:bg-paper-sunk aria-pressed:bg-paper-sunk aria-pressed:shadow-[inset_0_-2px_0_var(--theme-accent)] aria-disabled:text-ink-muted',
  chrome: 'text-on-chrome-muted hover:bg-chrome-raised hover:text-on-chrome focus-visible:bg-chrome-raised focus-visible:text-on-chrome aria-expanded:bg-chrome-raised aria-expanded:text-on-chrome data-[status=active]:text-on-chrome data-[status=active]:shadow-[inset_0_-2px_0_var(--theme-accent)] aria-disabled:text-on-chrome-muted',
};

/** The icon-action box (size, hit area, focus, tone) for icon controls that
 *  can't be an `IconAction` button — e.g. a router `Link` in the masthead. */
export function iconActionClass(tone: IconTone = 'paper'): string {
  return `touch-hit relative grid size-9 shrink-0 cursor-pointer place-items-center rounded-sm no-underline transition-colors duration-150 ease-guide aria-disabled:cursor-not-allowed aria-disabled:opacity-60 aria-disabled:hover:bg-transparent ${TONE[tone]}`;
}

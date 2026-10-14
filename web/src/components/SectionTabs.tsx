import { Link, type LinkProps } from '@tanstack/react-router';
import { useContext } from 'react';
import { SubnavSlot } from './subnavSlot';

export type SectionTab = {
  id: string;
  label: string;
  /** Where the tab goes (a route, or the same route with a different search). */
  link: Omit<LinkProps, 'children' | 'className'>;
  /** Set when tabs share one route (a `mode` search key): the router can't tell
   *  them apart, so the caller says which is current. Unset = the router's own
   *  active match (`link.activeOptions`). */
  active?: boolean;
};

// No negative bottom margin: the row scrolls sideways, so a tab hanging below it
// would give the row a vertical scrollbar. The underline sits on the rule.
const TAB = 'relative shrink-0 text-sm voice-semi uppercase tracking-[0.06em] no-underline transition-colors ease-guide after:absolute after:inset-x-0 after:bottom-0 after:rounded-pill';
const TONE = {
  // The sub-nav strip under the top nav: chrome stock, quieter than the top nav
  // (small semi-condensed caps, a 2px underline instead of 3px).
  chrome: {
    row: 'flex min-h-10 items-stretch gap-6 overflow-x-auto px-4 lg:px-5',
    tab: 'flex items-center py-2 hover:text-on-chrome after:h-[2px]',
    routed: 'text-on-chrome-muted after:bg-transparent data-[status=active]:text-on-chrome data-[status=active]:after:bg-accent',
    on: 'text-on-chrome after:bg-accent',
    off: 'text-on-chrome-muted after:bg-transparent',
  },
  // Legacy: tabs across the top of a GuideSheet (its `nav` slot).
  paper: {
    row: 'flex gap-5 overflow-x-auto border-b border-rule px-5 pt-2',
    tab: 'py-1.5 hover:text-ink after:h-[3px]',
    routed: 'text-ink-muted after:bg-transparent data-[status=active]:text-ink data-[status=active]:after:bg-accent',
    on: 'text-ink after:bg-accent',
    off: 'text-ink-muted after:bg-transparent',
  },
} as const;

/**
 * A section's modes (Collection: Cards · Purchase history; Explore: Rankings ·
 * Specific cards). One look for every section that has modes.
 *
 * Put it in `ViewLayout`'s `subnav` slot — `<ViewLayout subnav={<SectionTabs
 * label="Explore modes" tabs={tabs} />} …>` — where it renders as the full-width
 * chrome strip under the top nav. (Inside a `GuideSheet`'s legacy `nav` slot it
 * keeps the paper look.) Renders nothing for fewer than two tabs: a section
 * with one mode shows no strip.
 */
export function SectionTabs({ label, tabs }: { label: string; tabs: readonly SectionTab[] }) {
  const tone = TONE[useContext(SubnavSlot) ? 'chrome' : 'paper'];
  if (tabs.length < 2) return null;
  return (
    <nav aria-label={label} className={tone.row}>
      {tabs.map((t) => (
        <Link
          key={t.id}
          {...t.link}
          aria-current={t.active ? 'page' : undefined}
          className={`${TAB} ${tone.tab} ${t.active === undefined ? tone.routed : t.active ? tone.on : tone.off}`}
        >
          {t.label}
        </Link>
      ))}
    </nav>
  );
}

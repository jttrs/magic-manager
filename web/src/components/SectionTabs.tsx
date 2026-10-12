import { Link, type LinkProps } from '@tanstack/react-router';

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
const TAB = 'relative py-1.5 text-sm voice-semi uppercase tracking-[0.06em] no-underline transition-colors ease-guide hover:text-ink after:absolute after:inset-x-0 after:bottom-0 after:h-[3px] after:rounded-pill';
const ROUTED = 'text-ink-muted after:bg-transparent data-[status=active]:text-ink data-[status=active]:after:bg-accent';
const ON = 'text-ink after:bg-accent';
const OFF = 'text-ink-muted after:bg-transparent';

/** A section's modes as tabs across the top of its sheet (Collection: Cards ·
 *  Purchase history · Store orders; Explore: Rankings · Specific cards). One look
 *  for every section that has modes. */
export function SectionTabs({ label, tabs }: { label: string; tabs: readonly SectionTab[] }) {
  return (
    <nav aria-label={label} className="flex gap-5 overflow-x-auto border-b border-rule px-5 pt-2">
      {tabs.map((t) => (
        <Link
          key={t.id}
          {...t.link}
          aria-current={t.active ? 'page' : undefined}
          className={`${TAB} shrink-0 ${t.active === undefined ? ROUTED : t.active ? ON : OFF}`}
        >
          {t.label}
        </Link>
      ))}
    </nav>
  );
}

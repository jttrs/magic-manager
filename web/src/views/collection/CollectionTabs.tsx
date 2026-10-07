import { Link } from '@tanstack/react-router';

const TABS = [
  { to: '/collection', label: 'Cards', exact: true },
  { to: '/collection/history', label: 'Purchase history', exact: false },
  { to: '/collection/jumpstart', label: 'Jumpstart', exact: false },
] as const;

/** Collection's sheets: the cards you own, how they came in, and Jumpstart packs. */
export function CollectionTabs() {
  return (
    <nav aria-label="Collection views" className="flex gap-5 border-b border-rule px-5 pt-2">
      {TABS.map((t) => (
        <Link
          key={t.to}
          to={t.to}
          activeOptions={{ exact: t.exact, includeSearch: false }}
          className="relative -mb-px py-1.5 text-sm voice-semi uppercase tracking-[0.06em] text-ink-muted no-underline transition-colors ease-guide hover:text-ink
                     after:absolute after:inset-x-0 after:bottom-0 after:h-[3px] after:rounded-pill after:bg-transparent
                     data-[status=active]:text-ink data-[status=active]:after:bg-accent"
        >
          {t.label}
        </Link>
      ))}
    </nav>
  );
}

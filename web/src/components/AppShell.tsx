import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { jobsQuery } from '../app/queries';
import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { ToggleGroup, Tooltip } from 'radix-ui';
import { applyTheme, readTheme, type ThemePref } from '../app/theme';
import { useMediaQuery } from '../app/useMediaQuery';
import { UndoButton } from './UndoButton';

const NAV = [
  { to: '/collection', label: 'Collection' },
  { to: '/decks', label: 'Decks' },
  { to: '/explore', label: 'Explore' },
  { to: '/market', label: 'Market' },
] as const;

/** Global frame: masthead + full-width top nav; views supply sidebar + main below it. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-dvh grid-rows-[var(--size-topbar)_1fr] overflow-x-clip bg-chrome text-on-chrome">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 bg-accent text-on-accent px-3 py-1 rounded-sm">
        Skip to content
      </a>
      <header className="flex min-w-0 items-stretch gap-2 border-b border-chrome-line px-2 sm:gap-8 sm:px-6">
        <Link to="/" className="flex shrink-0 items-center text-xl voice-condensed font-bold tracking-[-0.01em] text-on-chrome no-underline sm:text-2xl" translate="no">
          <span className="sm:hidden">mm</span>
          <span className="hidden sm:inline">magic-manager</span>
        </Link>
        <nav aria-label="Primary" className="flex min-w-0 items-stretch overflow-x-auto">
          <ul className="flex items-stretch sm:gap-1">
            {NAV.map((n) => (
              <li key={n.to} className="flex">
                <Link
                  to={n.to}
                  className="relative flex items-center px-1.5 text-md voice-condensed sm:px-3 sm:text-xl text-on-chrome-muted no-underline transition-colors ease-guide hover:text-on-chrome
                             after:absolute after:inset-x-1.5 after:bottom-0 sm:after:inset-x-3 after:h-[3px] after:rounded-pill after:bg-transparent
                             data-[status=active]:text-on-chrome data-[status=active]:after:bg-accent"
                >
                  {n.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <UndoButton />
          <JobsLink />
          <ThemeSwitch />
        </div>
      </header>
      {children}
    </div>
  );
}

/** Sidebar (starts below the nav) + main region. */
export function ViewLayout({ sidebar, children, label, summary, startOpen = false }: { sidebar: ReactNode; children: ReactNode; label: string; summary?: string; startOpen?: boolean }) {
  const wide = useMediaQuery('(min-width: 64rem)');
  const [open, setOpen] = useState(startOpen);
  const shown = wide || open;
  return (
    <div className="grid min-h-0 min-w-0 grid-cols-1 lg:grid-cols-[var(--size-sidebar)_minmax(0,1fr)]">
      <aside aria-label={label} className="min-w-0 border-b border-chrome-line px-4 py-3 lg:max-h-[calc(100dvh-var(--size-topbar))] lg:overflow-y-auto lg:border-b-0 lg:border-r lg:px-5 lg:py-5">
        {!wide && (
          <button
            type="button"
            aria-expanded={open}
            aria-controls="view-controls"
            onClick={() => setOpen((o) => !o)}
            className="flex w-full cursor-pointer items-center gap-3 py-1 text-left"
          >
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="text-md voice-condensed uppercase tracking-[0.06em] text-on-chrome">{label}</span>
              {summary && !open && <span className="truncate text-xs text-on-chrome-muted">{summary}</span>}
            </span>
            <span aria-hidden="true" className={`text-on-chrome transition-transform ease-guide ${open ? 'rotate-180' : ''}`}>▾</span>
          </button>
        )}
        <div id="view-controls" hidden={!shown} className={`flex-col gap-6 ${shown ? 'flex' : ''} ${wide ? '' : 'pt-3'}`}>{sidebar}</div>
      </aside>
      <main id="main" tabIndex={-1} className="min-h-0 min-w-0 p-2 sm:p-3 lg:h-[calc(100dvh-var(--size-topbar))] lg:p-4">
        {children}
      </main>
    </div>
  );
}

function ThemeSwitch() {
  const [pref, setPref] = useState<ThemePref>(() => readTheme());
  useEffect(() => applyTheme(pref), [pref]);
  const order: ThemePref[] = ['system', 'light', 'dark'];
  const label = { system: 'Auto', light: 'Light', dark: 'Dark' } as const;
  return (
    <>
    <button
      type="button"
      onClick={() => setPref(order[(order.indexOf(pref) + 1) % order.length])}
      aria-label={`Color theme: ${label[pref]}. Change theme`}
      className="min-h-8 cursor-pointer rounded-sm border border-chrome-line px-2 text-xs voice-semi text-on-chrome sm:hidden"
    >
      {label[pref]}
    </button>
    <ToggleGroup.Root
      type="single"
      value={pref}
      onValueChange={(v) => v && setPref(v as ThemePref)}
      aria-label="Color theme"
      className="hidden rounded-sm border border-chrome-line p-0.5 sm:flex"
    >
      {(['system', 'light', 'dark'] as const).map((t) => (
        <ToggleGroup.Item
          key={t}
          value={t}
          className="px-2 py-1 text-xs voice-semi capitalize text-on-chrome-muted rounded-xs cursor-pointer transition-colors ease-guide hover:text-on-chrome data-[state=on]:bg-chrome-raised data-[state=on]:text-on-chrome"
        >
          {t === 'system' ? 'Auto' : t}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
    </>
  );
}

/** Background work lives behind a utility link, not in the primary IA. */
/** Background jobs: housekeeping, not a destination — a quiet icon that pulses
 *  while something runs; the tooltip names it. */
function JobsLink() {
  const jobs = useQuery(jobsQuery());
  const running = jobs.data?.filter((j) => j.status === 'queued' || j.status === 'running').length ?? 0;
  const label = running ? `Background jobs · ${running} running` : 'Background jobs';
  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <Link
            to="/jobs"
            aria-label={label}
            className="relative grid size-8 place-items-center rounded-sm text-on-chrome-muted no-underline transition-colors ease-guide hover:text-on-chrome data-[status=active]:text-on-chrome"
          >
            <svg viewBox="0 0 16 16" aria-hidden="true" className="size-4">
              <path d="M3 4.5h10M3 8h10M3 11.5h6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
            {running > 0 && <span aria-hidden="true" className="absolute right-1 top-1 size-2 animate-pulse rounded-pill bg-accent" />}
          </Link>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content side="bottom" sideOffset={6} collisionPadding={12} className="z-50 rounded-sm border border-chrome-line bg-chrome-raised px-2.5 py-1.5 text-sm text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]">
            {label}
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { jobsQuery } from '../app/queries';
import type { ReactNode } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { IconTooltip } from './IconTooltip';
import { Pressable } from './controls/Pressable';
import { CaretMark, JobsMark } from './icons/marks';
import { iconActionClass } from './iconActionClass';
import { applyTheme, readTheme, type ThemePref } from '../app/theme';
import { useMediaQuery } from '../app/useMediaQuery';
import { useSettingsSection } from '../app/settings';
import { UndoButton } from './UndoButton';
import { PrivacyPrompt } from './Telemetry';
import { useAnalytics } from '../app/analytics';
import { CompanionButton } from './companion/CompanionSetup';
import { useFeature } from '../app/features';
import { SettingsButton } from './settings/SettingsDialog';
import { SettingsChoice, SettingsRow } from './settings/SettingsControls';
import { SubnavSlot } from './subnavSlot';
import { SheetHeaderSlots } from './sheetHeaderSlots';
import { FlagsButton } from './flags/FlagsButton';
import { AccountButton } from './auth/AccountButton';
import { useCollectionPrefsSettings } from './settings/CollectionPrefsSettings';
import { AccountSettings } from './account/AccountSettings';

const NAV = [
  { to: '/collection', label: 'Collection' },
  { to: '/decks', label: 'Decks' },
  { to: '/explore', label: 'Explore' },
  { to: '/market', label: 'Market' },
] as const;

/** Global frame: masthead + full-width top nav; views supply sidebar + main below it. */
export function AppShell({ children }: { children: ReactNode }) {
  useAnalytics();
  useAppearanceSettings();
  useCollectionPrefsSettings();
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
                             after:absolute after:inset-x-1.5 after:bottom-0 sm:after:inset-x-3 after:h-underline after:rounded-pill after:bg-transparent
                             data-[status=active]:text-on-chrome data-[status=active]:after:bg-accent"
                >
                  {n.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        {/* Status first (restore point, companion, jobs), then the one Settings gear; hosted adds your account last. */}
        <div className="ml-auto flex shrink-0 items-center gap-2 sm:gap-1.5">
          <UndoButton />
          <CompanionSlot />
          <JobsLink />
          <FlagsButton />
          <SettingsButton />
          <AccountButton />
        </div>
      </header>
      <PrivacyPrompt />
      <AccountSettings />
      {children}
    </div>
  );
}

/** The companion is a desktop Chrome extension, so phones never show it. */
function CompanionSlot() {
  return useFeature('companion') ? <span className="contents max-sm:hidden"><CompanionButton /></span> : null;
}

/** Sidebar (starts below the nav) + main region, under ONE full-width strip.
 *
 *  The strip sits under the top nav, above BOTH the rail and the sheet, in chrome
 *  stock (`surface-chrome` remaps the paper-styled header controls to it): the
 *  section's mode tabs on the left, then — right-aligned — the icon groups, each
 *  set off by a divider on its left and hidden (with it) while empty:
 *  [tabs] … | [arrange] | [buy] | [actions, rightmost]. No stats text.
 *  - `subnav` fills the tabs section — the section's modes (Collection: Cards ·
 *    History; Explore: Rankings · Cards · Surfer). Pass `<SectionTabs label=…
 *    tabs=… />`; it takes the strip's look and renders nothing for fewer than two tabs.
 *  - arrange / buy / actions are slots: the first `GuideSheet` under the layout
 *    portals its `arrange`, `buy` and `actions` into them (`SheetHeaderSlots`).
 *  With nothing in any section the strip collapses to nothing. Below `lg` it wraps:
 *  tabs on one row, then the icon groups; it stays visible while the rail is collapsed. */
export function ViewLayout({ sidebar, children, label, summary, startOpen = false, subnav }: { sidebar: ReactNode; children: ReactNode; label: string; summary?: string; startOpen?: boolean; subnav?: ReactNode }) {
  const wide = useMediaQuery('(min-width: 64rem)');
  const [open, setOpen] = useState(startOpen);
  const shown = wide || open;
  const [arrange, setArrange] = useState<HTMLElement | null>(null);
  const [buy, setBuy] = useState<HTMLElement | null>(null);
  const [actions, setActions] = useState<HTMLElement | null>(null);
  const owner = useRef<symbol | null>(null);
  const slots = useMemo(() => ({ arrange, buy, actions, owner }), [arrange, buy, actions]);
  const group = 'flex min-h-10 items-center border-l border-chrome-line px-sheet empty:hidden';
  return (
    <div className="flex min-h-0 min-w-0 flex-col lg:h-[calc(100dvh-var(--size-topbar))]">
      <div data-subnav="" className="surface-chrome flex shrink-0 flex-wrap items-stretch border-b border-chrome-line bg-chrome text-on-chrome not-has-[>:first-child:not(:empty)]:not-has-[[data-slot]:not(:empty)]:hidden">
        <div className="w-full max-w-full empty:hidden lg:w-auto">
          <SubnavSlot.Provider value>{subnav}</SubnavSlot.Provider>
        </div>
        <div className="ml-auto flex items-stretch">
          <div ref={setArrange} data-slot="" className={group} />
          <div ref={setBuy} data-slot="" className={group} />
          <div ref={setActions} data-slot="" className={group} />
        </div>
      </div>
      <div className="grid min-h-0 min-w-0 flex-1 grid-cols-1 lg:grid-cols-[var(--size-sidebar)_minmax(0,1fr)] lg:grid-rows-[minmax(0,1fr)]">
        <aside aria-label={label} className="relative min-w-0 border-b border-chrome-line px-4 py-3 lg:overflow-y-auto lg:border-b-0 lg:border-r lg:px-5 lg:py-3">
          {!wide && (
            <Pressable
              aria-expanded={open}
              aria-controls="view-controls"
              onClick={() => setOpen((o) => !o)}
              className="flex w-full items-center gap-3 py-1"
            >
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="text-md voice-condensed uppercase tracking-caps text-on-chrome">{label}</span>
                {summary && !open && <span className="truncate text-xs text-on-chrome-muted">{summary}</span>}
              </span>
              <CaretMark className={`size-icon-sm text-on-chrome transition-transform ease-guide ${open ? 'rotate-180' : ''}`} />
            </Pressable>
          )}
          <div id="view-controls" hidden={!shown} className={`flex-col gap-3 ${shown ? 'flex' : ''} ${wide ? '' : 'pt-3'}`}>{sidebar}</div>
        </aside>
        <main id="main" tabIndex={-1} className="min-h-0 min-w-0 lg:h-full">
          <SheetHeaderSlots.Provider value={slots}>{children}</SheetHeaderSlots.Provider>
        </main>
      </div>
    </div>
  );
}

const THEMES: { value: ThemePref; label: string }[] = [
  { value: 'system', label: 'Auto' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
];

/** Settings → Appearance: the colour theme (Auto follows the OS). */
function useAppearanceSettings() {
  const [pref, setPref] = useState<ThemePref>(() => readTheme());
  useEffect(() => applyTheme(pref), [pref]);
  const section = useMemo(() => ({
    id: 'appearance',
    title: 'Appearance',
    order: 0,
    content: (
      <SettingsRow
        label="Theme"
        description="Auto follows your device’s light or dark setting."
        control={(ids) => <SettingsChoice value={pref} options={THEMES} onChange={setPref} {...ids} />}
      />
    ),
  }), [pref]);
  useSettingsSection(section);
}

/** Background jobs: housekeeping, not a destination — a quiet icon that pulses
 *  while something runs; the tooltip names it. Phones show it only while a job
 *  runs (Settings → About links to the list). */
function JobsLink() {
  const jobs = useQuery(jobsQuery());
  const running = jobs.data?.filter((j) => j.status === 'queued' || j.status === 'running').length ?? 0;
  const label = running ? `Background jobs · ${running} running` : 'Background jobs';
  return (
    <IconTooltip label={label}>
      <Link
        to="/jobs"
        aria-label={label}
        className={`${iconActionClass('chrome')} ${running ? '' : 'max-sm:hidden'}`}
      >
        <JobsMark className="size-icon-md" />
        {running > 0 && <span aria-hidden="true" className="absolute right-1.5 top-1.5 size-2 animate-pulse rounded-pill bg-accent" />}
      </Link>
    </IconTooltip>
  );
}

import { Link } from '@tanstack/react-router';
import { Dialog } from 'radix-ui';
import { useState, type SVGProps } from 'react';
import { useFeature, useOwnerPath } from '../../app/features';
import { useSettingsSections } from '../../app/settings';
import { IconAction } from '../IconAction';
import { PrivacySettings } from '../Telemetry';
import { PRIVACY_LEAD } from '../privacyCopy';
import { SettingsGroup } from './SettingsControls';

function GearIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" {...props}>
      <path
        d="M8 1.6v1.9M8 12.5v1.9M14.4 8h-1.9M3.5 8H1.6M12.5 3.5l-1.35 1.35M4.85 11.15 3.5 12.5M12.5 12.5l-1.35-1.35M4.85 4.85 3.5 3.5"
        fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      />
      <circle cx="8" cy="8" r="4.1" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="8" cy="8" r="1.6" fill="none" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

/** The masthead gear: ONE surface for preferences — Appearance, any section a
 *  view registers (`useSettingsSection`), Privacy, and About. */
export function SettingsButton() {
  const [open, setOpen] = useState(false);
  const sections = useSettingsSections();
  const analyticsOn = useFeature('analytics');
  const dashboardAllowed = useOwnerPath('analytics.dashboard');
  const analytics = analyticsOn && dashboardAllowed;
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <IconAction label="Settings" Icon={GearIcon} tone="chrome" />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        <Dialog.Content className="paper-grain fixed left-1/2 top-1/2 z-50 flex max-h-[min(48rem,calc(100dvh-1.5rem))] w-[min(38rem,calc(100vw-1.5rem))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-sm bg-paper text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none">
          <header className="flex items-center gap-3 border-b-2 border-rule-strong px-5 pb-2 pt-4">
            <Dialog.Title className="min-w-0 flex-1 text-2xl voice-condensed font-bold leading-none">Settings</Dialog.Title>
            <Dialog.Description className="sr-only">Appearance, view preferences, privacy and more.</Dialog.Description>
            <Dialog.Close className="touch-hit grid size-9 cursor-pointer place-items-center rounded-sm text-xl text-ink-muted hover:bg-paper-sunk hover:text-ink" aria-label="Close">×</Dialog.Close>
          </header>
          <div className="flex min-h-0 flex-1 flex-col gap-7 overflow-y-auto overscroll-contain px-5 pb-6 pt-4">
            {sections.map((s) => (
              <SettingsGroup key={s.id} title={s.title}>{s.content}</SettingsGroup>
            ))}
            <SettingsGroup title="Privacy">
              <p className="pt-3 text-sm leading-relaxed text-ink-muted">{PRIVACY_LEAD}</p>
              <PrivacySettings />
            </SettingsGroup>
            <SettingsGroup title="About">
              <p className="pt-3 text-sm leading-relaxed text-ink-muted">
                magic-manager keeps your collection, set completion and decks over the exact printings you own.
              </p>
              <ul className="flex flex-col pt-2">
                <AboutLink to="/jobs" label="Background jobs" detail="Syncs, imports and valuations — running and finished." />
                {analytics && <AboutLink to="/analytics" label="Analytics" detail="Errors and usage recorded by this server." />}
              </ul>
            </SettingsGroup>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function AboutLink({ to, label, detail }: { to: '/jobs' | '/analytics'; label: string; detail: string }) {
  return (
    <li className="border-b border-rule last:border-b-0">
      <Dialog.Close asChild>
        <Link to={to} className="group flex min-h-11 items-center gap-3 py-2 text-ink no-underline">
          <span className="min-w-0 flex-1">
            <span className="block text-md font-medium underline decoration-accent decoration-1 underline-offset-2 group-hover:decoration-2">{label}</span>
            <span className="block text-sm text-ink-muted">{detail}</span>
          </span>
          <span aria-hidden="true" className="text-ink-muted">→</span>
        </Link>
      </Dialog.Close>
    </li>
  );
}

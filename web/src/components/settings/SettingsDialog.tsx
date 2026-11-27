import { Link } from '@tanstack/react-router';
import { Dialog } from 'radix-ui';
import { useState } from 'react';
import { useFeature, useOwnerPath } from '../../app/features';
import { peekAccountReturn } from '../../app/accountReturn';
import { useSettingsSections } from '../../app/settings';
import { dialogContentClass, dialogOverlayClass } from '../controls/surfaces';
import { CloseMark, GearMark } from '../icons/marks';
import { IconAction } from '../IconAction';
import { PrivacySettings } from '../Telemetry';
import { PRIVACY_LEAD } from '../privacyCopy';
import { SettingsGroup } from './SettingsControls';

/** The masthead gear: ONE surface for preferences — Appearance, any section a
 *  view registers (`useSettingsSection`; the shell registers Account), Privacy, and About. */
export function SettingsButton() {
  // Back from re-auth for Delete account: open where the person left off.
  const [open, setOpen] = useState(peekAccountReturn);
  const sections = useSettingsSections();
  const analyticsOn = useFeature('analytics');
  const dashboardAllowed = useOwnerPath('analytics.dashboard');
  const analytics = analyticsOn && dashboardAllowed;
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <IconAction label="Settings" Icon={GearMark} tone="chrome" />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className={dialogOverlayClass} />
        <Dialog.Content className={dialogContentClass('md', 'frame')}>
          <header className="flex items-center gap-3 border-b-2 border-rule-strong px-5 pb-2 pt-4">
            <Dialog.Title className="min-w-0 flex-1 text-2xl voice-condensed font-bold leading-none">Settings</Dialog.Title>
            <Dialog.Description className="sr-only">Appearance, view preferences, privacy and more.</Dialog.Description>
            <Dialog.Close className="touch-hit grid size-9 cursor-pointer place-items-center rounded-sm text-ink-muted hover:bg-paper-sunk hover:text-ink" aria-label="Close"><CloseMark className="size-icon-md" /></Dialog.Close>
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

import { useMutation } from '@tanstack/react-query';
import { Dialog } from 'radix-ui';
import { useState, type ReactNode } from 'react';
import { unwrap } from '../../app/queries';
import { Button } from '../../components/Button';
import { TextInput } from '../../components/controls/TextField';
import { dialogContentClass, dialogOverlayClass, dialogTitleClass } from '../../components/controls/surfaces';
import { CopyButton } from '../../components/CopyButton';
import { SettingsChoice, SettingsRow } from '../../components/settings/SettingsControls';
import { adminInvite } from '../../core/api';
import { INVITE_DAYS, inviteDaysLabel } from '../../core/admin';

const DATE = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' });

/** Mint a single-use invite link. It's shown once — only its fingerprint stays on the server. */
export function InviteDialog({ trigger }: { trigger: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className={dialogOverlayClass} />
        <Dialog.Content className={dialogContentClass('sm')}>
          {open && <Invite onDone={() => setOpen(false)} />}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function Invite({ onDone }: { onDone: () => void }) {
  const [role, setRole] = useState<'member' | 'admin'>('member');
  const [days, setDays] = useState<`${(typeof INVITE_DAYS)[number]}`>('7');
  const mint = useMutation({
    mutationFn: async () => unwrap(await adminInvite({ body: { admin: role === 'admin', expires_days: Number(days) } })),
  });
  const inv = mint.data;
  const link = inv ? (inv.url ?? `${window.location.origin}/?invite=${encodeURIComponent(inv.code)}`) : '';

  return (
    <>
      <Dialog.Title className={dialogTitleClass}>Invite someone</Dialog.Title>
      {!inv ? (
        <>
          <Dialog.Description className="text-md leading-relaxed text-ink-muted">
            A link for one person’s first sign-in. They choose Discord or Google once and sign in with it from then on, with their own empty collection.
          </Dialog.Description>
          <div>
            <SettingsRow
              label="They join as"
              description={role === 'admin' ? 'Admins can invite people, turn features on, and use the owner-only parts.' : 'Members see the features you turn on for them.'}
              control={(ids) => <SettingsChoice {...ids} value={role} options={[{ value: 'member', label: 'Member' }, { value: 'admin', label: 'Admin' }]} onChange={setRole} />}
            />
            <SettingsRow
              label="Link works for"
              control={(ids) => <SettingsChoice {...ids} value={days} options={INVITE_DAYS.map((d) => ({ value: `${d}` as const, label: inviteDaysLabel(d) }))} onChange={setDays} />}
            />
          </div>
          {mint.error && <p role="alert" className="text-sm text-danger">{mint.error.message}</p>}
          <div className="flex flex-wrap justify-end gap-2">
            <Dialog.Close asChild><Button tone="paper" disabled={mint.isPending}>Cancel</Button></Dialog.Close>
            <Button emphasis="primary" disabled={mint.isPending} onClick={() => mint.mutate()}>{mint.isPending ? 'Making the link…' : 'Make invite link'}</Button>
          </div>
        </>
      ) : (
        <>
          <Dialog.Description className="text-md leading-relaxed">
            <span className="highlighter px-1 voice-semi font-medium">Shown once — copy it now.</span>{' '}
            It works for one {inv.admin ? 'admin' : 'member'} sign-in until {DATE.format(new Date(inv.expires_at))}. Send it privately: anyone with the link can use it.
          </Dialog.Description>
          <label className="flex flex-col gap-1.5 text-sm voice-semi text-ink-muted">
            Invite link
            <TextInput
              tone="paper"
              readOnly
              value={link}
              onFocus={(e) => e.currentTarget.select()}
            />
          </label>
          <div className="flex flex-wrap items-start justify-end gap-2">
            <CopyButton tone="paper" emphasis="primary" label="Copy link" getText={() => link} />
            <Button tone="paper" onClick={onDone}>Done</Button>
          </div>
        </>
      )}
    </>
  );
}

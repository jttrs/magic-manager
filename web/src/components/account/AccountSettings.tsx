import { useQuery } from '@tanstack/react-query';
import { AlertDialog } from 'radix-ui';
import { useId, useMemo, useState } from 'react';
import { markAccountReturn, takeAccountReturn } from '../../app/accountReturn';
import { meQuery } from '../../app/auth';
import { serverModeQuery } from '../../app/queries';
import { useSettingsSection } from '../../app/settings';
import { DELETE_CONSEQUENCES, DELETE_PHRASE, confirmMatches, exportFilename, reauthLinks, signInFresh } from '../../core/account';
import { accountDelete, accountExport } from '../../core/api';
import { ApiError, apiErrorFrom } from '../../core/apiError';
import { Button } from '../Button';
import { buttonClass } from '../buttonClass';
import { dialogContentClass, dialogOverlayClass, dialogTitleClass } from '../controls/surfaces';
import { TextInput } from '../controls/TextField';
import { SettingsRow } from '../settings/SettingsControls';

/** Registers Settings → Account: *Download my data* (both modes) and, hosted, *Delete my account*. */
export function AccountSettings() {
  const mode = useQuery(serverModeQuery());
  const hosted = mode.data === 'hosted';
  const section = useMemo(() => ({
    id: 'account',
    title: 'Account',
    order: 90,
    content: (
      <>
        <SettingsRow
          label="Download my data"
          description="One zip: a copy of your collection you can open with any SQLite tool, spreadsheets of your cards, decks, wishlist and purchase history, and a README."
          control={({ labelId }) => <DownloadButton labelId={labelId} />}
        />
        {hosted && (
          <SettingsRow
            label="Delete my account"
            description="Removes your collection and sign-in from this server for good."
            control={({ labelId }) => <DeleteAccount labelId={labelId} />}
          />
        )}
      </>
    ),
  }), [hosted]);
  useSettingsSection(section);
  return null;
}

function errorText(e: unknown): string {
  if (e instanceof ApiError) return e.ref && !e.message.includes(e.ref) ? `${e.message} (ref ${e.ref})` : e.message;
  return e instanceof Error ? e.message : 'Something went wrong. Try again.';
}

function DownloadButton({ labelId }: { labelId: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await accountExport({ parseAs: 'blob' });
      if (!r.response?.ok || !(r.data instanceof Blob)) throw apiErrorFrom(r.error, r.response);
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = exportFilename(r.response.headers.get('content-disposition'));
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex flex-col items-start gap-1 sm:items-end">
      <Button tone="paper" aria-describedby={labelId} disabled={busy} onClick={() => void run()}>
        {busy ? 'Packing…' : 'Download'}
      </Button>
      <p aria-live="polite" className="m-0 max-w-[18rem] text-sm text-danger empty:hidden">{error}</p>
    </div>
  );
}

function DeleteAccount({ labelId }: { labelId: string }) {
  // Back from "Sign in again": reopen the confirmation where the person left it.
  const [open, setOpen] = useState(() => takeAccountReturn());
  return (
    <AlertDialog.Root open={open} onOpenChange={setOpen}>
      <AlertDialog.Trigger asChild>
        <Button tone="paper" emphasis="danger" aria-describedby={labelId}>Delete account…</Button>
      </AlertDialog.Trigger>
      {open && <DeleteDialog />}
    </AlertDialog.Root>
  );
}

function DeleteDialog() {
  const me = useQuery(meQuery());
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const inputId = useId();
  const data = me.data;
  const minutes = data?.reauth_minutes ?? 10;
  // The server's clock decides (seconds left when /me was read); only elapsed time is local.
  const fresh = !stale && signInFresh(data?.reauth_seconds_left, me.dataUpdatedAt);
  const ok = confirmMatches(text);
  const here = `${window.location.pathname}${window.location.search}`;
  const links = reauthLinks(data?.providers ?? [], data?.user?.providers ?? [], here);

  const remove = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await accountDelete({ body: { confirm: text } });
      if (!r.response?.ok) throw apiErrorFrom(r.error, r.response);
      window.location.assign('/?auth_error=account_deleted');
    } catch (e) {
      if (e instanceof ApiError && e.code === 'auth.reauth_required') setStale(true);
      else setError(errorText(e));
      setBusy(false);
    }
  };

  return (
    <AlertDialog.Portal>
      <AlertDialog.Overlay className={dialogOverlayClass} />
      <AlertDialog.Content className={dialogContentClass('sm')}>
        <AlertDialog.Title className={dialogTitleClass}>
          Delete your account
        </AlertDialog.Title>
        <AlertDialog.Description asChild>
          <ul className="m-0 flex list-none flex-col p-0 text-md leading-relaxed">
            {DELETE_CONSEQUENCES.map((line) => (
              <li key={line} className="border-b border-rule py-2 last:border-b-0">{line}</li>
            ))}
          </ul>
        </AlertDialog.Description>
        {fresh ? (
          <div className="flex flex-col gap-1.5 border-t-2 border-rule-strong pt-3">
            <label htmlFor={inputId} className="text-sm text-ink-muted">
              Type <span className="font-semibold text-ink">{DELETE_PHRASE}</span> to confirm
            </label>
            <TextInput
              tone="paper"
              id={inputId}
              value={text}
              autoComplete="off"
              spellCheck={false}
              maxLength={64}
              disabled={busy}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && ok && !busy) void remove(); }}
            />
          </div>
        ) : (
          <div className="flex flex-col gap-2 border-t-2 border-rule-strong pt-3">
            <p className="m-0 text-md leading-relaxed">
              To make sure it’s you, sign in again first. You’ll come straight back here and have {minutes} minutes to finish.
            </p>
            <div className="flex flex-wrap gap-2">
              {links.map((l) => (
                <a key={l.href} href={l.href} onClick={() => markAccountReturn()} className={buttonClass('paper', 'quiet')}>
                  Sign in again with {l.title}
                </a>
              ))}
            </div>
          </div>
        )}
        {error && <p role="alert" className="m-0 text-sm text-danger">{error}</p>}
        <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
          <AlertDialog.Cancel asChild>
            <Button tone="paper" disabled={busy}>Cancel</Button>
          </AlertDialog.Cancel>
          {fresh && (
            <Button tone="paper" emphasis="danger-solid" disabled={!ok || busy} onClick={() => void remove()}>
              {busy ? 'Deleting…' : 'Delete my account'}
            </Button>
          )}
        </div>
      </AlertDialog.Content>
    </AlertDialog.Portal>
  );
}

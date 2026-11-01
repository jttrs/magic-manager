import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { adminUsersQuery, unwrap } from '../../app/queries';
import { Button } from '../../components/Button';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { SettingsChoice, SettingsGroup, SettingsRow } from '../../components/settings/SettingsControls';
import { adminDisable, adminEnable, adminSetFlag, adminSignOut, type AdminUserOut, type AdminUsersOut, type OwnerPathOut } from '../../core/api';
import { choiceValue, defaultChoiceLabel, flagChoice, flagTitle, ownerOnlyNote, providersLabel, roleLabel, seenLabel, statusLabel, unflaggedPaths, type FlagChoice } from '../../core/admin';

const DATE = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium' });

/** One person: who they are, their sign-in state, and their feature switches. */
export function UserInspector({ user, paths, self, onClose }: { user: AdminUserOut; paths: OwnerPathOut[]; self: boolean; onClose?: () => void }) {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [confirmOff, setConfirmOff] = useState(false);
  const put = (row: AdminUserOut) =>
    qc.setQueryData(adminUsersQuery().queryKey, (d: AdminUsersOut | undefined) => d && { ...d, users: d.users.map((u) => (u.id === row.id ? row : u)) });
  const path = { user_id: user.id };
  const begin = () => { setError(null); setNote(null); };

  const flag = useMutation({
    mutationFn: async ({ name, choice }: { name: string; choice: FlagChoice }) =>
      unwrap(await adminSetFlag({ path: { ...path, flag: name }, body: { value: choiceValue(choice) } })),
    onMutate: begin,
    onSuccess: (row, v) => { put(row); if (self) void qc.invalidateQueries({ queryKey: ['features'] }); setNote(`${flagTitle(v.name)}: ${v.choice === 'default' ? 'back to the default' : `turned ${v.choice}`} for ${user.display_name}.`); },
    onError: (e) => setError(e.message),
  });
  const signOut = useMutation({
    mutationFn: async () => unwrap(await adminSignOut({ path })),
    onMutate: begin,
    onSuccess: (r) => { setNote(r.ended ? `Signed out of ${r.ended === 1 ? '1 browser' : `${r.ended} browsers`}.` : 'Already signed out.'); void qc.invalidateQueries({ queryKey: adminUsersQuery().queryKey }); },
    onError: (e) => setError(e.message),
  });
  const enable = useMutation({
    mutationFn: async () => unwrap(await adminEnable({ path })),
    onMutate: begin,
    onSuccess: (row) => { put(row); setNote(`${user.display_name} can sign in again.`); },
    onError: (e) => setError(e.message),
  });
  const busy = flag.isPending || signOut.isPending || enable.isPending;
  const unflagged = unflaggedPaths(paths);

  return (
    <article aria-labelledby="admin-user-h" className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 pb-8">
      <header className="flex flex-col gap-1 border-b-2 border-rule-strong pb-2">
        {onClose && (
          <button type="button" onClick={onClose} className="mb-1 cursor-pointer self-start text-sm voice-semi text-ink-muted hover:text-ink">← People</button>
        )}
        <h2 id="admin-user-h" className="text-3xl voice-condensed font-bold leading-none">
          {user.display_name}
          {self && <span className="ml-2 text-md voice-semi font-normal text-ink-muted">(you)</span>}
        </h2>
        <p className="text-sm text-ink-muted">{user.email ?? 'No email shared'}</p>
      </header>

      <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-6 text-md">
        {([
          ['Role', roleLabel(user)],
          ['Signs in with', providersLabel(user)],
          ['Now', statusLabel(user)],
          ['Last seen', seenLabel(user.last_seen_at)],
          ['Joined', DATE.format(new Date(user.created_at))],
        ] as const).map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="ruled py-1.5 text-sm voice-semi uppercase tracking-[0.06em] text-ink-muted">{k}</dt>
            <dd className="ruled py-1.5 tabular">{v}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button tone="paper" disabled={busy || user.sessions === 0} onClick={() => signOut.mutate()}>Sign out everywhere</Button>
        {user.disabled_at ? (
          <Button tone="paper" disabled={busy} onClick={() => enable.mutate()}>Let them sign in again</Button>
        ) : (
          <Button tone="paper" disabled={busy || self} title={self ? 'You can’t turn yourself off' : undefined} onClick={() => setConfirmOff(true)}>Turn off sign-in</Button>
        )}
      </div>
      <div aria-live="polite" className="min-h-6 pt-2 text-sm">
        {error ? <p role="alert" className="text-danger">{error}</p> : note && <p><span className="highlighter px-1">{note}</span></p>}
      </div>

      <div className="mt-4">
        <SettingsGroup title="Features">
          {user.flags.map((f) => {
            const owner = ownerOnlyNote(f, paths, user.is_admin);
            return (
              <SettingsRow
                key={f.name}
                label={`${flagTitle(f.name)} — ${f.effective ? 'on' : 'off'}`}
                description={
                  <>
                    {f.about}
                    {owner && <span className="mt-1 block text-ink">{owner}</span>}
                  </>
                }
                control={(ids) => (
                  <SettingsChoice<FlagChoice>
                    {...ids}
                    value={flagChoice(f)}
                    options={[{ value: 'default', label: defaultChoiceLabel(f) }, { value: 'on', label: 'On' }, { value: 'off', label: 'Off' }]}
                    onChange={(choice) => { if (!busy) flag.mutate({ name: f.name, choice }); }}
                  />
                )}
              />
            );
          })}
        </SettingsGroup>
      </div>

      {unflagged.length > 0 && (
        <div className="mt-6">
          <SettingsGroup title="Owner-only">
            <ul className="flex flex-col">
              {unflagged.map((p) => (
                <li key={p.key} className="ruled flex items-baseline justify-between gap-4 py-2 text-md">
                  <span>{p.title}</span>
                  <span className="shrink-0 text-sm voice-semi text-ink-muted">{user.is_admin ? 'Yes — admin' : 'No — admins only'}</span>
                </li>
              ))}
            </ul>
            <p className="pt-2 text-sm leading-relaxed text-ink-muted">These use this server’s own computer and logins, so they stay with admins whatever the switches above say.</p>
          </SettingsGroup>
        </div>
      )}

      <ConfirmDialog
        open={confirmOff}
        onOpenChange={setConfirmOff}
        title={`Turn off ${user.display_name}?`}
        confirmLabel="Turn off sign-in"
        onConfirm={async () => {
          begin();
          put(unwrap(await adminDisable({ path })));
          setNote(`${user.display_name} is signed out and can’t sign in until you let them.`);
        }}
      >
        <p>They’re signed out everywhere and can’t sign in again until you let them. Their collection stays as it is.</p>
      </ConfirmDialog>
    </article>
  );
}

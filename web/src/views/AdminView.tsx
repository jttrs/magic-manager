import { useQuery } from '@tanstack/react-query';
import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { useMemo } from 'react';
import { meQuery } from '../app/auth';
import { adminUsersQuery, serverModeQuery } from '../app/queries';
import { useMediaQuery } from '../app/useMediaQuery';
import { ViewLayout } from '../components/AppShell';
import { ListRow } from '../components/controls/ListRow';
import { InviteMark } from '../components/icons/marks';
import { IconAction } from '../components/IconAction';
import { Segmented, SideSection, TextField } from '../components/Sidebar';
import { SplitPanes } from '../components/SplitPanes';
import { EmptyNote, ErrorNote, GuideSheet } from '../components/States';
import { filterUsers, roleLabel, seenLabel, SHOW_LABEL, SHOWS, showCounts, statusLabel, type AdminSearch, type Show } from '../core/admin';
import { fmtCount } from '../core/format';
import { InviteDialog } from './admin/InviteDialog';
import { UserInspector } from './admin/UserInspector';

const route = getRouteApi('/admin');

/** Hosted, admins only: who can sign in, invites, sign-outs, and per-person feature flags.
 *  Never anyone's collection (§25.0) — the server serves none of it here. */
export function AdminView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/admin' });
  const set = (patch: Partial<AdminSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const mode = useQuery(serverModeQuery());
  const me = useQuery({ ...meQuery(), enabled: mode.data === 'hosted' });
  const isAdmin = mode.data === 'hosted' && me.data?.user?.is_admin === true;
  const q = useQuery({ ...adminUsersQuery(), enabled: isAdmin });
  const narrow = useMediaQuery('(max-width: 47.99rem)');

  const users = useMemo(() => q.data?.users ?? [], [q.data]);
  const shown = useMemo(() => filterUsers(users, search), [users, search]);
  const counts = useMemo(() => showCounts(users), [users]);
  const open = users.find((u) => u.id === search.user);

  const sidebar = (
    <div className="flex flex-col gap-6">
      <SideSection title="Find" quiet>
        <TextField name="q" label="Name or email" value={search.q} placeholder="Search people…" onChange={(v) => set({ q: v })} />
      </SideSection>
      <SideSection title="Show" quiet>
        <Segmented<Show>
          label="Show"
          wrap
          value={search.show}
          options={SHOWS.map((s) => ({ value: s, label: `${SHOW_LABEL[s]} ${counts[s]}` }))}
          onChange={(v) => set({ show: v })}
        />
      </SideSection>
      <p className="text-sm leading-relaxed text-on-chrome-muted">
        Admins manage who can sign in and which features each person sees. Nobody — admins included — can open another person’s collection.
      </p>
    </div>
  );

  let body;
  if (mode.data && mode.data !== 'hosted') {
    body = <EmptyNote title="No sign-in on this computer">The Admin page manages people on the hosted app. Here, you’re the only person, so there’s nobody to manage.</EmptyNote>;
  } else if (me.data && !isAdmin) {
    body = <EmptyNote title="Only an admin can see this page">Ask an admin if you need a feature turned on.</EmptyNote>;
  } else if (q.error) {
    body = <ErrorNote error={q.error} onRetry={() => void q.refetch()} />;
  } else if (!q.data) {
    body = <p role="status" className="px-sheet py-6 text-md text-ink-muted">Reading the people list…</p>;
  } else {
    const list = (
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-sheet pb-6">
        <h2 className="border-b-2 border-rule-strong pb-1 text-2xl voice-condensed font-bold uppercase">People</h2>
        {shown.length ? (
          <ul aria-label="People">
            {shown.map((u) => {
              const active = u.id === search.user;
              return (
                <li key={u.id}>
                  <ListRow active={active} onClick={() => set({ user: u.id })} className="py-2">
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="flex items-baseline gap-2">
                        <span className={`truncate text-md voice-semi font-medium ${u.disabled_at ? 'text-ink-muted line-through decoration-rule-strong' : ''}`}>{u.display_name}</span>
                        <span className="shrink-0 text-xs voice-semi uppercase tracking-caps text-ink-muted">{roleLabel(u)}</span>
                      </span>
                      <span className="truncate text-sm text-ink-muted">{u.email ?? 'No email shared'}</span>
                    </span>
                    <span className="flex shrink-0 flex-col items-end text-xs tabular text-ink-muted">
                      <span>{statusLabel(u)}</span>
                      <span>seen {seenLabel(u.last_seen_at)}</span>
                    </span>
                  </ListRow>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mt-3 text-md text-ink-muted">Nobody matches. Clear the search or show everyone.</p>
        )}
      </div>
    );
    const inspector = open ? (
      <UserInspector user={open} paths={q.data.owner_paths} self={open.id === me.data?.user?.id} onClose={narrow ? () => set({ user: undefined }) : undefined} />
    ) : (
      <EmptyNote title="Pick a person">Their sign-in, sessions and feature switches show here.</EmptyNote>
    );
    body = narrow ? (open ? inspector : list) : <SplitPanes id="mm.admin.split" label="Resize people list" list={list} inspector={inspector} defaults={[38, 62]} />;
  }

  return (
    <ViewLayout label="People filters" summary={q.data ? fmtCount(shown.length, 'person', 'people') : undefined} sidebar={sidebar}>
      <GuideSheet
        title="Admin"
        actionsLabel="Admin actions"
        actions={isAdmin ? <InviteDialog trigger={<IconAction Icon={InviteMark} label="Invite someone" />} /> : undefined}
      >
        {body}
      </GuideSheet>
    </ViewLayout>
  );
}

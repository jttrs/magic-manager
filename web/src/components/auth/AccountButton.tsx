import { useQuery } from '@tanstack/react-query';
import { Popover } from 'radix-ui';
import { useState, type SVGProps } from 'react';
import { meQuery, signOut } from '../../app/auth';
import { serverModeQuery } from '../../app/queries';
import { Button } from '../Button';
import { IconAction } from '../IconAction';

function PersonIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" {...props}>
      <circle cx="8" cy="5.4" r="2.9" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M2.6 14.2c.6-2.9 2.8-4.5 5.4-4.5s4.8 1.6 5.4 4.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

/** Hosted mode: who's signed in and Sign out, behind one quiet masthead mark. Local mode: nothing. */
export function AccountButton() {
  const mode = useQuery(serverModeQuery());
  const me = useQuery({ ...meQuery(), enabled: mode.data === 'hosted' });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const user = me.data?.user;
  if (mode.data !== 'hosted' || !user) return null;
  const label = `Signed in as ${user.display_name}`;
  return (
    <Popover.Root onOpenChange={() => setError(null)}>
      <Popover.Trigger asChild>
        <IconAction label={label} Icon={PersonIcon} tone="chrome" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={6}
          collisionPadding={12}
          aria-label="Your account"
          className="z-50 flex w-[min(18rem,calc(100vw-1.5rem))] flex-col gap-3 rounded-sm border border-chrome-line bg-chrome-raised p-3 text-sm text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]"
        >
          <p className="m-0 flex min-w-0 flex-col gap-0.5">
            <span className="truncate text-md voice-semi font-medium">{user.display_name}</span>
            {user.email && <span className="truncate text-on-chrome-muted">{user.email}</span>}
            {user.is_admin && <span className="text-on-chrome-muted">Admin</span>}
          </p>
          {error && <p role="alert" className="m-0 text-danger">{error}</p>}
          <Button
            className="w-full"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                await signOut();
              } catch (e) {
                setError(e instanceof Error ? e.message : 'Couldn’t sign out. Try again.');
                setBusy(false);
              }
            }}
          >
            {busy ? 'Signing out…' : 'Sign out'}
          </Button>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

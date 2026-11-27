import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { Popover } from 'radix-ui';
import { useState } from 'react';
import { meQuery, signOut } from '../../app/auth';
import { serverModeQuery } from '../../app/queries';
import { Button } from '../Button';
import { buttonClass } from '../buttonClass';
import { IconAction } from '../IconAction';
import { PersonMark } from '../icons/marks';

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
        <IconAction label={label} Icon={PersonMark} tone="chrome" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={6}
          collisionPadding={12}
          aria-label="Your account"
          className="z-50 flex w-[min(18rem,calc(100vw-1.5rem))] flex-col gap-3 rounded-sm border border-chrome-line bg-chrome-raised p-3 text-sm text-on-chrome shadow-popover"
        >
          <p className="m-0 flex min-w-0 flex-col gap-0.5">
            <span className="truncate text-md voice-semi font-medium">{user.display_name}</span>
            {user.email && <span className="truncate text-on-chrome-muted">{user.email}</span>}
            {user.is_admin && <span className="text-on-chrome-muted">Admin</span>}
          </p>
          {error && <p role="alert" className="m-0 text-danger">{error}</p>}
          {user.is_admin && (
            <Popover.Close asChild>
              <Link to="/admin" className={`${buttonClass('chrome', 'quiet')} w-full`}>People and features</Link>
            </Popover.Close>
          )}
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

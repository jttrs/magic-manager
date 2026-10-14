import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState, type ReactNode } from 'react';
import { meQuery, onSignedOut } from '../../app/auth';
import { serverModeQuery } from '../../app/queries';
import type { MeOut } from '../../core/api';
import { authErrorMessage, loginHref, readSignInParams } from '../../core/auth';
import { buttonClass } from '../buttonClass';

/** Hosted mode: nothing of the app renders until someone is signed in. Local mode: a pass-through. */
export function AuthGate({ children }: { children: ReactNode }) {
  const mode = useQuery(serverModeQuery());
  if (mode.isPending) return <Stock />;
  // Unknown mode (features unreachable): let the app render and report its own errors.
  if (mode.data !== 'hosted') return <>{children}</>;
  return <HostedGate>{children}</HostedGate>;
}

function HostedGate({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const me = useQuery(meQuery());
  useEffect(() => onSignedOut(() => void qc.invalidateQueries({ queryKey: meQuery().queryKey })), [qc]);
  if (me.isPending) return <Stock />;
  if (me.data?.user) {
    forgetInvite();
    return <>{children}</>;
  }
  return <SignInScreen me={me.data ?? null} failed={me.isError} onRetry={() => void me.refetch()} />;
}

/** The bare chrome while we find out who you are (no flash of the app or the sheet). */
function Stock() {
  return <div className="min-h-dvh bg-chrome" aria-busy="true" />;
}

// The invite survives a cancelled or failed sign-in in this tab (the server's error
// redirect doesn't carry it back), and is forgotten once someone is signed in.
const INVITE_KEY = 'mm.invite';

function rememberInvite(invite: string | null): string | null {
  try {
    if (invite) window.sessionStorage.setItem(INVITE_KEY, invite);
    return invite ?? window.sessionStorage.getItem(INVITE_KEY);
  } catch {
    return invite;
  }
}

function forgetInvite() {
  try {
    window.sessionStorage.removeItem(INVITE_KEY);
  } catch {
    // storage unavailable: nothing was kept
  }
}

// Read the invite / error once and take them out of the address bar (the invite
// shouldn't linger in history or be copied along with the URL).
function useSignInParams() {
  const [params] = useState(() => {
    const p = readSignInParams(window.location.search);
    if (p.error === 'invite_invalid' && !p.invite) forgetInvite(); // a spent/expired invite: don't retry it
    return { ...p, invite: rememberInvite(p.invite) };
  });
  useEffect(() => {
    if (window.location.search.includes('invite=') || params.error) {
      window.history.replaceState(window.history.state, '', `${window.location.pathname}${params.rest}${window.location.hash}`);
    }
  }, [params]);
  return params;
}

function SignInScreen({ me, failed, onRetry }: { me: MeOut | null; failed: boolean; onRetry: () => void }) {
  const { invite, error, rest } = useSignInParams();
  const message = failed ? 'The server didn’t answer. Try again in a moment.' : authErrorMessage(error);
  const next = `${window.location.pathname}${rest}`;
  const providers = me?.providers ?? [];
  return (
    <main className="grid min-h-dvh place-items-start justify-items-center bg-chrome px-3 pb-10 pt-[clamp(1.5rem,14vh,9rem)] text-on-chrome">
      <section
        aria-labelledby="signin-title"
        className="paper-grain w-[min(27rem,100%)] rounded-sm bg-paper text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)]"
      >
        <header className="border-b-2 border-rule-strong px-6 pb-3 pt-6">
          <h1 id="signin-title" className="text-3xl voice-condensed font-bold leading-none tracking-[-0.01em]" translate="no">
            magic-manager
          </h1>
          <p className="mt-2 text-md leading-snug text-ink-muted">
            Your collection, set completion and decks — over the exact printings you own.
          </p>
        </header>
        <div className="flex flex-col gap-4 px-6 pb-6 pt-5">
          <p className="text-md leading-relaxed">
            {invite
              ? 'You’re invited. Choose the account you’ll sign in with from now on.'
              : 'Invite-only. Sign in with the account you joined with.'}
          </p>
          {message && <p role="alert" className="text-md leading-snug text-danger">{message}</p>}
          {failed ? (
            <button type="button" onClick={onRetry} className={`${buttonClass('paper')} min-h-11 w-full`}>Try again</button>
          ) : providers.length ? (
            <ul className="flex flex-col gap-2.5" aria-label="Sign in with">
              {providers.map((p) => (
                <li key={p.name}>
                  <a href={loginHref(p.login_url, invite, next)} className={`${buttonClass('paper')} min-h-11 w-full text-md no-underline`}>
                    Continue with {p.title}
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-md text-ink-muted">Sign-in isn’t set up on this server yet.</p>
          )}
          <p className="border-t border-rule pt-3 text-sm leading-relaxed text-ink-muted">
            From your Discord or Google account we keep only its id, your name and your email.
          </p>
        </div>
      </section>
    </main>
  );
}

// Hosted sign-in view-model (framework-free): the sign-in screen's messages and links,
// and reading the invite / error the server put in the URL. Local mode never uses it.

/** `?auth_error=<code>` from the sign-in routes → a plain sentence (problem + way out). */
const AUTH_ERRORS: Record<string, string> = {
  not_invited: 'That account isn’t on the invite list yet. Ask for an invite link, then sign in from it.',
  invite_invalid: 'That invite link can’t be used — it may have been used already or expired. Ask for a new one.',
  profiles_soon: 'Profiles open soon — for now only the admin can sign in.',
  disabled: 'This profile is turned off. Ask the admin if that’s a mistake.',
  denied: 'Sign-in was cancelled. Choose a provider to try again.',
  state: 'That sign-in took too long or was started in another tab. Start again.',
  rate_limited: 'Too many sign-in attempts. Wait a minute, then try again.',
  provider_unavailable: 'That sign-in option isn’t set up on this server. Try the other one.',
  provider_error: 'The provider didn’t complete the sign-in. Try again in a moment.',
  id_token: 'The provider’s sign-in couldn’t be verified. Start again.',
  profile_unavailable: 'Your collection couldn’t be opened on this server. Try again in a moment, or ask the admin.',
};

export function authErrorMessage(code: string | null | undefined): string | null {
  if (!code) return null;
  return AUTH_ERRORS[code] ?? 'Sign-in didn’t finish. Start again.';
}

export type SignInParams = { invite: string | null; error: string | null; rest: string };

const INVITE_RE = /^[A-Za-z0-9_-]{16,128}$/;

/** Pull `invite` and `auth_error` out of a query string; `rest` is the query without them. */
export function readSignInParams(search: string): SignInParams {
  const p = new URLSearchParams(search);
  const rawInvite = p.get('invite');
  const invite = rawInvite && INVITE_RE.test(rawInvite) ? rawInvite : null;
  const error = p.get('auth_error');
  p.delete('invite');
  p.delete('auth_error');
  const rest = p.toString();
  return { invite, error: error && /^[a-z_]{1,40}$/.test(error) ? error : error ? 'unknown' : null, rest: rest ? `?${rest}` : '' };
}

/** Where a provider button goes: the server's login route + the invite + the page to return to. */
export function loginHref(loginUrl: string, invite: string | null, next: string): string {
  const q = new URLSearchParams();
  if (invite) q.set('invite', invite);
  if (next && next !== '/' && next.startsWith('/') && !next.startsWith('//')) q.set('next', next);
  const qs = q.toString();
  return qs ? `${loginUrl}?${qs}` : loginUrl;
}

/** Is this API error "you're signed out" (the session ended or expired)? */
export function isSignedOut(error: unknown): boolean {
  return Boolean(error && typeof error === 'object' && (error as { code?: unknown }).code === 'auth.required');
}

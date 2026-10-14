// Hosted sign-in wiring: who's signed in, the CSRF header on every write, and
// noticing when the session ends. Local mode never fetches /api/auth/me.
import { queryOptions } from '@tanstack/react-query';
import { authLogout, authMe } from '../core/api';
import { client } from '../core/api/client.gen';
import { apiErrorFrom } from '../core/apiError';
import { unwrap } from './queries';

let csrfToken: string | null = null;
const signedOutListeners = new Set<() => void>();

/** Every write while signed in carries the session's CSRF token (the server checks it). */
client.interceptors.request.use((req) => {
  if (csrfToken && req.method !== 'GET' && req.method !== 'HEAD' && !req.headers.has('X-CSRF-Token')) {
    req.headers.set('X-CSRF-Token', csrfToken);
  }
  return req;
});

/** A 401 means the session ended (expired, signed out elsewhere, revoked): show sign-in. */
client.interceptors.response.use((res) => {
  if (res.status === 401 && csrfToken) for (const fn of signedOutListeners) fn();
  return res;
});

export function onSignedOut(fn: () => void): () => void {
  signedOutListeners.add(fn);
  return () => signedOutListeners.delete(fn);
}

export const meQuery = () =>
  queryOptions({
    queryKey: ['auth', 'me'],
    queryFn: async ({ signal }) => {
      const me = unwrap(await authMe({ signal }));
      csrfToken = me.csrf_token ?? null;
      return me;
    },
    staleTime: Infinity,
    retry: 1,
  });

/** End this session on the server, then reload to the sign-in screen. */
export async function signOut(): Promise<void> {
  const r = await authLogout();
  if (!r.response?.ok) throw apiErrorFrom(r.error, r.response);
  csrfToken = null;
  window.location.assign('/');
}

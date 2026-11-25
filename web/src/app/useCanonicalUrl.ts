import { useRouter, useRouterState } from '@tanstack/react-router';
import { useEffect } from 'react';
import { stringifySearch } from './urlCodec';

/** Rewrites an old-style link (lists written as JSON, e.g. `families=%5B%22dft%22…`) to the
 *  short form the app writes today (`families=dft,…`), in place — no new history entry, no
 *  reload. The router already reads both forms (and its own `location.searchStr` is already
 *  re-written), so compare against what the address bar actually shows. */
export function useCanonicalUrl() {
  const router = useRouter();
  const search = useRouterState({ select: (s) => s.location.search });
  useEffect(() => {
    const canonical = stringifySearch(search);
    // Compare normalized, not raw: the same search can be encoded more than one way (`'` vs
    // `%27`, `%20` vs `+`), and a browser that re-encodes what it shows must not make the
    // canonical form look different on every render.
    if (same(canonical, window.location.search)) return;
    router.history.replace(`${window.location.pathname}${canonical}${window.location.hash}`);
  }, [router, search]);
}

const same = (a: string, b: string) => new URLSearchParams(a).toString() === new URLSearchParams(b).toString();

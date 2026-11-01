import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import {
  CompanionError, isOlder, onHello, ping, request, type CompanionHello, type CompanionKind, type ErrorCatalog, type RequestParams,
} from '../core/companion';
import { ApiError } from '../core/apiError';
import { trackCompanionError } from './analytics';
import { companionInfoQuery } from './queries';
import { reportScraperFailure } from './scraperHealth';

export type CompanionState = {
  /** checking: waiting for the bridge to say hello; absent: no paired companion on this page. */
  status: 'checking' | 'absent' | 'ready';
  hello: CompanionHello | null;
  /** The version in this app's repo (an older install should update). */
  latest: string | null;
  /** The Chrome Web Store page (the primary install), once published; null until then. */
  storeUrl: string | null;
  privacyUrl: string | null;
  outdated: boolean;
  catalog: ErrorCatalog;
  /** Ask the companion to read; resolves after you approve in its window. */
  read: <K extends CompanionKind>(kind: K, params?: RequestParams, onAwaiting?: (summary: string) => void, opts?: { ackTimeoutMs?: number }) => ReturnType<typeof request<K>>;
};

const EMPTY: ErrorCatalog = {};

/** The browser companion as this page sees it (detected via its bridge's hello). */
export function useCompanion(): CompanionState {
  const info = useQuery(companionInfoQuery());
  const qc = useQueryClient();
  const catalog = (info.data?.errors as ErrorCatalog | undefined) ?? EMPTY;
  const [hello, setHello] = useState<CompanionHello | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const off = onHello(window, setHello);
    ping(window);
    const t = window.setTimeout(() => setChecked(true), 1200);
    return () => { off(); window.clearTimeout(t); };
  }, []);

  const read = useCallback(
    <K extends CompanionKind>(kind: K, params: RequestParams = {}, onAwaiting?: (summary: string) => void, opts: { ackTimeoutMs?: number } = {}) =>
      request(window, kind, params, { catalog, onAwaitingApproval: onAwaiting, ...opts }).catch((e: unknown) => {
        if (e instanceof CompanionError) {
          trackCompanionError(e.code);
          void reportScraperFailure(e.code, qc, kind === 'cart' ? params.store : undefined);   // a changed page flags that read "temporarily down"
        }
        throw e;
      }),
    [catalog, qc],
  );

  const latest = info.data?.version ?? null;
  return {
    status: hello ? 'ready' : checked ? 'absent' : 'checking',
    hello,
    latest,
    storeUrl: info.data?.store_url ?? null,
    privacyUrl: info.data?.privacy_url ?? null,
    outdated: Boolean(hello && latest && isOlder(hello.version, latest)),
    catalog,
    read,
  };
}

/** A failure's message, its fix, its code and (server errors) the request ref to quote. */
export function errorText(e: unknown): { message: string; fix: string | null; code: string | null; ref: string | null; detail: string | null } {
  if (e instanceof CompanionError) return { message: e.message, fix: e.fix, code: e.code, ref: null, detail: e.detail };
  if (e instanceof ApiError) {
    const d = e.detail as { fix?: unknown } | null | undefined;
    const fix = d && typeof d === 'object' && typeof d.fix === 'string' ? d.fix : null;
    return { message: e.message, fix, code: e.code, ref: e.ref, detail: null };
  }
  return { message: (e as Error)?.message || 'Something went wrong.', fix: null, code: null, ref: null, detail: null };
}

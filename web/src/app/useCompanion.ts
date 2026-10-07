import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import {
  CompanionError, isOlder, onHello, ping, request, type CompanionHello, type CompanionKind, type ErrorCatalog,
} from '../core/companion';
import { ApiError } from '../core/apiError';
import { trackCompanionError } from './analytics';
import { companionInfoQuery } from './queries';

export type CompanionState = {
  /** checking: waiting for the bridge to say hello; absent: no paired companion on this page. */
  status: 'checking' | 'absent' | 'ready';
  hello: CompanionHello | null;
  /** The version in this app's repo (an older install should update). */
  latest: string | null;
  outdated: boolean;
  catalog: ErrorCatalog;
  /** Ask the companion to read; resolves after you approve in its window. */
  read: <K extends CompanionKind>(kind: K, params?: { url?: string }, onAwaiting?: (summary: string) => void) => ReturnType<typeof request<K>>;
};

const EMPTY: ErrorCatalog = {};

/** The browser companion as this page sees it (detected via its bridge's hello). */
export function useCompanion(): CompanionState {
  const info = useQuery(companionInfoQuery());
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
    <K extends CompanionKind>(kind: K, params: { url?: string } = {}, onAwaiting?: (summary: string) => void) =>
      request(window, kind, params, { catalog, onAwaitingApproval: onAwaiting }).catch((e: unknown) => {
        if (e instanceof CompanionError) trackCompanionError(e.code);
        throw e;
      }),
    [catalog],
  );

  const latest = info.data?.version ?? null;
  return {
    status: hello ? 'ready' : checked ? 'absent' : 'checking',
    hello,
    latest,
    outdated: Boolean(hello && latest && isOlder(hello.version, latest)),
    catalog,
    read,
  };
}

/** A failure's message, its fix, its code and (server errors) the request ref to quote. */
export function errorText(e: unknown): { message: string; fix: string | null; code: string | null; ref: string | null } {
  if (e instanceof CompanionError) return { message: e.message, fix: e.fix, code: e.code, ref: null };
  if (e instanceof ApiError) {
    const d = e.detail as { fix?: unknown } | null | undefined;
    const fix = d && typeof d === 'object' && typeof d.fix === 'string' ? d.fix : null;
    return { message: e.message, fix, code: e.code, ref: e.ref };
  }
  return { message: (e as Error)?.message || 'Something went wrong.', fix: null, code: null, ref: null };
}

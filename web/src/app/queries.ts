// Server state via TanStack Query over the generated, typed API client.
import { keepPreviousData, queryOptions } from '@tanstack/react-query';
import { cardDiff, cardDiffFamilies, commanders, compare, listJobs } from '../core/api';
import type { Pool } from '../core/search';

class ApiError extends Error {}

function unwrap<T>(r: { data?: T; error?: unknown; response?: Response }): T {
  if (r.error !== undefined || r.data === undefined) {
    const detail = (r.error as { detail?: unknown } | undefined)?.detail;
    const msg = typeof detail === 'string' ? detail : `Request failed (${r.response?.status ?? 'network'})`;
    throw new ApiError(msg);
  }
  return r.data;
}

export const commanderSearchQuery = (q: string) =>
  queryOptions({
    queryKey: ['commanders', q],
    queryFn: async ({ signal }) => unwrap(await commanders({ query: { q, limit: 12 }, signal })),
    enabled: q.trim().length >= 2,
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });

export const compareQuery = (a?: string, b?: string) =>
  queryOptions({
    queryKey: ['compare', a, b],
    queryFn: async ({ signal }) => unwrap(await compare({ query: { a: a!, b: b! }, signal })),
    enabled: Boolean(a && b),
    staleTime: 5 * 60_000,
  });

export const familiesQuery = () =>
  queryOptions({
    queryKey: ['card-diff', 'families'],
    queryFn: async ({ signal }) => unwrap(await cardDiffFamilies({ signal })),
    staleTime: 5 * 60_000,
  });

export const cardDiffQuery = (families: string[], chase: 'exclude' | 'include' | 'only', pools?: Pool[]) =>
  queryOptions({
    queryKey: ['card-diff', families, chase, pools],
    queryFn: async ({ signal }) =>
      unwrap(await cardDiff({ query: { families, chase, ...(pools ? { pools } : {}) }, signal })),
    enabled: families.length > 0,
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  });

export const jobsQuery = () =>
  queryOptions({
    queryKey: ['jobs'],
    queryFn: async ({ signal }) => unwrap(await listJobs({ signal })),
    // Poll only while something is still running.
    refetchInterval: (q) => (q.state.data?.some((j) => j.status === 'queued' || j.status === 'running') ? 3_000 : false),
  });

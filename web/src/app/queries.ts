// Server state via TanStack Query over the generated, typed API client.
import { keepPreviousData, queryOptions } from '@tanstack/react-query';
import { collection, collectionFamilies, commanders, compare, ingestPrecons, ingestSearch, listJobs } from '../core/api';

class ApiError extends Error {}

export function unwrap<T>(r: { data?: T; error?: unknown; response?: Response }): T {
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
    queryKey: ['collection', 'families'],
    queryFn: async ({ signal }) => unwrap(await collectionFamilies({ signal })),
    staleTime: 5 * 60_000,
  });

export const collectionQuery = (families: string[]) =>
  queryOptions({
    queryKey: ['collection', [...families].sort()],
    queryFn: async ({ signal }) => unwrap(await collection({ query: { families }, signal })),
    enabled: families.length > 0,
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });

export const jobsQuery = () =>
  queryOptions({
    queryKey: ['jobs'],
    queryFn: async ({ signal }) => unwrap(await listJobs({ signal })),
    // Poll only while something is still running.
    refetchInterval: (q) => (q.state.data?.some((j) => j.status === 'queued' || j.status === 'running') ? 3_000 : false),
  });

export const printingSearchQuery = (q: string) =>
  queryOptions({
    queryKey: ['ingest', 'search', q.trim().toLowerCase()],
    queryFn: async ({ signal }) => unwrap(await ingestSearch({ query: { q: q.trim(), limit: 60 }, signal })),
    enabled: q.trim().length >= 2,
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });

export const preconCatalogQuery = (q: string) =>
  queryOptions({
    queryKey: ['ingest', 'precons', q.trim().toLowerCase()],
    queryFn: async ({ signal }) => unwrap(await ingestPrecons({ query: { q: q.trim(), limit: 40 }, signal })),
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  });

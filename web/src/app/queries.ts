// Server state via TanStack Query over the generated, typed API client.
import { keepPreviousData, queryOptions } from '@tanstack/react-query';
import type { DraftCardIn } from '../core/api';
import { cartSetup, featuresRoute, marketCards, marketDeck, marketProducts, marketProductTree, cardHoldings, collection, deckCheck, exploreCard, exploreSearch, deckSuggestions, collectionFamilies, commanders, compare, deckDetail, deckList, ingestPrecons, ingestSearch, listJobs } from '../core/api';

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
    queryKey: ['compare', a, b ?? null],
    queryFn: async ({ signal }) => unwrap(await compare({ query: { a: a!, ...(b ? { b } : {}) }, signal })),
    enabled: Boolean(a),
    staleTime: 5 * 60_000,
  });

export const exploreCardQuery = (a?: string, b?: string) =>
  queryOptions({
    queryKey: ['explore', 'card', a, b ?? null],
    queryFn: async ({ signal }) => unwrap(await exploreCard({ query: { a: a!, ...(b ? { b } : {}) }, signal })),
    enabled: Boolean(a),
    staleTime: 5 * 60_000,
  });

export const cardSearchQuery = (q: string) =>
  queryOptions({
    queryKey: ['explore', 'search', q],
    queryFn: async ({ signal }) => unwrap(await exploreSearch({ query: { q, limit: 12 }, signal })),
    enabled: q.trim().length >= 2,
    staleTime: 60_000,
    placeholderData: keepPreviousData,
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

export const holdingsQuery = (scryfallId: string | null | undefined) =>
  queryOptions({
    queryKey: ['holdings', scryfallId],
    queryFn: async ({ signal }) => unwrap(await cardHoldings({ path: { scryfall_id: scryfallId! }, signal })),
    enabled: Boolean(scryfallId),
    staleTime: 30_000,
  });

export const deckCheckQuery = (slug: string, cards: DraftCardIn[], combos: boolean) =>
  queryOptions({
    queryKey: ['decks', 'check', slug, cards, combos],
    queryFn: async ({ signal }) => unwrap(await deckCheck({ path: { slug }, body: { cards, combos }, signal })),
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  });

export const suggestionsQuery = (commander: string | null) =>
  queryOptions({
    queryKey: ['decks', 'suggestions', commander],
    queryFn: async ({ signal }) => unwrap(await deckSuggestions({ query: { commander: commander! }, signal })),
    enabled: Boolean(commander),
    staleTime: 10 * 60_000,
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

export const featuresQuery = () =>
  queryOptions({
    queryKey: ['features'],
    queryFn: async ({ signal }) => unwrap(await featuresRoute({ signal })).flags,
    staleTime: Infinity,
  });

export const cartSetupQuery = (enabled: boolean) =>
  queryOptions({
    queryKey: ['cart', 'setup'],
    queryFn: async ({ signal }) => unwrap(await cartSetup({ signal })),
    enabled,
    staleTime: Infinity,
  });

export const marketProductsQuery = (code?: string) =>
  queryOptions({
    queryKey: ['market', 'products', code],
    queryFn: async ({ signal }) => unwrap(await marketProducts({ query: { code: code! }, signal })),
    enabled: Boolean(code),
    staleTime: 10 * 60_000,
  });

export const productTreeQuery = (set: string, name: string, enabled: boolean) =>
  queryOptions({
    queryKey: ['market', 'tree', set, name],
    queryFn: async ({ signal }) => unwrap(await marketProductTree({ query: { set, name }, signal })),
    enabled,
    staleTime: 10 * 60_000,
  });

export const marketCardsQuery = (code?: string) =>
  queryOptions({
    queryKey: ['market', 'cards', code],
    queryFn: async ({ signal }) => unwrap(await marketCards({ query: { code: code! }, signal })),
    enabled: Boolean(code),
    staleTime: 5 * 60_000,
  });

export const deckCostQuery = (slug?: string) =>
  queryOptions({
    queryKey: ['market', 'deck', slug],
    queryFn: async ({ signal }) => unwrap(await marketDeck({ query: { slug: slug! }, signal })),
    enabled: Boolean(slug),
    staleTime: 60_000,
  });

export const decksQuery = () =>
  queryOptions({
    queryKey: ['decks'],
    queryFn: async ({ signal }) => unwrap(await deckList({ signal })),
    staleTime: 60_000,
  });

export const deckQuery = (slug?: string) =>
  queryOptions({
    queryKey: ['decks', slug],
    queryFn: async ({ signal }) => unwrap(await deckDetail({ path: { slug: slug! }, signal })),
    enabled: Boolean(slug),
    staleTime: 60_000,
  });

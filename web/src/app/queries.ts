// Server state via TanStack Query over the generated, typed API client.
import { keepPreviousData, queryOptions } from '@tanstack/react-query';
import type { DraftCardIn } from '../core/api';
import { apiErrorFrom } from '../core/apiError';
import type { RankingPageRequest } from '../core/rankings';
import { adminUsers, analyticsConsent, analyticsSummary, analyticsCatalog, dealsTabs, dealsWatched, marketProductCost, marketSecretLair, undoInfo, cartSetup, featuresRoute, marketCards, marketDeck, marketProducts, marketProductTree, cardHoldings, cardFloors, collection, deckCheck, exploreCard, exploreSearch, deckSuggestions, collectionFamilies, commanders, compare, deckDetail, deckList, ingestPrecons, ingestSearch, listJobs, historyList, historyEvent, historyRevertPlan, exploreRanking, exploreRankingOptions, cardCombos, deckCombos, draftCombos, artTags, artSwaps, jumpstartView, recipeList, recipeDetail, surfOptions, companionInfo, scrapersHealth, purchaseStores, purchaseList, purchaseReview, cardEarmarksList, deckEarmarks } from '../core/api';

export function unwrap<T>(r: { data?: T; error?: unknown; response?: Response }): T {
  if (r.error !== undefined || r.data === undefined) throw apiErrorFrom(r.error, r.response);
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

/** A cached EDHREC ranking (never fetches; `cached: false` → run the `edhrec.rankings` job). */
export const rankingQuery = (req: RankingPageRequest | null) =>
  queryOptions({
    queryKey: ['explore', 'ranking', req],
    queryFn: async ({ signal }) => unwrap(await exploreRanking({ query: req!, signal })),
    enabled: req != null,
    // A never-read answer is always stale, so returning to the view re-checks the server
    // instead of re-running a job another visit already finished.
    staleTime: (q) => (q.state.data?.cached ? 5 * 60_000 : 0),
    placeholderData: keepPreviousData,
  });

export const rankingOptionsQuery = () =>
  queryOptions({
    queryKey: ['explore', 'ranking-options'],
    queryFn: async ({ signal }) => unwrap(await exploreRankingOptions({ signal })),
    staleTime: 60 * 60_000,
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

/** The cheapest nonfoil + foil printing of the card behind each printing id —
 *  local prices, or every set on Scryfall when `live`. */
export const cardFloorsQuery = (scryfallIds: string[], live = false) =>
  queryOptions({
    queryKey: ['card-floors', scryfallIds, live],
    queryFn: async ({ signal }) => unwrap(await cardFloors({ body: { scryfall_ids: scryfallIds, live }, signal })),
    enabled: scryfallIds.length > 0,
    staleTime: live ? 30 * 60_000 : 60_000,
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

export const undoQuery = () =>
  queryOptions({
    queryKey: ['undo'],
    queryFn: async ({ signal }) => unwrap(await undoInfo({ signal })),
    staleTime: 10_000,
    // Appears after the session's first change; a slow poll keeps the header honest.
    refetchInterval: 30_000,
  });

export const featuresQuery = () =>
  queryOptions({
    queryKey: ['features'],
    queryFn: async ({ signal }) => unwrap(await featuresRoute({ signal })),
    select: (d) => d.flags,
    staleTime: Infinity,
  });

/** Owner-machine paths (`owner_machine.PATHS`) → may you use them here (the same /api/features call).
 *  Locally always yes; hosted, admins only — whatever the flags say. */
export const ownerPathsQuery = () =>
  queryOptions({
    queryKey: ['features'],
    queryFn: async ({ signal }) => unwrap(await featuresRoute({ signal })),
    select: (d) => ({ paths: d.owner_paths ?? {}, hosted: d.mode === 'hosted' }),
    staleTime: Infinity,
  });

/** Hosted, admins only: everyone who can sign in, with their flags (the Admin page). */
export const adminUsersQuery = () =>
  queryOptions({
    queryKey: ['admin', 'users'],
    queryFn: async ({ signal }) => unwrap(await adminUsers({ signal })),
    staleTime: 30_000,
  });

/** `hosted` = sign-in required; `local` = no login (the same one /api/features call). */
export const serverModeQuery = () =>
  queryOptions({
    queryKey: ['features'],
    queryFn: async ({ signal }) => unwrap(await featuresRoute({ signal })),
    select: (d) => d.mode ?? 'local',
    staleTime: Infinity,
  });

/** The companion version in this repo + the error catalog (unflagged). */
export const companionInfoQuery = () =>
  queryOptions({
    queryKey: ['companion', 'info'],
    queryFn: async ({ signal }) => unwrap(await companionInfo({ signal })),
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

export const deckCostQuery = (slug?: string, live = false) =>
  queryOptions({
    queryKey: ['market', 'deck', slug, live],
    queryFn: async ({ signal }) => unwrap(await marketDeck({ query: { slug: slug!, live }, signal })),
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

export const watchedQuery = () =>
  queryOptions({
    queryKey: ['deals', 'watched'],
    queryFn: async ({ signal }) => unwrap(await dealsWatched({ signal })),
    staleTime: 60_000,
  });

/** The open-tabs read. Disabled: only the explicit "Read my open tabs" refetches it. */
export const dealsTabsQuery = () =>
  queryOptions({
    queryKey: ['deals', 'tabs'],
    queryFn: async () => unwrap(await dealsTabs({ query: { browser: 'chrome' } })),
    enabled: false,
    retry: false,
    staleTime: Infinity,
    gcTime: 30 * 60_000,
  });

/** What a sealed product / Secret Lair drop is worth (server-memoized 30 min). */
export const secretLairQuery = (limit: number) =>
  queryOptions({
    queryKey: ['market', 'secret-lair', limit],
    queryFn: async ({ signal }) => unwrap(await marketSecretLair({ query: { limit }, signal })),
    staleTime: 30 * 60_000,
  });

export const productCostQuery = (kind: 'sealed' | 'sld', set: string, name: string, finish: string | null) =>
  queryOptions({
    queryKey: ['market', 'product-cost', kind, set, name, finish],
    queryFn: async ({ signal }) => unwrap(await marketProductCost({ query: { kind, set, name, finish }, signal })),
    staleTime: 30 * 60_000,
    retry: 1,
  });

export const historyQuery = () =>
  queryOptions({
    queryKey: ['history'],
    queryFn: async ({ signal }) => unwrap(await historyList({ signal })),
    staleTime: 30_000,
  });

/** What reverting this import would do (the engine's dry run). Always fresh. */
export const revertPlanQuery = (ingestId: number, enabled: boolean) =>
  queryOptions({
    queryKey: ['history', ingestId, 'revert'],
    queryFn: async ({ signal }) => unwrap(await historyRevertPlan({ path: { ingest_id: ingestId }, signal })),
    enabled,
    staleTime: 0,
  });

export const historyEventQuery = (ingestId?: number) =>
  queryOptions({
    queryKey: ['history', ingestId],
    queryFn: async ({ signal }) => unwrap(await historyEvent({ path: { ingest_id: ingestId! }, signal })),
    enabled: ingestId != null,
    staleTime: 30_000,
  });

/** Order history (purchases flag): what each store's reader can be trusted for. */
export const purchaseStoresQuery = (enabled: boolean) =>
  queryOptions({
    queryKey: ['purchases', 'stores'],
    queryFn: async ({ signal }) => unwrap(await purchaseStores({ signal })),
    enabled,
    staleTime: Infinity,
  });

/** Every store order read so far, with the paid / worth / gain totals. */
export const purchasesQuery = (enabled: boolean) =>
  queryOptions({
    queryKey: ['purchases'],
    queryFn: async ({ signal }) => unwrap(await purchaseList({ signal })),
    enabled,
    staleTime: 30_000,
  });

export const purchaseReviewQuery = (id: number | undefined, enabled: boolean) =>
  queryOptions({
    queryKey: ['purchases', id],
    queryFn: async ({ signal }) => unwrap(await purchaseReview({ path: { purchase_id: id! }, signal })),
    enabled: enabled && id != null,
    staleTime: 30_000,
  });

export const deckCombosQuery = (slug: string | undefined, enabled = true) =>
  queryOptions({
    queryKey: ['decks', slug, 'combos'],
    queryFn: async ({ signal }) => unwrap(await deckCombos({ path: { slug: slug! }, signal })),
    enabled: Boolean(slug) && enabled,
    staleTime: 10 * 60_000,
  });

export const draftCombosQuery = (cards: DraftCardIn[]) =>
  queryOptions({
    queryKey: ['combos', 'draft', cards],
    queryFn: async ({ signal }) => unwrap(await draftCombos({ body: { cards }, signal })),
    staleTime: 10 * 60_000,
    placeholderData: keepPreviousData,
  });

export const cardCombosQuery = (name: string | undefined, enabled = true) =>
  queryOptions({
    queryKey: ['combos', 'card', name],
    queryFn: async ({ signal }) => unwrap(await cardCombos({ query: { name: name! }, signal })),
    enabled: Boolean(name) && enabled,
    staleTime: 10 * 60_000,
  });

export const artTagsQuery = (q: string) =>
  queryOptions({
    queryKey: ['art', 'tags', q],
    queryFn: async ({ signal }) => unwrap(await artTags({ query: { q, limit: 8 }, signal })),
    staleTime: 10 * 60_000,
    placeholderData: keepPreviousData,
  });

export const artSwapsQuery = (tag: string | null, sids: string[]) =>
  queryOptions({
    queryKey: ['art', 'swaps', tag, sids],
    queryFn: async ({ signal }) =>
      unwrap(await artSwaps({ body: { tag: tag!, cards: sids.map((scryfall_id) => ({ scryfall_id, board: 'main', finish: 'either', count: 1 })) }, signal })),
    enabled: !!tag && sids.length > 0,
    staleTime: 10 * 60_000,
    placeholderData: keepPreviousData,
  });

export const recipesQuery = () =>
  queryOptions({
    // Under the decks root, so every deck write's invalidateQueries(['decks']) refreshes the list.
    queryKey: ['decks', { recipes: 'list' }],
    queryFn: async ({ signal }) => unwrap(await recipeList({ signal })),
    staleTime: 60_000,
  });

export const recipeQuery = (fileName?: string) =>
  queryOptions({
    queryKey: ['decks', { recipe: fileName }],
    queryFn: async ({ signal }) => unwrap(await recipeDetail({ path: { file_name: fileName! }, signal })),
    enabled: Boolean(fileName),
    staleTime: 60_000,
  });

/** One Jumpstart set's shopping-list totals (the Buy strip in Decks). */
export const jumpstartQuery = (code?: string) =>
  queryOptions({
    queryKey: ['jumpstart', code],
    queryFn: async ({ signal }) => unwrap(await jumpstartView({ path: { code: code! }, signal })),
    enabled: Boolean(code),
    staleTime: 30_000,
  });

export const surfOptionsQuery = () =>
  queryOptions({
    queryKey: ['surf', 'options'],
    queryFn: async ({ signal }) => unwrap(await surfOptions({ signal })),
    staleTime: 60 * 60_000,
  });

export const consentQuery = () =>
  queryOptions({
    queryKey: ['analytics', 'consent'],
    queryFn: async ({ signal }) => unwrap(await analyticsConsent({ signal })),
    staleTime: 5 * 60_000,
    retry: 0,
  });

export const analyticsCatalogQuery = () =>
  queryOptions({
    queryKey: ['analytics', 'catalog'],
    queryFn: async ({ signal }) => unwrap(await analyticsCatalog({ signal })),
    staleTime: 60 * 60_000,
  });

export const analyticsSummaryQuery = (days: number) =>
  queryOptions({
    queryKey: ['analytics', 'summary', days],
    queryFn: async ({ signal }) => unwrap(await analyticsSummary({ query: { days }, signal })),
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });

/** Every scraper's health (docs/scraper-health.md) — drives the "temporarily down" notices. */
export const scraperHealthQuery = () =>
  queryOptions({
    queryKey: ['scrapers', 'health'],
    queryFn: async ({ signal }) => unwrap(await scrapersHealth({ signal })),
    staleTime: 5 * 60_000,
  });

/** Every earmarked card (small; the inspector, Explore and marks all share it). */
export const cardEarmarksQuery = () =>
  queryOptions({
    queryKey: ['cardEarmarks'],
    queryFn: async ({ signal }) => unwrap(await cardEarmarksList({ signal })),
    staleTime: 60_000,
  });

/** Earmarked cards for a deck being edited, filtered on the draft's format + commander. */
export const deckEarmarksQuery = (slug: string, cards: DraftCardIn[]) =>
  queryOptions({
    queryKey: ['cardEarmarks', 'deck', slug, cards],
    queryFn: async ({ signal }) => unwrap(await deckEarmarks({ path: { slug }, body: { cards }, signal })),
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });

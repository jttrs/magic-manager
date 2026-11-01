import { queryOptions, useMutation, useQueries, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import { dealsTabsQuery, productCostQuery, unwrap, watchedQuery } from '../../app/queries';
import { dealsWatch, type ProductCostOut } from '../../core/api';
import { mergeTabs, productsFromWatched, storeNames, type DealFilters, type DealProduct, type PriceRow, type TabListing } from '../../core/deals';
import type { MarketSearch } from '../../core/search';

/** The read-prices result of your open tabs (plus confirms), kept in the query cache so the rail sees it. */
const dealsPricesKey = ['deals', 'prices'] as const;
export const dealsPricesQuery = () =>
  queryOptions({
    queryKey: dealsPricesKey,
    queryFn: async () => new Map<string, PriceRow>(),
    enabled: false,
    staleTime: Infinity,
    gcTime: 30 * 60_000,
  });

export const setPrices = (qc: QueryClient, prices: Map<string, PriceRow>) => qc.setQueryData(dealsPricesKey, prices);

/** Updates some rows of the cached prices (a confirm, or a watch toggle). */
export function patchPrices(qc: QueryClient, urls: string[], patch: (r: PriceRow) => PriceRow) {
  qc.setQueryData<Map<string, PriceRow>>(dealsPricesKey, (old) => {
    if (!old) return old;
    const next = new Map(old);
    for (const u of urls) {
      const r = next.get(u);
      if (r) next.set(u, patch(r));
    }
    return next;
  });
}

/** Pinned rows you dismissed (product or listing keys) — hidden until the next read of your tabs. */
const dismissedKey = ['deals', 'dismissed'] as const;
const NO_KEYS: ReadonlySet<string> = new Set();
const dismissedQuery = () =>
  queryOptions({ queryKey: dismissedKey, queryFn: async () => NO_KEYS, enabled: false, staleTime: Infinity, gcTime: 30 * 60_000 });
export const dismiss = (qc: QueryClient, keys: string[]) =>
  qc.setQueryData<ReadonlySet<string>>(dismissedKey, (old) => new Set([...(old ?? []), ...keys]));
export const undismiss = (qc: QueryClient, key: string) =>
  qc.setQueryData<ReadonlySet<string>>(dismissedKey, (old) => {
    if (!old?.has(key)) return old;
    const next = new Set(old);
    next.delete(key);
    return next;
  });
export const clearDismissed = (qc: QueryClient) => qc.setQueryData(dismissedKey, NO_KEYS);

const NO_ROWS: PriceRow[] = [];
const NO_PRICES = new Map<string, PriceRow>();

export type DealsData = {
  /** The watchlist (with fresh offers from your open tabs merged in). */
  products: DealProduct[];
  /** From your open tabs, not watched yet: matched products, then listings needing a look. */
  pinned: DealProduct[];
  listings: TabListing[];
  storeOptions: string[];
  loading: boolean;
  error: unknown;
};

/** Deals: the products you watch, with the last read of your open tabs pinned above them. */
export function useDealsData(enabled: boolean, watchErrors: PriceRow[] = NO_ROWS): DealsData {
  const watched = useQuery({ ...watchedQuery(), enabled });
  const tabs = useQuery(dealsTabsQuery());
  const prices = useQuery(dealsPricesQuery()).data ?? NO_PRICES;
  const dismissed = useQuery(dismissedQuery()).data ?? NO_KEYS;
  return useMemo(() => {
    const list = watched.data ? productsFromWatched(watched.data, watchErrors) : [];
    const storeOf = new Map(tabs.data?.stores.flatMap((s) => s.tabs.map((t) => [t.url, s.name] as const)) ?? []);
    const titleOf = new Map(tabs.data?.stores.flatMap((s) => s.tabs.map((t) => [t.url, t.title] as const)) ?? []);
    const { watched: products, pinned, listings } = mergeTabs(list, prices, storeOf, titleOf, dismissed);
    const storeOptions = [...new Set([...storeNames([...products, ...pinned]), ...listings.flatMap((l) => (l.store ? [l.store] : []))])].sort((a, b) => a.localeCompare(b));
    return { products, pinned, listings, storeOptions, loading: watched.isPending && enabled, error: watched.error };
  }, [watched.data, watched.isPending, watched.error, enabled, watchErrors, tabs.data, prices, dismissed]);
}

/** Watch a product read from your open tabs at its best store: it moves into the watchlist. */
export function useWatch(p: DealProduct) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => unwrap(await dealsWatch({ body: { url: p.best!.url, choice: p.match!, price: p.best!.price, currency: 'USD' } })),
    onSuccess: () => {
      patchPrices(qc, [p.best!.url], (r) => ({ ...r, watching: true }));
      return qc.invalidateQueries({ queryKey: ['deals', 'watched'] });
    },
  });
}

export type CostState = { loading: boolean; error?: string };
export type DealCosts = { data: Map<string, ProductCostOut | undefined>; state: Map<string, CostState> };

/** Fetches each sealed/Secret Lair product's worth; rows render at once and fill in as these arrive. */
export function useDealCosts(products: DealProduct[]): DealCosts {
  const priced = useMemo(() => products.filter((p) => p.kind !== 'single'), [products]);
  const results = useQueries({ queries: priced.map((p) => productCostQuery(p.kind as 'sealed' | 'sld', p.set_code, p.name, p.finish)) });
  const data = new Map<string, ProductCostOut | undefined>();
  const state = new Map<string, CostState>();
  priced.forEach((p, i) => {
    const r = results[i];
    data.set(p.key, r.data);
    state.set(p.key, { loading: r.isPending, error: r.isError ? (r.error as Error).message : undefined });
  });
  return { data, state };
}

export const dealFilters = (s: MarketSearch): DealFilters => ({
  q: s.dq, stores: s.stores, types: s.types, minOff: s.minOff, basis: s.basis, sort: s.dsort, inStock: s.inStock, atTarget: s.atTarget,
});

import { queryOptions, useQueries, useQuery, type QueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import { dealsTabsQuery, productCostQuery, watchedQuery } from '../../app/queries';
import type { ProductCostOut } from '../../core/api';
import { productsFromTabs, productsFromWatched, storeNames, type DealFilters, type DealProduct, type PriceRow } from '../../core/deals';
import type { MarketSearch } from '../../core/search';

/** The read-prices result (plus confirms), kept in the query cache so the sidebar can see it. */
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

const NONE: DealProduct[] = [];
const NO_ROWS: PriceRow[] = [];

export type DealsData = { products: DealProduct[]; needsLook: PriceRow[]; storeOptions: string[]; loading: boolean; error: unknown };

/** The current Deals product set: watched products, or the open tabs' read prices. */
export function useDealsData(mode: MarketSearch['deals'], enabled: boolean, watchErrors: PriceRow[] = NO_ROWS): DealsData {
  const watched = useQuery({ ...watchedQuery(), enabled: enabled && mode === 'watching' });
  const tabs = useQuery(dealsTabsQuery());
  const prices = useQuery(dealsPricesQuery());
  return useMemo(() => {
    if (mode === 'watching') {
      const products = watched.data ? productsFromWatched(watched.data, watchErrors) : NONE;
      return { products, needsLook: NO_ROWS, storeOptions: storeNames(products), loading: watched.isPending, error: watched.error };
    }
    const storeOf = new Map(tabs.data?.stores.flatMap((s) => s.tabs.map((t) => [t.url, s.name] as const)) ?? []);
    const { products, needsLook } = prices.data?.size ? productsFromTabs(prices.data, storeOf) : { products: NONE, needsLook: NO_ROWS };
    const storeOptions = products.length ? storeNames(products) : (tabs.data?.stores.map((s) => s.name) ?? []);
    return { products, needsLook, storeOptions, loading: false, error: null };
  }, [mode, watched.data, watched.isPending, watched.error, watchErrors, tabs.data, prices.data]);
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
  q: s.dq, stores: s.stores, types: s.types, minOff: s.minOff, basis: s.basis, sort: s.dsort, inStock: s.inStock,
});

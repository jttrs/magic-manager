// "Temporarily down" flags for site reads (docs/scraper-health.md).
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';
import { scrapersReport } from '../core/api';
import { downAmong, isReportable, storeHealthLookup, type ScraperHealth } from '../core/scraperHealth';
import { scraperHealthQuery } from './queries';

/** The down scrapers among `keys` (empty while loading or when the health file can't be read). */
export function useDownScrapers(keys: readonly string[]): ScraperHealth[] {
  const q = useQuery(scraperHealthQuery());
  return downAmong(q.data?.scrapers, keys);
}

/** A Deals store's health by vendor key or store name, for per-row marks (one shared query). */
export function useStoreHealth() {
  const all = useQuery(scraperHealthQuery()).data?.scrapers;
  return useMemo(() => storeHealthLookup(all), [all]);
}

/** A companion read found the site's page changed: flag it (best effort, never throws). */
export async function reportScraperFailure(code: string, qc?: QueryClient) {
  if (!isReportable(code)) return;
  try {
    await scrapersReport({ body: { code } });
  } catch {
    return;
  }
  await qc?.invalidateQueries({ queryKey: ['scrapers', 'health'] });
}

/** After a read that may have cleared or set a flag on the server. */
export function useRefreshScraperHealth() {
  const qc = useQueryClient();
  return useCallback(() => qc.invalidateQueries({ queryKey: ['scrapers', 'health'] }), [qc]);
}

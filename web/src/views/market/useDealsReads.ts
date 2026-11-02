import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { useFeature, useOwnerPath } from '../../app/features';
import { dealsTabsQuery, unwrap, watchedQuery } from '../../app/queries';
import { useCompanion } from '../../app/useCompanion';
import { useJob, type JobLive } from '../../app/useJob';
import { dealsSuppliedTabs, type OpenTabsOut } from '../../core/api';
import { warningLines, type RenderedPage } from '../../core/companion';
import { browserReadUrls, newlyMetFrom, pricesFrom, watchlistErrors, type NewlyMet, type PriceRow } from '../../core/deals';
import { fmtInt } from '../../core/format';
import { clearDismissed, setPrices } from './useDealsData';

const NO_ROWS: PriceRow[] = [];
const NO_SERVER_TABS = 'Connect the browser companion to read your open tabs — it reads them in this browser. This server can’t read your tabs for you.';
const done = (l: JobLive | null) => l == null || l.status === 'succeeded' || l.status === 'failed';
const urlsOf = (o: OpenTabsOut) => o.stores.flatMap((s) => s.tabs.map((t) => t.url));

export type DealsReads = ReturnType<typeof useDealsReads>;

/** Deals' two reads, shared by the sheet's header actions and the status above the table.
 *  Read my open tabs: the product pages open in this browser (the companion, when connected) or in
 *  Chrome on this Mac, then their prices — one action. Read watched prices: every watched link again. */
export function useDealsReads(enabled: boolean) {
  const qc = useQueryClient();
  const c = useCompanion();
  const inBrowser = useFeature('companion') && c.status === 'ready';
  // Reading tabs in this server's Chrome (AppleScript) is the owner's machine: admins only when hosted.
  const serverTabs = useOwnerPath('deals.mac_tabs');
  const tabsQuery = useQuery(dealsTabsQuery());
  const prices = useJob();
  const watch = useJob();
  const [awaiting, setAwaiting] = useState<string | null>(null);
  const [notes, setNotes] = useState<string[]>([]);
  const [failure, setFailure] = useState<{ error: unknown; companion: boolean; needsCompanion?: boolean } | null>(null);
  const [reading, setReading] = useState<'tabs' | 'watched' | null>(null);
  /** The last read that ran (set as it starts): tells the status line which result to explain. */
  const [lastRead, setLastRead] = useState<'tabs' | 'watched' | null>(null);
  const watchedRows = useQuery({ ...watchedQuery(), enabled }).data;
  const browser = useMemo(() => browserReadUrls(watchedRows ?? []), [watchedRows]);

  const busy = reading != null || !done(prices.live) || !done(watch.live);

  const begin = (what: 'tabs' | 'watched') => {
    setReading(what);
    setLastRead(what);
    setNotes([]);
    setFailure(null);
    prices.reset();
    watch.reset();
  };

  const readTabs = async () => {
    begin('tabs');
    try {
      let out: OpenTabsOut;
      let pages: Record<string, RenderedPage> = {};
      if (inBrowser) {
        try {
          const d = await c.read('tabs', {}, setAwaiting);
          setAwaiting(null);
          out = unwrap(await dealsSuppliedTabs({ body: { tabs: d.tabs } }));
          pages = d.pages;
          qc.setQueryData(dealsTabsQuery().queryKey, out);
          setNotes(warningLines(d.warnings, c.catalog));
        } catch (error) {
          setFailure({ error, companion: true });
          return;
        }
      } else if (serverTabs) {
        out = (await tabsQuery.refetch({ throwOnError: true })).data!;
      } else {
        setFailure({ error: new Error(NO_SERVER_TABS), companion: false, needsCompanion: true });
        return;
      }
      // A new read replaces the pinned group, dismissals included.
      setPrices(qc, new Map());
      clearDismissed(qc);
      const urls = urlsOf(out);
      if (!urls.length) return;
      const err = await prices.start('deals.read_prices', { urls, pages: Object.fromEntries(urls.filter((u) => pages[u]).map((u) => [u, pages[u]])) });
      if (err) setFailure({ error: new Error(err), companion: false });
    } catch (error) {
      setFailure({ error, companion: false });
    } finally {
      setAwaiting(null);
      setReading(null);
    }
  };

  // Open-tab stores (Best Buy, Target …) among the watched links are read in this browser by the
  // companion when it's connected — you approve the pages, then what is sent; else Chrome on this Mac.
  const readWatched = async () => {
    begin('watched');
    try {
      if (inBrowser && browser.urls.length) {
        try {
          const d = await c.read('watched', { urls: browser.urls }, setAwaiting);
          setAwaiting(null);
          setNotes([
            ...warningLines(d.warnings, c.catalog),
            ...(browser.skipped ? [`${fmtInt(browser.skipped)} more open-tab store links weren’t read this time (at most ${fmtInt(browser.urls.length)} per read).`] : []),
          ]);
          const err = await watch.start('deals.watchlist', { refresh: true, in_browser: true, pages: d.pages });
          if (err) setFailure({ error: new Error(err), companion: false });
        } catch (error) {
          setFailure({ error, companion: true });
        }
      } else {
        const err = await watch.start('deals.watchlist', { refresh: true });
        if (err) setFailure({ error: new Error(err), companion: false });
      }
    } finally {
      setAwaiting(null);
      setReading(null);
    }
  };

  useEffect(() => {
    if (prices.live?.status !== 'succeeded') return;
    setPrices(qc, pricesFrom(prices.live.artifacts));
    // Reads of watched links are added to their history server-side: their rows pick up the price.
    void qc.invalidateQueries({ queryKey: ['deals', 'watched'] });
    void qc.invalidateQueries({ queryKey: ['scrapers', 'health'] });
  }, [prices.live?.status, prices.live?.artifacts, qc]);
  useEffect(() => {
    if (watch.live?.status !== 'succeeded') return;
    void qc.invalidateQueries({ queryKey: ['deals', 'watched'] });
    void qc.invalidateQueries({ queryKey: ['scrapers', 'health'] });
  }, [watch.live?.status, qc]);

  const watchErrors = useMemo(() => (watch.live?.status === 'succeeded' ? watchlistErrors(watch.live.artifacts) : NO_ROWS), [watch.live]);
  const newlyMet: NewlyMet[] = useMemo(() => (watch.live?.status === 'succeeded' ? newlyMetFrom(watch.live.artifacts) : []), [watch.live]);

  return {
    inBrowser,
    /** The last read of your tabs (store groups, uncatalogued stores, warnings). */
    tabs: tabsQuery.data,
    readTabs: () => void readTabs(),
    readWatched: () => void readWatched(),
    busy,
    reading,
    lastRead,
    awaiting,
    notes,
    failure,
    pricesLive: prices.live,
    watchLive: watch.live,
    watchErrors,
    newlyMet,
    /** Watched links on open-tab stores the companion reads in this browser. */
    browserReads: browser.urls.length,
  };
}

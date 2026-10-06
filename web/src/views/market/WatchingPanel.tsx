import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo } from 'react';
import { useJob } from '../../app/useJob';
import { Button } from '../../components/Button';
import { EmptyNote, ErrorNote } from '../../components/States';
import { sharedErrors, watchlistErrors, type PriceRow } from '../../core/deals';
import { fmtInt } from '../../core/format';
import type { MarketSearch } from '../../core/search';
import { DealsWorkspace } from './DealsWorkspace';
import { useDealCosts, useDealsData } from './useDealsData';

const NO_ROWS: PriceRow[] = [];

/** Internal (deals flag): the products you watch, one row per product with its stores in the
 *  inspector. The list is instant; reading every store's price again is an explicit action. */
export function WatchingPanel({ search, set }: { search: MarketSearch; set: (patch: Partial<MarketSearch>) => void }) {
  const qc = useQueryClient();
  const job = useJob();
  const live = job.live;
  const busy = live != null && live.status !== 'succeeded' && live.status !== 'failed';
  const errors = useMemo(() => (live?.status === 'succeeded' ? watchlistErrors(live.artifacts) : NO_ROWS), [live]);
  const data = useDealsData('watching', true, errors);
  const costs = useDealCosts(data.products);
  useEffect(() => {
    if (live?.status === 'succeeded') void qc.invalidateQueries({ queryKey: ['deals', 'watched'] });
  }, [live?.status, qc]);
  const shared = sharedErrors(errors);
  const refresh = () => { job.reset(); void job.start('deals.watchlist', { refresh: true }); };
  const header = (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <Button tone="paper" emphasis="quiet" disabled={busy} onClick={refresh}>{busy ? 'Reading prices…' : 'Read watched prices'}</Button>
        {live?.status === 'succeeded' && live.summary && <span className="text-sm tabular text-ink-muted">{live.summary}</span>}
      </div>
      {busy && (
        <p role="status" className="text-sm tabular text-ink-muted">
          {live?.total ? `Reading ${fmtInt(Math.min(live.done + 1, live.total))} of ${fmtInt(live.total)}` : 'Starting…'}
          {live?.log.at(-1)?.msg ? ` · ${live.log.at(-1)!.msg}` : ''}
        </p>
      )}
      {live?.status === 'failed' && <p role="alert" className="text-md text-danger">{live.error ?? 'Couldn’t read prices.'}</p>}
      {shared.map((e) => <p key={e} role="alert" className="max-w-[70ch] text-md leading-relaxed text-ink">{e}</p>)}
    </div>
  );
  const emptyNote = data.loading
    ? <p role="status" className="text-md text-ink-muted">Loading what you watch…</p>
    : data.error
      ? <ErrorNote error={data.error} />
      : <EmptyNote title="Nothing watched yet">Read your open tabs, then choose Watch on a sealed product or Secret Lair drop.</EmptyNote>;
  return <DealsWorkspace products={data.products} costs={costs} search={search} set={set} header={header} emptyNote={emptyNote} />;
}

import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { useJob } from '../../app/useJob';
import { Button } from '../../components/Button';
import { EmptyNote, ErrorNote } from '../../components/States';
import { newlyMetFrom, sharedErrors, watchlistErrors, type DealProduct, type NewlyMet, type PriceRow } from '../../core/deals';
import { fmtInt, fmtUsd } from '../../core/format';
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
  const met = useMemo(() => (live?.status === 'succeeded' ? newlyMetFrom(live.artifacts) : []), [live]);
  const [dismissed, setDismissed] = useState(false);
  const refresh = () => { setDismissed(false); job.reset(); void job.start('deals.watchlist', { refresh: true }); };
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
      {met.length > 0 && !dismissed && (
        <TargetsMet met={met} products={data.products} onPick={(item) => set({ item })} onDismiss={() => setDismissed(true)} />
      )}
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

/** After a read: the products whose target this read met, each a link into the inspector. */
function TargetsMet({ met, products, onPick, onDismiss }: { met: NewlyMet[]; products: DealProduct[]; onPick: (key: string) => void; onDismiss: () => void }) {
  const keyOf = new Map(products.map((p) => [p.productId, p.key]));
  return (
    <section role="status" aria-labelledby="targets-met-h" className="flex flex-col gap-1.5 border-y-2 border-rule-strong py-2">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h3 id="targets-met-h" className="flex-1 text-lg voice-condensed font-bold text-ink">
          <span className="highlighter">{met.length === 1 ? '1 product hit its target' : `${fmtInt(met.length)} products hit their target`}</span>
        </h3>
        <Button tone="paper" emphasis="quiet" onClick={onDismiss}>Dismiss</Button>
      </div>
      <ul className="flex flex-col">
        {met.map((m) => {
          const key = keyOf.get(m.product_id);
          return (
            <li key={m.product_id} className="flex flex-wrap items-baseline gap-x-2 border-b border-rule/60 py-1.5 text-sm tabular last:border-b-0">
              {key ? (
                <button type="button" onClick={() => onPick(key)} className="touch-hit cursor-pointer text-left voice-semi font-medium text-accent-ink underline">{m.name}</button>
              ) : <span className="voice-semi font-medium text-ink">{m.name}</span>}
              <span className="text-ink">{fmtUsd(m.price)}</span>
              <a href={m.url} target="_blank" rel="noreferrer" className="touch-hit text-ink-muted hover:text-accent-ink">
                at {m.store ?? 'a store'}<span aria-hidden="true"> ↗</span><span className="sr-only"> (opens in a new tab)</span>
              </a>
              <span className="text-ink-muted">· target {fmtUsd(m.target_price)}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

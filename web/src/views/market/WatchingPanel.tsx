import { useEffect, useRef } from 'react';
import { useJob } from '../../app/useJob';
import { Button } from '../../components/Button';
import { EmptyNote } from '../../components/States';
import { deltaLabel, readAge, sharedErrors, stockLabel, trendLabel, watchlistFrom, type Watched, type WatchStore } from '../../core/deals';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';

/** Internal (deals flag): the products you watch, valued now, with each store's
 *  last price and how it moved. Reading prices again is an explicit action. */
export function WatchingPanel() {
  const job = useJob();
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void job.start('deals.watchlist', { refresh: false });
  }, [job]);
  const live = job.live;
  const busy = live == null || (live.status !== 'succeeded' && live.status !== 'failed');
  const { watched, errors } = live?.status === 'succeeded' ? watchlistFrom(live.artifacts) : { watched: [], errors: [] };
  const shared = sharedErrors(errors);
  const refresh = () => { job.reset(); void job.start('deals.watchlist', { refresh: true }); };
  return (
    <div className="flex flex-col gap-4 px-5 pt-2">
      <div className="flex flex-wrap items-center gap-3">
        <Button tone="paper" emphasis="quiet" disabled={busy} onClick={refresh}>{busy ? 'Working…' : 'Read watched prices'}</Button>
        {live?.status === 'succeeded' && live.summary && <span className="text-sm tabular text-ink-muted">{live.summary}</span>}
      </div>
      {busy && (
        <p role="status" className="text-sm tabular text-ink-muted">
          {live?.total ? `${live.log.at(-1)?.msg.startsWith('reading') ? 'Reading' : 'Valuing'} ${fmtInt(Math.min(live.done + 1, live.total))} of ${fmtInt(live.total)}` : 'Valuing what you watch…'}
        </p>
      )}
      {live?.status === 'failed' && <p role="alert" className="text-md text-danger">{live.error ?? 'Couldn’t load what you watch.'}</p>}
      {shared.map((e) => <p key={e} role="alert" className="max-w-[70ch] text-md leading-relaxed text-ink">{e}</p>)}
      {live?.status === 'succeeded' && !watched.length && (
        <EmptyNote title="Nothing watched yet">Read your open tabs, then choose “watch price” on a sealed product or Secret Lair drop.</EmptyNote>
      )}
      {watched.length > 0 && (
        <ul aria-label="Watched products" className="flex flex-col">
          {watched.map((w) => <WatchedRow key={`${w.set_code}|${w.name}`} w={w} errors={errors} shared={shared} />)}
        </ul>
      )}
    </div>
  );
}

function WatchedRow({ w, errors, shared }: { w: Watched; errors: { url: string; error: string | null }[]; shared: string[] }) {
  const delta = deltaLabel(w);
  return (
    <li className="flex flex-col gap-1 border-b border-rule py-2.5">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <span className="min-w-0 flex-1 text-md font-medium text-ink">{w.name}<span className="ml-2 text-xs font-normal uppercase text-ink-muted">{w.set_code}</span></span>
        <span className="w-20 shrink-0 text-right tabular text-ink">{w.best_price != null ? fmtUsd(w.best_price) : <span className="text-ink-muted">—</span>}</span>
      </div>
      <p className="flex flex-wrap items-baseline gap-x-2 text-xs text-ink-muted">
        {w.best_store && <span>best at {w.best_store}</span>}
        {w.market != null && <span className="tabular">· market {fmtUsd(w.market)}</span>}
        {w.contents != null && <span className="tabular">· cards inside {fmtUsd(w.contents)}{w.partial ? '+' : ''}</span>}
        {delta && <span className={`font-medium ${delta.tone === 'good' ? 'text-accent-ink' : delta.tone === 'bad' ? 'text-danger' : ''}`}>· {delta.text}</span>}
        {w.error && <span className="text-danger">· {w.error}</span>}
      </p>
      <ul aria-label={`Stores for ${w.name}`} className="flex flex-col pl-3">
        {w.stores.map((s) => <StoreLine key={s.url} s={s} error={errors.find((e) => e.url === s.url)?.error ?? null} shared={shared} />)}
      </ul>
    </li>
  );
}

function StoreLine({ s, error, shared }: { s: WatchStore; error: string | null; shared: string[] }) {
  const trend = trendLabel(s);
  const stock = stockLabel(s);
  return (
    <li className="flex flex-col text-sm">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <a href={s.url} target="_blank" rel="noreferrer" className="min-w-0 flex-1 truncate text-ink no-underline hover:text-accent-ink">
          {s.store ?? new URL(s.url).hostname}<span className="sr-only"> (opens in a new tab)</span>
        </a>
        {trend && <span className={`shrink-0 text-xs ${trend.tone === 'good' ? 'text-accent-ink' : trend.tone === 'bad' ? 'text-danger' : 'text-ink-muted'}`}>{trend.text}</span>}
        {stock && <span className={`shrink-0 text-xs ${s.available ? 'text-ink-muted' : 'text-danger'}`}>{stock}</span>}
        <span className="shrink-0 text-xs text-ink-muted">{readAge(s)}</span>
        <span className="w-20 shrink-0 text-right tabular text-ink">{s.price != null ? fmtUsd(s.price) : <span className="text-ink-muted">—</span>}</span>
      </div>
      {error && !shared.includes(error) && <span className="text-xs text-danger">{error}</span>}
      {s.history.length > 2 && <span className="text-xs tabular text-ink-muted">{fmtCount(s.history.length, 'reading')}</span>}
    </li>
  );
}

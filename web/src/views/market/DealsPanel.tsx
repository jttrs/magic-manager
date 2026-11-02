import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { Button } from '../../components/Button';
import { AwaitingNote, FailureNote } from '../../components/companion/CompanionNotes';
import { CompanionRequired } from '../../components/companion/CompanionRequired';
import { EmptyNote, ErrorNote } from '../../components/States';
import { sharedErrors, type DealProduct, type NewlyMet, type PriceRow } from '../../core/deals';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';
import type { MarketSearch } from '../../core/search';
import type { OpenTabsOut } from '../../core/api';
import { DealsWorkspace } from './DealsWorkspace';
import { dealsPricesQuery, type DealCosts, type DealsData } from './useDealsData';
import type { DealsReads } from './useDealsReads';

const NO_PRICES = new Map<string, PriceRow>();
const hostOf = (url: string) => { try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return url; } };

/** Internal (deals flag): the products you watch — best price now, what each is worth and what's inside.
 *  A read of your open tabs (a header action) pins what it found above the table until you Watch or
 *  Dismiss it. Reads happen only on demand. */
export function DealsPanel({ data, costs, reads, search, set }: { data: DealsData; costs: DealCosts; reads: DealsReads; search: MarketSearch; set: (patch: Partial<MarketSearch>) => void }) {
  const prices = useQuery(dealsPricesQuery()).data ?? NO_PRICES;
  const shared = useMemo(() => sharedErrors([...prices.values(), ...reads.watchErrors]), [prices, reads.watchErrors]);
  const [dismissedMet, setDismissedMet] = useState<NewlyMet[] | null>(null);
  const met = reads.newlyMet.length && dismissedMet !== reads.newlyMet ? reads.newlyMet : [];
  const pl = reads.pricesLive, wl = reads.watchLive;
  const live = pl ?? wl;
  const running = live != null && live.status !== 'succeeded' && live.status !== 'failed';

  const header = (
    <div className="flex flex-col gap-2 empty:hidden">
      {reads.awaiting != null && <AwaitingNote summary={reads.awaiting} />}
      {reads.reading === 'tabs' && reads.awaiting == null && !running && <p role="status" className="text-sm text-ink-muted">Reading your open tabs…</p>}
      {reads.failure && (reads.failure.needsCompanion
        ? <CompanionRequired what="Your open store tabs" />
        : reads.failure.companion
        ? <FailureNote error={reads.failure.error} />
        : <p role="alert" className="text-md text-danger">{(reads.failure.error as Error).message}</p>)}
      {reads.notes.map((w) => <p key={w} role="status" className="text-md leading-relaxed text-ink">{w}</p>)}
      {reads.tabs?.warnings.map((w) => <p key={w} role="status" className="text-md leading-relaxed text-ink">{w}</p>)}
      {running && (
        <p role="status" className="text-sm tabular text-ink-muted">
          {pl ? 'Reading prices from your open tabs' : 'Reading watched prices'}
          {live.total ? ` · ${fmtInt(Math.min(live.done + 1, live.total))} of ${fmtInt(live.total)}` : ' · starting…'}
          {live.log.at(-1)?.msg ? ` · ${pl ? hostOf(live.log.at(-1)!.msg) : live.log.at(-1)!.msg}` : ''}
        </p>
      )}
      {live?.status === 'failed' && <p role="alert" className="text-md text-danger">{live.error ?? 'Couldn’t read prices.'}</p>}
      {wl?.status === 'succeeded' && wl.summary && <p role="status" className="text-sm tabular text-ink-muted">{wl.summary}</p>}
      {reads.lastRead === 'tabs' && !reads.busy && !reads.failure && pl?.status !== 'failed' && reads.tabs && (
        <TabsSummary r={reads.tabs} pinned={data.pinned.length + data.listings.length} />
      )}
      {met.length > 0 && (
        <TargetsMet met={met} products={data.products} onPick={(item) => set({ item })} onDismiss={() => setDismissedMet(reads.newlyMet)} />
      )}
      {shared.map((e) => <p key={e} role="alert" className="max-w-[70ch] text-md leading-relaxed text-ink">{e}</p>)}
      {!reads.busy && reads.inBrowser && reads.browserReads > 0 && (
        <p className="text-sm text-ink-muted">Open-tab stores are read in this browser by the companion</p>
      )}
    </div>
  );
  const emptyNote = data.loading
    ? <p role="status" className="text-md text-ink-muted">Loading what you watch…</p>
    : data.error
      ? <ErrorNote error={data.error} />
      : <EmptyNote title="Nothing watched yet">Read your open tabs, then choose Watch on a product you want to follow.</EmptyNote>;
  return <DealsWorkspace data={data} costs={costs} search={search} set={set} header={header} emptyNote={emptyNote} />;
}

/** After a read of your tabs: where they came from, what was pinned, and what was left out. */
function TabsSummary({ r, pinned }: { r: OpenTabsOut; pinned: number }) {
  const pages = r.stores.reduce((n, s) => n + s.tabs.length, 0);
  const uncatalogued = r.uncatalogued.reduce((n, u) => n + u.tabs.length, 0);
  const parts = [
    r.browser === 'extension' ? 'Read in this browser' : `${fmtInt(r.windows_read)} of ${fmtCount(r.windows, 'window')} read`,
    fmtCount(pages, 'product page'),
    pages ? `${fmtInt(pinned)} new to review` : null,
    uncatalogued ? `${fmtCount(uncatalogued, 'page')} at stores without a recipe yet (${r.uncatalogued.map((u) => u.host).join(', ')})` : null,
    r.store_pages ? fmtCount(r.store_pages, 'other store page') : null,
    r.other ? fmtCount(r.other, 'other tab') : null,
  ].filter(Boolean);
  return (
    <p role="status" className="text-sm tabular text-ink-muted">
      {!pages && <span className="text-ink">No store product pages open — open product pages from a store, then read again. </span>}
      {parts.join(' · ')}
    </p>
  );
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

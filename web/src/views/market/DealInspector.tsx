import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { dealsTabsQuery, unwrap } from '../../app/queries';
import { Button } from '../../components/Button';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { dealsUnwatch, dealsWatch, type ProductCostOut } from '../../core/api';
import { effectiveType, PRODUCT_TYPE_LABEL, stockLabel, type DealProduct, type Offer } from '../../core/deals';
import { fmtUsd } from '../../core/format';
import { CardLines } from './CardLines';
import { H3 } from './inspectorStyles';
import { PriceHistory } from './PriceHistory';
import { PriceTarget } from './PriceTarget';
import { ProductContents } from './ProductContents';
import { patchPrices, type CostState } from './useDealsData';

const tone = (t: 'good' | 'bad' | 'even' | undefined) => (t === 'good' ? 'text-accent-ink' : t === 'bad' ? 'text-danger' : 'text-ink-muted');

export { H3 };

/** The chosen product: where to buy it, what it's worth, what's in it. */
export function DealInspector({ product: p, cost, costState }: { product: DealProduct; cost?: ProductCostOut; costState?: CostState }) {
  const type = effectiveType(p, cost);
  const released = cost?.release_date;
  const sealed = p.kind !== 'single';
  return (
    <section aria-labelledby="deal-h" className="flex h-full min-h-0 flex-col gap-5 overflow-y-auto overscroll-contain px-4 pb-8 pt-1 [scrollbar-gutter:stable]">
      <header className="flex flex-wrap items-end gap-x-4 gap-y-2 border-b-2 border-rule-strong pb-1.5">
        <div className="min-w-0 flex-1">
          <h2 id="deal-h" className="text-2xl voice-condensed font-bold leading-tight text-ink">{p.name}</h2>
          <p className="mt-1 text-sm tabular text-ink-muted">
            {[p.set_code.toUpperCase(), PRODUCT_TYPE_LABEL[type], p.finish === 'foil' && 'foil', released && `released ${released}`].filter(Boolean).join(' · ')}
          </p>
        </div>
        <WatchControl p={p} />
      </header>

      <section aria-label="Stores" className="flex flex-col gap-1">
        <h3 className={H3}>Stores</h3>
        <ul>{p.offers.map((o) => <OfferLine key={o.url} o={o} fromTab={p.match != null} />)}</ul>
      </section>

      {p.productId != null && (
        <>
          <PriceTarget product={p} cost={cost} />
          <PriceHistory product={p} cost={cost} />
        </>
      )}

      <section aria-label="What it’s worth" className="flex flex-col gap-1">
        <h3 className={H3}>What it’s worth</h3>
        {sealed ? <Worth p={p} cost={cost} state={costState} /> : (
          <>
            <dl className="flex flex-col"><Row label="Printing price" value={p.singleMarket ?? null} best={p.best?.price ?? null} /></dl>
            <p className="text-sm text-ink-muted">A single card has no contents to add up.</p>
          </>
        )}
      </section>

      {sealed && (
        <section aria-label="Contents" className="flex flex-col gap-1">
          <h3 className={H3}>Contents</h3>
          <ProductContents set={p.set_code} name={p.name} />
        </section>
      )}

      {cost?.lines?.length ? (
        <CardLines title="Cards" lines={cost.lines} sortable labels={{ need: 'Qty', exact: 'This printing', floor: 'Cheapest' }} />
      ) : null}
    </section>
  );
}

function OfferLine({ o, fromTab }: { o: Offer; fromTab: boolean }) {
  const tabs = useQuery(dealsTabsQuery());
  const mode = tabs.data?.stores.find((s) => s.name === o.store)?.mode;
  const stock = stockLabel(o);
  const name = o.store ?? new URL(o.url).hostname.replace(/^www\./, '');
  return (
    <li className="flex flex-col gap-0.5 border-b border-rule/60 py-2 text-sm">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
        <a href={o.url} target="_blank" rel="noreferrer" className="touch-hit min-w-0 flex-1 text-accent-ink underline">
          {name}<span aria-hidden="true"> ↗</span><span className="sr-only"> (opens in a new tab)</span>
        </a>
        {stock && <span className={`text-xs ${o.available ? 'text-ink-muted' : 'text-danger'}`}>{stock}</span>}
        {o.readAge && <span className="text-xs text-ink-muted">{o.readAge}</span>}
        <span className="w-20 shrink-0 text-right tabular text-ink">{o.price != null ? fmtUsd(o.price) : <span className="text-ink-muted">—</span>}</span>
      </div>
      {o.trend && <span className={`text-xs ${tone(o.trend.tone)}`}>{o.trend.text}</span>}
      {o.error && <span className="text-xs text-danger">{o.error}</span>}
      {fromTab && mode === 'rendered' && <span className="text-xs text-ink-muted">Read from your open tab — keep the page open to refresh</span>}
    </li>
  );
}

export function Row({ label, value, best, note, strong = false }: { label: string; value: number | null | undefined; best: number | null; note?: string | null; strong?: boolean }) {
  const delta = value != null && value !== 0 && best != null ? ((best - value) / value) * 100 : null;
  return (
    <div className="flex flex-wrap items-baseline gap-x-3 border-b border-rule/60 py-1.5 text-sm">
      <dt className={`min-w-0 flex-1 ${strong ? 'voice-semi font-medium text-ink' : 'text-ink'}`}>{label}{note && <span className="ml-1.5 text-xs text-ink-muted">{note}</span>}</dt>
      <dd className="flex items-baseline gap-2 tabular">
        <span className={strong ? 'text-ink voice-semi font-medium' : 'text-ink'}>{value != null ? fmtUsd(value) : <span className="text-ink-muted">—</span>}</span>
        <span className={`w-12 text-right text-xs ${delta == null ? '' : delta < -0.5 ? 'text-accent-ink' : delta > 0.5 ? 'text-danger' : 'text-ink-muted'}`}>
          {delta == null ? '' : Math.abs(delta) < 0.5 ? 'even' : `${delta < 0 ? '−' : '+'}${Math.abs(Math.round(delta))}%`}
        </span>
      </dd>
    </div>
  );
}

function Worth({ p, cost, state }: { p: DealProduct; cost?: ProductCostOut; state?: CostState }) {
  if (!cost) {
    return state?.error
      ? <p role="alert" className="text-sm text-danger">Couldn’t work out what it’s worth: {state.error}</p>
      : <p role="status" aria-busy="true" className="text-sm text-ink-muted">Working out what it’s worth…</p>;
  }
  const best = p.best?.price ?? null;
  const hasCards = (cost.known_exact ?? 0) > 0 || (cost.known_floor ?? 0) > 0;
  const hasBoosters = (cost.booster_ev ?? 0) > 0;
  return (
    <>
      <dl className="flex flex-col">
        <Row label="Sealed price" value={cost.market} best={best} note={cost.market_source} />
        {hasCards && <Row label="Cards inside, exact printings" value={cost.known_exact} best={hasBoosters ? null : best} />}
        {hasCards && <Row label="Cards inside, cheapest printings" value={cost.known_floor} best={hasBoosters ? null : best} />}
        {hasBoosters && <Row label="Boosters, expected value" value={cost.booster_ev} best={hasCards ? null : best} />}
        {hasCards && hasBoosters && <Row strong label="Total, exact" value={cost.exact} best={best} />}
        {hasCards && hasBoosters && <Row strong label="Total, cheapest" value={cost.floor} best={best} />}
      </dl>
      {(cost.unpriced ?? 0) > 0 && (
        <p className="text-sm text-ink-muted">{cost.unpriced} of {cost.total_cards} cards have no price at their exact printing — totals count only the rest.</p>
      )}
      {cost.notes?.map((n) => <p key={n} className="text-sm text-ink-muted">{n}</p>)}
    </>
  );
}

function WatchControl({ p }: { p: DealProduct }): ReactNode {
  const qc = useQueryClient();
  const [confirm, setConfirm] = useState(false);
  const fromTab = p.match != null;
  const done = (urls: string[], watching: boolean) => {
    if (fromTab) patchPrices(qc, urls, (r) => ({ ...r, watching }));
    return qc.invalidateQueries({ queryKey: ['deals', 'watched'] });
  };
  const watch = useMutation({
    mutationFn: async () => unwrap(await dealsWatch({ body: { url: p.best!.url, choice: p.match!, price: p.best!.price, currency: 'USD' } })),
    onSuccess: () => done([p.best!.url], true),
  });
  const urls = p.offers.map((o) => o.url);
  const unwatch = async () => {
    for (const url of urls) unwrap(await dealsUnwatch({ query: { url } }));
    await done(urls, false);
  };
  if (!p.watching && !fromTab) return null;
  return (
    <span className="flex flex-col items-end gap-1">
      {p.watching ? (
        <Button tone="paper" emphasis="quiet" onClick={() => setConfirm(true)}>Stop watching</Button>
      ) : fromTab && p.best ? (
        <Button tone="paper" emphasis="quiet" disabled={watch.isPending} onClick={() => watch.mutate()}>{watch.isPending ? 'Saving…' : 'Watch'}</Button>
      ) : null}
      {watch.isError && <span role="alert" className="text-xs text-danger">{(watch.error as Error).message}</span>}
      <ConfirmDialog open={confirm} onOpenChange={setConfirm} title={`Stop watching ${p.name}?`} confirmLabel="Stop watching" onConfirm={unwatch}>
        <p>It stops being tracked at {urls.length === 1 ? 'its store' : `all ${urls.length} stores`}.</p>
      </ConfirmDialog>
    </span>
  );
}

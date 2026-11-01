import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useStoreHealth } from '../../app/scraperHealth';
import { ScraperDownMark } from '../../components/ScraperNotice';
import { useState, type ReactNode } from 'react';
import { dealsTabsQuery, unwrap } from '../../app/queries';
import { Button } from '../../components/Button';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { dealsMatch, dealsUnwatch, type MatchOut, type ProductCostOut } from '../../core/api';
import { effectiveType, PRODUCT_TYPE_LABEL, stockLabel, tabProductKey, type DealProduct, type Offer, type PriceRow, type TabListing } from '../../core/deals';
import { fmtUsd } from '../../core/format';
import { CardLines } from './CardLines';
import { H3 } from './inspectorStyles';
import { PriceHistory } from './PriceHistory';
import { PriceTarget } from './PriceTarget';
import { ProductContents } from './ProductContents';
import { dealsPricesQuery, patchPrices, useWatch, type CostState } from './useDealsData';

const tone = (t: 'good' | 'bad' | 'even' | undefined) => (t === 'good' ? 'text-accent-ink' : t === 'bad' ? 'text-danger' : 'text-ink-muted');

export { H3 };

/** The chosen product: where to buy it, what it's worth, what's in it. */
export function DealInspector({ product: p, cost, costState, onPick }: { product: DealProduct; cost?: ProductCostOut; costState?: CostState; onPick: (key: string) => void }) {
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
        <ul>{p.offers.map((o) => <OfferLine key={o.url} o={o} onPick={onPick} />)}</ul>
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

      {p.kind === 'sealed' && (
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

function OfferLine({ o, onPick }: { o: Offer; onPick: (key: string) => void }) {
  const tabs = useQuery(dealsTabsQuery());
  const read = useQuery(dealsPricesQuery()).data?.get(o.url);
  const storeHealth = useStoreHealth();
  const mode = tabs.data?.stores.find((s) => s.name === o.store)?.mode;
  const stock = stockLabel(o);
  const name = o.store ?? new URL(o.url).hostname.replace(/^www\./, '');
  // Read from your open tabs and not a watched link: its match can be corrected here.
  const fromTabs = read != null && !read.watching;
  return (
    <li className="flex flex-col gap-0.5 border-b border-rule/60 py-2 text-sm">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
        <a href={o.url} target="_blank" rel="noreferrer" className="touch-hit min-w-0 flex-1 text-accent-ink underline">
          {name}<span aria-hidden="true"> ↗</span><span className="sr-only"> (opens in a new tab)</span>
        </a>
        <ScraperDownMark health={storeHealth(o.store)} />
        {stock && <span className={`text-xs ${o.available ? 'text-ink-muted' : 'text-danger'}`}>{stock}</span>}
        {o.readAge && <span className="text-xs text-ink-muted">{o.readAge}</span>}
        <span className="w-20 shrink-0 text-right tabular text-ink">{o.price != null ? fmtUsd(o.price) : <span className="text-ink-muted">—</span>}</span>
      </div>
      {o.trend && <span className={`text-xs ${tone(o.trend.tone)}`}>{o.trend.text}</span>}
      {o.error && <span className="text-xs text-danger">{o.error}</span>}
      {o.fromTab && <span className="text-xs text-ink-muted">From your open tabs — not watched at this store</span>}
      {fromTabs && mode === 'rendered' && <span className="text-xs text-ink-muted">Read from your open tab — keep the page open to read it again</span>}
      {fromTabs && read.title && <span className="text-xs text-ink-muted">Listed as “{read.title}”</span>}
      {fromTabs && <MatchControl p={read} onPick={onPick} />}
    </li>
  );
}

const sameChoice = (a: MatchOut, b: MatchOut | null | undefined) =>
  !!b && a.set_code === b.set_code && a.name === b.name && a.scryfall_id === b.scryfall_id && a.finish === b.finish;

/** What a listing from your open tabs was matched to, with a way to correct it: "not this?" on a
 *  guess, "change" on a confirmed one, a picker when it's ambiguous. A save opens the product it now is. */
function MatchControl({ p, onPick }: { p: PriceRow; onPick: (key: string) => void }) {
  const qc = useQueryClient();
  const [pick, setPick] = useState(0);
  const [changing, setChanging] = useState(false);
  const candidates = p.candidates ?? [];
  const save = useMutation({
    mutationFn: async (choice: MatchOut | null) =>
      unwrap(await dealsMatch({ body: { url: p.url, title: p.title, price: p.price, currency: p.currency, available: p.available, choice } })),
    onSuccess: (row) => {
      patchPrices(qc, [row.url], () => row);
      setChanging(false);
      if (row.match && row.kind && (row.status === 'matched' || row.status === 'confirmed')) onPick(tabProductKey(row.kind, row.match));
    },
  });
  const error = save.isError && <span role="alert" className="text-xs text-danger">{(save.error as Error).message}</span>;
  if (p.match && !changing) {
    return (
      <p className="flex flex-wrap items-baseline gap-x-2 text-xs text-ink-muted">
        <span>Matched to <span className="text-ink">{p.match.name}</span>{p.kind === 'single' && p.match.finish === 'foil' ? ' · foil' : ''}</span>
        {p.status === 'confirmed' ? (
          <button type="button" onClick={() => save.mutate(null)} className="touch-hit cursor-pointer underline hover:text-ink">you confirmed this · change</button>
        ) : p.status === 'matched' && candidates.some((c) => !sameChoice(c, p.match)) ? (
          <button type="button" onClick={() => setChanging(true)} className="touch-hit cursor-pointer underline hover:text-ink">not this?</button>
        ) : null}
        {error}
      </p>
    );
  }
  if ((p.status === 'ambiguous' || changing) && candidates.length) {
    return (
      <div className="flex flex-col gap-1 text-xs">
        <span className="text-ink-muted">{changing ? 'Which product is this?' : p.note || 'Which product is this?'}</span>
        <span className="flex flex-wrap items-center gap-2">
          <select
            aria-label={`Which product is ${p.title ?? 'this'}?`}
            value={pick}
            onChange={(e) => setPick(Number(e.target.value))}
            className="max-w-full rounded-sm border border-rule-strong bg-paper-raised px-2 py-1 text-sm text-ink"
          >
            {candidates.map((c, i) => <option key={`${c.set_code}|${c.name}|${c.scryfall_id}|${c.finish}`} value={i}>{c.name}{p.kind === 'sld' && c.finish ? ` · ${c.finish}` : ''}{c.price != null ? ` — ${fmtUsd(c.price)}` : ''}</option>)}
          </select>
          <Button tone="paper" onClick={() => save.mutate(candidates[pick])} disabled={save.isPending}>{save.isPending ? 'Saving…' : 'This one'}</Button>
          {changing && <button type="button" onClick={() => setChanging(false)} className="touch-hit cursor-pointer text-ink-muted underline hover:text-ink">cancel</button>}
        </span>
        {error}
      </div>
    );
  }
  return p.note ? <span className="text-xs text-ink-muted">{p.note}</span> : null;
}

/** A pinned listing that isn't a known product yet: the page, why, and the fix when there is one. */
export function ListingInspector({ listing: l, onPick, onDismiss }: { listing: TabListing; onPick: (key: string) => void; onDismiss: () => void }) {
  const storeHealth = useStoreHealth();
  const r = l.row;
  const stock = stockLabel(r);
  return (
    <section aria-labelledby="deal-h" className="flex h-full min-h-0 flex-col gap-5 overflow-y-auto overscroll-contain px-4 pb-8 pt-1 [scrollbar-gutter:stable]">
      <header className="flex flex-wrap items-end gap-x-4 gap-y-2 border-b-2 border-rule-strong pb-1.5">
        <div className="min-w-0 flex-1">
          <h2 id="deal-h" className="text-2xl voice-condensed font-bold leading-tight text-ink">{l.title}</h2>
          <p className="mt-1 text-sm text-ink-muted">From your open tabs · not a product we know yet</p>
        </div>
        <Button tone="paper" emphasis="quiet" onClick={onDismiss}>Dismiss</Button>
      </header>
      <section aria-label="Store" className="flex flex-col gap-1">
        <h3 className={H3}>Store</h3>
        <div className="flex flex-wrap items-baseline gap-x-3 border-b border-rule/60 py-2 text-sm">
          <a href={l.url} target="_blank" rel="noreferrer" className="touch-hit min-w-0 flex-1 text-accent-ink underline">
            {l.store ?? new URL(l.url).hostname.replace(/^www\./, '')}<span aria-hidden="true"> ↗</span><span className="sr-only"> (opens in a new tab)</span>
          </a>
          <ScraperDownMark health={storeHealth(l.store)} />
          {stock && <span className={`text-xs ${r.available ? 'text-ink-muted' : 'text-danger'}`}>{stock}</span>}
          <span className="w-20 shrink-0 text-right tabular text-ink">{r.price != null ? fmtUsd(r.price) : <span className="text-ink-muted">—</span>}</span>
        </div>
      </section>
      <section aria-label="What it is" className="flex flex-col gap-1">
        <h3 className={H3}>What it is</h3>
        {r.error ? <p role="alert" className="text-sm text-danger">{r.error}</p> : <MatchControl p={r} onPick={onPick} />}
      </section>
    </section>
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
        <Row label="Sealed value" value={cost.market} best={best} note={cost.market_source} />
        {hasCards && <Row label="Cards inside, exact printings" value={cost.known_exact} best={hasBoosters ? null : best} />}
        {hasCards && <Row label="Cards inside, cheapest printings" value={cost.known_floor} best={hasBoosters ? null : best} />}
        {hasBoosters && <Row label="Boosters, expected value" value={cost.booster_ev} best={hasCards ? null : best} />}
        {hasCards && hasBoosters && <Row strong label="Total, exact" value={cost.exact} best={best} />}
        {hasCards && hasBoosters && <Row strong label="Total, cheapest" value={cost.floor} best={best} />}
      </dl>
      {(cost.unpriced ?? 0) > 0 && (
        <p className="text-sm text-ink-muted">{cost.unpriced} of {cost.total_cards} cards have no value at their exact printing — totals count only the rest.</p>
      )}
      {cost.notes?.map((n) => <p key={n} className="text-sm text-ink-muted">{n}</p>)}
    </>
  );
}

function WatchControl({ p }: { p: DealProduct }): ReactNode {
  const qc = useQueryClient();
  const [confirm, setConfirm] = useState(false);
  const watch = useWatch(p);
  const urls = p.offers.filter((o) => !o.fromTab).map((o) => o.url);
  const unwatch = async () => {
    for (const url of urls) unwrap(await dealsUnwatch({ query: { url } }));
    patchPrices(qc, urls, (r) => ({ ...r, watching: false }));
    await qc.invalidateQueries({ queryKey: ['deals', 'watched'] });
  };
  if (!p.watching && !p.match) return null;
  return (
    <span className="flex flex-col items-end gap-1">
      {p.watching ? (
        <Button tone="paper" emphasis="quiet" onClick={() => setConfirm(true)}>Stop watching</Button>
      ) : p.best ? (
        <Button tone="paper" disabled={watch.isPending} onClick={() => watch.mutate()}>{watch.isPending ? 'Saving…' : 'Watch'}</Button>
      ) : null}
      {watch.isError && <span role="alert" className="text-xs text-danger">{(watch.error as Error).message}</span>}
      <ConfirmDialog open={confirm} onOpenChange={setConfirm} title={`Stop watching ${p.name}?`} confirmLabel="Stop watching" onConfirm={unwatch}>
        <p>It stops being tracked at {urls.length === 1 ? 'its store' : `all ${urls.length} stores`}.</p>
      </ConfirmDialog>
    </span>
  );
}

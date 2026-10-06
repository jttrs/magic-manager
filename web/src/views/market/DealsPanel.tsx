import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { useJob } from '../../app/useJob';
import { deltaLabel, pricesFrom, sharedErrors, stockLabel, type PriceRow } from '../../core/deals';
import { dealsTabsQuery, unwrap } from '../../app/queries';
import { Button } from '../../components/Button';
import { EmptyNote } from '../../components/States';
import { dealsMatch, type MatchOut, type OpenTabsOut, type StoreTabsOut } from '../../core/api';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';
import type { MarketSearch } from '../../core/search';
import { DealsWorkspace } from './DealsWorkspace';
import { dealsPricesQuery, patchPrices, setPrices, useDealCosts, useDealsData } from './useDealsData';

const MODE_NOTE: Record<StoreTabsOut['mode'], string> = {
  shopify: 'price read from the store',
  meta: 'price read from the store',
  rendered: 'price read from your open tab',
};

const NO_PRICES = new Map<string, PriceRow>();
const H2 = 'flex items-baseline gap-2 border-b-2 border-rule-strong pb-1 text-lg voice-condensed font-bold text-ink';

/** Internal (deals flag): the product pages open in your browser. Read on demand only —
 *  the open-tab set changes under us. Before prices: the pages by store; after: the product table. */
export function DealsPanel({ search, set }: { search: MarketSearch; set: (patch: Partial<MarketSearch>) => void }) {
  const qc = useQueryClient();
  const read = useQuery(dealsTabsQuery());
  const r = read.data;
  const job = useJob();
  const urls = r ? r.stores.flatMap((s) => s.tabs.map((t) => t.url)) : [];
  const live = job.live;
  const reading = live != null && live.status !== 'succeeded' && live.status !== 'failed';
  const prices = useQuery(dealsPricesQuery()).data ?? NO_PRICES;
  useEffect(() => {
    if (live?.status === 'succeeded') setPrices(qc, pricesFrom(live.artifacts));
  }, [live?.status, live?.artifacts, qc]);
  const data = useDealsData('tabs', true);
  const costs = useDealCosts(data.products);
  const onConfirmed = (row: PriceRow) => patchPrices(qc, [row.url], () => row);
  const shared = sharedErrors(prices.values());

  const controls = (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button tone="paper" emphasis={r ? 'quiet' : 'primary'} onClick={() => void read.refetch()} disabled={read.isFetching}>
          {read.isFetching ? 'Reading your tabs…' : r ? 'Read again' : 'Read my open tabs'}
        </Button>
        {r && urls.length > 0 && (
          <Button tone="paper" emphasis={prices.size ? 'quiet' : 'primary'} disabled={reading} onClick={() => { job.reset(); void job.start('deals.read_prices', { urls }); }}>
            {reading ? 'Reading prices…' : prices.size ? 'Read prices again' : `Read ${fmtCount(urls.length, 'price')}`}
          </Button>
        )}
        {r && <span className="text-sm tabular text-ink-muted">{fmtInt(r.windows_read)} of {fmtCount(r.windows, 'window')} read</span>}
      </div>
      {read.isError && <p role="alert" className="text-md text-danger">{(read.error as Error).message}</p>}
      {r?.warnings.map((w) => <p key={w} role="status" className="text-md leading-relaxed text-ink">{w}</p>)}
      {!r && !read.isFetching && !read.isError && (
        <p className="max-w-[60ch] text-md leading-relaxed text-ink-muted">
          Reads the tabs open in Chrome on this computer and keeps the store product pages. Nothing is opened, closed or changed.
        </p>
      )}
      {reading && (
        <p role="status" className="text-sm tabular text-ink-muted">
          {live?.total ? `Reading ${fmtInt(Math.min(live.done + 1, live.total))} of ${fmtInt(live.total)}` : 'Starting…'}
          {live?.log.at(-1)?.msg ? ` · ${new URL(live.log.at(-1)!.msg, 'https://x').hostname.replace(/^www\./, '')}` : ''}
        </p>
      )}
      {live?.status === 'failed' && <p role="alert" className="text-md text-danger">{live.error ?? 'Couldn’t read prices.'}</p>}
      {shared.map((e) => <p key={e} role="alert" className="max-w-[70ch] text-md leading-relaxed text-ink">{e}</p>)}
    </div>
  );

  if (prices.size > 0) {
    return (
      <DealsWorkspace
        products={data.products}
        costs={costs}
        search={search}
        set={set}
        header={controls}
        footer={r && <TabsFooter r={r} needsLook={data.needsLook} shared={shared} onConfirmed={onConfirmed} />}
        emptyNote={<EmptyNote title="Nothing matched yet">Choose a product for the listings below, or read again.</EmptyNote>}
      />
    );
  }
  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto px-5 pb-8 pt-2">
      {controls}
      {r && <Results r={r} />}
    </div>
  );
}

function Results({ r }: { r: OpenTabsOut }) {
  const products = r.stores.reduce((n, s) => n + s.tabs.length, 0);
  if (!products && !r.uncatalogued.length) {
    return r.warnings.length
      ? <EmptyNote title="Couldn’t see your store tabs">Follow the note above, then read again.</EmptyNote>
      : <EmptyNote title="No store pages open">Open product pages from a store, then read again.</EmptyNote>;
  }
  return (
    <div className="flex flex-col gap-5">
      {r.stores.map((s) => (
        <section key={s.key} aria-label={s.name} className="flex flex-col">
          <h2 className={H2}>
            {s.name}
            <span className="text-sm font-normal tabular text-ink-muted">{fmtInt(s.tabs.length)}</span>
            <span className="ml-auto text-xs font-normal text-ink-muted">{MODE_NOTE[s.mode]}{s.no_sales_tax ? ' · no sales tax' : ''}</span>
          </h2>
          <ul>
            {s.tabs.map((t) => <Listing key={t.url} url={t.url} title={t.title} p={undefined} shared={[]} onConfirmed={() => {}} />)}
          </ul>
        </section>
      ))}
      <Uncatalogued r={r} />
      <OtherTabs r={r} />
    </div>
  );
}

function Uncatalogued({ r }: { r: OpenTabsOut }) {
  if (!r.uncatalogued.length) return null;
  return (
    <section aria-label="Stores without a recipe yet" className="flex flex-col gap-1">
      <h2 className="text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">Stores without a recipe yet</h2>
      <ul className="text-sm text-ink">
        {r.uncatalogued.map((u) => <li key={u.host} className="border-b border-rule py-1.5">{u.host} <span className="tabular text-ink-muted">· {fmtCount(u.tabs.length, 'product page')}</span></li>)}
      </ul>
    </section>
  );
}

function OtherTabs({ r }: { r: OpenTabsOut }) {
  return (
    <p className="text-xs text-ink-muted">
      Also open: {fmtCount(r.store_pages, 'other store page')} (carts, collections) · {fmtCount(r.other, 'other tab')}
      {r.dropped_local ? ` · ${fmtCount(r.dropped_local, 'local tab')} skipped` : ''}
      {r.duplicates ? ` · ${fmtCount(r.duplicates, 'duplicate')}` : ''}
    </p>
  );
}

/** Under the table: listings that aren't a known product yet (pick one, or see why), then the rest. */
function TabsFooter({ r, needsLook, shared, onConfirmed }: { r: OpenTabsOut; needsLook: PriceRow[]; shared: string[]; onConfirmed: (row: PriceRow) => void }) {
  const titleOf = useMemo(() => new Map(r.stores.flatMap((s) => s.tabs.map((t) => [t.url, t.title] as const))), [r]);
  return (
    <div className="flex flex-col gap-5">
      {needsLook.length > 0 && (
        <section aria-label="Needs a look" className="flex flex-col">
          <h2 className={H2}>Needs a look <span className="text-sm font-normal tabular text-ink-muted">{fmtInt(needsLook.length)}</span></h2>
          <ul>
            {needsLook.map((p) => <Listing key={p.url} url={p.url} title={titleOf.get(p.url) ?? ''} p={p} shared={shared} onConfirmed={onConfirmed} />)}
          </ul>
        </section>
      )}
      <Uncatalogued r={r} />
      <OtherTabs r={r} />
    </div>
  );
}

function Listing({ url, title, p, shared, onConfirmed }: { url: string; title: string; p?: PriceRow; shared: string[]; onConfirmed: (row: PriceRow) => void }) {
  const stock = stockLabel(p);
  const delta = p ? deltaLabel(p) : null;
  return (
    <li className="flex flex-col gap-0.5 border-b border-rule py-1.5 text-sm">
      <div className="flex items-baseline gap-3">
        <a href={url} target="_blank" rel="noreferrer" className="min-w-0 flex-1 truncate text-ink no-underline hover:text-accent-ink">
          {p?.title || title || url}<span className="sr-only"> (opens in a new tab)</span>
        </a>
        {stock && <span className={`shrink-0 text-xs ${p?.available ? 'text-ink-muted' : 'text-danger'}`}>{stock}</span>}
        <span className="w-20 shrink-0 text-right tabular text-ink">{p?.price != null ? fmtUsd(p.price) : <span className="text-ink-muted">—</span>}</span>
      </div>
      {p?.error && !shared.includes(p.error) && <span className="text-xs text-danger">{p.error}</span>}
      {p && !p.error && <Identity p={p} delta={delta} onConfirmed={onConfirmed} />}
    </li>
  );
}

/** What the listing is and how it compares: a matched/confirmed product line, a
 *  picker when it's ambiguous, or the reason it isn't valued. */
function Identity({ p, delta, onConfirmed }: { p: PriceRow; delta: ReturnType<typeof deltaLabel>; onConfirmed: (row: PriceRow) => void }) {
  const [pick, setPick] = useState(0);
  const [changing, setChanging] = useState(false);
  const candidates = p.candidates ?? [];
  const save = useMutation({
    mutationFn: async (choice: MatchOut | null) =>
      unwrap(await dealsMatch({ body: { url: p.url, title: p.title, price: p.price, currency: p.currency, available: p.available, choice } })),
    onSuccess: onConfirmed,
  });
  if (p.match && !changing) {
    return (
      <p className="flex flex-wrap items-baseline gap-x-2 text-xs text-ink-muted">
        <span className="text-ink">{p.match.name}</span>
        {p.kind === 'single' && p.match.finish === 'foil' && <span>foil</span>}
        {p.market != null && <span className="tabular">· market {fmtUsd(p.market)}</span>}
        {p.contents != null && <span className="tabular">· cards inside {fmtUsd(p.contents)}{p.partial ? '+' : ''}</span>}
        {delta && <span className={`font-medium ${delta.tone === 'good' ? 'text-accent-ink' : delta.tone === 'bad' ? 'text-danger' : ''}`}>· {delta.text}</span>}
        {p.status === 'confirmed' ? (
          <button type="button" onClick={() => save.mutate(null)} className="cursor-pointer underline hover:text-ink">you confirmed this · change</button>
        ) : p.status === 'matched' && candidates.length > 1 ? (
          <button type="button" onClick={() => setChanging(true)} className="cursor-pointer underline hover:text-ink">not this?</button>
        ) : null}
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
            {candidates.map((c, i) => <option key={`${c.set_code}|${c.name}|${c.scryfall_id}`} value={i}>{c.name}{c.price != null ? ` — ${fmtUsd(c.price)}` : ''}</option>)}
          </select>
          <Button tone="paper" onClick={() => save.mutate(candidates[pick], { onSuccess: () => setChanging(false) })} disabled={save.isPending}>{save.isPending ? 'Saving…' : 'This one'}</Button>
          {changing && <button type="button" onClick={() => setChanging(false)} className="cursor-pointer text-ink-muted underline hover:text-ink">cancel</button>}
        </span>
        {save.isError && <span role="alert" className="text-danger">{(save.error as Error).message}</span>}
      </div>
    );
  }
  if (p.status === 'unmatched' || p.status === 'skipped') return <span className="text-xs text-ink-muted">{p.note}</span>;
  return p.note ? <span className="text-xs text-ink-muted">{p.note}</span> : null;
}

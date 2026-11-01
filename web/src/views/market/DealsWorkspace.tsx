import { useQueryClient } from '@tanstack/react-query';
import { useMemo, useRef, type KeyboardEvent, type ReactNode } from 'react';
import { useStoreHealth } from '../../app/scraperHealth';
import { ScraperDownMark } from '../../components/ScraperNotice';
import { Group, Panel, Separator, useDefaultLayout } from 'react-resizable-panels';
import { useMediaQuery } from '../../app/useMediaQuery';
import { Button } from '../../components/Button';
import { Chevron } from '../../components/Chevron';
import { EmptyNote } from '../../components/States';
import type { ProductCostOut } from '../../core/api';
import { BASIS_LABEL, deltaLabel, effectiveType, filterListings, filterSortProducts, gapOf, listingStatus, PRODUCT_TYPE_LABEL, stockLabel, targetMet, targetPriceOf, type DealProduct, type TabListing } from '../../core/deals';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';
import type { MarketSearch } from '../../core/search';
import { DealInspector, ListingInspector } from './DealInspector';
import { dealFilters, dismiss, useWatch, type CostState, type DealCosts, type DealsData } from './useDealsData';

type Props = {
  data: DealsData;
  costs: DealCosts;
  search: MarketSearch;
  set: (patch: Partial<MarketSearch>) => void;
  /** Above the table: progress, notes and shared errors of the reads. */
  header?: ReactNode;
  /** Shown when there is nothing watched and nothing pinned. */
  emptyNote: ReactNode;
};

/** The watchlist table + inspector; what a read of your open tabs found is pinned on top. */
export function DealsWorkspace({ data, costs, search, set, header, emptyNote }: Props) {
  const qc = useQueryClient();
  const filters = useMemo(() => dealFilters(search), [search]);
  const shown = useMemo(() => filterSortProducts(data.products, costs.data, filters), [data.products, costs.data, filters]);
  const pinned = useMemo(() => filterSortProducts(data.pinned, costs.data, filters), [data.pinned, costs.data, filters]);
  const listings = useMemo(() => filterListings(data.listings, filters), [data.listings, filters]);
  const selected = data.products.find((p) => p.key === search.item) ?? data.pinned.find((p) => p.key === search.item);
  const listing = selected ? undefined : data.listings.find((l) => l.key === search.item);
  const pinnedTotal = data.pinned.length + data.listings.length;
  const onDismiss = (keys: string[]) => {
    dismiss(qc, keys);
    if (search.item && keys.includes(search.item)) set({ item: undefined });
  };
  const anything = data.products.length + pinnedTotal > 0;
  const anyShown = shown.length + pinned.length + listings.length > 0;
  const list = (
    <div className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto overscroll-contain px-4 pb-8 pt-2 [scrollbar-gutter:stable]">
      {header}
      {!anything ? (
        emptyNote
      ) : !anyShown ? (
        <EmptyNote title="Nothing matches these filters">
          <Button tone="paper" onClick={() => set({ dq: '', stores: [], types: [], minOff: 0, inStock: false, atTarget: false })}>Clear filters</Button>
        </EmptyNote>
      ) : (
        <>
          <p role="status" className="text-sm tabular text-ink-muted">
            {fmtInt(shown.length)} of {fmtCount(data.products.length, 'watched product')}
            {pinnedTotal > 0 && ` · ${fmtInt(pinned.length + listings.length)} from your open tabs`} · compared to {BASIS_LABEL[search.basis]}
          </p>
          <ProductTable shown={shown} pinned={pinned} listings={listings} costs={costs} basis={search.basis} item={search.item} onPick={(item) => set({ item })} onDismiss={onDismiss} />
        </>
      )}
    </div>
  );
  const inspector = selected
    ? <DealInspector key={selected.key} product={selected} cost={costs.data.get(selected.key)} costState={costs.state.get(selected.key)} onPick={(item) => set({ item })} />
    : listing
      ? <ListingInspector key={listing.key} listing={listing} onPick={(item) => set({ item })} onDismiss={() => onDismiss([listing.key])} />
      : <EmptyNote title="Pick a product">Choose a row to see its stores, what it’s worth and what’s inside.</EmptyNote>;
  return <MasterDetail list={list} inspector={inspector} open={selected != null || listing != null} onBack={() => set({ item: undefined })} backLabel="All products" splitId="mm.deals.split" />;
}

/** A list beside its inspector (resizable split, list 60 / inspector 40); phones show one at a time with a back link. */
export function MasterDetail({ list, inspector, open, onBack, backLabel, splitId }: { list: ReactNode; inspector: ReactNode; open: boolean; onBack: () => void; backLabel: string; splitId: string }) {
  const narrow = useMediaQuery('(max-width: 47.99rem)');
  if (narrow) {
    return open ? (
      <div className="flex h-full min-h-0 flex-col">
        <button type="button" onClick={onBack} className="touch-hit mx-4 inline-flex min-h-11 cursor-pointer items-center gap-0.5 self-start text-sm voice-semi text-accent-ink">
          <Chevron dir="left" className="size-3.5" /> {backLabel}
        </button>
        <div className="min-h-0 flex-1">{inspector}</div>
      </div>
    ) : list;
  }
  return <Split id={splitId} list={list} inspector={inspector} />;
}

function Split({ id, list, inspector }: { id: string; list: ReactNode; inspector: ReactNode }) {
  const layout = useDefaultLayout({ id, panelIds: ['list', 'item'], storage: localStorage });
  return (
    <Group orientation="horizontal" className="h-full min-h-0" defaultLayout={layout.defaultLayout ?? { list: 60, item: 40 }} onLayoutChanged={layout.onLayoutChanged}>
      <Panel id="list" minSize="35" className="flex min-w-0 flex-col">{list}</Panel>
      <Separator aria-label="Resize product list" className="group relative w-4 shrink-0 cursor-col-resize outline-none">
        <span className="absolute inset-y-2 left-1/2 w-px -translate-x-1/2 bg-rule-strong/40 transition-colors ease-guide group-hover:bg-rule-strong group-focus-visible:bg-focus group-data-[separator=active]:bg-focus" />
        <span aria-hidden="true" className="absolute left-1/2 top-1/2 grid h-12 w-3 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-pill border border-rule-strong bg-paper text-2xs leading-none text-ink-muted transition-colors ease-guide group-hover:border-accent group-hover:bg-highlight-solid group-hover:text-on-accent group-focus-visible:bg-highlight-solid group-focus-visible:text-on-accent">⋮</span>
      </Separator>
      <Panel id="item" minSize="28" className="flex min-w-0 flex-col">{inspector}</Panel>
    </Group>
  );
}

const TH = 'py-1.5 pl-3 text-right font-medium';
const GROUP_H = 'pb-1 pt-3 text-left text-sm voice-condensed font-medium uppercase tracking-[0.06em]';

type TableProps = {
  shown: DealProduct[]; pinned: DealProduct[]; listings: TabListing[]; costs: DealCosts; basis: MarketSearch['basis'];
  item?: string; onPick: (key: string) => void; onDismiss: (keys: string[]) => void;
};

function ProductTable({ shown, pinned, listings, costs, basis, item, onPick, onDismiss }: TableProps) {
  const ref = useRef<HTMLTableElement>(null);
  // ↑/↓ move between the product buttons, across both groups.
  const move = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    const btns = [...(ref.current?.querySelectorAll<HTMLButtonElement>('button[data-product]') ?? [])];
    const i = btns.indexOf(document.activeElement as HTMLButtonElement);
    if (i < 0) return;
    e.preventDefault();
    btns[Math.max(0, Math.min(btns.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))]?.focus();
  };
  const fromTabs = pinned.length + listings.length;
  return (
    <div className="@container">
      <table ref={ref} onKeyDown={move} className="w-full border-collapse text-sm tabular">
        <caption className="sr-only">Products</caption>
        <thead>
          <tr className="border-b-2 border-rule-strong text-left text-xs voice-semi text-ink-muted">
            <th scope="col" className="py-1.5 pr-3 font-medium">Product</th>
            <th scope="col" className={TH}>Best</th>
            <th scope="col" className={TH}>Gap</th>
            <th scope="col" className={`${TH} hidden @lg:table-cell`}>Sealed</th>
            <th scope="col" className={`${TH} hidden @md:table-cell`}>Cards inside</th>
          </tr>
        </thead>
        {fromTabs > 0 && (
          <tbody aria-label="From your open tabs">
            <tr className="border-b border-rule-strong">
              <th scope="colgroup" colSpan={5} className={`${GROUP_H} text-accent-ink`}>
                <span className="flex items-baseline gap-2">
                  <span className="min-w-0 truncate">From your open tabs</span>
                  <span className="tabular normal-case tracking-normal text-ink-muted">{fmtInt(fromTabs)}</span>
                  <button
                    type="button"
                    onClick={() => onDismiss([...pinned.map((p) => p.key), ...listings.map((l) => l.key)])}
                    className="touch-hit ml-auto cursor-pointer text-xs normal-case tracking-normal text-ink-muted underline hover:text-ink"
                  >
                    Dismiss all
                  </button>
                </span>
              </th>
            </tr>
            {pinned.map((p) => (
              <ProductRow key={p.key} p={p} cost={costs.data.get(p.key)} state={costs.state.get(p.key)} basis={basis} selected={p.key === item} onPick={() => onPick(p.key)} onDismiss={() => onDismiss([p.key])} />
            ))}
            {listings.map((l) => <ListingRow key={l.key} l={l} selected={l.key === item} onPick={() => onPick(l.key)} onDismiss={() => onDismiss([l.key])} />)}
          </tbody>
        )}
        {shown.length > 0 && (
          <tbody aria-label="Watching">
            {fromTabs > 0 && (
              <tr className="border-b border-rule-strong">
                <th scope="colgroup" colSpan={5} className={`${GROUP_H} text-ink-muted`}>Watching <span className="tabular normal-case tracking-normal">{fmtInt(shown.length)}</span></th>
              </tr>
            )}
            {shown.map((p) => (
              <ProductRow key={p.key} p={p} cost={costs.data.get(p.key)} state={costs.state.get(p.key)} basis={basis} selected={p.key === item} onPick={() => onPick(p.key)} />
            ))}
          </tbody>
        )}
      </table>
    </div>
  );
}

const ROW = 'cursor-pointer border-b border-rule/60 align-top transition-colors ease-guide hover:bg-paper-sunk';
const ROW_ACTION = 'touch-hit cursor-pointer text-xs underline';

/** Watch / Dismiss under a pinned product's name. */
function PinnedActions({ p, onDismiss }: { p: DealProduct; onDismiss: () => void }) {
  const watch = useWatch(p);
  return (
    <span className="mt-0.5 flex flex-wrap items-baseline gap-x-3">
      {p.best && p.match && (
        <button type="button" disabled={watch.isPending} onClick={() => watch.mutate()} className={`${ROW_ACTION} voice-semi font-medium text-accent-ink disabled:cursor-default disabled:opacity-60`}>
          {watch.isPending ? 'Saving…' : 'Watch'}<span className="sr-only"> {p.name}</span>
        </button>
      )}
      <button type="button" onClick={onDismiss} className={`${ROW_ACTION} text-ink-muted hover:text-ink`}>Dismiss<span className="sr-only"> {p.name}</span></button>
      {watch.isError && <span role="alert" className="text-xs text-danger">{(watch.error as Error).message}</span>}
    </span>
  );
}

/** A pinned listing that isn't a known product yet: what it needs, its price, and Dismiss. */
function ListingRow({ l, selected, onPick, onDismiss }: { l: TabListing; selected: boolean; onPick: () => void; onDismiss: () => void }) {
  const storeHealth = useStoreHealth();
  const r = l.row;
  const dash = <span className="text-ink-muted">—</span>;
  return (
    <tr onClick={(e) => { if (!(e.target as HTMLElement).closest('a,button')) onPick(); }} className={ROW}>
      <th scope="row" className="py-2 pr-3 text-left font-normal">
        <button type="button" data-product onClick={onPick} aria-current={selected ? 'true' : undefined} className="touch-hit min-h-11 cursor-pointer text-left text-md voice-semi font-medium text-ink md:min-h-0">
          <span className={selected ? 'highlighter' : ''}>{l.title}</span>
        </button>
        <span className={`block text-xs ${r.error ? 'text-danger' : 'text-ink-muted'}`}>{listingStatus(l)}</span>
        <span className="mt-0.5 flex flex-wrap items-baseline gap-x-3">
          <button type="button" onClick={onDismiss} className={`${ROW_ACTION} text-ink-muted hover:text-ink`}>Dismiss<span className="sr-only"> {l.title}</span></button>
        </span>
      </th>
      <td className="py-2 pl-3 text-right">
        {r.price != null ? <span className="text-ink">{fmtUsd(r.price)}</span> : dash}
        {l.store && <span className="flex items-baseline justify-end gap-1.5 text-xs text-ink-muted">{l.store}<ScraperDownMark health={storeHealth(l.store)} /></span>}
        {r.available === false && <span className="block text-xs text-danger">{stockLabel(r)}</span>}
      </td>
      <td className="py-2 pl-3 text-right">{dash}</td>
      <td className="hidden py-2 pl-3 text-right @lg:table-cell">{dash}</td>
      <td className="hidden py-2 pl-3 text-right @md:table-cell">{dash}</td>
    </tr>
  );
}

function ProductRow({ p, cost, state, basis, selected, onPick, onDismiss }: { p: DealProduct; cost?: ProductCostOut; state?: CostState; basis: MarketSearch['basis']; selected: boolean; onPick: () => void; onDismiss?: () => void }) {
  const loading = p.kind !== 'single' && state?.loading === true;
  const failed = p.kind !== 'single' ? state?.error : undefined;
  const type = effectiveType(p, cost);
  const gap = gapOf(p, cost, basis);
  const label = gap ? deltaLabel({ delta: gap.usd, pct: gap.pct }) : null;
  const toneCls = label?.tone === 'good' ? 'text-accent-ink' : label?.tone === 'bad' ? 'text-danger' : 'text-ink-muted';
  const best = p.best;
  const storeHealth = useStoreHealth();
  const soldOut = best != null && best.available === false;
  const pct = gap == null ? null : Math.abs(gap.pct) < 1 ? 'even' : `${gap.pct < 0 ? '−' : '+'}${Math.abs(Math.round(gap.pct))}%`;
  const dash = (title?: string) => <span className="text-ink-muted" title={title}>{loading ? '…' : '—'}</span>;
  const value = (v: number | null | undefined) => (v == null ? dash(failed) : fmtUsd(v));
  const sealedValue = p.kind === 'single' ? p.singleMarket : cost?.market;
  const exact = cost?.exact;
  const target = targetPriceOf(p, cost);
  const met = targetMet(p, cost) === true;
  return (
    <tr
      aria-busy={loading || undefined}
      onClick={(e) => { if (!(e.target as HTMLElement).closest('a,button')) onPick(); }}
      className={ROW}
    >
      <th scope="row" className="py-2 pr-3 text-left font-normal">
        <button type="button" data-product onClick={onPick} aria-current={selected ? 'true' : undefined} className="touch-hit min-h-11 cursor-pointer text-left text-md voice-semi font-medium text-ink md:min-h-0">
          <span className={selected ? 'highlighter' : ''}>{p.name}</span>
        </button>
        <span className="block text-xs text-ink-muted">
          {[p.set_code.toUpperCase(), PRODUCT_TYPE_LABEL[type], p.finish === 'foil' && 'foil'].filter(Boolean).join(' · ')}
        </span>
        {onDismiss && <PinnedActions p={p} onDismiss={onDismiss} />}
      </th>
      <td className="py-2 pl-3 text-right">
        {best?.price != null ? (
          <>
            <span className="inline-flex items-baseline gap-1.5">
              <span className={`text-ink ${met ? 'highlighter voice-semi font-medium' : ''}`}>{fmtUsd(best.price)}</span>
              {best.store && (
                <a href={best.url} target="_blank" rel="noreferrer" className="touch-hit text-ink-muted no-underline hover:text-accent-ink">
                  <span aria-hidden="true">↗</span><span className="sr-only">Open {best.store} page (new tab)</span>
                </a>
              )}
            </span>
            <span className="flex items-baseline justify-end gap-1.5 text-xs text-ink-muted">{best.store}<ScraperDownMark health={storeHealth(best.store)} /></span>
            {soldOut && <span className="block text-xs text-danger">{stockLabel(best)}</span>}
            {target != null && (
              <span className={`block text-xs ${met ? 'voice-semi text-accent-ink' : 'text-ink-muted'}`}>{met ? `at target ${fmtUsd(target)}` : `target ${fmtUsd(target)}`}</span>
            )}
            {best.trend && best.trend.tone !== 'even' && (
              <span className={`block text-xs ${best.trend.tone === 'good' ? 'text-accent-ink' : 'text-danger'}`} title={best.trend.text}>{best.trend.text.slice(0, 1)}</span>
            )}
          </>
        ) : <span className="text-ink-muted">—</span>}
      </td>
      <td className="py-2 pl-3 text-right" title={label?.text}>
        {gap && pct ? (
          <>
            <span className={`text-md voice-semi font-medium ${toneCls}`}>{pct}</span>
            <span className="block text-xs text-ink-muted">{fmtUsd(Math.abs(gap.usd))}</span>
          </>
        ) : dash(failed)}
      </td>
      <td className="hidden py-2 pl-3 text-right text-ink @lg:table-cell">{value(sealedValue)}</td>
      <td className="hidden py-2 pl-3 text-right @md:table-cell">
        {p.kind === 'single' ? <span className="text-ink-muted">—</span> : exact == null ? dash(failed) : (
          <>
            <span className="text-ink">{fmtUsd(exact)}{(cost?.unpriced ?? 0) > 0 && <span aria-hidden="true" className="text-ink-muted">+</span>}</span>
            {(cost?.unpriced ?? 0) > 0 && <span className="block text-xs text-danger">{fmtInt(cost!.unpriced)} of {fmtInt(cost!.total_cards)} unpriced</span>}
            {cost?.floor != null && <span className="block text-xs text-ink-muted">cheapest {fmtUsd(cost.floor)}</span>}
            {(cost?.booster_ev ?? 0) > 0 && cost?.known_exact != null && (
              <span className="block text-xs text-ink-muted">{fmtUsd(cost.known_exact)} cards + {fmtUsd(cost.booster_ev)} boosters</span>
            )}
          </>
        )}
      </td>
    </tr>
  );
}

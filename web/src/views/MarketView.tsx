import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { decksQuery, deckCostQuery, familiesQuery, marketCardsQuery, marketProductsQuery } from '../app/queries';
import { useJob } from '../app/useJob';
import { ViewLayout } from '../components/AppShell';
import { useFeature } from '../app/features';
import { DealsPanel } from './market/DealsPanel';
import { WatchingPanel } from './market/WatchingPanel';
import { SecretLairFind, SecretLairPanel } from './market/SecretLairPanel';
import { dealFilters, useDealCosts, useDealsData } from './market/useDealsData';
import { CardLines } from './market/CardLines';
import { ProductContents } from './market/ProductContents';
import { FoilGapCell, FoilPremiumFilter } from './market/FoilGap';
import { FloorBasis } from './market/FloorBasis';
import { Chevron } from '../components/Chevron';
import { CopyTargets } from '../components/CopyButton';
import { InfoTip } from '../components/InfoTip';
import { ProgressRule } from '../components/ProgressRule';
import { SearchSelect } from '../components/SearchSelect';
import { ChipToggles, Segmented, SelectField, SideSection, TextField } from '../components/Sidebar';
import { MultiSelect } from '../components/MultiSelect';
import { EmptyNote, ErrorNote, GuideSheet } from '../components/States';
import { buyListTargets } from '../components/buyTargets';
import { TcgplayerMark } from '../components/StoreMarks';
import { collectionBuyList, type CardPriceOut, type DeckCostOut, type ProductValueOut } from '../core/api';
import { fmtCount, fmtInt, fmtUsd } from '../core/format';
import { filterSortProducts, PRODUCT_TYPE_LABEL, PRODUCT_TYPES, typeCounts, type Basis, type DealSort } from '../core/deals';
import { contentsGap, deckBuyItems, deckLedger, filterCardPrices, partialNote, premium, productGroups, type ProductRow } from '../core/market';
import type { MarketSearch } from '../core/search';

const route = getRouteApi('/market');

/** Market: what a set family's sealed products, its cards, or a deck costs —
 *  each priced at the exact printing beside the cheapest printing anywhere. */
export function MarketView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/market' });
  const set = (patch: Partial<MarketSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const fams = useQuery(familiesQuery());
  const decks = useQuery({ ...decksQuery(), enabled: search.subject === 'deck' });
  const cost = useQuery({ ...deckCostQuery(search.deck, search.live), enabled: search.subject === 'deck' && Boolean(search.deck) });

  const famName = fams.data?.find((f) => f.code === search.code)?.name ?? search.code;
  const deckName = decks.data?.find((d) => d.slug === search.deck)?.name ?? search.deck;

  const buyText = (target: 'manapool' | 'tcgplayer' | 'cardkingdom') => async () => {
    const items = cost.data ? deckBuyItems(cost.data.lines, search.buyAt) : [];
    if (!items.length) return '';
    const r = await collectionBuyList({ body: { target, items } });
    if (r.error || !r.data) throw new Error('buy-list failed');
    return r.data.text;
  };
  const dealsOn = useFeature('deals');
  const inDeals = dealsOn && search.subject === 'deals';
  const dealsData = useDealsData(search.deals, inDeals);
  const dealCosts = useDealCosts(dealsData.products);
  // Changing a filter keeps the open product only while it's still in the list.
  const setFilter = (patch: Partial<MarketSearch>) => {
    const next = { ...search, ...patch };
    const stillShown = filterSortProducts(dealsData.products, dealCosts.data, dealFilters(next)).some((p) => p.key === search.item);
    set(search.item && dealsData.products.length && !stillShown ? { ...patch, item: undefined } : patch);
  };
  const counts = typeCounts(dealsData.products, dealCosts.data);
  const toBuy = cost.data?.lines.reduce((n, l) => n + l.buy, 0) ?? 0;
  const toBuyUsd = cost.data?.lines.reduce((s, l) => s + l.buy * ((search.buyAt === 'floor' ? l.floor_usd : l.unit_usd) ?? 0), 0) ?? 0;

  const sidebar = (
    <>
      <SideSection title="Price">
        <Segmented<MarketSearch['subject']>
          label="Subject"
          wrap={dealsOn}
          value={search.subject}
          onChange={(subject) => set({ subject })}
          options={[{ value: 'family', label: 'Set family' }, { value: 'deck', label: 'Deck' }, { value: 'sld', label: 'Secret Lair' }, ...(dealsOn ? [{ value: 'deals' as const, label: 'Deals' }] : [])]}
        />
        {search.subject === 'sld' ? null : search.subject === 'deals' ? (
          <Segmented<MarketSearch['deals']> label="Show" value={search.deals} onChange={(deals) => set({ deals, item: undefined })} options={[{ value: 'tabs', label: 'Open tabs' }, { value: 'watching', label: 'Watching' }]} />
        ) : search.subject === 'family' ? (
          fams.isError ? (
            <p className="text-sm text-danger">Couldn’t load families: {(fams.error as Error).message}</p>
          ) : (
            <SearchSelect label="Set family" noun="family" value={search.code} onChange={(code) => set({ code })} options={(fams.data ?? []).map((f) => ({ value: f.code, label: f.name, hint: f.code.toUpperCase() }))} />
          )
        ) : decks.isError ? (
          <p className="text-sm text-danger">Couldn’t load decks: {(decks.error as Error).message}</p>
        ) : (
          <SearchSelect label="Deck" noun="deck" value={search.deck} onChange={(deck) => set({ deck, live: false })} options={(decks.data ?? []).map((d) => ({ value: d.slug, label: d.name, hint: d.deck_type }))} />
        )}
      </SideSection>
      {search.subject === 'sld' && <SecretLairFind search={search} set={set} />}
      {inDeals && (
        <SideSection title="Find">
          <TextField name="dq" label="Search" value={search.dq} placeholder="Name or set code" onChange={(dq) => setFilter({ dq })} />
          <MultiSelect
            label="Stores"
            noun="stores"
            searchable={false}
            summary={search.stores.length ? undefined : 'All stores'}
            value={search.stores}
            onChange={(stores) => setFilter({ stores })}
            options={dealsData.storeOptions.map((s) => ({ value: s, label: s }))}
          />
          <ChipToggles<(typeof PRODUCT_TYPES)[number]>
            label="Type"
            showLabel
            value={search.types}
            onChange={(types) => setFilter({ types })}
            options={PRODUCT_TYPES.map((t) => ({ value: t, label: PRODUCT_TYPE_LABEL[t], count: counts[t] }))}
          />
          <Segmented<'0' | '10' | '20' | '30'>
            label="Discount"
            showLabel
            labelExtra={<InfoTip label="Under what?">Under the price chosen in <b>Compare to</b>.</InfoTip>}
            value={String(search.minOff) as '0'}
            onChange={(v) => setFilter({ minOff: Number(v) as 0 })}
            options={[{ value: '0', label: 'Any' }, { value: '10', label: '10%+' }, { value: '20', label: '20%+' }, { value: '30', label: '30%+' }]}
          />
          <Segmented<Basis>
            label="Compare to"
            showLabel
            labelExtra={<InfoTip label="What is each price compared to?"><b>Sealed</b> is the sealed product’s market price. <b>Exact</b> is the cards inside at their exact printings plus the boosters’ expected value. <b>Cheapest</b> is each card inside at its cheapest printing anywhere plus the boosters’ expected value.</InfoTip>}
            value={search.basis}
            onChange={(basis) => setFilter({ basis })}
            options={[{ value: 'market', label: 'Sealed' }, { value: 'exact', label: 'Exact' }, { value: 'floor', label: 'Cheapest' }]}
          />
          <SelectField<DealSort>
            label="Sort"
            value={search.dsort}
            onChange={(dsort) => setFilter({ dsort })}
            options={[
              { value: 'gap_pct', label: 'Biggest discount %' }, { value: 'gap_usd', label: 'Biggest discount $' }, { value: 'price', label: 'Lowest price' },
              { value: 'market', label: 'Sealed price' }, { value: 'exact', label: 'Cards, exact' }, { value: 'floor', label: 'Cards, cheapest' }, { value: 'name', label: 'Name' },
            ]}
          />
          <ChipToggles<'in'> label="Availability" value={search.inStock ? ['in'] : []} onChange={(v) => setFilter({ inStock: v.length > 0 })} options={[{ value: 'in', label: 'In stock only' }]} />
          {search.deals === 'watching' && (
            <ChipToggles<'met'> label="Target" value={search.atTarget ? ['met'] : []} onChange={(v) => setFilter({ atTarget: v.length > 0 })} options={[{ value: 'met', label: 'At or under target' }]} />
          )}
        </SideSection>
      )}
      {search.subject === 'family' && (
        <SideSection title="Show">
          <Segmented<MarketSearch['tab']> label="Prices of" value={search.tab} onChange={(tab) => set({ tab })} options={[{ value: 'products', label: 'Sealed' }, { value: 'cards', label: 'Cards' }]} />
          <TextField name="q" label={search.tab === 'products' ? 'Product name' : 'Card name'} value={search.q} placeholder={search.tab === 'products' ? 'e.g. Bundle…' : 'e.g. Cloud…'} onChange={(q) => set({ q })} />
          {search.tab === 'cards' && (
            <>
              <Segmented
                label="Printings"
                showLabel
                value={search.cheaper ? 'cheaper' : 'all'}
                onChange={(v) => set({ cheaper: v === 'cheaper' })}
                options={[{ value: 'all', label: 'All' }, { value: 'cheaper', label: 'Not cheapest' }]}
              />
              <FoilPremiumFilter value={search.foilMax} onChange={(foilMax) => set({ foilMax })} />
              <SelectField<MarketSearch['sort']>
                label="Sort"
                value={search.sort}
                onChange={(sort) => set({ sort })}
                options={[{ value: 'savings', label: 'Biggest premium' }, { value: 'price', label: 'Highest price' }, { value: 'foil', label: 'Smallest foil premium' }, { value: 'set', label: 'Set and number' }]}
              />
            </>
          )}
        </SideSection>
      )}
      {search.subject === 'deck' && search.deck && (
        <SideSection title="Buy">
          <Segmented<MarketSearch['buyAt']>
            label="Printing"
            showLabel
            labelExtra={<InfoTip label="Which printing goes on the list?"><b>Cheapest</b> picks the cheapest nonfoil printing of each card from any set. <b>Deck’s</b> keeps the exact printing and finish in the deck list.</InfoTip>}
            value={search.buyAt}
            onChange={(buyAt) => set({ buyAt })}
            options={[{ value: 'floor', label: 'Cheapest' }, { value: 'exact', label: 'Deck’s' }]}
          />
          <CopyTargets
            lead={`Copy bulk lists · ${fmtCount(toBuy, 'card')} to buy · ≈ ${fmtUsd(toBuyUsd)} at market`}
            targets={buyListTargets(buyText, { cardKingdomNote: 'Card Kingdom takes names only; pick each printing after Find Cards' })}
          />
        </SideSection>
      )}
    </>
  );

  let title = 'Market';
  let summary: ReactNode;
  let body: ReactNode;
  if (search.subject === 'sld') {
    title = 'Secret Lair';
    summary = 'The newest drops: sealed price beside the cards inside, bonus card included';
    body = <SecretLairPanel search={search} set={set} />;
  } else if (search.subject === 'deals' && dealsOn) {
    title = search.deals === 'watching' ? 'Watching' : 'Deals';
    summary = search.deals === 'watching' ? 'Products you watch: best price now, what it’s worth, and what’s inside' : 'Product pages open in your browser, compared to what they’re worth';
    body = search.deals === 'watching' ? <WatchingPanel search={search} set={set} /> : <DealsPanel search={search} set={set} />;
  } else if (search.subject === 'family' || search.subject === 'deals') {
    if (!search.code) {
      body = (
        <EmptyNote title="What does it cost?">
          Choose a set family to price its sealed products against the cards inside, or its cards against the cheapest printing of each. Or choose a deck to cost it out.
        </EmptyNote>
      );
    } else {
      title = famName ?? 'Market';
      body = search.tab === 'products' ? <ProductsPanel code={search.code} q={search.q} /> : <CardsPanel code={search.code} search={search} />;
      summary = search.tab === 'products' ? 'Sealed market price beside what the cards inside are worth' : 'Each printing’s price beside the cheapest printing of the same card';
    }
  } else if (!search.deck) {
    body = <EmptyNote title="Cost out a deck">Choose a deck to see what it costs sealed, bought card by card, or built from your free cards first.</EmptyNote>;
  } else {
    title = deckName ?? 'Deck';
    if (cost.isPending) body = <Loading label={search.live ? 'Checking every set for the cheapest printings…' : 'Pricing the deck…'} />;
    else if (cost.isError) body = <ErrorNote error={cost.error} onRetry={() => cost.refetch()} />;
    else {
      body = <DeckPanel d={cost.data} buyAt={search.buyAt} onCheckLive={() => set({ live: true })} />;
      summary = `${fmtCount(cost.data.total_need, 'card')} · ${fmtInt(cost.data.total_need - toBuy)} from your free cards · ${fmtInt(toBuy)} to buy`;
    }
  }

  const sideSummary = search.subject === 'family' ? famName : search.subject === 'sld' ? 'Secret Lair' : deckName;
  return (
    <ViewLayout label="Market controls" summary={sideSummary} sidebar={sidebar} startOpen={!(search.code || search.deck || search.subject === 'deals' || search.subject === 'sld')}>
      <GuideSheet title={title} summary={summary}>
        {inDeals || search.subject === 'sld' ? <div className="h-full min-h-0">{body}</div> : <div className="h-full overflow-y-auto pb-8">{body}</div>}
      </GuideSheet>
    </ViewLayout>
  );
}

function Loading({ label }: { label: string }) {
  return <p role="status" className="px-5 pt-6 text-md text-ink-muted">{label}</p>;
}

// ---------- sealed products ----------

type Artifact = { label: string; data: unknown };

// Product valuations are slow to compute and prices move about daily: keep each
// family's for 12 hours across reloads.
const VALUES_TTL = 12 * 3600_000;
const valuesStorageKey = (code: string) => `mm.market.values.v2.${code}`;
function readValues(code: string): ProductValueOut[] | null {
  try {
    const hit = JSON.parse(localStorage.getItem(valuesStorageKey(code)) ?? 'null') as { at: number; rows: ProductValueOut[] } | null;
    return hit && Date.now() - hit.at < VALUES_TTL ? hit.rows : null;
  } catch {
    return null;
  }
}
function saveValues(code: string, rows: ProductValueOut[]) {
  try {
    localStorage.setItem(valuesStorageKey(code), JSON.stringify({ at: Date.now(), rows }));
  } catch {
    // Storage full or blocked: the values still show for this visit.
  }
}

function ProductsPanel({ code, q }: { code: string; q: string }) {
  const qc = useQueryClient();
  const products = useQuery(marketProductsQuery(code));
  const valuesKey = useMemo(() => ['market', 'values', code], [code]);
  const values = useQuery({ queryKey: valuesKey, queryFn: () => qc.getQueryData<ProductValueOut[]>(valuesKey) ?? readValues(code), staleTime: Infinity, gcTime: 30 * 60_000 });
  const { live, start, reset } = useJob();
  const started = useRef<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  // Price the family's products once per visit (cached for the session).
  useEffect(() => {
    if (!products.data?.products.length || values.data || started.current === code) return;
    started.current = code;
    reset();
    void start('market.value_family', { code });
  }, [code, products.data, values.data, start, reset]);

  useEffect(() => {
    const art = (live?.artifacts as Artifact[] | undefined)?.find((a) => a.label === 'values');
    if (live?.status === 'succeeded' && art && started.current === code) {
      qc.setQueryData(valuesKey, art.data as ProductValueOut[]);
      saveValues(code, art.data as ProductValueOut[]);
    }
  }, [live?.status, live?.artifacts, code, qc, valuesKey]);

  const retry = () => {
    started.current = code;
    reset();
    void start('market.value_family', { code });
  };

  const groups = useMemo(() => (products.data ? productGroups(products.data.products, values.data ?? undefined, q) : []), [products.data, values.data, q]);

  if (products.isPending) return <Loading label="Reading the family’s sealed products…" />;
  if (products.isError) return <ErrorNote error={products.error} onRetry={() => products.refetch()} />;
  if (!products.data.products.length) return <EmptyNote title="No sealed products">MTGJSON lists no sealed products for this family.</EmptyNote>;

  const running = !values.data && live && live.status !== 'succeeded' && live.status !== 'failed';
  const failed = !values.data && live?.status === 'failed';
  return (
    <div className="flex flex-col gap-2">
      {running && <div className="mx-5"><ProgressRule label="Pricing products" verb="Pricing" done={live.done} total={live.total} message={live.log.at(-1)?.msg} /></div>}
      {failed && (
        <p role="alert" className="mx-5 text-sm text-danger">
          Couldn’t price these products: {live.error ?? 'the job failed'}.{' '}
          <button type="button" className="cursor-pointer underline" onClick={retry}>Try again</button>
        </p>
      )}
      {groups.length === 0 ? (
        <EmptyNote title="Nothing matches">Clear the product name filter.</EmptyNote>
      ) : (
        <table className="mx-5 w-[calc(100%-2.5rem)] border-collapse text-sm tabular">
          <caption className="sr-only">Sealed products: market price and contents value</caption>
          <thead>
            <tr className="border-b-2 border-rule-strong text-left text-xs voice-semi text-ink-muted">
              <th scope="col" className="py-1.5 pr-3 font-medium">Product</th>
              <th scope="col" className="py-1.5 pl-3 text-right font-medium">Sealed</th>
              <th scope="col" className="py-1.5 pl-3 text-right font-medium">
                <span className="inline-flex items-center gap-1">Cards inside<InfoTip label="What is cards inside?" tone="paper">The fixed cards at market plus the expected value of every booster in the box.</InfoTip></span>
              </th>
              <th scope="col" className="hidden py-1.5 pl-3 text-right font-medium sm:table-cell">Difference</th>
            </tr>
          </thead>
          {groups.map((g) => (
            <tbody key={g.key}>
              <tr>
                <th scope="colgroup" colSpan={4} className="border-b border-rule pb-1 pt-4 text-left text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">
                  {g.label} <span className="tabular">· {g.rows.length}</span>
                </th>
              </tr>
              {g.rows.map((p) => (
                <ProductLine key={`${p.set_code}|${p.name}`} p={p} open={open === `${p.set_code}|${p.name}`} onToggle={() => setOpen((o) => (o === `${p.set_code}|${p.name}` ? null : `${p.set_code}|${p.name}`))} pricing={Boolean(running)} />
              ))}
            </tbody>
          ))}
        </table>
      )}
    </div>
  );
}

function ProductLine({ p, open, onToggle, pricing }: { p: ProductRow; open: boolean; onToggle: () => void; pricing: boolean }) {
  const v = p.value;
  const gap = contentsGap(v);
  const pending = pricing && !v;
  return (
    <>
      <tr className="border-b border-rule/60">
        <th scope="row" className="py-1.5 pr-3 text-left font-normal">
          <button type="button" aria-expanded={open} onClick={onToggle} className="group flex cursor-pointer items-baseline gap-1.5 text-left text-ink">
            <Chevron dir={open ? 'down' : 'right'} className="size-3 shrink-0 self-center text-ink-muted transition-transform group-hover:text-ink" />
            <span>{p.name}</span>
          </button>
          {v?.error && <span className="ml-4.5 block text-xs text-danger">Couldn’t price: {v.error}</span>}
        </th>
        <Money v={v?.sealed_market} pending={pending} />
        <Money v={v?.contents_value} pending={pending} partial={partialNote(v)} />
        <td className="hidden py-1.5 pl-3 text-right sm:table-cell">
          {gap == null || partialNote(v) ? <span className="text-ink-muted">{pending ? '…' : '—'}</span> : <Gap gap={gap} />}
        </td>
      </tr>
      {open && (
        <tr>
          <td colSpan={4} className="border-b border-rule bg-paper-sunk/60 px-4 py-3">
            <ProductDetail p={p} />
          </td>
        </tr>
      )}
    </>
  );
}

function Money({ v, pending, partial }: { v: number | null | undefined; pending?: boolean; partial?: string | null }) {
  if (v == null) return <td className="py-1.5 pl-3 text-right"><span className="text-ink-muted">{pending ? '…' : '—'}</span></td>;
  return (
    <td className="py-1.5 pl-3 text-right text-ink">
      {partial ? (
        <span title={partial}>
          {fmtUsd(v)}
          <span aria-hidden="true" className="text-ink-muted">+</span>
          <span className="sr-only"> or more: {partial}</span>
        </span>
      ) : (
        fmtUsd(v)
      )}
    </td>
  );
}

/** Signed difference: cards worth more than the box read in the accent ink. */
function Gap({ gap }: { gap: number }) {
  const sign = gap >= 0.005 ? '+' : gap <= -0.005 ? '−' : '';
  return <span className={gap >= 0.005 ? 'font-medium text-accent-ink' : 'text-ink-muted'}>{sign}{fmtUsd(Math.abs(gap))}</span>;
}

function ProductDetail({ p }: { p: ProductRow }) {
  const v = p.value;
  return (
    <div className="flex flex-col gap-3">
      {v && !v.error && !v.booster_only && v.floor_singles != null && (
        <p className="text-sm text-ink-muted">
          At the cheapest printing of each card: <span className="tabular text-ink">{fmtUsd(v.floor_singles)}</span>
          {' '}(boosters at their expected value)
        </p>
      )}
      <ProductContents set={p.set_code} name={p.name} />
      {p.tcgplayer_url && (
        <a href={p.tcgplayer_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 self-start text-sm voice-semi text-accent-ink no-underline hover:text-ink">
          <TcgplayerMark className="size-4" />Sealed on TCGplayer<span className="sr-only">(opens in a new tab)</span>
        </a>
      )}
    </div>
  );
}

// ---------- cards ----------

const CARD_PAGE = 200;

function CardsPanel({ code, search }: { code: string; search: MarketSearch }) {
  const q = useQuery(marketCardsQuery(code));
  const shown = useMemo(() => (q.data ? filterCardPrices(q.data.cards, search) : []), [q.data, search]);
  // A new filter starts back at the first page.
  const filterKey = `${code}|${search.q}|${search.cheaper}|${search.sort}|${search.foilMax}`;
  const foilFocus = search.sort === 'foil' || search.foilMax !== 'any';
  const [page, setPage] = useState({ key: filterKey, n: CARD_PAGE });
  const limit = page.key === filterKey ? page.n : CARD_PAGE;

  if (q.isPending) return <Loading label="Reading the family’s printings…" />;
  if (q.isError) return <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  if (!shown.length) return <EmptyNote title="Nothing matches">Clear the name filter, show all printings, or allow any foil premium.</EmptyNote>;
  return (
    <div className="flex flex-col">
      <table className="mx-5 w-[calc(100%-2.5rem)] border-collapse text-sm tabular">
        <caption className="sr-only">Card printings: price beside the cheapest printing of the same card</caption>
        <thead className="sticky top-0 z-10 bg-paper">
          <tr className="border-b-2 border-rule-strong text-left text-xs voice-semi text-ink-muted">
            <th scope="col" className="py-1.5 pr-3 font-medium">Card</th>
            <th scope="col" className="py-1.5 pl-3 text-right font-medium">This printing</th>
            <th scope="col" className="py-1.5 pl-3 text-right font-medium">Cheapest</th>
            <th scope="col" className="hidden py-1.5 pl-3 text-right font-medium sm:table-cell">Premium</th>
            <th scope="col" className={`py-1.5 pl-3 text-right font-medium ${foilFocus ? '' : 'hidden sm:table-cell'}`}>Foil premium</th>
            <th scope="col" className="hidden py-1.5 pl-3 text-right font-medium md:table-cell">You own</th>
          </tr>
        </thead>
        <tbody>
          {shown.slice(0, limit).map((c) => <CardLine key={c.scryfall_id} c={c} foilFocus={foilFocus} />)}
        </tbody>
      </table>
      {shown.length > limit && (
        <button type="button" onClick={() => setPage({ key: filterKey, n: limit + CARD_PAGE * 2 })} className="mx-5 mt-3 cursor-pointer self-start rounded-sm border border-rule px-3 py-1.5 text-sm voice-semi text-ink hover:border-rule-strong">
          Show more · {fmtInt(shown.length - limit)} left
        </button>
      )}
    </div>
  );
}

function CardLine({ c, foilFocus }: { c: CardPriceOut; foilFocus: boolean }) {
  const extra = premium(c);
  const same = c.floor_set_code === c.set_code && c.floor_collector_number === c.collector_number;
  return (
    <tr className="border-b border-rule/60">
      <th scope="row" className="py-1.5 pr-3 text-left font-normal">
        <span className="text-ink">{c.name}</span>
        <span className="ml-2 text-xs text-ink-muted">{c.set_code.toUpperCase()} {c.collector_number}{c.treatment ? ' · treated' : ''}</span>
      </th>
      <td className="py-1.5 pl-3 text-right text-ink">{fmtUsd(c.price_usd ?? c.price_usd_foil)}{c.price_usd == null && c.price_usd_foil != null && <span className="ml-1 text-xs text-ink-muted">foil</span>}</td>
      <td className="py-1.5 pl-3 text-right">
        <span className="text-ink">{fmtUsd(c.floor_usd)}</span>
        {c.floor_set_code && !same && <span className="ml-1.5 text-xs text-ink-muted">{c.floor_set_code.toUpperCase()} {c.floor_collector_number}</span>}
      </td>
      <td className="hidden py-1.5 pl-3 text-right sm:table-cell">{extra == null ? <span className="text-ink-muted">—</span> : extra < 0.01 ? <span className="text-ink-muted">cheapest</span> : <span className="text-ink">+{fmtUsd(extra)}</span>}</td>
      <FoilGapCell c={c} className={foilFocus ? '' : 'hidden sm:table-cell'} />
      <td className="hidden py-1.5 pl-3 text-right md:table-cell">{c.owned ? fmtInt(c.owned) : <span className="text-ink-muted">—</span>}</td>
    </tr>
  );
}

// ---------- deck ----------

function DeckPanel({ d, buyAt, onCheckLive }: { d: DeckCostOut; buyAt: MarketSearch['buyAt']; onCheckLive: () => void }) {
  const ledger = deckLedger(d);
  const toBuy = d.lines.filter((l) => l.buy > 0);
  const covered = d.lines.filter((l) => l.buy === 0);
  return (
    <div className="flex flex-col gap-6 px-5 pt-2">
      <table className="w-full max-w-[40rem] border-collapse text-md tabular">
        <caption className="sr-only">Three ways to get this deck</caption>
        <thead>
          <tr className="border-b-2 border-rule-strong text-left text-xs voice-semi text-ink-muted">
            <th scope="col" className="py-1.5 pr-3 font-medium">Way to get it</th>
            <th scope="col" className="py-1.5 pl-3 text-right font-medium">Deck’s printings</th>
            <th scope="col" className="py-1.5 pl-3 text-right font-medium">Cheapest printings</th>
          </tr>
        </thead>
        <tbody>
          {ledger.map((r) => (
            <tr key={r.key} className="border-b border-rule">
              <th scope="row" className="py-2.5 pr-3 text-left font-normal">
                <span className="text-ink">{r.label}</span>
                {r.key === 'sealed' && d.sealed_product && <span className="block text-xs text-ink-muted">{d.sealed_product}</span>}
              </th>
              {r.key === 'sealed' ? (
                <LedgerCell cell={r.exact} colSpan={2} />
              ) : (
                <>
                  <LedgerCell cell={r.exact} />
                  <LedgerCell cell={r.floor} />
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      <FloorBasis live={d.live ?? false} liveError={d.live_error} onCheckLive={onCheckLive} />
      {d.unpriced > 0 && <p className="-mt-3 text-sm text-ink-muted">{fmtCount(d.unpriced, 'printing')} without a price — totals undercount.</p>}

      <CardLines title="To buy" lines={toBuy} unitBasis={buyAt} />
      <CardLines title="Covered by your free cards" worth lines={covered} unitBasis={buyAt} />
    </div>
  );
}

function LedgerCell({ cell, colSpan }: { cell: { value: number | null; best: boolean }; colSpan?: number }) {
  return (
    <td colSpan={colSpan} className="py-2.5 pl-3 text-right">
      {cell.value == null ? (
        <span className="text-ink-muted">—</span>
      ) : (
        <span className={cell.best ? 'text-xl voice-condensed font-bold text-accent-ink' : 'text-xl voice-condensed text-ink'}>
          {fmtUsd(cell.value)}
          {cell.best && <span className="ml-1.5 align-middle text-xs voice-semi font-medium">lowest</span>}
        </span>
      )}
    </td>
  );
}

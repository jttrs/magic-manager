import { useQuery } from '@tanstack/react-query';
import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { useMemo, useState, type ReactNode } from 'react';
import { decksQuery, deckCostQuery, familiesQuery, marketCardsQuery, marketProductsQuery } from '../app/queries';
import { ViewLayout } from '../components/AppShell';
import { useFeature } from '../app/features';
import { DealsPanel } from './market/DealsPanel';
import { useDealsReads } from './market/useDealsReads';
import { SecretLairFind, SecretLairPanel } from './market/SecretLairPanel';
import { dealFilters, useDealCosts, useDealsData } from './market/useDealsData';
import { CardLines } from './market/CardLines';
import { ProductContents } from './market/ProductContents';
import { FoilGapCell, FoilPremiumFilter } from './market/FoilGap';
import { FloorBasis } from './market/FloorBasis';
import { useFamilyValues } from './market/useFamilyValues';
import { Chevron } from '../components/Chevron';
import { CopyTargets } from '../components/CopyButton';
import { InfoTip } from '../components/InfoTip';
import { ProgressRule } from '../components/ProgressRule';
import { SearchSelect } from '../components/SearchSelect';
import { Segmented, SelectField, SideSection, TextField } from '../components/Sidebar';
import { MultiSelect } from '../components/MultiSelect';
import { EmptyNote, ErrorNote, GuideSheet } from '../components/States';
import { buyListTargets } from '../components/buyTargets';
import { ReadTabsMark, RefreshMark, TcgplayerMark } from '../components/StoreMarks';
import { IconAction } from '../components/IconAction';
import { MarketTabs } from './market/MarketTabs';
import { collectionBuyList, type CardPriceOut, type DeckCostOut } from '../core/api';
import { fmtCount, fmtInt, fmtUsd } from '../core/format';
import { filterListings, filterSortProducts, PRODUCT_TYPE_LABEL, PRODUCT_TYPES, typeCounts, type Basis, type DealSort } from '../core/deals';
import { contentsGap, deckBuyItems, deckLedger, filterCardPrices, partialNote, premium, productGroups, type ProductRow } from '../core/market';
import type { MarketSearch } from '../core/search';

const route = getRouteApi('/market');

/** Market: what a set family's sealed products and singles are worth, what a
 *  deck costs, Secret Lair drops and store deals — each valued at the exact
 *  printing beside the cheapest printing anywhere. Modes are the sub-nav strip. */
export function MarketView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/market' });
  const set = (patch: Partial<MarketSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const dealsOn = useFeature('deals');
  // Deals without the feature reads as the default mode.
  const subject = search.subject === 'deals' && !dealsOn ? 'family' : search.subject;
  const fams = useQuery(familiesQuery());
  const decks = useQuery({ ...decksQuery(), enabled: subject === 'deck' });
  const cost = useQuery({ ...deckCostQuery(search.deck, search.live), enabled: subject === 'deck' && Boolean(search.deck) });

  const famName = fams.data?.find((f) => f.code === search.code)?.name ?? search.code;
  const deckName = decks.data?.find((d) => d.slug === search.deck)?.name ?? search.deck;

  const buyText = (target: 'manapool' | 'tcgplayer' | 'cardkingdom') => async () => {
    const items = cost.data ? deckBuyItems(cost.data.lines, search.buyAt) : [];
    if (!items.length) return '';
    const r = await collectionBuyList({ body: { target, items } });
    if (r.error || !r.data) throw new Error('buy-list failed');
    return r.data.text;
  };
  const inDeals = subject === 'deals';
  const dealReads = useDealsReads(inDeals);
  const dealsData = useDealsData(inDeals, dealReads.watchErrors);
  const dealProducts = useMemo(() => [...dealsData.products, ...dealsData.pinned], [dealsData.products, dealsData.pinned]);
  const dealCosts = useDealCosts(dealProducts);
  // Changing a filter keeps the open product only while it's still in the list.
  const setFilter = (patch: Partial<MarketSearch>) => {
    const next = dealFilters({ ...search, ...patch });
    const stillShown = filterSortProducts(dealProducts, dealCosts.data, next).some((p) => p.key === search.item)
      || filterListings(dealsData.listings, next).some((l) => l.key === search.item);
    set(search.item && !dealsData.loading && !stillShown ? { ...patch, item: undefined } : patch);
  };
  const counts = typeCounts(dealProducts, dealCosts.data);
  const toBuy = cost.data?.lines.reduce((n, l) => n + l.buy, 0) ?? 0;
  const toBuyUsd = cost.data?.lines.reduce((s, l) => s + l.buy * ((search.buyAt === 'floor' ? l.floor_usd : l.unit_usd) ?? 0), 0) ?? 0;

  const famPicker = fams.isError ? (
    <p role="alert" className="text-sm text-danger">Couldn’t load families: {(fams.error as Error).message}</p>
  ) : (
    <SearchSelect label="Set family" noun="family" nouns="families" value={search.code} onChange={(code) => set({ code })} options={(fams.data ?? []).map((f) => ({ value: f.code, label: f.name, hint: f.code.toUpperCase() }))} />
  );
  const singles = search.tab === 'cards';

  // Every mode's rail follows Find (text search alone) → Show → Arrange.
  const sidebar = (
    <>
      {subject === 'family' && (
        <>
          <SideSection title="Find">
            <TextField name="q" label={singles ? 'Card name' : 'Product name'} value={search.q} placeholder={singles ? 'e.g. Cloud…' : 'e.g. Bundle…'} onChange={(q) => set({ q })} />
          </SideSection>
          <SideSection title="Show">
            {famPicker}
            <Segmented<MarketSearch['tab']> label="Product type" showLabel value={search.tab} onChange={(tab) => set({ tab })} options={[{ value: 'products', label: 'Sealed' }, { value: 'cards', label: 'Singles' }]} />
            {singles && (
              <>
                <Segmented
                  label="Printings"
                  showLabel
                  value={search.cheaper ? 'cheaper' : 'all'}
                  onChange={(v) => set({ cheaper: v === 'cheaper' })}
                  options={[{ value: 'all', label: 'All' }, { value: 'cheaper', label: 'Not cheapest' }]}
                />
                <FoilPremiumFilter value={search.foilMax} onChange={(foilMax) => set({ foilMax })} />
              </>
            )}
          </SideSection>
          {singles && (
            <SideSection title="Arrange">
              <SelectField<MarketSearch['sort']>
                label="Sort"
                value={search.sort}
                onChange={(sort) => set({ sort })}
                options={[{ value: 'savings', label: 'Biggest premium' }, { value: 'price', label: 'Highest value' }, { value: 'foil', label: 'Smallest foil premium' }, { value: 'set', label: 'Set and number' }]}
              />
            </SideSection>
          )}
        </>
      )}
      {subject === 'deck' && (
        <SideSection title="Show">
          {decks.isError ? (
            <p role="alert" className="text-sm text-danger">Couldn’t load decks: {(decks.error as Error).message}</p>
          ) : (
            <SearchSelect label="Deck" noun="deck" value={search.deck} onChange={(deck) => set({ deck, live: false })} options={(decks.data ?? []).map((d) => ({ value: d.slug, label: d.name, hint: d.deck_type }))} />
          )}
        </SideSection>
      )}
      {subject === 'sld' && <SecretLairFind search={search} set={set} />}
      {inDeals && (
        <>
          <SideSection title="Find">
            <TextField name="dq" label="Product name or set" value={search.dq} placeholder="e.g. Bundle, fin…" onChange={(dq) => setFilter({ dq })} />
          </SideSection>
          <SideSection title="Show">
            <MultiSelect
              label="Stores"
              noun="stores"
              searchable={false}
              summary={search.stores.length ? undefined : 'All stores'}
              value={search.stores}
              onChange={(stores) => setFilter({ stores })}
              options={dealsData.storeOptions.map((s) => ({ value: s, label: s }))}
            />
            <MultiSelect
              label="Product type"
              noun="types"
              searchable={false}
              keepOrder
              summary={search.types.length ? undefined : 'All types'}
              value={search.types}
              onChange={(types) => setFilter({ types: types as MarketSearch['types'] })}
              options={PRODUCT_TYPES.map((t) => ({ value: t, label: PRODUCT_TYPE_LABEL[t], count: counts[t] }))}
            />
            <Segmented<Basis>
              label="Compare to"
              showLabel
              labelExtra={<InfoTip label="What is each price compared to?"><b>Sealed</b> is the sealed product’s market value. <b>Exact</b> is the cards inside at their exact printings plus the boosters’ expected value. <b>Cheapest</b> is each card inside at its cheapest printing anywhere plus the boosters’ expected value.</InfoTip>}
              value={search.basis}
              onChange={(basis) => setFilter({ basis })}
              options={[{ value: 'market', label: 'Sealed' }, { value: 'exact', label: 'Exact' }, { value: 'floor', label: 'Cheapest' }]}
            />
            <Segmented<'0' | '10' | '20' | '30'>
              label="Discount"
              showLabel
              labelExtra={<InfoTip label="Under what?">How far the best price sits under the value chosen in <b>Compare to</b>.</InfoTip>}
              value={String(search.minOff) as '0'}
              onChange={(v) => setFilter({ minOff: Number(v) as 0 })}
              options={[{ value: '0', label: 'Any' }, { value: '10', label: '10%+' }, { value: '20', label: '20%+' }, { value: '30', label: '30%+' }]}
            />
            <Segmented<'all' | 'in'> label="Availability" showLabel value={search.inStock ? 'in' : 'all'} onChange={(v) => setFilter({ inStock: v === 'in' })} options={[{ value: 'all', label: 'Any' }, { value: 'in', label: 'In stock' }]} />
            <Segmented<'all' | 'met'> label="Target" showLabel value={search.atTarget ? 'met' : 'all'} onChange={(v) => setFilter({ atTarget: v === 'met' })} options={[{ value: 'all', label: 'Any' }, { value: 'met', label: 'At or under' }]} />
          </SideSection>
          <SideSection title="Arrange">
            <SelectField<DealSort>
              label="Sort"
              value={search.dsort}
              onChange={(dsort) => setFilter({ dsort })}
              options={[
                { value: 'gap_pct', label: 'Biggest discount %' }, { value: 'gap_usd', label: 'Biggest discount $' }, { value: 'price', label: 'Lowest price' },
                { value: 'market', label: 'Sealed value' }, { value: 'exact', label: 'Cards value, exact' }, { value: 'floor', label: 'Cards value, cheapest' }, { value: 'name', label: 'Name' },
              ]}
            />
          </SideSection>
        </>
      )}
      {subject === 'deck' && search.deck && (
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

  // The title is the sheet's accessible h1 only (never printed): the strip and
  // the summary already say where you are.
  let title = 'Market';
  let summary: ReactNode;
  let actions: ReactNode;
  let body: ReactNode;
  if (subject === 'sld') {
    title = 'Secret Lair';
    summary = 'The newest drops: sealed value beside the cards inside, bonus card included';
    body = <SecretLairPanel search={search} set={set} />;
  } else if (inDeals) {
    title = 'Deals';
    summary = 'Products you watch: best price now, what it’s worth, and what’s inside';
    body = <DealsPanel data={dealsData} costs={dealCosts} reads={dealReads} search={search} set={set} />;
    const busy = dealReads.busy ? 'Reading…' : undefined;
    actions = (
      <>
        <IconAction label="Read my open tabs" Icon={ReadTabsMark} disabled={dealReads.busy} disabledReason={busy} onClick={dealReads.readTabs} />
        <IconAction label="Read watched prices" Icon={RefreshMark} disabled={dealReads.busy || !dealsData.products.length} disabledReason={busy ?? 'Nothing watched yet'} onClick={dealReads.readWatched} />
      </>
    );
  } else if (subject === 'family') {
    if (!search.code) {
      body = (
        <EmptyNote title="Choose a set family">
          Value its sealed products against the cards inside, or its singles against the cheapest printing of each.
        </EmptyNote>
      );
    } else {
      title = famName ?? 'Market';
      body = singles ? <CardsPanel code={search.code} search={search} /> : <ProductsPanel code={search.code} q={search.q} />;
      summary = `${famName} · ${singles ? 'each printing’s value beside the cheapest printing of the same card' : 'sealed value beside what the cards inside are worth'}`;
    }
  } else if (!search.deck) {
    body = <EmptyNote title="Choose a deck">See what it costs sealed, bought card by card, or built from your unused cards first.</EmptyNote>;
  } else {
    title = deckName ?? 'Deck';
    if (cost.isPending) body = <Loading label={search.live ? 'Rechecking every printing for the cheapest…' : 'Working out the deck’s cost…'} />;
    else if (cost.isError) body = <ErrorNote error={cost.error} onRetry={() => cost.refetch()} />;
    else {
      body = <DeckPanel d={cost.data} buyAt={search.buyAt} checkedAt={search.live ? cost.dataUpdatedAt : undefined} />;
      summary = `${deckName} · ${fmtCount(cost.data.total_need, 'card')} · ${fmtInt(cost.data.total_need - toBuy)} from your unused cards · ${fmtInt(toBuy)} to buy`;
    }
    // A12: one recheck across every printing; afterwards the note says so with the time.
    if (!search.live) actions = <IconAction label="Recheck for cheapest" Icon={RefreshMark} disabled={cost.isPending} disabledReason="Working out the cost…" onClick={() => set({ live: true })} />;
  }

  const sideSummary = subject === 'family' ? famName : subject === 'sld' ? 'Secret Lair' : subject === 'deals' ? 'Deals' : deckName;
  return (
    <ViewLayout label="Market controls" summary={sideSummary} sidebar={sidebar} subnav={<MarketTabs subject={subject} />} startOpen={!(search.code || search.deck || search.subject === 'deals' || subject === 'sld')}>
      <GuideSheet title={title} summary={summary} actions={actions} actionsLabel={inDeals ? 'Deals actions' : undefined}>
        {inDeals || subject === 'sld' ? <div className="h-full min-h-0">{body}</div> : <div className="h-full overflow-y-auto pb-8">{body}</div>}
      </GuideSheet>
    </ViewLayout>
  );
}

function Loading({ label }: { label: string }) {
  return <p role="status" className="px-5 pt-6 text-md text-ink-muted">{label}</p>;
}

// ---------- sealed products ----------

function ProductsPanel({ code, q }: { code: string; q: string }) {
  const products = useQuery(marketProductsQuery(code));
  const { values, live, running, failure, reprice } = useFamilyValues(code, Boolean(products.data?.products.length));
  const [open, setOpen] = useState<string | null>(null);

  const groups = useMemo(() => (products.data ? productGroups(products.data.products, values ?? undefined, q) : []), [products.data, values, q]);

  if (products.isPending) return <Loading label="Reading the family’s sealed products…" />;
  if (products.isError) return <ErrorNote error={products.error} onRetry={() => products.refetch()} />;
  if (!products.data.products.length) return <EmptyNote title="No sealed products">MTGJSON lists no sealed products for this family.</EmptyNote>;

  const unpriced = values?.filter((v) => v.error).length ?? 0;
  return (
    <div className="flex flex-col gap-2">
      {running && live && <div className="mx-5"><ProgressRule label="Valuing products" verb="Valuing" done={live.done} total={live.total} message={live.log.at(-1)?.msg} /></div>}
      {failure && (
        <p role="alert" className="mx-5 text-sm text-danger">
          Couldn’t value these products: {failure}.{' '}
          <button type="button" className="cursor-pointer underline" onClick={reprice}>Try again</button>
        </p>
      )}
      {unpriced > 0 && (
        <p className="mx-5 text-sm text-ink-muted">
          {fmtCount(unpriced, 'product')} couldn’t be valued.{' '}
          <button type="button" className="cursor-pointer text-ink underline" onClick={reprice}>Value again</button>
        </p>
      )}
      {groups.length === 0 ? (
        <EmptyNote title="Nothing matches">Clear the product name filter.</EmptyNote>
      ) : (
        <table className="mx-5 w-[calc(100%-2.5rem)] border-collapse text-sm tabular">
          <caption className="sr-only">Sealed products: sealed value and contents value</caption>
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
                <ProductLine key={`${p.set_code}|${p.name}`} p={p} open={open === `${p.set_code}|${p.name}`} onToggle={() => setOpen((o) => (o === `${p.set_code}|${p.name}` ? null : `${p.set_code}|${p.name}`))} pricing={running} />
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
          {v?.error && <span className="ml-4.5 block text-xs text-danger">Couldn’t value: {v.error}</span>}
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
      <PartialUsd v={v} partial={partial} />
    </td>
  );
}

/** A dollar figure; `partial` (why it undercounts) adds a muted "+" — the real value is higher. */
function PartialUsd({ v, partial }: { v: number; partial?: string | null }) {
  if (!partial) return <span className="tabular text-ink">{fmtUsd(v)}</span>;
  return (
    <span className="tabular text-ink" title={partial}>
      {fmtUsd(v)}
      <span aria-hidden="true" className="text-ink-muted">+</span>
      <span className="sr-only"> or more: {partial}</span>
    </span>
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
      {v && !v.error && !v.booster_only && (v.exact_singles != null || v.floor_singles != null) && (
        <p className="text-sm text-ink-muted">
          {v.exact_singles != null && (
            <>At each card’s own printing: <PartialUsd v={v.exact_singles} partial={partialNote(v)} /></>
          )}
          {v.exact_singles != null && v.floor_singles != null && ' · '}
          {v.floor_singles != null && (
            <>At the cheapest printing of each card: <PartialUsd v={v.floor_singles} /></>
          )}
          {v.booster_ev != null && ' (boosters at their expected value)'}
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

// ---------- singles ----------

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
        <caption className="sr-only">Singles: each printing’s value beside the cheapest printing of the same card</caption>
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

function DeckPanel({ d, buyAt, checkedAt }: { d: DeckCostOut; buyAt: MarketSearch['buyAt']; checkedAt?: number }) {
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
      <FloorBasis live={d.live ?? false} liveError={d.live_error} checkedAt={checkedAt} />
      {(d.unpriced > 0 || (d.floor_unpriced ?? 0) > 0) && (
        <p className="-mt-3 text-sm text-ink-muted">
          {d.unpriced > 0 && `${fmtCount(d.unpriced, 'card')} without a price at the deck’s printing`}
          {d.unpriced > 0 && (d.floor_unpriced ?? 0) > 0 && ' · '}
          {(d.floor_unpriced ?? 0) > 0 && `${fmtCount(d.floor_unpriced ?? 0, 'card')} without a price at any printing`}
          {' '}— totals marked + undercount, so they can’t be the lowest.
        </p>
      )}

      <CardLines title="To buy" lines={toBuy} unitBasis={buyAt} />
      <CardLines title="Covered by your unused cards" worth lines={covered} unitBasis={buyAt} />
    </div>
  );
}

function LedgerCell({ cell, colSpan }: { cell: { value: number | null; best: boolean; partial: boolean }; colSpan?: number }) {
  return (
    <td colSpan={colSpan} className="py-2.5 pl-3 text-right">
      {cell.value == null ? (
        <span className="text-ink-muted">—</span>
      ) : (
        <span className={cell.best ? 'text-xl voice-condensed font-bold text-accent-ink' : 'text-xl voice-condensed text-ink'}>
          {fmtUsd(cell.value)}
          {cell.partial && (
            <>
              <span aria-hidden="true" className="text-ink-muted">+</span>
              <span className="sr-only"> or more: some cards have no price</span>
            </>
          )}
          {cell.best && <span className="ml-1.5 align-middle text-xs voice-semi font-medium">lowest</span>}
        </span>
      )}
    </td>
  );
}

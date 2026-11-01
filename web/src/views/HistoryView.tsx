import { useQuery } from '@tanstack/react-query';
import { getRouteApi, Link, useNavigate } from '@tanstack/react-router';
import { useMemo, useState } from 'react';
import { useFeature } from '../app/features';
import { historyEventQuery, historyQuery, purchasesQuery } from '../app/queries';
import { useMediaQuery } from '../app/useMediaQuery';
import { useSelection } from '../app/selection';
import { useRovingFocus } from '../app/useRovingFocus';
import { ViewLayout } from '../components/AppShell';
import { Button } from '../components/Button';
import { Chevron } from '../components/Chevron';
import { InfoTip } from '../components/InfoTip';
import { MultiSelect } from '../components/MultiSelect';
import { IconAction } from '../components/IconAction';
import { DateField, SideSection, TextField } from '../components/Sidebar';
import { FindProductsMark, ReadOrdersMark } from '../components/StoreMarks';
import { SplitPanes } from '../components/SplitPanes';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { VirtualGuide } from '../components/VirtualGuide';
import type { HistoryEntryOut, PurchaseOut } from '../core/api';
import { exportLines } from '../core/guideCard';
import { fmtCount, fmtInt, fmtUsd } from '../core/format';
import { datedNote, filterHistory, filterOrders, fromHistoryLine, groupTimeline, historyCardGroups, KIND_HELP, KIND_LABEL, kindCounts, mergeOrders, movesSummary, type HistorySearch, type MonthGroup, type TimelineRow } from '../core/history';
import { STATUS_LABEL } from '../core/purchases';
import { CollectionTabs } from './collection/CollectionTabs';
import { FindProductsDialog } from './history/FindProductsDialog';
import { OrderReview } from './history/OrderReview';
import { OrderRow, OrdersTotals } from './history/OrderRow';
import { ReadOrdersDialog } from './history/ReadOrdersDialog';
import { RevertImport } from './history/RevertImport';

const route = getRouteApi('/collection/history');
const DAY = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
const FULL = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeZone: 'UTC' });
const dayLabel = (at: string) => DAY.format(new Date(at));

/** Purchase history: every ledger entry and store order, newest first — orders still to decide pinned
 *  under Needs review; the chosen entry's cards (or the order's review) on the right. */
export function HistoryView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/collection/history' });
  const set = (patch: Partial<HistorySearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const q = useQuery(historyQuery());
  const narrow = useMediaQuery('(max-width: 47.99rem)');
  const purchasesOn = useFeature('purchases');
  const orders = useQuery(purchasesQuery(purchasesOn));
  const openEntry = (entry: number | undefined) => set({ entry, order: undefined });
  const openOrder = (order: number | undefined) => set({ order, entry: undefined });

  const merged = useMemo(() => (q.data ? mergeOrders(q.data.entries, purchasesOn ? orders.data?.purchases : []) : null), [q.data, orders.data, purchasesOn]);
  const shown = useMemo(() => (merged ? filterHistory(merged.entries, search) : []), [merged, search]);
  const review = useMemo(() => (merged ? filterOrders(merged.review, search) : []), [merged, search]);
  const recorded = useMemo(() => (merged ? filterOrders(merged.orders, search) : []), [merged, search]);
  const groups = useMemo(() => groupTimeline(shown, recorded), [shown, recorded]);
  const kinds = useMemo(() => (merged ? kindCounts(merged.entries, merged.review.length + merged.orders.length) : []), [merged]);
  const allDays = useMemo(() => (merged ? [...merged.entries.map((e) => e.at), ...merged.review.map((p) => p.ordered_at), ...merged.orders.map((p) => p.ordered_at)].map((d) => d.slice(0, 10)).sort() : []), [merged]);
  const first = allDays[0];
  const last = allDays.at(-1);
  const filtered = Boolean(search.q || search.kinds.length || search.from || search.to);

  // Marks live with the open entry's cards; the header copies them.
  const ev = useQuery(historyEventQuery(search.order == null ? search.entry : undefined));
  const { selected, toggle, clear } = useSelection(`history:${search.entry ?? 0}`);
  const markedCards = useMemo(() => (ev.data ? ev.data.lines.map(fromHistoryLine).filter((c) => selected.has(c.key)) : []), [ev.data, selected]);
  const markable = search.order == null && search.entry != null && Boolean(ev.data?.entry.ledgered && ev.data.lines.length);

  const sidebar = (
    <>
      <SideSection title="Find">
        <TextField name="q" label={purchasesOn ? 'Product, set, file or order' : 'Product, set or file'} value={search.q} placeholder="e.g. Jumpstart, FIN…" onChange={(qv) => set({ q: qv })} />
      </SideSection>
      <SideSection title="Show">
        <MultiSelect
          label="Kind of entry"
          noun="kinds"
          searchable={false}
          keepOrder
          summary={search.kinds.length ? undefined : 'Every kind'}
          value={search.kinds}
          onChange={(v) => set({ kinds: v as HistorySearch['kinds'] })}
          options={kinds}
        />
        <DateField name="from" label="From" value={search.from} min={first} max={search.to ?? last} onChange={(from) => set({ from })} />
        <DateField name="to" label="To" value={search.to} min={search.from ?? first} max={last} onChange={(to) => set({ to })} />
        {filtered && (
          <button type="button" onClick={() => set({ q: '', kinds: [], from: undefined, to: undefined })} className="self-start cursor-pointer text-sm text-on-chrome-muted underline hover:text-on-chrome">
            Clear filters
          </button>
        )}
      </SideSection>
      <SideSection title="What the kinds mean">
        <dl className="flex flex-col gap-1.5 text-xs leading-snug text-on-chrome-muted">
          {kinds.map((k) => (
            <div key={k.value}>
              <dt className="inline voice-semi text-on-chrome">{k.label}: </dt>
              <dd className="inline">{KIND_HELP[k.value]}</dd>
            </div>
          ))}
        </dl>
      </SideSection>
    </>
  );

  let body;
  if (q.isPending) body = <GridSkeleton label="Reading your purchase history…" />;
  else if (q.isError) body = <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  else if (!merged || (!merged.entries.length && !merged.review.length && !merged.orders.length)) {
    body = <EmptyNote title="Nothing added yet">Add cards from Collection → Add cards; every addition appears here with what came in and what it is worth.</EmptyNote>;
  } else {
    const list = <Timeline review={review} groups={groups} total={shown.length + review.length + recorded.length} orderOf={merged.orderOf} active={{ entry: search.entry, order: search.order }} onEntry={openEntry} onOrder={openOrder} />;
    const back = narrow ? () => set({ entry: undefined, order: undefined }) : undefined;
    const inspector = search.order != null && purchasesOn ? (
      <OrderReview key={`o${search.order}`} purchaseId={search.order} onBack={back} onForgotten={() => openOrder(undefined)} />
    ) : search.entry != null ? (
      <EntryInspector key={search.entry} ingestId={search.entry} view={search.view} selected={selected} onToggle={toggle} onReview={openOrder} onView={(view) => set({ view })} onOpen={openEntry} onBack={back} />
    ) : (
      <EmptyNote title={review.length ? 'Pick an entry or an order' : 'Pick an entry'}>
        {review.length
          ? 'Choose an order under Needs review to match it to cards you own or add it, or an entry to see the exact cards it brought in.'
          : 'Choose an entry to see the exact cards it brought in and what they are worth today.'}
      </EmptyNote>
    );
    const open = search.entry != null || (search.order != null && purchasesOn);
    body = narrow ? (open ? inspector : list) : <SplitPanes id="mm.history.split" label="Resize history list" list={list} inspector={inspector} defaults={[40, 60]} />;
  }

  const held = useMemo(() => shown.filter((e) => e.kind !== 'move').reduce((t, e) => t + e.value_usd, 0), [shown]);
  const orderTotals = purchasesOn && orders.data?.purchases.length ? orders.data : null;
  return (
    <ViewLayout label="History controls" summary={filtered ? `${fmtCount(shown.length + review.length + recorded.length, 'entry', 'entries')} shown` : 'Every entry'} sidebar={sidebar} subnav={<CollectionTabs />}>
      <GuideSheet
        title="Purchase history"
        actionsLabel="Purchase history actions"
        actions={
          <>
            {purchasesOn && <ReadOrdersDialog trigger={<IconAction Icon={ReadOrdersMark} label="Read my orders" />} onReview={openOrder} />}
            <FindProductsDialog trigger={<IconAction Icon={FindProductsMark} label="Find products in your cards" />} />
          </>
        }
        marked={markable ? { count: markedCards.length, getText: () => exportLines(markedCards, 'plain'), onClear: clear } : undefined}
        summary={
          q.data
            ? <>
                {fmtCount(shown.length + review.length + recorded.length, 'entry', 'entries')} · {fmtUsd(held)} held at today’s prices
                {orderTotals && <> · <OrdersTotals totals={orderTotals} /></>}
                {q.data.prices_as_of && ` · prices ${q.data.prices_as_of}`}
                {q.data.stale_sets.length > 0 && <span title={q.data.stale_sets.join(', ').toUpperCase()}> · {fmtInt(q.data.stale_sets.length)} sets older than a week</span>}
              </>
            : undefined
        }
      >
        {body}
      </GuideSheet>
    </ViewLayout>
  );
}

type Active = { entry?: number; order?: number };

/** Needs review (pinned) then month sections; one tab stop for the whole list (↑/↓, Home/End). */
function Timeline({ review, groups, total, orderOf, active, onEntry, onOrder }: { review: PurchaseOut[]; groups: MonthGroup[]; total: number; orderOf: Map<number, PurchaseOut>; active: Active; onEntry: (id: number) => void; onOrder: (id: number) => void }) {
  const reviewKeys = review.map((p) => `review:${p.purchase_id}`);
  const keys = [...reviewKeys, ...groups.flatMap((g) => g.rows.map((r) => r.key))];
  const isActive = (r: TimelineRow) =>
    r.type === 'entry' ? r.entry.ingest_id === active.entry || (active.order != null && orderOf.get(r.entry.ingest_id)?.purchase_id === active.order)
    : r.type === 'order' ? r.order.purchase_id === active.order
    : r.entries.some((e) => e.ingest_id === active.entry);
  const activeKey = active.order != null && review.some((p) => p.purchase_id === active.order)
    ? `review:${active.order}`
    : groups.flatMap((g) => g.rows).find(isActive)?.key;
  const { navRef, tabKey, setFocusKey, onKeyDown: move } = useRovingFocus(keys, activeKey, 'data-row');
  if (!total) return <EmptyNote title="No entries match">Clear the search, widen the dates, or show more kinds.</EmptyNote>;
  const paid = review.reduce((t, p) => t + p.paid_usd, 0);
  return (
    <nav ref={navRef} aria-label="Purchase history" onKeyDown={move} className="h-full min-h-0 overflow-y-auto overscroll-contain px-4 pb-6 [scrollbar-gutter:stable]">
      {review.length > 0 && (
        <section aria-labelledby="hm-review" className="mb-2">
          <h2 id="hm-review" className="sticky top-0 z-10 flex items-baseline gap-2 border-b border-rule-strong bg-paper pb-1 pt-3 text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-accent-ink">
            <span className="min-w-0 truncate">Needs review</span>
            <span className="ml-auto tabular normal-case tracking-normal text-ink-muted">{fmtCount(review.length, 'order')} · paid {fmtUsd(paid)}</span>
          </h2>
          <p className="pt-1 text-xs text-ink-muted">Store orders not fully in your collection yet. Open one to match its cards to copies you own or add them.</p>
          <ul>
            {review.map((p, i) => (
              <li key={p.purchase_id}>
                <OrderRow p={p} rowKey={reviewKeys[i]} active={active.order === p.purchase_id} tabbable={reviewKeys[i] === tabKey} onFocus={() => setFocusKey(reviewKeys[i])} onPick={onOrder} />
              </li>
            ))}
          </ul>
        </section>
      )}
      {groups.map((g) => (
        <section key={g.key} aria-labelledby={`hm-${g.key}`} className="[content-visibility:auto] [contain-intrinsic-size:auto_24rem]">
          <h2 id={`hm-${g.key}`} className="sticky top-0 z-10 flex items-baseline gap-2 border-b border-rule bg-paper pb-1 pt-3 text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">
            <span className="min-w-0 truncate">{g.label}</span>
            <span className="ml-auto tabular normal-case tracking-normal">{g.copiesIn ? `${fmtInt(g.copiesIn)} held · ${fmtUsd(g.valueUsd)}` : ''}</span>
          </h2>
          <ul>
            {g.rows.map((r) => (
              <li key={r.key}>
                <Row row={r} order={r.type === 'entry' ? orderOf.get(r.entry.ingest_id) : undefined} active={active} current={isActive(r)} tabbable={r.key === tabKey} onFocus={() => setFocusKey(r.key)} onEntry={onEntry} onOrder={onOrder} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </nav>
  );
}

function Row({ row, order, active, current, tabbable, onFocus, onEntry, onOrder }: { row: TimelineRow; order?: PurchaseOut; active: Active; current: boolean; tabbable: boolean; onFocus: () => void; onEntry: (id: number) => void; onOrder: (id: number) => void }) {
  if (row.type === 'moves') return <MovesRun row={row} active={active.entry} tabbable={tabbable} onFocus={onFocus} onPick={onEntry} />;
  if (row.type === 'order') return <OrderRow p={row.order} rowKey={row.key} active={current} tabbable={tabbable} onFocus={onFocus} onPick={onOrder} />;
  const e = row.entry;
  if (e.kind === 'move') return <MoveLine e={e} rowKey={row.key} active={current} tabbable={tabbable} onFocus={onFocus} onPick={onEntry} />;
  return <EntryRow e={e} order={order} rowKey={row.key} active={current} tabbable={tabbable} onFocus={onFocus} onPick={onEntry} />;
}

const rowClass = (active: boolean) => `ruled flex w-full cursor-pointer items-center gap-3 px-1 text-left transition-colors ease-guide hover:bg-paper-sunk ${active ? 'highlighter' : ''}`;

function EntryRow({ e, order, rowKey, active, tabbable, onFocus, onPick }: { e: HistoryEntryOut; order?: PurchaseOut; rowKey: string; active: boolean; tabbable: boolean; onFocus: () => void; onPick: (id: number) => void }) {
  const sub = [KIND_LABEL[e.kind], order && STATUS_LABEL[order.status], e.set_code?.toUpperCase(), e.detail && e.detail !== e.product ? e.detail : null].filter(Boolean).join(' · ');
  return (
    <button type="button" data-row={rowKey} tabIndex={tabbable ? 0 : -1} onFocus={onFocus} onClick={() => onPick(e.ingest_id)} aria-current={active ? 'true' : undefined} className={`${rowClass(active)} py-2`}>
      <time dateTime={e.at} className="w-12 shrink-0 text-xs tabular text-ink-muted">{dayLabel(e.at)}</time>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className={`truncate text-md voice-semi font-medium ${e.kind === 'unknown' ? 'text-ink-muted' : 'text-ink'}`}>{e.title}</span>
        <span className="truncate text-xs text-ink-muted">
          {sub}
          {e.dated === 'identified' && ' · identified'}
          {e.reverted_by != null && ' · reverted'}
        </span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-0.5 text-xs tabular">
        {e.reverted_by != null ? (
          <span className="text-ink-muted">reverted</span>
        ) : e.ledgered ? (
          <>
            {(e.kind !== 'revert' || e.held > 0) && <span className="text-ink">{fmtUsd(e.value_usd)}</span>}
            {e.kind === 'purchase' && e.paid_usd != null && <span className="text-ink-muted">Paid {fmtUsd(e.paid_usd)}</span>}
            <span className="text-ink-muted">{e.copies_in ? `+${fmtInt(e.copies_in)}` : ''}{e.copies_out ? ` −${fmtInt(e.copies_out)}` : ''}</span>
          </>
        ) : (
          <span className="text-ink-muted" title="Recorded before the ledger: its copies are counted in “Checklists before the ledger”.">{fmtCount(e.lines, 'row')}</span>
        )}
      </span>
    </button>
  );
}

/** A deck move: quieter than an acquisition — nothing new was owned. */
function MoveLine({ e, rowKey, active, tabbable, onFocus, onPick, nested = false }: { e: HistoryEntryOut; rowKey: string; active: boolean; tabbable: boolean; onFocus: () => void; onPick: (id: number) => void; nested?: boolean }) {
  return (
    <button type="button" data-row={rowKey} tabIndex={tabbable ? 0 : -1} onFocus={onFocus} onClick={() => onPick(e.ingest_id)} aria-current={active ? 'true' : undefined} className={`${rowClass(active)} py-1`}>
      <span className="w-12 shrink-0 text-xs tabular text-ink-muted">{nested ? '' : <time dateTime={e.at}>{dayLabel(e.at)}</time>}</span>
      <span className="min-w-0 flex-1 truncate text-sm text-ink-muted">{e.title}</span>
      <span className="shrink-0 text-xs tabular text-ink-muted">{fmtCount(e.lines, 'line')}</span>
    </button>
  );
}

function MovesRun({ row, active, tabbable, onFocus, onPick }: { row: Extract<TimelineRow, { type: 'moves' }>; active?: number; tabbable: boolean; onFocus: () => void; onPick: (id: number) => void }) {
  const holdsActive = row.entries.some((e) => e.ingest_id === active);
  const [open, setOpen] = useState(holdsActive);
  const id = `run-${row.key}`;
  return (
    <>
      <button type="button" data-row={row.key} tabIndex={tabbable ? 0 : -1} onFocus={onFocus} onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls={id} className={`${rowClass(false)} py-1`}>
        <time dateTime={row.entries[0].at} className="w-12 shrink-0 text-xs tabular text-ink-muted">{dayLabel(row.entries[0].at)}</time>
        <span className="min-w-0 flex-1 truncate text-sm text-ink-muted">{movesSummary(row.entries)}</span>
        <Chevron dir={open ? 'up' : 'down'} className="size-3.5 shrink-0 text-ink-muted" />
      </button>
      {open && (
        <ul id={id} className="pl-3">
          {row.entries.map((e) => (
            <li key={e.ingest_id}>
              <MoveLine e={e} rowKey={`${row.key}:${e.ingest_id}`} nested active={active === e.ingest_id} tabbable={false} onFocus={onFocus} onPick={onPick} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function EntryInspector({ ingestId, view, selected, onToggle, onView, onReview, onOpen, onBack }: { ingestId: number; view: 'grid' | 'list'; selected: ReadonlySet<string>; onToggle: (key: string) => void; onView: (v: 'grid' | 'list') => void; onReview: (purchaseId: number) => void; onOpen: (id: number) => void; onBack?: () => void }) {
  const q = useQuery(historyEventQuery(ingestId));
  const all = useQuery(historyQuery());
  const reconstructed = all.data?.entries.find((x) => x.kind === 'checklist' && x.dated === 'reconstructed')?.ingest_id;
  const [reverted, setReverted] = useState<string | null>(null);
  const sections = useMemo(() => (q.data ? historyCardGroups(q.data.lines).map((g) => ({ ...g, level: 2 as const, noun: 'section' })) : []), [q.data]);

  if (q.isPending) return <GridSkeleton label="Loading entry…" />;
  if (q.isError) return <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  const { entry: e, lines } = q.data;
  const note = datedNote(e);

  let cards;
  if (e.kind === 'move') {
    cards = <EmptyNote title="Cards moved, nothing bought">{e.title} {e.method === 'deck-assign' ? 'pledged' : 'released'} {fmtCount(e.lines, 'line')}. What you own did not change.</EmptyNote>;
  } else if (!e.ledgered) {
    cards = (
      <EmptyNote title="Recorded before the ledger">
        This ingest ({fmtCount(e.lines, 'row')}) happened before every copy was tracked. Its cards are counted in{' '}
        {reconstructed ? (
          <button type="button" onClick={() => onOpen(reconstructed)} className="cursor-pointer voice-semi text-accent-ink underline underline-offset-2">Checklists before the ledger</button>
        ) : (
          <b>Checklists before the ledger</b>
        )}{' '}
        (or Provenance unknown), not here.
      </EmptyNote>
    );
  } else if (!lines.length) {
    cards = <EmptyNote title="No cards">This entry moved no copies.</EmptyNote>;
  } else {
    cards = <VirtualGuide sections={sections} density={view} selected={selected} onToggle={onToggle} label={`${e.title} cards`} minCardWidth={118} />;
  }

  return (
    <section aria-labelledby="entry-h" className="flex h-full min-h-0 flex-col">
      <header className="mx-4 flex flex-col gap-2 border-b-2 border-rule-strong pb-2 pt-1">
        {onBack && (
          <button type="button" onClick={onBack} className="inline-flex w-full cursor-pointer items-center gap-0.5 text-sm voice-semi text-accent-ink">
            <Chevron dir="left" className="size-3.5" /> Purchase history
          </button>
        )}
        <div className="flex flex-wrap items-end gap-x-4 gap-y-1">
          <div className="min-w-0">
            <h2 id="entry-h" className="text-2xl voice-condensed font-bold uppercase leading-none text-ink">{e.title}</h2>
            <p className="mt-1 text-sm text-ink-muted">
              {[KIND_LABEL[e.kind], FULL.format(new Date(e.at)), e.set_code?.toUpperCase(), e.detail !== e.product && e.detail].filter(Boolean).join(' · ')}
              <span className="ml-1 inline-flex align-middle">
                <InfoTip label={`What is a ${KIND_LABEL[e.kind].toLowerCase()} entry?`} tone="paper">
                  {KIND_HELP[e.kind]}
                  {e.kind === 'checklist' && ' Opened boosters, bundles and boxes usually arrive this way, so their source product stays unknown unless you record it.'}
                </InfoTip>
              </span>
            </p>
            {note && <p className="mt-0.5 text-xs text-ink-muted">{note}</p>}
            {e.reverted_by != null && (
              <p className="mt-0.5 text-xs text-ink-muted">
                Reverted — its copies were taken back out.{' '}
                <button type="button" onClick={() => onOpen(e.reverted_by!)} className="-my-1 cursor-pointer py-1 voice-semi text-accent-ink underline underline-offset-2">See the revert</button>
              </p>
            )}
            {e.reverts != null && (
              <p className="mt-0.5 text-xs text-ink-muted">
                Undid{' '}
                <button type="button" onClick={() => onOpen(e.reverts!)} className="-my-1 cursor-pointer py-1 voice-semi text-accent-ink underline underline-offset-2">{e.detail ?? 'an import'}</button>.
              </p>
            )}
            {reverted && <p role="status" className="mt-1 text-sm"><span className="highlighter px-1 voice-semi font-medium">{reverted}</span></p>}
          </div>
          <span className="ml-auto flex items-center gap-3 text-sm">
            {e.revertible && e.ledgered && <RevertImport ingestId={e.ingest_id} onDone={setReverted} />}
            {e.kind === 'purchase' && e.purchase_id != null && (
              <Button tone="paper" onClick={() => onReview(e.purchase_id!)}>Review order</Button>
            )}
            {e.deck_slug && (
              <Link to="/decks" search={{ deck: e.deck_slug }} className="voice-semi text-accent-ink underline-offset-2 hover:underline">
                Open deck
              </Link>
            )}
            {e.ledgered && lines.length > 0 && (
              <button type="button" onClick={() => onView(view === 'grid' ? 'list' : 'grid')} className="cursor-pointer text-ink-muted underline hover:text-ink">
                {view === 'grid' ? 'List view' : 'Card view'}
              </button>
            )}
          </span>
        </div>
        {e.kind === 'revert' && (
          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm tabular">
            <Fact label="Took out" value={fmtCount(e.copies_out, 'copy', 'copies')} />
            {e.copies_in > 0 && <Fact label="Put back" value={fmtCount(e.copies_in, 'copy', 'copies')} />}
          </dl>
        )}
        {e.ledgered && e.kind !== 'move' && e.kind !== 'revert' && (
          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm tabular">
            <Fact label="Came in" value={fmtCount(e.copies_in, 'copy', 'copies')} />
            {e.copies_out > 0 && <Fact label={e.dated === 'reconstructed' ? 'Moved to products' : 'Removed'} value={`−${fmtInt(e.copies_out)}`} />}
            <Fact label="Still held" value={`${fmtInt(e.held)} · ${fmtCount(e.printings, 'printing')}`} />
            {e.kind === 'purchase' && e.paid_usd != null && <Fact label="Paid" value={fmtUsd(e.paid_usd)} />}
            <Fact label="Worth today" value={fmtUsd(e.value_usd)} strong />
          </dl>
        )}
      </header>
      <div className="min-h-0 flex-1">{cards}</div>
    </section>
  );
}

function Fact({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="text-xs voice-semi uppercase tracking-[0.06em] text-ink-muted">{label}</dt>
      <dd className={strong ? 'voice-semi font-medium text-ink' : 'text-ink'}>{value}</dd>
    </div>
  );
}

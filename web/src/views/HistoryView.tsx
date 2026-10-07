import { useQuery } from '@tanstack/react-query';
import { getRouteApi, Link, useNavigate } from '@tanstack/react-router';
import { useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { historyEventQuery, historyQuery } from '../app/queries';
import { useMediaQuery } from '../app/useMediaQuery';
import { useSelection } from '../app/selection';
import { ViewLayout } from '../components/AppShell';
import { Chevron } from '../components/Chevron';
import { InfoTip } from '../components/InfoTip';
import { MultiSelect } from '../components/MultiSelect';
import { DateField, SideSection, TextField } from '../components/Sidebar';
import { SplitPanes } from '../components/SplitPanes';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { VirtualGuide } from '../components/VirtualGuide';
import type { HistoryEntryOut } from '../core/api';
import { fmtCount, fmtInt, fmtUsd } from '../core/format';
import { datedNote, filterHistory, groupTimeline, historyCardGroups, KIND_HELP, KIND_LABEL, kindCounts, movesSummary, type HistorySearch, type MonthGroup, type TimelineRow } from '../core/history';
import { CollectionTabs } from './collection/CollectionTabs';

const route = getRouteApi('/collection/history');
const DAY = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
const FULL = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeZone: 'UTC' });
const dayLabel = (at: string) => DAY.format(new Date(at));

/** Purchase history: every ledger entry, newest first; the chosen entry's cards on the right. */
export function HistoryView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/collection/history' });
  const set = (patch: Partial<HistorySearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const q = useQuery(historyQuery());
  const narrow = useMediaQuery('(max-width: 47.99rem)');

  const entries = q.data?.entries;
  const shown = useMemo(() => (entries ? filterHistory(entries, search) : []), [entries, search]);
  const groups = useMemo(() => groupTimeline(shown), [shown]);
  const kinds = useMemo(() => (entries ? kindCounts(entries) : []), [entries]);
  const first = entries?.at(-1)?.at.slice(0, 10);
  const last = entries?.[0]?.at.slice(0, 10);
  const filtered = Boolean(search.q || search.kinds.length || search.from || search.to);

  const sidebar = (
    <>
      <SideSection title="Find">
        <TextField name="q" label="Product, set or file" value={search.q} placeholder="e.g. Jumpstart, FIN…" onChange={(qv) => set({ q: qv })} />
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
        <div className="grid grid-cols-2 gap-2">
          <DateField name="from" label="From" value={search.from} min={first} max={search.to ?? last} onChange={(from) => set({ from })} />
          <DateField name="to" label="To" value={search.to} min={search.from ?? first} max={last} onChange={(to) => set({ to })} />
        </div>
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
  else if (!q.data.entries.length) body = <EmptyNote title="Nothing added yet">Add cards from Collection → Add cards; every addition appears here with what came in and what it is worth.</EmptyNote>;
  else {
    const list = <Timeline groups={groups} total={shown.length} active={search.entry} onPick={(entry) => set({ entry })} />;
    const inspector = search.entry ? (
      <EntryInspector ingestId={search.entry} view={search.view} onView={(view) => set({ view })} onOpen={(entry) => set({ entry })} onBack={narrow ? () => set({ entry: undefined }) : undefined} />
    ) : (
      <EmptyNote title="Pick an entry">Choose an entry to see the exact cards it brought in and what they are worth today.</EmptyNote>
    );
    body = narrow ? (search.entry ? inspector : list) : <SplitPanes id="mm.history.split" label="Resize history list" list={list} inspector={inspector} defaults={[40, 60]} />;
  }

  const held = useMemo(() => shown.filter((e) => e.kind !== 'move').reduce((t, e) => t + e.value_usd, 0), [shown]);
  return (
    <ViewLayout label="History controls" summary={filtered ? `${fmtCount(shown.length, 'entry', 'entries')} shown` : 'Every entry'} sidebar={sidebar}>
      <GuideSheet
        nav={<CollectionTabs />}
        title="Purchase history"
        summary={
          q.data
            ? <>
                {fmtCount(shown.length, 'entry', 'entries')} · {fmtUsd(held)} held at today’s prices
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

/** Month sections; one tab stop for the list (↑/↓, Home/End). */
function Timeline({ groups, total, active, onPick }: { groups: MonthGroup[]; total: number; active?: number; onPick: (id: number) => void }) {
  const navRef = useRef<HTMLElement>(null);
  const [focusKey, setFocusKey] = useState<string | undefined>(undefined);
  const keys = groups.flatMap((g) => g.rows.map((r) => r.key));
  const activeKey = active == null ? undefined : groups.flatMap((g) => g.rows).find((r) => (r.type === 'entry' ? r.entry.ingest_id === active : r.entries.some((e) => e.ingest_id === active)))?.key;
  const tabKey = (focusKey && keys.includes(focusKey) ? focusKey : undefined) ?? activeKey ?? keys[0];
  const move = (e: KeyboardEvent<HTMLElement>) => {
    if (!(e.target as HTMLElement).dataset.row) return;
    const i = keys.indexOf(tabKey ?? '');
    const next = e.key === 'ArrowDown' ? i + 1 : e.key === 'ArrowUp' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? keys.length - 1 : null;
    if (next == null) return;
    e.preventDefault();
    const k = keys[Math.max(0, Math.min(keys.length - 1, next))];
    setFocusKey(k);
    navRef.current?.querySelector<HTMLElement>(`[data-row="${CSS.escape(k)}"]`)?.focus();
  };
  if (!total) return <EmptyNote title="No entries match">Clear the search, widen the dates, or show more kinds.</EmptyNote>;
  return (
    <nav ref={navRef} aria-label="Purchase history" onKeyDown={move} className="h-full min-h-0 overflow-y-auto overscroll-contain px-4 pb-6 [scrollbar-gutter:stable]">
      {groups.map((g) => (
        <section key={g.key} aria-labelledby={`hm-${g.key}`} className="[content-visibility:auto] [contain-intrinsic-size:auto_24rem]">
          <h2 id={`hm-${g.key}`} className="sticky top-0 z-10 flex items-baseline gap-2 border-b border-rule bg-paper pb-1 pt-3 text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">
            <span className="min-w-0 truncate">{g.label}</span>
            <span className="ml-auto tabular normal-case tracking-normal">{g.copiesIn ? `${fmtInt(g.copiesIn)} held · ${fmtUsd(g.valueUsd)}` : ''}</span>
          </h2>
          <ul>
            {g.rows.map((r) => (
              <li key={r.key}>
                <Row row={r} active={active} tabbable={r.key === tabKey} onFocus={() => setFocusKey(r.key)} onPick={onPick} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </nav>
  );
}

function Row({ row, active, tabbable, onFocus, onPick }: { row: TimelineRow; active?: number; tabbable: boolean; onFocus: () => void; onPick: (id: number) => void }) {
  if (row.type === 'moves') return <MovesRun row={row} active={active} tabbable={tabbable} onFocus={onFocus} onPick={onPick} />;
  const e = row.entry;
  if (e.kind === 'move') return <MoveLine e={e} rowKey={row.key} active={active === e.ingest_id} tabbable={tabbable} onFocus={onFocus} onPick={onPick} />;
  return <EntryRow e={e} rowKey={row.key} active={active === e.ingest_id} tabbable={tabbable} onFocus={onFocus} onPick={onPick} />;
}

const rowClass = (active: boolean) => `ruled flex w-full cursor-pointer items-center gap-3 px-1 text-left transition-colors ease-guide hover:bg-paper-sunk ${active ? 'highlighter' : ''}`;

function EntryRow({ e, rowKey, active, tabbable, onFocus, onPick }: { e: HistoryEntryOut; rowKey: string; active: boolean; tabbable: boolean; onFocus: () => void; onPick: (id: number) => void }) {
  const sub = [KIND_LABEL[e.kind], e.set_code?.toUpperCase(), e.detail && e.detail !== e.product ? e.detail : null].filter(Boolean).join(' · ');
  return (
    <button type="button" data-row={rowKey} tabIndex={tabbable ? 0 : -1} onFocus={onFocus} onClick={() => onPick(e.ingest_id)} aria-current={active ? 'true' : undefined} className={`${rowClass(active)} py-2`}>
      <time dateTime={e.at} className="w-12 shrink-0 text-xs tabular text-ink-muted">{dayLabel(e.at)}</time>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className={`truncate text-md voice-semi font-medium ${e.kind === 'unknown' ? 'text-ink-muted' : 'text-ink'}`}>{e.title}</span>
        <span className="truncate text-xs text-ink-muted">
          {sub}
          {e.dated === 'identified' && ' · identified'}
        </span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-0.5 text-xs tabular">
        {e.ledgered ? (
          <>
            <span className="text-ink">{fmtUsd(e.value_usd)}</span>
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

function EntryInspector({ ingestId, view, onView, onOpen, onBack }: { ingestId: number; view: 'grid' | 'list'; onView: (v: 'grid' | 'list') => void; onOpen: (id: number) => void; onBack?: () => void }) {
  const q = useQuery(historyEventQuery(ingestId));
  const all = useQuery(historyQuery());
  const reconstructed = all.data?.entries.find((x) => x.kind === 'checklist' && x.dated === 'reconstructed')?.ingest_id;
  const { selected, toggle } = useSelection(`history:${ingestId}`);
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
    cards = <VirtualGuide sections={sections} density={view} selected={selected} onToggle={toggle} label={`${e.title} cards`} minCardWidth={118} />;
  }

  return (
    <section aria-labelledby="entry-h" className="flex h-full min-h-0 flex-col">
      <header className="mx-4 flex flex-col gap-2 border-b-2 border-rule-strong pb-2 pt-1">
        {onBack && (
          <button type="button" onClick={onBack} className="inline-flex w-full cursor-pointer items-center gap-0.5 text-sm voice-semi text-accent-ink">
            <Chevron dir="left" className="size-3.5" /> All entries
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
          </div>
          <span className="ml-auto flex items-center gap-3 text-sm">
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
        {e.ledgered && e.kind !== 'move' && (
          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm tabular">
            <Fact label="Came in" value={fmtCount(e.copies_in, 'copy', 'copies')} />
            {e.copies_out > 0 && <Fact label={e.dated === 'reconstructed' ? 'Moved to products' : 'Removed'} value={`−${fmtInt(e.copies_out)}`} />}
            <Fact label="Still held" value={`${fmtInt(e.held)} · ${fmtCount(e.printings, 'printing')}`} />
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

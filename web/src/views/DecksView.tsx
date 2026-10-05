import { useQuery } from '@tanstack/react-query';
import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { Group, Panel, Separator, useDefaultLayout } from 'react-resizable-panels';
import { deckQuery, decksQuery } from '../app/queries';
import { useMediaQuery } from '../app/useMediaQuery';
import { useSelection } from '../app/selection';
import { AddCardsDialog, type AddCardsSeed } from '../components/addcards/AddCardsDialog';
import { ViewLayout } from '../components/AppShell';
import { Chevron } from '../components/Chevron';
import { Segmented, SegmentedToggles, SelectField, SideSection, TextField } from '../components/Sidebar';
import { InfoTip } from '../components/InfoTip';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { AddCardMark } from '../components/StoreMarks';
import { VirtualGuide } from '../components/VirtualGuide';
import type { DeckSummaryOut } from '../core/api';
import { DECK_GROUP_LABEL, DECK_GROUPS, deckGuideGroups, deckReviewLines, deckTypeCounts, filterDecks, groupDecks, type DeckGroupBy } from '../core/decks';
import { MultiSelect } from '../components/MultiSelect';
import { fmtInt, fmtUsd } from '../core/format';
import type { DecksSearch } from '../core/search';

const route = getRouteApi('/decks');
const crop = (url: string) => url.replace('/normal/', '/art_crop/');

/** Deck Manager: every tracked deck (recipe) on the left, the chosen deck's cards on the right. */
export function DecksView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/decks' });
  const set = (patch: Partial<DecksSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const decks = useQuery(decksQuery());
  const narrow = useMediaQuery('(max-width: 47.99rem)');

  const shown = useMemo(() => (decks.data ? filterDecks(decks.data, { q: search.q, states: search.states, types: search.types }) : []), [decks.data, search.q, search.states, search.types]);
  const typeOptions = useMemo(() => (decks.data ? deckTypeCounts(decks.data) : []), [decks.data]);
  const groups = useMemo(() => groupDecks(shown, search.group), [shown, search.group]);
  const counts = useMemo(() => {
    const c = { built: 0, deconstructed: 0 };
    for (const d of decks.data ?? []) c[d.state]++;
    return c;
  }, [decks.data]);

  const sidebar = (
    <>
      <SideSection title="Find">
        <TextField name="q" label="Deck, set or author" value={search.q} placeholder="e.g. Counter Blitz, fic…" onChange={(q) => set({ q })} />
      </SideSection>
      <SideSection title="Show">
        <SegmentedToggles
          label="Decks"
          showLabel
          value={[...search.states]}
          onChange={(states) => set({ states: (['built', 'deconstructed'] as const).filter((s) => states.includes(s)) })}
          options={[
            { value: 'built', label: 'Built', count: counts.built },
            { value: 'deconstructed', label: 'Loose', count: counts.deconstructed },
          ]}
        />
        <MultiSelect
          label="Deck type"
          noun="deck types"
          searchable={false}
          keepOrder
          summary={search.types.length ? undefined : 'All deck types'}
          value={search.types}
          onChange={(types) => set({ types })}
          options={typeOptions}
        />
      </SideSection>
      <SideSection title="Arrange">
        <SelectField<DeckGroupBy> label="Group decks by" value={search.group} onChange={(group) => set({ group })} options={DECK_GROUPS.map((g) => ({ value: g, label: DECK_GROUP_LABEL[g] }))} />
        <Segmented label="Card view" showLabel value={search.view} onChange={(view) => set({ view })} options={[{ value: 'grid', label: 'Cards' }, { value: 'list', label: 'List' }]} />
      </SideSection>
    </>
  );

  let body;
  if (decks.isPending) body = <GridSkeleton label="Loading your decks…" />;
  else if (decks.isError) body = <ErrorNote error={decks.error} onRetry={() => decks.refetch()} />;
  else if (!decks.data.length) body = <EmptyNote title="No decks yet">Add a precon or a deck URL from Collection → Add cards, or build one with <span translate="no">uv run mm deck</span>.</EmptyNote>;
  else {
    const list = <DeckList groups={groups} total={shown.length} active={search.deck} onPick={(deck) => set({ deck })} />;
    const inspector = search.deck ? <DeckInspector slug={search.deck} view={search.view} onView={narrow ? (view) => set({ view }) : undefined} onBack={narrow ? () => set({ deck: undefined }) : undefined} /> : <EmptyNote title="Pick a deck">Choose a deck on the left to see its cards.</EmptyNote>;
    body = narrow ? (search.deck ? inspector : list) : <Split list={list} inspector={inspector} />;
  }

  return (
    <ViewLayout label="Deck controls" summary={`${fmtInt(shown.length)} decks · grouped by ${DECK_GROUP_LABEL[search.group].toLowerCase()}`} sidebar={sidebar}>
      <GuideSheet title="Decks" summary={decks.data ? `${fmtInt(decks.data.length)} decks · ${fmtInt(counts.built)} built, ${fmtInt(counts.deconstructed)} loose` : undefined}>
        {body}
      </GuideSheet>
    </ViewLayout>
  );
}

function Split({ list, inspector }: { list: ReactNode; inspector: ReactNode }) {
  const layout = useDefaultLayout({ id: 'mm.decks.split', panelIds: ['list', 'deck'], storage: localStorage });
  return (
    <Group orientation="horizontal" className="h-full min-h-0" defaultLayout={layout.defaultLayout ?? { list: 34, deck: 66 }} onLayoutChanged={layout.onLayoutChanged}>
      <Panel id="list" minSize="22" className="flex min-w-0 flex-col">{list}</Panel>
      <Separator aria-label="Resize deck list" className="group relative w-4 shrink-0 cursor-col-resize outline-none">
        <span className="absolute inset-y-2 left-1/2 w-px -translate-x-1/2 bg-rule-strong/40 transition-colors ease-guide group-hover:bg-rule-strong group-focus-visible:bg-focus group-data-[separator=active]:bg-focus" />
        <span aria-hidden="true" className="absolute left-1/2 top-1/2 grid h-12 w-3 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-pill border border-rule-strong bg-paper text-2xs leading-none text-ink-muted transition-colors ease-guide group-hover:border-accent group-hover:bg-highlight-solid group-hover:text-on-accent group-focus-visible:bg-highlight-solid group-focus-visible:text-on-accent">⋮</span>
      </Separator>
      <Panel id="deck" minSize="40" className="flex min-w-0 flex-col">{inspector}</Panel>
    </Group>
  );
}

/** One tab stop for the whole list (roving focus): ↑/↓ move between decks, Home/End jump, Enter opens. */
function DeckList({ groups, total, active, onPick }: { groups: ReturnType<typeof groupDecks>; total: number; active?: string; onPick: (slug: string) => void }) {
  const navRef = useRef<HTMLElement>(null);
  const flat = groups.flatMap((g) => g.decks.map((d) => d.slug));
  const [focusSlug, setFocusSlug] = useState<string | undefined>(undefined);
  const tabSlug = (focusSlug && flat.includes(focusSlug) ? focusSlug : undefined) ?? (active && flat.includes(active) ? active : flat[0]);
  const move = (e: KeyboardEvent<HTMLElement>) => {
    const i = flat.indexOf(tabSlug ?? '');
    const next = e.key === 'ArrowDown' ? i + 1 : e.key === 'ArrowUp' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? flat.length - 1 : null;
    if (next == null) return;
    e.preventDefault();
    const slug = flat[Math.max(0, Math.min(flat.length - 1, next))];
    setFocusSlug(slug);
    navRef.current?.querySelector<HTMLButtonElement>(`[data-slug="${CSS.escape(slug)}"]`)?.focus();
  };
  if (!total) return <EmptyNote title="No decks match">Clear the search or show both built and loose decks.</EmptyNote>;
  return (
    <nav ref={navRef} aria-label="Decks" onKeyDown={move} className="h-full min-h-0 overflow-y-auto overscroll-contain px-4 pb-6 [scrollbar-gutter:stable]">
      {groups.map((g) => (
        <section key={g.key} aria-labelledby={`dg-${g.key}`} className="[content-visibility:auto] [contain-intrinsic-size:auto_20rem]">
          <h2 id={`dg-${g.key}`} className="sticky top-0 z-10 flex items-baseline gap-2 border-b border-rule bg-paper pb-1 pt-3 text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">
            <span className="min-w-0 truncate">{g.label}</span>
            <span className="ml-auto tabular">{g.decks.length}</span>
          </h2>
          <ul>
            {g.decks.map((d) => (
              <li key={d.slug}><DeckRow d={d} active={d.slug === active} tabbable={d.slug === tabSlug} onFocus={() => setFocusSlug(d.slug)} onPick={() => onPick(d.slug)} /></li>
            ))}
          </ul>
        </section>
      ))}
    </nav>
  );
}

function DeckRow({ d, active, tabbable, onFocus, onPick }: { d: DeckSummaryOut; active: boolean; tabbable: boolean; onFocus: () => void; onPick: () => void }) {
  return (
    <button
      type="button"
      data-slug={d.slug}
      tabIndex={tabbable ? 0 : -1}
      onFocus={onFocus}
      onClick={onPick}
      aria-current={active ? 'true' : undefined}
      className={`ruled flex w-full cursor-pointer items-center gap-3 px-1 py-2 text-left transition-colors ease-guide hover:bg-paper-sunk ${active ? 'highlighter' : ''}`}
    >
      {d.image_uri ? (
        <img src={crop(d.image_uri)} alt="" loading="lazy" decoding="async" className="size-10 shrink-0 rounded-xs object-cover" />
      ) : (
        <span aria-hidden className="size-10 shrink-0 rounded-xs border border-rule bg-paper-sunk" />
      )}
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-md voice-semi font-medium text-ink">{d.name}</span>
        <span className="truncate text-xs tabular text-ink-muted">
          {[d.deck_type, d.set_code?.toUpperCase(), d.released?.slice(0, 4)].filter(Boolean).join(' · ')}
        </span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-0.5 text-xs tabular">
        <span className="text-ink">{fmtUsd(d.value_usd)}</span>
        <span className={`voice-condensed uppercase tracking-[0.06em] ${d.state === 'built' ? 'text-accent-ink' : 'text-ink-muted'}`}>{d.state === 'built' ? 'Built' : 'Loose'}</span>
      </span>
    </button>
  );
}

function DeckInspector({ slug, view, onView, onBack }: { slug: string; view: 'grid' | 'list'; onView?: (v: 'grid' | 'list') => void; onBack?: () => void }) {
  const q = useQuery(deckQuery(slug));
  const { selected, toggle, clear } = useSelection(`deck:${slug}`);
  const [seed, setSeed] = useState<AddCardsSeed | null>(null);
  const sections = useMemo(() => (q.data ? deckGuideGroups(q.data.cards).map((g) => ({ ...g, level: 2 as const, noun: 'section' })) : []), [q.data]);
  useEffect(() => setSeed(null), [slug]);

  if (q.isPending) return <GridSkeleton label="Loading deck…" />;
  if (q.isError) return <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  const { deck, cards } = q.data;
  const marked = selected.size;

  return (
    <section aria-labelledby="deck-h" className="flex h-full min-h-0 flex-col">
      <header className="mx-4 flex flex-wrap items-end gap-x-4 gap-y-1 border-b-2 border-rule-strong pb-1.5 pt-1">
        {onBack && (
          <button type="button" onClick={onBack} className="inline-flex w-full cursor-pointer items-center gap-0.5 text-sm voice-semi text-accent-ink">
            <Chevron dir="left" className="size-3.5" /> All decks
          </button>
        )}
        <div className="min-w-0">
          <h2 id="deck-h" className="text-2xl voice-condensed font-bold uppercase leading-none text-ink">{deck.name}</h2>
          <p className="mt-1 text-sm tabular text-ink-muted">
            {[deck.deck_type, deck.set_name ?? deck.set_code?.toUpperCase(), deck.released?.slice(0, 4), deck.source !== deck.deck_type && deck.source, deck.author && `by ${deck.author}`].filter(Boolean).join(' · ')}
            {' · '}
            {fmtInt(deck.cards)} cards · {fmtUsd(deck.value_usd)} · {deck.state === 'built' ? `built, ${Math.round(deck.pledged_pct)}% pledged` : 'loose'}
            <span className="ml-1 inline-flex align-middle">
              <InfoTip label="What do built, pledged and free mean?" tone="paper">
                <b>Built</b>: you keep this deck assembled; its cards are <b>pledged</b> to it, so they aren’t counted as free. <b>Loose</b>: you keep the recipe, but the cards sit in your collection. <b>Free to use</b>: copies you own that no built deck has pledged.
              </InfoTip>
            </span>
          </p>
        </div>
        <span className="ml-auto flex flex-wrap items-center gap-x-1">
          {marked > 0 && (
            <>
              <GhostAction onClick={() => setSeed({ name: deck.name, lines: deckReviewLines(cards, selected) })} label={`Review ${fmtInt(marked)} marked to add`} />
              <button type="button" onClick={clear} className="cursor-pointer px-1 text-sm text-ink-muted underline hover:text-ink">Clear</button>
            </>
          )}
          <GhostAction onClick={() => setSeed({ name: deck.name, lines: deckReviewLines(cards) })} label="Review deck to add" />
          {onView && (
            <button type="button" onClick={() => onView(view === 'grid' ? 'list' : 'grid')} className="cursor-pointer px-2 text-sm text-ink-muted underline hover:text-ink">
              {view === 'grid' ? 'List view' : 'Card view'}
            </button>
          )}
        </span>
      </header>
      <div className="min-h-0 flex-1">
        <VirtualGuide sections={sections} density={view} selected={selected} onToggle={toggle} label={`${deck.name} cards`} minCardWidth={118} />
      </div>
      <AddCardsDialog seed={seed} onSeedDone={() => setSeed(null)} />
    </section>
  );
}

function GhostAction({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group inline-flex min-h-8 cursor-pointer items-center gap-1.5 rounded-sm px-2 text-md voice-semi font-medium text-accent-ink transition-colors duration-200 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk"
    >
      <AddCardMark className="size-5 transition-transform duration-300 ease-guide group-hover:-translate-y-0.5" />
      <span className="underline-offset-4 group-hover:underline">{label}</span>
    </button>
  );
}

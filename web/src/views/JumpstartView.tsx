import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getRouteApi, Link, useNavigate } from '@tanstack/react-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { jumpstartPackQuery, jumpstartQuery, jumpstartSetsQuery } from '../app/queries';
import { useJob } from '../app/useJob';
import { useMediaQuery } from '../app/useMediaQuery';
import { useRovingFocus } from '../app/useRovingFocus';
import { useSelection } from '../app/selection';
import { ViewLayout } from '../components/AppShell';
import { Chevron } from '../components/Chevron';
import { CopyTargets } from '../components/CopyButton';
import { InfoTip } from '../components/InfoTip';
import { ProgressRule } from '../components/ProgressRule';
import { SearchSelect } from '../components/SearchSelect';
import { Segmented, SelectField, SideSection, TextField } from '../components/Sidebar';
import { SplitPanes } from '../components/SplitPanes';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { buyListTargets } from '../components/buyTargets';
import { RereadMark } from '../components/StoreMarks';
import { VirtualGuide } from '../components/VirtualGuide';
import { jumpstartBuyList, type JumpstartOut, type JumpstartPackOut } from '../core/api';
import { fmtCount, fmtInt, fmtUsd } from '../core/format';
import { colorLabel, coverage, filterPacks, groupPacks, ownedLabel, PACK_SHOW, packCardGroups, shopLead, showCounts, SHOW_LABEL, summaryLine, type JumpstartSearch, type PackGroup, type Shop } from '../core/jumpstart';
import { CollectionTabs } from './collection/CollectionTabs';

const route = getRouteApi('/collection/jumpstart');
const LAST_SET = 'mm.jumpstart.set';
const crop = (url: string) => url.replace('/normal/', '/art_crop/');

/** Jumpstart: every pack version of a set, what your free cards can build, and what to buy. */
export function JumpstartView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/collection/jumpstart' });
  const set = useCallback((patch: Partial<JumpstartSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true }), [navigate]);
  const qc = useQueryClient();
  const narrow = useMediaQuery('(max-width: 47.99rem)');
  const sets = useQuery(jumpstartSetsQuery());

  // Default set: the one you last looked at, else the newest you own packs from.
  const code = search.set ?? (sets.data ? (localStorage.getItem(LAST_SET) ?? (sets.data.sets.find((s) => s.owned_packs > 0) ?? sets.data.sets[0])?.code) : undefined);
  useEffect(() => {
    if (search.set) localStorage.setItem(LAST_SET, search.set);
  }, [search.set]);

  const q = useQuery(jumpstartQuery(code));
  const data = q.isPlaceholderData ? undefined : q.data;

  // A set never read fetches its pack lists once (a job); "Read again" re-reads them.
  const { live: jobLive, start, reset } = useJob();
  const [startedFor, setStartedFor] = useState<string | null>(null);
  const startedRef = useRef<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  // Set once the post-job refetch of the set has landed, so "succeeded but still not ready" can't flash.
  const [rechecked, setRechecked] = useState<string | null>(null);
  const read = useCallback(() => {
    if (!code) return;
    startedRef.current = code;
    setStartedFor(code);
    setStartError(null);
    setRechecked(null);
    reset();
    void start('jumpstart.read', { code }).then((err) => {
      if (err) {
        setStartError(err);
        startedRef.current = null;
      }
    });
  }, [code, reset, start]);
  useEffect(() => {
    if (data && !data.ready && !q.isFetching && startedRef.current !== code && !startError) read();
  }, [data, q.isFetching, code, read, startError]);
  const live = startedFor === code ? jobLive : null;
  const running = Boolean(live && live.status !== 'succeeded' && live.status !== 'failed');
  useEffect(() => {
    if (live?.status === 'succeeded' && code) void qc.invalidateQueries({ queryKey: ['jumpstart'] }).then(() => setRechecked(code));
  }, [live?.status, qc, code]);
  const readError = startError ?? (live?.status === 'failed' ? (live.error ?? 'Reading the packs failed.') : live?.status === 'succeeded' && rechecked === code ? 'The packs were read, but their card prices are still missing. Try again.' : null);

  const packs = useMemo(() => data?.packs ?? [], [data]);
  const shown = useMemo(() => filterPacks(packs, search), [packs, search]);
  const groups = useMemo(() => groupPacks(shown), [shown]);
  const counts = useMemo(() => showCounts(packs), [packs]);

  const buyText = (target: 'manapool' | 'tcgplayer' | 'cardkingdom') => async () => {
    const r = await jumpstartBuyList({ path: { code: code! }, body: { shop: search.shop, target } });
    if (r.error || !r.data) throw new Error('buy-list failed');
    return r.data.text;
  };

  const sidebar = (
    <>
      <SideSection title="Scope">
        {sets.isPending ? (
          <p role="status" className="text-sm text-on-chrome-muted">Loading Jumpstart sets…</p>
        ) : sets.isError ? (
          <p className="text-sm text-danger">Couldn’t load Jumpstart sets: {(sets.error as Error).message}</p>
        ) : (
          <SearchSelect
            label="Jumpstart set"
            noun="Jumpstart set"
            value={code}
            onChange={(s) => set({ set: s, pack: undefined })}
            options={sets.data.sets.map((s) => ({ value: s.code, label: s.name, hint: `${s.code.toUpperCase()} · ${s.owned_packs ? `${s.owned_packs} of ${s.packs} owned` : `${s.packs} packs`}` }))}
          />
        )}
      </SideSection>
      <SideSection title="Show">
        <SelectField<JumpstartSearch['show']>
          label="Packs"
          value={search.show}
          onChange={(show) => set({ show })}
          options={PACK_SHOW.map((s) => ({ value: s, label: SHOW_LABEL[s], count: data ? counts[s] : undefined }))}
        />
        <TextField name="q" label="Pack or card" value={search.q} placeholder="e.g. Angels, Giada…" onChange={(qv) => set({ q: qv })} />
        <Segmented label="Card view" showLabel value={search.view} onChange={(view) => set({ view })} options={[{ value: 'grid', label: 'Cards' }, { value: 'list', label: 'List' }]} />
      </SideSection>
      <SideSection title="Buy">
        <Segmented<Shop>
          label="Shop for"
          showLabel
          labelExtra={
            <InfoTip label="What do the two lists buy?">
              <b>Every theme</b>: the cards you’re missing to keep one built copy of every theme at once, plus each theme’s cards from its other versions — so any version can be assembled. Copies already in built packs count as yours. <b>Packs I don’t own</b>: each pack version you have no copy of, card for card, with its front card.
            </InfoTip>
          }
          value={search.shop}
          onChange={(shop) => set({ shop })}
          options={[{ value: 'buildable', label: 'Every theme' }, { value: 'packs', label: 'Packs I don’t own' }]}
        />
        {data?.ready && (
          <CopyTargets
            lead={shopLead(search.shop, data)}
            targets={buyListTargets(buyText)}
          />
        )}
      </SideSection>
    </>
  );

  let body;
  if (sets.isSuccess && !sets.data.sets.length) body = <EmptyNote title="No Jumpstart sets">MTGJSON lists no Jumpstart packs yet.</EmptyNote>;
  else if (!code || q.isPending) body = <GridSkeleton label="Loading Jumpstart packs…" />;
  else if (q.isError) body = <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  else if (!q.data.ready) {
    body = (
      <div className="mx-auto mt-[12vh] flex max-w-[52ch] flex-col gap-3 px-6">
        {readError ? (
          <ErrorNote error={new Error(readError)} onRetry={read} />
        ) : (
          <>
            <ProgressRule label="Reading the packs" verb="Reading" done={live?.done ?? 0} total={live?.total ?? null} message={live?.log.at(-1)?.msg ?? 'pack lists'} />
            <p className="text-sm text-ink-muted">The first time, every pack’s card list is fetched from MTGJSON — under a minute. After that it opens at once.</p>
          </>
        )}
      </div>
    );
  } else {
    const list = <PackList groups={groups} total={shown.length} active={search.pack} onPick={(pack) => set({ pack })} />;
    const inspector = search.pack ? (
      <PackInspector key={search.pack} code={q.data.code} fileName={search.pack} view={search.view} onView={narrow ? (view) => set({ view }) : undefined} onBack={narrow ? () => set({ pack: undefined }) : undefined} />
    ) : (
      <EmptyNote title="Pick a pack">Choose a pack to see its cards, which you have free, and which you’d still need.</EmptyNote>
    );
    body = narrow ? (search.pack ? inspector : list) : <SplitPanes id="mm.jumpstart.split" detailId="pack" label="Resize pack list" list={list} inspector={inspector} defaults={[42, 58]} />;
  }

  return (
    <ViewLayout label="Jumpstart controls" summary={[q.data?.name ?? code?.toUpperCase(), SHOW_LABEL[search.show]].filter(Boolean).join(' · ')} sidebar={sidebar}>
      <GuideSheet
        nav={<CollectionTabs />}
        title="Jumpstart"
        summary={
          running && q.data?.ready ? (
            <ProgressRule label="Reading the packs again" verb="Reading" done={live?.done ?? 0} total={live?.total ?? null} message={live?.log.at(-1)?.msg} />
          ) : data?.ready ? (
            <ReadySummary data={data} />
          ) : undefined
        }
        actions={
          q.data?.ready ? (
            <button
              type="button"
              onClick={read}
              disabled={running}
              title="Fetch every pack’s card list again, with its front card"
              className="inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-sm px-2 text-sm voice-semi font-medium text-accent-ink transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk disabled:cursor-not-allowed disabled:text-ink-muted disabled:opacity-60 disabled:hover:bg-transparent"
            >
              <RereadMark className="size-[1.2rem]" />
              {running ? 'Reading…' : 'Read again'}
            </button>
          ) : undefined
        }
      >
        {body}
      </GuideSheet>
    </ViewLayout>
  );
}

function ReadySummary({ data }: { data: JumpstartOut }) {
  return (
    <>
      <span className="voice-semi text-ink">{data.name}</span> · {summaryLine(data)}
      <span className="ml-1 inline-flex align-middle">
        <InfoTip label="What do ready, close and free mean?" tone="paper">
          <b>Free</b> cards are copies you own that no built deck has pledged. A pack is <b>ready</b> when your free cards cover all of it and <b>close</b> when it’s {fmtCount(data.close_short ?? 3, 'card')} or fewer short. Each pack is checked on its own, so two packs can count the same free copy.
        </InfoTip>
      </span>
    </>
  );
}

/** Colour sections of pack rows; one tab stop for the list (↑/↓, Home/End, Enter opens). */
function PackList({ groups, total, active, onPick }: { groups: PackGroup[]; total: number; active?: string; onPick: (fileName: string) => void }) {
  const keys = groups.flatMap((g) => g.packs.map((p) => p.file_name));
  const { navRef, tabKey, setFocusKey, onKeyDown } = useRovingFocus(keys, active, 'data-pack');
  if (!total) return <EmptyNote title="No packs match">Clear the search or show every pack.</EmptyNote>;
  return (
    <nav ref={navRef} aria-label="Jumpstart packs" onKeyDown={onKeyDown} className="h-full min-h-0 overflow-y-auto overscroll-contain px-4 pb-6 [scrollbar-gutter:stable]">
      {groups.map((g) => (
        <section key={g.key} aria-labelledby={`jg-${g.key}`} className="[content-visibility:auto] [contain-intrinsic-size:auto_24rem]">
          <h2 id={`jg-${g.key}`} className="sticky top-0 z-10 flex items-baseline gap-2 border-b border-rule bg-paper pb-1 pt-3 text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">
            <span className="min-w-0 truncate">{g.label}</span>
            <span className="ml-auto tabular normal-case tracking-normal">{fmtCount(g.packs.length, 'pack')}{g.ready ? ` · ${fmtInt(g.ready)} ready` : ''}</span>
          </h2>
          <ul>
            {g.packs.map((p) => (
              <li key={p.file_name}>
                <PackRow p={p} active={active === p.file_name} tabbable={p.file_name === tabKey} onFocus={() => setFocusKey(p.file_name)} onPick={() => onPick(p.file_name)} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </nav>
  );
}

function PackRow({ p, active, tabbable, onFocus, onPick }: { p: JumpstartPackOut; active: boolean; tabbable: boolean; onFocus: () => void; onPick: () => void }) {
  return (
    <button
      type="button"
      data-pack={p.file_name}
      tabIndex={tabbable ? 0 : -1}
      onFocus={onFocus}
      onClick={onPick}
      aria-current={active ? 'true' : undefined}
      className={`ruled flex w-full cursor-pointer items-center gap-3 px-1 py-2 text-left transition-colors ease-guide hover:bg-paper-sunk ${active ? 'highlighter' : ''}`}
    >
      {p.top_card_image ? (
        <img src={crop(p.top_card_image)} alt="" loading="lazy" decoding="async" className="size-10 shrink-0 rounded-xs object-cover" />
      ) : (
        <span aria-hidden className="size-10 shrink-0 rounded-xs border border-rule bg-paper-sunk" />
      )}
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="flex min-w-0 items-baseline gap-2">
          <span className="truncate text-md voice-semi font-medium text-ink">{p.name}</span>
          {p.built > 0 ? (
            <span className="shrink-0 text-xs voice-condensed uppercase tracking-[0.06em] text-accent-ink" aria-label={`${p.built} built`}>×{fmtInt(p.built)} built</span>
          ) : p.deconstructed > 0 ? (
            <span className="shrink-0 text-xs voice-condensed uppercase tracking-[0.06em] text-ink-muted" title={ownedLabel(p)}>owned</span>
          ) : null}
        </span>
        <span className="truncate text-xs tabular text-ink-muted">
          {[p.color.length > 1 ? p.color : null, p.top_card && `${fmtUsd(p.top_card_usd)} ${p.top_card}`].filter(Boolean).join(' · ')}
        </span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-0.5 text-xs tabular">
        <span className="text-ink">{fmtUsd(p.usd_total)}</span>
        <span className={p.status === 'far' ? 'text-ink-muted' : 'voice-semi text-accent-ink'}>{coverage(p)}</span>
      </span>
    </button>
  );
}

function PackInspector({ code, fileName, view, onView, onBack }: { code: string; fileName: string; view: 'grid' | 'list'; onView?: (v: 'grid' | 'list') => void; onBack?: () => void }) {
  const q = useQuery(jumpstartPackQuery(code, fileName));
  const { selected, toggle } = useSelection(`jumpstart:${fileName}`);
  const sections = useMemo(() => (q.data ? packCardGroups(q.data.cards).map((g) => ({ ...g, level: 2 as const, noun: 'section' })) : []), [q.data]);

  if (q.isPending) return <GridSkeleton label="Loading pack…" />;
  if (q.isError) return <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  const { pack: p, cards, unknown } = q.data;
  const owned = ownedLabel(p);

  return (
    <section aria-labelledby="pack-h" className="flex h-full min-h-0 flex-col">
      <header className="mx-4 flex flex-col gap-2 border-b-2 border-rule-strong pb-2 pt-1">
        {onBack && (
          <button type="button" onClick={onBack} className="inline-flex w-full cursor-pointer items-center gap-0.5 text-sm voice-semi text-accent-ink">
            <Chevron dir="left" className="size-3.5" /> All packs
          </button>
        )}
        <div className="flex flex-wrap items-end gap-x-4 gap-y-1">
          <div className="min-w-0">
            <h2 id="pack-h" className="text-2xl voice-condensed font-bold uppercase leading-none text-ink">{p.name}</h2>
            <p className="mt-1 text-sm tabular text-ink-muted">
              {[colorLabel(p.color), fmtCount(p.card_count, 'card'), fmtUsd(p.usd_total), p.front_card && `front card ${p.front_card}`].filter(Boolean).join(' · ')}
            </p>
          </div>
          <span className="ml-auto flex items-center gap-3 text-sm">
            {p.deck_slug && (
              <Link to="/decks" search={{ deck: p.deck_slug }} className="voice-semi text-accent-ink underline-offset-2 hover:underline">
                Open deck
              </Link>
            )}
            {onView && (
              <button type="button" onClick={() => onView(view === 'grid' ? 'list' : 'grid')} className="cursor-pointer text-ink-muted underline hover:text-ink">
                {view === 'grid' ? 'List view' : 'Card view'}
              </button>
            )}
          </span>
        </div>
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm tabular">
          <Fact label="Free cards cover" value={`${fmtInt(p.have)} of ${fmtInt(p.have + p.short)}`} strong={p.status === 'build'} />
          {p.short > 0 && <Fact label="Short" value={fmtCount(p.short, 'card')} />}
          <Fact label="You own" value={owned || 'No copy'} />
          {p.top_card && <Fact label="Top card" value={`${p.top_card} · ${fmtUsd(p.top_card_usd)}`} />}
        </dl>
        {unknown?.length ? <p className="text-xs text-ink-muted">Not in your card data yet: {unknown.join(', ')}. Read the packs again to fetch them.</p> : null}
      </header>
      <div className="min-h-0 flex-1">
        <VirtualGuide sections={sections} density={view} selected={selected} onToggle={toggle} label={`${p.name} cards`} minCardWidth={118} />
      </div>
      {cards.length === 0 && <EmptyNote title="No cards">This pack’s card list is empty.</EmptyNote>}
    </section>
  );
}

function Fact({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="text-xs voice-semi uppercase tracking-[0.06em] text-ink-muted">{label}</dt>
      <dd className={strong ? 'voice-semi font-medium text-accent-ink' : 'text-ink'}>{value}</dd>
    </div>
  );
}

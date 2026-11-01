import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useCallback, useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react';
import { familiesQuery, rankingOptionsQuery, rankingQuery } from '../../app/queries';
import { useJob } from '../../app/useJob';
import { useSelection } from '../../app/selection';
import { ViewLayout } from '../../components/AppShell';
import { Button } from '../../components/Button';
import { CardArt } from '../../components/CardFace';
import { CardInspector } from '../../components/CardInspector';
import { CardHover } from '../../components/CardHover';
import { ColorIdentity, ManaCost } from '../../components/ManaSymbols';
import { IconAction } from '../../components/IconAction';
import { IconTooltip } from '../../components/IconTooltip';
import { iconActionClass } from '../../components/iconActionClass';
import { InfoTip } from '../../components/InfoTip';
import { MarkToggle } from '../../components/MarkToggle';
import { ProgressRule } from '../../components/ProgressRule';
import { SearchSelect } from '../../components/SearchSelect';
import { Segmented, SelectField, SideSection, TextField } from '../../components/Sidebar';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../../components/States';
import { EdhrecMark, RereadMark } from '../../components/StoreMarks';
import { VirtualGuide } from '../../components/VirtualGuide';
import { EdhrecHealth } from '../../components/EdhrecHealth';
import type { RankedOut, RankingOut } from '../../core/api';
import { fmtInt, fmtUsd } from '../../core/format';
import { exportLines, type GuideCard } from '../../core/guideCard';
import {
  edhrecUrl, emptyRankingNote, failureText, fetchedAgo, filtersApply, FIRST_PAGE, fmtMetric, metricLabel, nextPage, OWN_LABEL, rankedCard, rankedTypes,
  rankingPage, rankingRequest, rankingSummary, roleFor, SCOPE_LABEL, TIMEFRAME_LABEL, timeframeApplies,
} from '../../core/rankings';
import { RANK_OWN, RANK_SCOPES, RANK_TIMEFRAMES, type CompareSearch, type RankOwn, type RankScope, type RankTimeframe } from '../../core/search';

const RANKING_HEALTH = ['edhrec-rankings/edhrec'];

type Props = { search: CompareSearch; set: (p: Partial<CompareSearch>) => void; subnav: ReactNode };

/** Explore → Rankings: EDHREC's top commanders (narrowed by any mix of color,
 *  tag and set), top cards and saltiest cards, each joined to what you own. The
 *  first 100 show; "Load more" adds 50 at a time from the cached list. A list
 *  never read is fetched as a job with progress. */
export function RankingsExplore({ search, set, subnav }: Props) {
  const qc = useQueryClient();
  const req = useMemo(() => rankingRequest(search), [search]);
  const reqKey = JSON.stringify(req);
  // Load more grows the page; any filter change starts again at the first page.
  const pageKey = JSON.stringify([req, search.own, search.rq.trim()]);
  const [more, setMore] = useState({ key: pageKey, limit: FIRST_PAGE });
  const limit = more.key === pageKey ? more.limit : FIRST_PAGE;
  const page = useMemo(() => rankingPage(req, search, limit), [req, search, limit]);
  const ranking = useQuery(rankingQuery(page));
  // The list dims while a filter change loads, not while "Load more" fetches.
  const dim = ranking.isPlaceholderData && limit === FIRST_PAGE;
  const opts = useQuery(rankingOptionsQuery());
  const commanders = filtersApply(search);
  const fams = useQuery({ ...familiesQuery(), enabled: commanders });
  const { selected, toggle, clear } = useSelection('explore');
  const [inspecting, setInspecting] = useState<GuideCard | null>(null);

  // A ranking never read is fetched once per visit; Refresh re-reads it.
  const { live: jobLive, start, reset } = useJob();
  const [startedKey, setStartedKey] = useState<string | null>(null);
  // Mirrors startedKey synchronously so a double-run effect can't submit twice.
  const startedRef = useRef<string | null>(null);
  const fetchRanking = useCallback((refresh: boolean) => {
    startedRef.current = reqKey;
    setStartedKey(reqKey);
    reset();
    void start('edhrec.rankings', { ...req, refresh });
  }, [req, reqKey, reset, start]);
  const data = ranking.isPlaceholderData ? undefined : ranking.data;
  useEffect(() => {
    // Wait for a fresh read: a stale "never read" answer may already be outdated.
    if (data && !data.cached && !ranking.isFetching && startedRef.current !== reqKey) fetchRanking(false);
  }, [data, ranking.isFetching, reqKey, fetchRanking]);
  const live = startedKey === reqKey ? jobLive : null;
  const running = Boolean(live && live.status !== 'succeeded' && live.status !== 'failed');
  useEffect(() => {
    if (live?.status === 'succeeded') {
      void qc.invalidateQueries({ queryKey: ['explore', 'ranking'] });
      void qc.invalidateQueries({ queryKey: ['explore', 'ranking-options'] });
    }
  }, [live?.status, qc]);

  const r = ranking.data?.cached ? ranking.data : undefined;
  const scope = (ranking.data?.scope ?? search.rank) as RankScope;
  const cards = useMemo(() => (ranking.data?.rows ?? []).map((x) => rankedCard(scope, x)), [ranking.data, scope]);
  // Marks outlive the page and the name filter: remember every card seen.
  const [seen] = useState(() => new Map<string, GuideCard>());
  const marked = useMemo(() => {
    for (const c of cards) seen.set(c.key, c);
    return [...selected].map((k) => seen.get(k)).filter((c): c is GuideCard => Boolean(c));
  }, [cards, seen, selected]);
  const famName = fams.data?.find((f) => f.code === search.fam)?.name;
  const tfOn = timeframeApplies(search);

  const sidebar = (
    <>
      <SideSection title="Find">
        <TextField name="rq" label="Card name" value={search.rq} placeholder="e.g. Krenko…" onChange={(rq) => set({ rq })} />
      </SideSection>
      <SideSection title="Show">
        <SelectField<RankScope> label="List" value={search.rank} onChange={(rank) => set({ rank })} options={RANK_SCOPES.map((s) => ({ value: s, label: SCOPE_LABEL[s] }))} />
        <fieldset disabled={!commanders} className="flex min-w-0 flex-col gap-4 disabled:opacity-55" aria-describedby={commanders ? undefined : 'rank-filters-note'}>
          <legend className="sr-only">Narrow top commanders</legend>
          <SearchSelect
            label="Color identity"
            noun="color identity"
            value={search.color ?? ''}
            onChange={(color) => set({ color: color || undefined })}
            options={[{ value: '', label: 'Any' }, ...(opts.data?.colors ?? []).map((c) => ({ value: c.slug, label: c.label, hint: c.colors || 'C' }))]}
          />
          <TagField key={search.tag ?? ''} value={search.tag ?? ''} suggestions={opts.data?.tags ?? []} onCommit={(tag) => set({ tag: tag || undefined })} />
          <SearchSelect
            label="Set family"
            noun="family"
            value={search.fam ?? ''}
            onChange={(fam) => set({ fam: fam || undefined })}
            options={[
              { value: '', label: 'Any' },
              // a family from the URL that isn't in the list (yet) still reads as itself
              ...(search.fam && !fams.data?.some((f) => f.code === search.fam) ? [{ value: search.fam, label: search.fam.toUpperCase() }] : []),
              ...(fams.data ?? []).map((f) => ({ value: f.code, label: f.name, hint: f.code.toUpperCase() })),
            ]}
          />
          {!commanders && <p id="rank-filters-note" className="text-sm text-on-chrome-muted">Color, tag and set narrow top commanders.</p>}
        </fieldset>
        <fieldset disabled={!tfOn} className="min-w-0 disabled:opacity-55" aria-describedby={tfOn ? undefined : 'rank-tf-note'}>
          <Segmented<RankTimeframe> label="Timeframe" showLabel value={search.tf} onChange={(tf) => set({ tf })} options={RANK_TIMEFRAMES.map((t) => ({ value: t, label: TIMEFRAME_LABEL[t] }))} />
          {!tfOn && <p id="rank-tf-note" className="mt-1.5 text-sm text-on-chrome-muted">{search.rank === 'salt' ? 'Salt is rated over all time.' : 'Set and tag lists cover all time.'}</p>}
        </fieldset>
        <Segmented<RankOwn> label="Ownership" showLabel value={search.own} onChange={(own) => set({ own })} options={RANK_OWN.map((o) => ({ value: o, label: OWN_LABEL[o] }))} />
      </SideSection>
      <SideSection title="Arrange">
        <Segmented label="View type" showLabel value={search.rview} onChange={(rview) => set({ rview })} options={[{ value: 'grid', label: 'Grid' }, { value: 'list', label: 'List' }]} />
      </SideSection>
    </>
  );

  const shown = ranking.data?.rows.length ?? 0;
  const footer = r && r.total > shown ? (
    <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 px-5 pt-2 pb-8">
      <p className="text-sm tabular text-ink-muted">Showing {fmtInt(shown)} of {fmtInt(r.total)}</p>
      <Button tone="paper" disabled={ranking.isFetching} onClick={() => setMore({ key: pageKey, limit: limit + nextPage(shown, r.total) })}>
        {ranking.isFetching ? 'Loading…' : `Load ${fmtInt(nextPage(shown, r.total))} more`}
      </Button>
    </div>
  ) : null;

  let body: ReactNode;
  if (ranking.isPending) {
    body = <GridSkeleton label="Reading the ranking…" />;
  } else if (ranking.isError) {
    body = <ErrorNote error={ranking.error} onRetry={() => ranking.refetch()} />;
  } else if (data && !data.cached) {
    body = live?.status === 'failed' ? (
      <ErrorNote error={new Error(`Couldn’t read this ranking. ${failureText(live.error)}`)} onRetry={() => fetchRanking(false)} />
    ) : (
      <div className="mx-5 flex flex-col gap-3 pt-2">
        <ProgressRule label="Reading the ranking" verb="Reading" done={live?.done ?? 0} total={live?.total ?? null} message={live?.log.at(-1)?.msg ?? 'EDHREC'} />
        <p className="text-sm text-ink-muted">First time for this list — fetching it from EDHREC. Next time it opens instantly.</p>
      </div>
    );
  } else if (r && r.pool === 0) {
    body = (
      <EmptyNote title="Nothing ranked">
        {r.local_filters.length ? 'No commander in this list matches all your filters. Set one of them to Any.' : emptyRankingNote(search, famName)}
      </EmptyNote>
    );
  } else if (r && r.total === 0) {
    body = (
      <EmptyNote title="Nothing matches">
        {search.own !== 'all' ? `You own none of these${search.own === 'unused' ? ' with an unused copy' : ''}. Show all to see the whole ranking.` : 'Clear the card name filter.'}
      </EmptyNote>
    );
  } else if (r && search.rview === 'grid') {
    body = <VirtualGuide sections={[{ key: 'ranking', label: r.title, items: cards, level: 2, noun: 'ranking', meta: fmtInt(r.total) }]} density="grid" selected={selected} onToggle={toggle} label={r.title} footer={footer} />;
  } else if (r) {
    body = <RankingList r={r} rows={r.rows} cards={cards} selected={selected} onToggle={toggle} onInspect={setInspecting} footer={footer} />;
  }

  const ago = fetchedAgo(r?.fetched_at);
  return (
    <ViewLayout label="Explore controls" summary={r ? `Rankings · ${r.title}` : 'Rankings'} sidebar={sidebar} subnav={subnav}>
      <GuideSheet
        title={r?.title ?? SCOPE_LABEL[search.rank]}
        summary={r ? `${rankingSummary(r)}${ago ? ` · read ${ago}` : ''}` : undefined}
        actionsLabel="Ranking actions"
        marked={{ count: marked.length, getText: () => exportLines(marked, 'plain'), onClear: clear }}
        actions={
          r && (
            <>
              <IconAction label={running ? 'Refreshing…' : 'Refresh'} Icon={RereadMark} disabled={running} disabledReason="Refreshing…" onClick={() => fetchRanking(true)} />
              <IconTooltip label="Open results in EDHREC">
                <a href={edhrecUrl(r)} target="_blank" rel="noreferrer" aria-label="Open results in EDHREC (opens in a new tab)" className={iconActionClass('paper')}>
                  <EdhrecMark className="size-4" />
                </a>
              </IconTooltip>
            </>
          )
        }
      >
        <div className={`flex h-full min-h-0 flex-col transition-opacity duration-150 ease-guide ${dim ? 'opacity-60' : ''}`}>
          <EdhrecHealth keys={RANKING_HEALTH} />
          {r && running && (
            <div className="mx-5 mb-2">
              <ProgressRule label="Refreshing the ranking" verb="Reading" done={live?.done ?? 0} total={live?.total ?? null} message={live?.log.at(-1)?.msg} />
            </div>
          )}
          {r && live?.status === 'failed' && (
            <p role="alert" className="mx-5 mb-2 text-sm text-danger">Couldn’t refresh: {failureText(live.error)} Showing the copy from {ago}.</p>
          )}
          <div className="min-h-0 flex-1">{body}</div>
        </div>
      </GuideSheet>
      <CardInspector card={inspecting} onClose={() => setInspecting(null)} />
    </ViewLayout>
  );
}

/** Tag / creature type: typed freely, committed on Enter or leaving the field. */
function TagField({ value, suggestions, onCommit }: { value: string; suggestions: string[]; onCommit: (v: string) => void }) {
  const id = useId();
  const [draft, setDraft] = useState(value);
  const commit = () => draft.trim() !== value && onCommit(draft.trim());
  return (
    <label className="flex flex-col gap-1.5 text-sm voice-semi text-on-chrome-muted">
      Tag or creature type
      <input
        name="tag"
        type="search"
        list={`${id}-tags`}
        autoComplete="off"
        spellCheck={false}
        value={draft}
        placeholder="Any — goblins, treasure…"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === 'Enter' && commit()}
        className="min-h-9 rounded-sm border border-chrome-line bg-chrome-raised px-2.5 text-md text-on-chrome placeholder:text-on-chrome-muted focus-visible:border-accent"
      />
      <datalist id={`${id}-tags`}>
        {suggestions.map((t) => <option key={t} value={t} />)}
      </datalist>
    </label>
  );
}

/** The ranking as a ruled list: # · art · name · card type · creature type ·
 *  color identity · mana cost · decks or salt · from $ · you own. Lower-priority
 *  columns give way as the sheet narrows (container queries). */
function RankingList({ r, rows, cards, selected, onToggle, onInspect, footer }: { r: RankingOut; rows: RankedOut[]; cards: GuideCard[]; selected: ReadonlySet<string>; onToggle: (k: string) => void; onInspect: (c: GuideCard) => void; footer?: ReactNode }) {
  const scope = r.scope as RankScope;
  const role = roleFor(scope);
  return (
    <div className="@container h-full overflow-y-auto px-3 pb-6 sm:px-5" role="region" aria-label={r.title} tabIndex={0}>
      <table className="w-full table-fixed border-collapse text-sm tabular">
        <caption className="sr-only">{r.title}: rank, card, card type, creature type, color identity, mana cost, {metricLabel(scope).toLowerCase()}, cheapest price, copies you own</caption>
        <thead className="sticky top-0 z-10 bg-paper">
          <tr className="border-b-2 border-rule-strong text-left text-xs voice-semi text-ink-muted">
            <th scope="col" className="w-8"><span className="sr-only">Mark</span></th>
            <th scope="col" className="w-8 py-1.5 pr-2 text-right font-medium @[30rem]:w-10">#</th>
            <th scope="col" className="hidden w-[calc(var(--size-thumb)+0.5rem)] @[22rem]:table-cell"><span className="sr-only">Art</span></th>
            <th scope="col" className="py-1.5 pl-1 font-medium">{scope === 'commanders' ? 'Commander' : 'Card'}</th>
            <th scope="col" className="hidden w-32 py-1.5 pl-3 font-medium @[46rem]:table-cell">Type</th>
            <th scope="col" className="hidden w-36 py-1.5 pl-3 font-medium @[64rem]:table-cell">{scope === 'commanders' ? 'Creature type' : 'Subtype'}</th>
            <th scope="col" className="hidden w-[5.5rem] py-1.5 pl-3 font-medium @[36rem]:table-cell">Colors</th>
            <th scope="col" className="hidden w-28 py-1.5 pl-3 font-medium @[54rem]:table-cell">Cost</th>
            <th scope="col" className="w-14 py-1.5 pl-3 text-right font-medium @[30rem]:w-20">
              {scope === 'salt' ? (
                <span className="inline-flex items-center gap-1">Salt<InfoTip label="What is salt?" tone="paper">EDHREC players’ average rating (0–4) of how unfun a card is to play against.</InfoTip></span>
              ) : 'Decks'}
            </th>
            <th scope="col" className="hidden w-20 py-1.5 pl-3 text-right font-medium @[30rem]:table-cell">From</th>
            <th scope="col" className="w-14 py-1.5 pl-3 text-right font-medium @[30rem]:w-28">You own</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((x, i) => {
            const c = cards[i];
            const on = selected.has(c.key);
            const types = rankedTypes(scope, x);
            const partner = x.facts.partner;
            return (
              <tr key={x.slug} className={`border-b border-rule/60 [contain-intrinsic-size:auto_2.75rem] [content-visibility:auto] ${on ? 'highlighter' : ''}`}>
                <td className="py-0.5"><MarkToggle name={x.name} marked={on} onToggle={() => onToggle(c.key)} size="sm" /></td>
                <td className="pr-2 text-right text-ink-muted">{x.rank ?? '—'}</td>
                <td className="hidden py-1 @[22rem]:table-cell">
                  <button type="button" onClick={() => onInspect(c)} aria-label={`Inspect ${x.name}`} className="block size-[var(--size-thumb)] cursor-pointer overflow-hidden rounded-xs">
                    <CardArt card={c} crop />
                  </button>
                </td>
                <th scope="row" className="py-1 pl-1 text-left font-normal">
                  <CardHover card={c}>
                    <Link
                      to="/explore"
                      search={((s: CompareSearch) => ({ ...s, mode: 'card', a: x.name.split(' // ')[0], b: undefined, role })) as never}
                      className="line-clamp-2 w-fit max-w-full break-words voice-semi leading-snug text-ink no-underline hover:underline @[30rem]:line-clamp-1"
                      title={`Explore ${x.name} ${role === 'commander' ? 'as a commander' : 'as a card'}`}
                    >
                      {x.name}
                    </Link>
                  </CardHover>
                </th>
                <td className="hidden truncate pl-3 text-ink-muted @[46rem]:table-cell" title={types.card ?? undefined}>{types.card ?? '—'}</td>
                <td className="hidden truncate pl-3 text-ink-muted @[64rem]:table-cell" title={types.sub ?? undefined}>{types.sub ?? '—'}</td>
                <td className="hidden pl-3 @[36rem]:table-cell">{x.facts.oracle_id || partner ? <ColorIdentity colors={x.facts.color_identity ?? []} /> : <span className="text-ink-muted" aria-label="Color identity unknown">—</span>}</td>
                <td className="hidden pl-3 @[54rem]:table-cell">
                  <span className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
                    <ManaCost cost={x.facts.mana_cost} />
                    {partner && <><span aria-hidden="true" className="text-ink-muted">+</span><ManaCost cost={partner.mana_cost} /></>}
                  </span>
                </td>
                <td className="pl-3 text-right text-ink">{fmtMetric(scope, x)}</td>
                <td className="hidden pl-3 text-right voice-semi font-medium text-ink @[30rem]:table-cell">{fmtUsd(x.facts.lowest_usd)}</td>
                <td className="whitespace-nowrap pl-3 text-right">
                  {x.facts.owned ? (
                    <>
                      <span className="text-ink">{x.facts.owned}</span>
                      <span className={`hidden @[30rem]:inline ${x.facts.free ? 'text-accent-ink' : 'text-ink-muted'}`}> · {x.facts.free} unused</span>
                    </>
                  ) : (
                    <span className="text-ink-muted">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {footer}
    </div>
  );
}

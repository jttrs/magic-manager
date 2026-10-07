import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { HoverCard } from 'radix-ui';
import { useCallback, useEffect, useId, useMemo, useState, type ReactNode } from 'react';
import { familiesQuery, rankingOptionsQuery, rankingQuery } from '../../app/queries';
import { useJob } from '../../app/useJob';
import { useSelection } from '../../app/selection';
import { ViewLayout } from '../../components/AppShell';
import { CardArt } from '../../components/CardFace';
import { CardInspector } from '../../components/CardInspector';
import { CardPreview } from '../../components/CardMeta';
import { CopyButton } from '../../components/CopyButton';
import { IconAction } from '../../components/IconAction';
import { InfoTip } from '../../components/InfoTip';
import { MarkToggle } from '../../components/MarkToggle';
import { ProgressRule } from '../../components/ProgressRule';
import { SearchSelect } from '../../components/SearchSelect';
import { Segmented, SelectField, SideSection, TextField } from '../../components/Sidebar';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../../components/States';
import { EdhrecMark, RereadMark } from '../../components/StoreMarks';
import { VirtualGuide } from '../../components/VirtualGuide';
import type { RankedOut, RankingOut } from '../../core/api';
import { fmtUsd } from '../../core/format';
import { exportLines, type GuideCard } from '../../core/guideCard';
import {
  BY_LABEL, edhrecUrl, fetchedAgo, fmtMetric, metricLabel, narrowBy, OWN_LABEL, rankedCard, rankingRequest, rankingSummary,
  roleFor, SCOPE_LABEL, shownRows, TIMEFRAME_LABEL, timeframeApplies,
} from '../../core/rankings';
import { RANK_BYS, RANK_OWN, RANK_SCOPES, RANK_TIMEFRAMES, type CompareSearch, type RankBy, type RankOwn, type RankScope, type RankTimeframe } from '../../core/search';

type Props = { search: CompareSearch; set: (p: Partial<CompareSearch>) => void; modeSwitch: ReactNode };

/** Explore → Rankings: EDHREC's top commanders (narrowed by one of colour, tag or
 *  set), top cards and saltiest cards, each joined to what you own. Cached lists
 *  read instantly; a list never read is fetched as a job with progress. */
export function RankingsExplore({ search, set, modeSwitch }: Props) {
  const qc = useQueryClient();
  const req = useMemo(() => rankingRequest(search), [search]);
  const reqKey = JSON.stringify(req);
  const ranking = useQuery(rankingQuery(req));
  const opts = useQuery(rankingOptionsQuery());
  const by = narrowBy(search);
  const fams = useQuery({ ...familiesQuery(), enabled: by === 'set' });
  const { selected, toggle, clear } = useSelection('explore');
  const [inspecting, setInspecting] = useState<GuideCard | null>(null);

  // A ranking never read is fetched once per visit; Refresh re-reads it.
  const { live: jobLive, start, reset } = useJob();
  const [startedKey, setStartedKey] = useState<string | null>(null);
  const fetchRanking = useCallback((refresh: boolean) => {
    if (!req) return;
    setStartedKey(reqKey);
    reset();
    void start('edhrec.rankings', { ...req, refresh });
  }, [req, reqKey, reset, start]);
  const data = ranking.isPlaceholderData ? undefined : ranking.data;
  useEffect(() => {
    if (data && !data.cached && startedKey !== reqKey) fetchRanking(false);
  }, [data, startedKey, reqKey, fetchRanking]);
  const live = startedKey === reqKey ? jobLive : null;
  const running = Boolean(live && live.status !== 'succeeded' && live.status !== 'failed');
  useEffect(() => {
    if (live?.status === 'succeeded') {
      void qc.invalidateQueries({ queryKey: ['explore', 'ranking'] });
      void qc.invalidateQueries({ queryKey: ['explore', 'ranking-options'] });
    }
  }, [live?.status, qc]);

  const shown = useMemo(() => (ranking.data ? shownRows(ranking.data.rows, search.own, search.rq) : []), [ranking.data, search.own, search.rq]);
  const scope = (ranking.data?.scope ?? search.rank) as RankScope;
  const cards = useMemo(() => shown.map((r) => rankedCard(scope, r)), [shown, scope]);
  const allCards = useMemo(() => (ranking.data?.rows ?? []).map((r) => rankedCard(scope, r)), [ranking.data, scope]);
  const marked = allCards.filter((c) => selected.has(c.key));

  const sidebar = (
    <>
      {modeSwitch}
      <SideSection title="Ranking">
        <SelectField<RankScope> label="List" value={search.rank} onChange={(rank) => set({ rank })} options={RANK_SCOPES.map((s) => ({ value: s, label: SCOPE_LABEL[s] }))} />
        {search.rank === 'commanders' && (
          <>
            <SelectField<RankBy> label="Narrow by" value={search.by} onChange={(b) => set({ by: b })} options={RANK_BYS.map((b) => ({ value: b, label: BY_LABEL[b] }))} />
            {by === 'color' && (
              <SearchSelect
                label="Colour identity"
                noun="colour identity"
                value={search.color}
                onChange={(color) => set({ color })}
                options={(opts.data?.colors ?? []).map((c) => ({ value: c.slug, label: c.label, hint: c.colors || 'C' }))}
              />
            )}
            {by === 'tag' && <TagField key={search.tag ?? ''} value={search.tag ?? ''} suggestions={opts.data?.tags ?? []} onCommit={(tag) => set({ tag: tag || undefined })} />}
            {by === 'set' && (
              <SearchSelect
                label="Set family"
                noun="family"
                value={search.fam}
                onChange={(fam) => set({ fam })}
                options={(fams.data ?? []).map((f) => ({ value: f.code, label: f.name, hint: f.code.toUpperCase() }))}
              />
            )}
          </>
        )}
        {timeframeApplies(search) && (
          <Segmented<RankTimeframe> label="Timeframe" showLabel value={search.tf} onChange={(tf) => set({ tf })} options={RANK_TIMEFRAMES.map((t) => ({ value: t, label: TIMEFRAME_LABEL[t] }))} />
        )}
      </SideSection>
      <SideSection title="Show">
        <Segmented<RankOwn> label="Show" value={search.own} onChange={(own) => set({ own })} options={RANK_OWN.map((o) => ({ value: o, label: OWN_LABEL[o] }))} />
        <TextField name="rq" label="Card name" value={search.rq} placeholder="e.g. Krenko…" onChange={(rq) => set({ rq })} />
        <Segmented label="View type" showLabel value={search.rview} onChange={(rview) => set({ rview })} options={[{ value: 'list', label: 'Ledger' }, { value: 'grid', label: 'Grid' }]} />
      </SideSection>
      <SideSection title={`Marked · ${marked.length}`}>
        <CopyButton label="Copy marked as list" emphasis="primary" getText={() => exportLines(marked, 'plain')} />
        {selected.size > 0 && (
          <button type="button" onClick={clear} className="self-start cursor-pointer text-sm text-on-chrome-muted underline hover:text-on-chrome">Clear marks</button>
        )}
      </SideSection>
    </>
  );

  let body: ReactNode;
  if (!req) {
    body = (
      <EmptyNote title={`Pick a ${by === 'color' ? 'colour identity' : by === 'tag' ? 'tag' : 'set family'}`}>
        {by === 'tag'
          ? 'Type a creature type or theme in the sidebar — goblins, treasure, spellslinger — and press Enter.'
          : `Choose one in the sidebar to see its top commanders. Filters don’t combine: one of colour, tag or set at a time.`}
      </EmptyNote>
    );
  } else if (ranking.isPending) {
    body = <GridSkeleton label="Reading the ranking…" />;
  } else if (ranking.isError) {
    body = <ErrorNote error={ranking.error} onRetry={() => ranking.refetch()} />;
  } else if (data && !data.cached) {
    body = live?.status === 'failed' ? (
      <ErrorNote error={new Error(`Couldn’t read this ranking from EDHREC: ${live.error ?? 'the job failed'}`)} onRetry={() => fetchRanking(false)} />
    ) : (
      <div className="mx-5 flex flex-col gap-3 pt-2">
        <ProgressRule label="Reading the ranking" verb="Reading" done={live?.done ?? 0} total={live?.total ?? null} message={live?.log.at(-1)?.msg ?? 'EDHREC'} />
        <p className="text-sm text-ink-muted">First time for this list — fetching it from EDHREC. Next time it opens instantly.</p>
      </div>
    );
  } else if (!shown.length) {
    body = (
      <EmptyNote title="Nothing matches">
        {search.own !== 'all' ? `You own none of these${search.own === 'free' ? ' with a free copy' : ''}. Show all to see the whole ranking.` : 'Clear the card name filter.'}
      </EmptyNote>
    );
  } else if (search.rview === 'grid') {
    body = <VirtualGuide sections={[{ key: 'ranking', label: ranking.data.title, items: cards, level: 2, noun: 'ranking' }]} density="grid" selected={selected} onToggle={toggle} label={ranking.data.title} />;
  } else {
    body = <Ledger r={ranking.data} rows={shown} cards={cards} selected={selected} onToggle={toggle} onInspect={setInspecting} />;
  }

  const r = ranking.data?.cached ? ranking.data : undefined;
  const ago = fetchedAgo(r?.fetched_at);
  return (
    <ViewLayout label="Explore controls" summary={r ? `Rankings · ${r.title}` : 'Rankings'} sidebar={sidebar}>
      <GuideSheet
        title={r?.title ?? (req ? SCOPE_LABEL[search.rank] : 'Rankings')}
        summary={r ? `${rankingSummary(r, shown)}${ago ? ` · read from EDHREC ${ago}` : ''}` : undefined}
        actions={
          r && (
            <div role="toolbar" aria-label="Ranking actions" className="flex items-center gap-1">
              <IconAction label={running ? 'Reading from EDHREC…' : 'Read again from EDHREC'} Icon={RereadMark} disabled={running} disabledReason="Reading from EDHREC…" onClick={() => fetchRanking(true)} />
              <a href={edhrecUrl(r)} target="_blank" rel="noreferrer" title="Open on EDHREC" className="inline-flex min-h-9 items-center gap-1.5 rounded-sm px-2 text-sm voice-semi font-medium text-accent-ink no-underline transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk">
                <EdhrecMark className="size-4" />
                <span className="hidden sm:inline">EDHREC</span>
                <span className="sr-only">Open on EDHREC (opens in a new tab)</span>
              </a>
            </div>
          )
        }
      >
        <div className={`flex h-full min-h-0 flex-col transition-opacity duration-150 ease-guide ${ranking.isPlaceholderData ? 'opacity-60' : ''}`}>
          {r && running && (
            <div className="mx-5 mb-2">
              <ProgressRule label="Reading the ranking again" verb="Reading" done={live?.done ?? 0} total={live?.total ?? null} message={live?.log.at(-1)?.msg} />
            </div>
          )}
          {r && live?.status === 'failed' && (
            <p role="alert" className="mx-5 mb-2 text-sm text-danger">Couldn’t read it again: {live.error ?? 'the job failed'}. Showing the copy from {ago}.</p>
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
        placeholder="goblins, treasure…"
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

/** The ranking as a ruled ledger: # · art · name (type) · decks or salt · from $ · you own. */
function Ledger({ r, rows, cards, selected, onToggle, onInspect }: { r: RankingOut; rows: RankedOut[]; cards: GuideCard[]; selected: ReadonlySet<string>; onToggle: (k: string) => void; onInspect: (c: GuideCard) => void }) {
  const scope = r.scope as RankScope;
  const role = roleFor(scope);
  return (
    <div className="@container h-full overflow-y-auto px-3 pb-6 sm:px-5" role="region" aria-label={r.title} tabIndex={0}>
      <table className="w-full table-fixed border-collapse text-sm tabular">
        <caption className="sr-only">{r.title}: rank, card, {metricLabel(scope).toLowerCase()}, cheapest price, copies you own</caption>
        <thead className="sticky top-0 z-10 bg-paper">
          <tr className="border-b-2 border-rule-strong text-left text-xs voice-semi text-ink-muted">
            <th scope="col" className="w-9"><span className="sr-only">Mark</span></th>
            <th scope="col" className="w-10 py-1.5 pr-2 text-right font-medium">#</th>
            <th scope="col" className="hidden w-[calc(var(--size-thumb)+0.5rem)] @[22rem]:table-cell"><span className="sr-only">Art</span></th>
            <th scope="col" className="py-1.5 pl-1 font-medium">{scope === 'commanders' ? 'Commander' : 'Card'}</th>
            <th scope="col" className="w-16 py-1.5 pl-3 text-right font-medium @[30rem]:w-20">
              {scope === 'salt' ? (
                <span className="inline-flex items-center gap-1">Salt<InfoTip label="What is salt?" tone="paper">EDHREC players’ average rating (0–4) of how unfun a card is to play against.</InfoTip></span>
              ) : 'Decks'}
            </th>
            <th scope="col" className="hidden w-20 py-1.5 pl-3 text-right font-medium @[30rem]:table-cell">From</th>
            <th scope="col" className="w-24 py-1.5 pl-3 text-right font-medium @[30rem]:w-28">You own</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((x, i) => {
            const c = cards[i];
            const on = selected.has(c.key);
            return (
              <tr key={x.slug} className={`border-b border-rule/60 [content-visibility:auto] ${on ? 'highlighter' : ''}`}>
                <td className="py-0.5"><MarkToggle name={x.name} marked={on} onToggle={() => onToggle(c.key)} size="sm" /></td>
                <td className="pr-2 text-right text-ink-muted">{x.rank ?? '—'}</td>
                <td className="hidden py-1 @[22rem]:table-cell">
                  <button type="button" onClick={() => onInspect(c)} aria-label={`Inspect ${x.name}`} className="block size-[var(--size-thumb)] cursor-pointer overflow-hidden rounded-xs">
                    <CardArt card={c} crop />
                  </button>
                </td>
                <th scope="row" className="py-1 pl-1 text-left font-normal">
                  <HoverCard.Root openDelay={250} closeDelay={80}>
                    <HoverCard.Trigger asChild>
                      <Link
                        to="/explore"
                        search={((s: CompareSearch) => ({ ...s, mode: 'card', a: x.name.split(' // ')[0], b: undefined, role })) as never}
                        className="flex min-w-0 items-baseline gap-2 text-ink no-underline hover:underline"
                        title={`Explore ${x.name} ${role === 'commander' ? 'as a commander' : 'as a card'}`}
                      >
                        <span className="max-w-full shrink-0 truncate voice-semi">{x.name}</span>
                        {x.facts.type_line && <span className="hidden min-w-0 truncate text-2xs text-ink-muted @[34rem]:inline">{x.facts.type_line}</span>}
                      </Link>
                    </HoverCard.Trigger>
                    <HoverCard.Portal>
                      <HoverCard.Content side="right" align="center" sideOffset={12} collisionPadding={16} className="z-40 w-56 drop-shadow-[0_10px_24px_var(--theme-scrim)]">
                        <CardPreview card={c} />
                      </HoverCard.Content>
                    </HoverCard.Portal>
                  </HoverCard.Root>
                </th>
                <td className="pl-3 text-right text-ink">{fmtMetric(scope, x)}</td>
                <td className="hidden pl-3 text-right voice-semi font-medium text-ink @[30rem]:table-cell">{fmtUsd(x.facts.lowest_usd)}</td>
                <td className="whitespace-nowrap pl-3 text-right">
                  {x.facts.owned ? (
                    <>
                      <span className="text-ink">{x.facts.owned}</span>
                      <span className={x.facts.free ? 'text-accent-ink' : 'text-ink-muted'}> · {x.facts.free} free</span>
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
    </div>
  );
}

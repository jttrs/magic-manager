import { useQuery } from '@tanstack/react-query';
import { getRouteApi, Link, useNavigate } from '@tanstack/react-router';
import { useMemo, useState, type ComponentType, type ReactNode, type SVGProps } from 'react';
import { compareQuery, exploreCardQuery } from '../app/queries';
import { useSelection } from '../app/selection';
import { ViewLayout } from '../components/AppShell';
import { CardInspector } from '../components/CardInspector';
import { CommanderPicker } from '../components/CommanderPicker';
import { CopyButton } from '../components/CopyButton';
import { GuideColumns, type Column } from '../components/GuideColumns';
import { InfoTip } from '../components/InfoTip';
import { MultiSelect } from '../components/MultiSelect';
import { ChipToggles, Segmented, SideSection, TextField } from '../components/Sidebar';
import { SortBuilder } from '../components/SortBuilder';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { EdhrecMark, ScryfallMark } from '../components/StoreMarks';
import { VirtualGuide, type GuideSection } from '../components/VirtualGuide';
import type { CardExploreOut, CardProfileOut, CompareOut, OracleTagOut } from '../core/api';
import { bucketCards, COMPARE_SORT, COMPARE_SORT_PRESETS, matches, tagCounts, tagLabel } from '../core/compare';
import { coplayGroups, deckShare, defaultRole, pairedSections, profileCard, profileSections } from '../core/explore';
import { fmtInt, fmtUsd } from '../core/format';
import { exportLines, fromCompare, type GuideCard } from '../core/guideCard';
import { compareSections, hasFunctionData } from '../core/groupBy';
import { BUCKETS, type Bucket, type CompareSearch, type GroupBy, type Role } from '../core/search';
import { decodeSort, encodeSort, sortBy } from '../core/sort';

const route = getRouteApi('/explore');
const cleanName = (n: string) => n.replace(/\s*\((?:Commander|Partner|Card)\)\s*$/i, '');
const shortName = (n: string) => cleanName(n).split(',')[0].split(' // ')[0];

/** Explore: a card in the role you choose — leading a deck (commander) or one of
 *  the 99 (card) — from EDHREC's community data joined to what you own; add a
 *  second card to compare, in the same role. */
export function ExploreView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/explore' });
  const set = (patch: Partial<CompareSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const { selected, toggle, clear } = useSelection('explore');
  const [inspecting, setInspecting] = useState<GuideCard | null>(null);

  const cards = useQuery(exploreCardQuery(search.a, search.b));
  const prof = cards.data;
  const canLead = prof ? prof.a.commander_eligible && (!prof.b || prof.b.commander_eligible) : undefined;
  const role: Role = search.role === 'commander' && canLead === false ? 'card' : search.role ?? defaultRole(canLead);
  const cmd = useQuery({ ...compareQuery(search.a, search.b), enabled: Boolean(search.a) && role === 'commander' && canLead !== false });

  const names = {
    a: prof ? shortName(prof.a.name) : search.a ? shortName(search.a) : 'A',
    b: prof?.b ? shortName(prof.b.name) : search.b ? shortName(search.b) : 'B',
  };
  const comparing = Boolean(search.b);

  // ---- commander role: recommended cards (today's compare, or one commander) ----
  const rules = useMemo(() => decodeSort(search.sort, COMPARE_SORT), [search.sort]);
  const cmdView = useMemo(() => (cmd.data && role === 'commander' ? buildCommander(cmd.data, search, rules) : null), [cmd.data, role, search, rules]);

  // ---- card role: commanders that run it, played alongside, similar ----
  const cardView = useMemo(() => {
    if (!prof || role !== 'card') return null;
    if (!prof.b) return { single: withTotals(profileSections(prof.a, search.q, search.tags)) };
    return {
      cols: {
        a_only: pairedSections(prof, 'a_only', search.q, search.tags) as GuideSection[],
        both: pairedSections(prof, 'both', search.q, search.tags) as GuideSection[],
        b_only: pairedSections(prof, 'b_only', search.q, search.tags) as GuideSection[],
      },
    };
  }, [prof, role, search.q, search.tags]);

  const byKey = useMemo(() => {
    const m = new Map<string, GuideCard>();
    const all = [...(cmdView?.all ?? []), ...(cardView?.single ?? []).flatMap((s) => s.items), ...Object.values(cardView?.cols ?? {}).flat().flatMap((s) => s.items)];
    for (const c of all) m.set(c.key, c);
    return m;
  }, [cmdView, cardView]);
  const marked = [...selected].map((k) => byKey.get(k)).filter((c) => c != null);

  const titles: Record<Bucket, string> = { a_only: `${names.a} only`, both: 'Both', b_only: `${names.b} only` };
  const columns = (sectionsOf: (b: Bucket) => GuideSection[], count: (b: Bucket) => number, metric: string): Column[] =>
    BUCKETS.map((b) => ({
      id: b,
      title: titles[b],
      count: count(b),
      legend: b === 'both' ? <BarLegend a={names.a} b={names.b} metric={metric} /> : undefined,
      body: <VirtualGuide sections={sectionsOf(b)} density={search.view} selected={selected} onToggle={toggle} barLabels={[names.a, names.b]} label={`${titles[b]} cards`} />,
    }));

  const sidebar = (
    <>
      <SideSection title="Cards">
        <div className="flex flex-col gap-3">
          <CommanderPicker scope="any" name="card-a" label="Card" value={search.a} onCommit={(a) => set({ a })} />
          <CommanderPicker scope="any" name="card-b" label="Compare with" placeholder="Add a second card…" value={search.b} onCommit={(b) => set({ b })} />
          {search.b && (
            <button type="button" onClick={() => set({ b: undefined })} className="self-start cursor-pointer text-sm text-on-chrome-muted underline hover:text-on-chrome">
              Stop comparing
            </button>
          )}
        </div>
      </SideSection>
      <SideSection title="Role">
        <Segmented<Role>
          label="Explore as"
          showLabel
          labelExtra={
            <InfoTip label="What do the roles mean?">
              <b>As commander</b>: the cards EDHREC decks led by it run. <b>As a card</b>: the commanders that run it, what it’s played alongside, and similar cards. Comparisons use one role for both cards.
            </InfoTip>
          }
          value={role}
          onChange={(r) => set({ role: r })}
          options={[
            { value: 'commander', label: 'As commander', disabled: canLead === false, title: canLead === false ? (comparing ? 'One of these cards can’t be a commander' : 'This card can’t be a commander') : undefined },
            { value: 'card', label: 'As a card' },
          ]}
        />
      </SideSection>
      {comparing && (
        <SideSection title="Columns">
          <ChipToggles
            label="Visible columns"
            value={search.show}
            onChange={(show) => set({ show: BUCKETS.filter((b) => show.includes(b)) })}
            options={BUCKETS.map((b) => ({ value: b, label: titles[b] }))}
          />
        </SideSection>
      )}
      <SideSection title="Display">
        {role === 'commander' && (
          <>
            <Segmented<GroupBy>
              label="Group by"
              value={search.groupBy}
              onChange={(groupBy) => set({ groupBy })}
              options={[{ value: 'lists', label: 'Card type' }, { value: 'function', label: 'Function' }]}
            />
            {search.groupBy === 'function' && cmdView && (
              cmdView.tagged ? (
                <p className="text-xs leading-relaxed text-on-chrome-muted">
                  Deck roles from Scryfall Tagger. A card with several roles is listed under each; column totals count it once.
                </p>
              ) : (
                <p role="note" className="text-sm leading-relaxed text-on-chrome-muted">
                  No Scryfall function tags yet — run <Link to="/jobs" className="text-on-chrome underline">Sync Scryfall tags</Link>, then reload.
                </p>
              )
            )}
          </>
        )}
        <Segmented label="View type" showLabel value={search.view} onChange={(view) => set({ view })} options={[{ value: 'grid', label: 'Grid' }, { value: 'list', label: 'List' }]} />
        {role === 'commander' && <SortBuilder keys={COMPARE_SORT} rules={rules} presets={COMPARE_SORT_PRESETS} onChange={(r) => set({ sort: encodeSort(r, COMPARE_SORT) })} />}
      </SideSection>
      <SideSection title="Filter">
        <TextField name="q" label="Card name" value={search.q} placeholder="e.g. Sol Ring…" onChange={(q) => set({ q })} />
        {role === 'commander' && cmdView && cmdView.tags.length > 0 && (
          <MultiSelect label="EDHREC lists" noun="lists" value={search.tags} onChange={(tags) => set({ tags })} options={cmdView.tags.map(([t, n]) => ({ value: t, label: tagLabel(t), count: n }))} />
        )}
        {role === 'card' && prof && (
          <MultiSelect label="Played alongside · card types" noun="types" searchable={false} keepOrder summary={search.tags.length ? undefined : 'All card types'} value={search.tags} onChange={(tags) => set({ tags })} options={coplayGroups(prof).map(([g, n]) => ({ value: g, label: g, count: n }))} />
        )}
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
  if (!search.a) {
    body = (
      <EmptyNote title="Explore a card">
        Type a card in the sidebar — any card. Explore it as a commander (what its decks run) or as a card (which commanders run it and what it’s played with), then add a second card to compare.
      </EmptyNote>
    );
  } else if (cards.isPending) {
    body = <GridSkeleton label={`Reading EDHREC for ${search.a}${search.b ? ` and ${search.b}` : ''}… cards not cached yet are fetched first.`} />;
  } else if (cards.isError) {
    body = <ErrorNote error={cards.error} onRetry={() => cards.refetch()} />;
  } else if (role === 'commander') {
    if (cmd.isPending) body = <GridSkeleton label="Loading the cards its decks run…" />;
    else if (cmd.isError) body = <ErrorNote error={cmd.error} onRetry={() => cmd.refetch()} />;
    else if (cmdView && !comparing) body = <VirtualGuide sections={cmdView.sections.a_only} density={search.view} selected={selected} onToggle={toggle} label={`${names.a} recommended cards`} />;
    else if (cmdView) body = <GuideColumns columns={columns((b) => cmdView.sections[b], (b) => cmdView.buckets[b].length, 'inclusion')} visible={search.show} onHide={(id) => set({ show: search.show.filter((s) => s !== id) })} storageKey="explore-commander" />;
  } else if (cardView?.single) {
    body = cardView.single.length ? <VirtualGuide sections={cardView.single} density={search.view} selected={selected} onToggle={toggle} label={`${names.a} on EDHREC`} /> : <EmptyNote title="Nothing matches">Clear the name filter or pick more card types.</EmptyNote>;
  } else if (cardView?.cols) {
    const cols = cardView.cols;
    body = <GuideColumns columns={columns((b) => cols[b], (b) => cols[b].reduce((n, s) => n + s.items.length, 0), 'share of decks')} visible={search.show} onHide={(id) => set({ show: search.show.filter((s) => s !== id) })} storageKey="explore-card" />;
  }

  return (
    <ViewLayout label="Explore controls" summary={search.a ? `${search.a}${search.b ? ` vs ${search.b}` : ''} · ${role === 'commander' ? 'as commander' : 'as a card'}` : undefined} sidebar={sidebar} startOpen={!search.a}>
      <GuideSheet title="Explore" summary={summaryLine(role, prof, cmd.data)}>
        <div className="flex h-full min-h-0 flex-col">
          {prof && <Plates r={prof} role={role} onInspect={(p) => setInspecting(profileCard(p))} />}
          <div className="min-h-0 flex-1">{body}</div>
        </div>
      </GuideSheet>
      <CardInspector card={inspecting} onClose={() => setInspecting(null)} />
    </ViewLayout>
  );
}

/** Level-1 heads count the cards in their level-2 groups (their own item list is empty). */
function withTotals(sections: GuideSection[]): GuideSection[] {
  return sections.map((s, i) => {
    if (s.level !== 1) return s;
    let n = 0;
    for (let j = i + 1; j < sections.length && sections[j].level !== 1; j++) n += sections[j].items.length;
    return { ...s, meta: fmtInt(n) };
  });
}

function summaryLine(role: Role, prof?: CardExploreOut, cmd?: CompareOut): string | undefined {
  if (!prof) return undefined;
  if (role === 'commander' && cmd) return `${fmtInt(cmd.cards.length)} recommended cards · EDHREC inclusion · cheapest price across printings`;
  if (role === 'card') return `EDHREC decks running ${prof.b ? 'each card' : 'it'} · lift = how much more often a card shares its decks than chance`;
  return undefined;
}

function buildCommander(data: CompareOut, search: CompareSearch, rules: ReturnType<typeof decodeSort>) {
  const shown = sortBy(data.cards.filter((c) => matches(c, search.q, search.tags)), rules, COMPARE_SORT);
  const buckets = bucketCards(shown);
  const roots = data.functions ?? [];
  const noun = search.groupBy === 'function' ? 'function' : 'card type';
  const sec = (b: Bucket) => compareSections(buckets[b], search.groupBy, roots).map((g) => ({ ...g, level: 2 as const, noun }));
  return {
    buckets,
    sections: { a_only: sec('a_only'), both: sec('both'), b_only: sec('b_only') },
    tags: tagCounts(data.cards),
    all: shown.map((c) => fromCompare(c)),
    tagged: hasFunctionData(data.cards),
  };
}

// ---------- the card plate(s) ----------

function Plates({ r, role, onInspect }: { r: CardExploreOut; role: Role; onInspect: (p: CardProfileOut) => void }) {
  return (
    <div className="mx-4 flex flex-col gap-3 border-b-2 border-rule-strong pb-3">
      <div className={`grid gap-4 ${r.b ? 'md:grid-cols-[1fr_auto_1fr]' : ''}`}>
        <Plate p={r.a} role={role} side={r.b ? 'A' : null} compact={Boolean(r.b)} onInspect={onInspect} />
        {r.b && <span aria-hidden="true" className="hidden self-center text-2xl voice-condensed font-bold text-ink-muted md:block">vs</span>}
        {r.b && <Plate p={r.b} role={role} side="B" compact onInspect={onInspect} />}
      </div>
      {r.b && role === 'card' && <TagSplit tags={r.tags ?? {}} a={shortName(r.a.name)} b={shortName(r.b.name)} />}
    </div>
  );
}

function Plate({ p, role, side, compact = false, onInspect }: { p: CardProfileOut; role: Role; side: 'A' | 'B' | null; compact?: boolean; onInspect: (p: CardProfileOut) => void }) {
  const f = p.facts;
  const share = deckShare(p);
  const mix = [...p.deck_mix].sort((x, y) => (y.value as number) - (x.value as number)).slice(0, 5);
  const edhrec = `https://edhrec.com/${role === 'commander' && p.commander_eligible ? 'commanders' : 'cards'}/${p.slug}`;
  return (
    <section aria-label={cleanName(p.name)} className="flex min-w-0 gap-4">
      <button type="button" onClick={() => onInspect(p)} aria-label={`Inspect ${cleanName(p.name)}`} className={`shrink-0 cursor-pointer self-start ${compact ? 'w-[4.5rem] sm:w-[5.5rem]' : 'w-[6.5rem] sm:w-[7.5rem]'}`}>
        {f.image_uri ? (
          <img src={f.image_uri} alt="" width={488} height={680} className="aspect-[488/680] h-auto w-full rounded-[4.5%/3.2%] bg-paper-sunk shadow-[0_8px_20px_-12px_var(--theme-scrim)]" />
        ) : (
          <span className="grid aspect-[488/680] w-full place-items-center rounded-sm border border-rule bg-paper-sunk p-2 text-center text-xs text-ink-muted">{p.name}</span>
        )}
      </button>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex items-baseline gap-2">
          {side && <span className="shrink-0 rounded-xs border border-rule-strong px-1 text-xs voice-condensed font-bold text-ink-muted">{side}</span>}
          <h2 className="min-w-0 truncate text-2xl voice-condensed font-bold leading-tight text-ink">{cleanName(p.name)}</h2>
        </div>
        <p className="text-sm text-ink-muted">{f.type_line ?? '—'}{p.commander_eligible ? ' · can lead a deck' : ''}</p>
        <dl className="flex flex-wrap gap-x-4 gap-y-0.5 text-sm tabular">
          {share && <Fact k="Played in">{share}</Fact>}
          {p.salt != null && (
            <Fact k="Salt" tip="EDHREC players’ average rating (0–4) of how unfun this card is to play against.">{p.salt.toFixed(2)}</Fact>
          )}
          <Fact k="From">{fmtUsd(f.lowest_usd)}</Fact>
          <Fact k="You own">{f.owned ? <>{fmtInt(f.owned)} <span className={f.free ? 'text-accent-ink' : 'text-ink-muted'}>· {fmtInt(f.free)} free</span></> : <span className="text-ink-muted">none</span>}</Fact>
        </dl>
        {!(compact && role === 'card') && (p.functions.length > 0 || p.tags.length > 0) && (
          <ul aria-label="Scryfall tags" className="flex flex-wrap gap-1">
            {p.tags.slice(0, 10).map((t) => <li key={t.id} className="rounded-xs border border-rule px-1.5 py-0.5 text-xs text-ink-muted">{t.label}</li>)}
          </ul>
        )}
        {!compact && mix.length > 0 && role === 'card' && (
          <p className="text-xs text-ink-muted">Typical deck it’s in: {mix.map((m) => `${m.value} ${String(m.label).toLowerCase()}`).join(' · ')}</p>
        )}
        <nav aria-label={`${cleanName(p.name)} elsewhere`} className="-ml-2 mt-auto flex flex-wrap gap-x-1">
          <OutLink href={edhrec} label="EDHREC" Mark={EdhrecMark} />
          {f.scryfall_url && <OutLink href={f.scryfall_url} label="Scryfall" Mark={ScryfallMark} />}
        </nav>
      </div>
    </section>
  );
}

function Fact({ k, tip, children }: { k: string; tip?: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="shrink-0 whitespace-nowrap text-ink-muted">{k}</dt>
      <dd className="text-ink">{children}</dd>
      {tip && <span className="self-center"><InfoTip label={`What is ${k.toLowerCase()}?`} tone="paper">{tip}</InfoTip></span>}
    </div>
  );
}

function OutLink({ href, label, Mark }: { href: string; label: string; Mark: ComponentType<SVGProps<SVGSVGElement>> }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" title={`Open on ${label}`} className="inline-flex min-h-8 items-center gap-1.5 rounded-sm px-2 text-sm voice-semi font-medium text-accent-ink no-underline transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk">
      <Mark className="size-4" />
      {label}
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  );
}

/** Scryfall Tagger tags split: only A · both · only B. */
function TagSplit({ tags, a, b }: { tags: Record<string, OracleTagOut[]>; a: string; b: string }) {
  const groups: [string, OracleTagOut[]][] = [[`Only ${a}`, tags.a_only ?? []], ['Both', tags.both ?? []], [`Only ${b}`, tags.b_only ?? []]];
  if (!groups.some(([, ts]) => ts.length)) return null;
  return (
    <section aria-label="Tags compared" className="grid gap-3 sm:grid-cols-3">
      {groups.map(([label, ts]) => (
        <div key={label} className="flex min-w-0 flex-col gap-1">
          <h3 className="text-xs voice-semi text-ink-muted">{label} · tags</h3>
          {ts.length ? (
            <ul className="flex flex-wrap gap-1">
              {ts.map((t) => <li key={t.id} className={`rounded-xs border px-1.5 py-0.5 text-xs ${label === 'Both' ? 'border-rule-strong text-ink' : 'border-rule text-ink-muted'}`}>{t.label}</li>)}
            </ul>
          ) : (
            <p className="text-xs text-ink-muted">—</p>
          )}
        </div>
      ))}
    </section>
  );
}

/** Identifies the two stacked bars in the Both column. */
function BarLegend({ a, b, metric }: { a: string; b: string; metric: string }) {
  return (
    <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
      <span className="flex items-center gap-1.5"><span className="h-[3px] w-5 rounded-pill bg-rule-strong" />{a} (top)</span>
      <span className="flex items-center gap-1.5"><span className="h-[3px] w-5 rounded-pill bg-ink-muted" />{b} (bottom)</span>
      <span>bars = {metric}</span>
    </p>
  );
}

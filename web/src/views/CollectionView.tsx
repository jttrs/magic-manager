import { useQuery } from '@tanstack/react-query';
import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { useEffect, useMemo } from 'react';
import { collectionQuery, familiesQuery } from '../app/queries';
import { useSelection } from '../app/selection';
import { ViewLayout } from '../components/AppShell';
import { CopyButton } from '../components/CopyButton';
import { MultiSelect } from '../components/MultiSelect';
import { ChipToggles, Segmented, SideSection, TextField } from '../components/Sidebar';
import { SortBuilder } from '../components/SortBuilder';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { VirtualGuide, type GuideSection } from '../components/VirtualGuide';
import { collectionBuyList, type CollectionCardOut, type CollectionOut } from '../core/api';
import { CARD_SORT, CARD_SORT_PRESETS, type CardSortKey } from '../core/cardSort';
import { buyFinish, collectionStats, filterCollection, isMissing, TRAITS, traitCounts, type MissingBasis } from '../core/collection';
import { fmtInt, fmtUsd } from '../core/format';
import { fromCollection, groupCards, type GuideCard } from '../core/guideCard';
import { SHOW, type CollectionSearch } from '../core/search';
import { decodeSort, encodeSort, leadSection, sortBy, type SortRule } from '../core/sort';

const route = getRouteApi('/collection');

const LAST_FAMILIES = 'mm.collection.families';
const RESET: Partial<CollectionSearch> = { show: [...SHOW], basis: 'either', exclude: [], q: '' };

export function CollectionView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/collection' });
  const set = (patch: Partial<CollectionSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const fams = useQuery(familiesQuery());
  const q = useQuery(collectionQuery(search.families));
  const { selected, toggle, clear } = useSelection('collection');
  const rules = useMemo(() => decodeSort(search.sort, CARD_SORT), [search.sort]);

  // Default scope: the families you last looked at (first visit opens the picker).
  useEffect(() => {
    if (search.families.length) localStorage.setItem(LAST_FAMILIES, JSON.stringify(search.families));
    else {
      const last = JSON.parse(localStorage.getItem(LAST_FAMILIES) ?? '[]') as string[];
      if (last.length) navigate({ search: (s) => ({ ...s, families: last }), replace: true });
    }
  }, [search.families, navigate]);

  const view = useMemo(() => (q.data ? buildView(q.data, search, rules) : null), [q.data, search, rules]);
  const counts = useMemo(() => (q.data ? traitCounts(q.data.cards) : null), [q.data]);

  const marked = view ? [...selected].map((k) => view.byId.get(k)).filter((c) => c != null) : [];
  const buyPool = marked.length ? marked : (view?.shown.filter((c) => isMissing(c, search.basis)) ?? []);
  const buyText = (target: 'manapool' | 'tcgplayer') => async () => {
    const r = await collectionBuyList({
      body: { target, items: buyPool.map((c) => ({ scryfall_id: c.scryfall_id, finish: buyFinish(c, search.basis), qty: 1 })) },
    });
    if (r.error || !r.data) throw new Error('buy-list failed');
    return r.data.text;
  };

  const sidebar = (
    <>
      <SideSection title="Scope">
        {fams.isPending ? (
          <p role="status" className="text-sm text-on-chrome-muted">Loading your set families…</p>
        ) : fams.isError ? (
          <p className="text-sm text-danger">Couldn’t load families: {(fams.error as Error).message}</p>
        ) : (
          <MultiSelect
            label="Set families"
            noun="families"
            value={search.families}
            onChange={(families) => set({ families })}
            options={fams.data.map((f) => ({ value: f.code, label: f.name }))}
          />
        )}
      </SideSection>
      <SideSection title="Show">
        <ChipToggles
          label="Show cards"
          value={search.show}
          onChange={(show) => set({ show: SHOW.filter((s) => show.includes(s)) })}
          options={[
            { value: 'owned', label: 'Owned', count: view?.stats.owned },
            { value: 'missing', label: 'Missing', count: view?.stats.missing },
          ]}
        />
        <Segmented<MissingBasis>
          label="Finish"
          value={search.basis}
          onChange={(basis) => set({ basis })}
          options={[{ value: 'either', label: 'Any finish' }, { value: 'nonfoil', label: 'Nonfoil' }, { value: 'foil', label: 'Foil' }]}
        />
        <MultiSelect
          label="Card types"
          noun="card types"
          searchable={false}
          summary={typesSummary(search.exclude)}
          value={TRAITS.map((t) => t.key).filter((k) => !search.exclude.includes(k))}
          onChange={(included) => set({ exclude: TRAITS.map((t) => t.key).filter((k) => !included.includes(k)) })}
          options={TRAITS.filter((t) => !counts || counts.has(t.key) || search.exclude.includes(t.key)).map((t) => ({ value: t.key, label: t.label, group: t.group, count: counts?.get(t.key) ?? 0 }))}
        />
        {(search.exclude.length > 0 || search.show.length < 2 || search.basis !== 'either' || search.q) && (
          <button type="button" onClick={() => set(RESET)} className="self-start cursor-pointer text-sm text-on-chrome-muted underline hover:text-on-chrome">Reset filters</button>
        )}
      </SideSection>
      <SideSection title="Arrange">
        <SortBuilder keys={CARD_SORT} rules={rules} presets={CARD_SORT_PRESETS} onChange={(r) => set({ sort: encodeSort(r, CARD_SORT) })} />
        <Segmented label="Density" value={search.density} onChange={(density) => set({ density })} options={[{ value: 'grid', label: 'Grid' }, { value: 'rows', label: 'Rows' }]} />
        <TextField name="q" label="Card name" value={search.q} placeholder="e.g. Cloud…" onChange={(qv) => set({ q: qv })} />
      </SideSection>
      <SideSection title={marked.length ? `Buy list · ${marked.length} marked` : `Buy list · ${buyPool.length} missing shown`}>
        <CopyButton label="Copy ManaPool list" emphasis="primary" getText={buyText('manapool')} />
        <CopyButton label="Copy TCGplayer list" getText={buyText('tcgplayer')} />
        {selected.size > 0 && (
          <button type="button" onClick={clear} className="self-start cursor-pointer text-sm text-on-chrome-muted underline hover:text-on-chrome">Clear marks</button>
        )}
      </SideSection>
    </>
  );

  let body;
  if (!search.families.length) {
    body = (
      <EmptyNote title="Choose the sets you collect">
        Pick one or more set families in the sidebar. Every printing appears with your copies counted under the card; gaps are marked Missing.
      </EmptyNote>
    );
  } else if (q.isPending) {
    body = <GridSkeleton label="Loading your collection…" />;
  } else if (q.isError) {
    body = <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  } else if (!view || view.cards.length === 0) {
    body = <EmptyNote title="Nothing matches">No printings match these filters. Turn a layer back on or show both owned and missing cards.</EmptyNote>;
  } else {
    body = <VirtualGuide sections={view.sections} density={search.density} selected={selected} onToggle={toggle} label="Collection cards" minCardWidth={128} />;
  }

  const title = q.data?.families.length ? q.data.families.map((f) => f.name).join(' · ') : 'Collection';
  const s = view?.stats;
  return (
    <ViewLayout label="Collection controls" summary={controlsSummary(search, rules, fams.data)} sidebar={sidebar} startOpen={!search.families.length}>
      <GuideSheet
        title={title}
        summary={s ? `${fmtInt(s.owned)} of ${fmtInt(s.printings)} printings owned · ${fmtInt(s.copies)} copies · ${fmtInt(s.missing)} missing (${fmtUsd(s.missingUsd)})${q.data?.skipped?.length ? ` · skipped ${q.data.skipped.join(', ')}` : ''}` : undefined}
      >
        {body}
      </GuideSheet>
    </ViewLayout>
  );
}

/** "All card types" or the unchecked traits, e.g. "Hiding Common, Uncommon +2". */
function typesSummary(exclude: readonly string[]): string {
  if (!exclude.length) return 'All card types';
  const labels = TRAITS.filter((t) => exclude.includes(t.key)).map((t) => t.label);
  return `Hiding ${labels.slice(0, 2).join(', ')}${labels.length > 2 ? ` +${labels.length - 2}` : ''}`;
}

type Built = { cards: GuideCard[]; shown: CollectionCardOut[]; sections: GuideSection[]; byId: Map<string, CollectionCardOut>; stats: ReturnType<typeof collectionStats> };

/** Filter → map → sort → section (family running head, then the lead sort key's groups). */
function buildView(data: CollectionOut, search: CollectionSearch, rules: SortRule<CardSortKey>[]): Built {
  const shown = filterCollection(data.cards, search);
  const cards = sortBy(shown.map((c) => fromCollection(c, isMissing(c, search.basis))), rules, CARD_SORT);
  const section = leadSection(rules, CARD_SORT);
  const sections: GuideSection[] = [];
  for (const fam of data.families) {
    const famCards = cards.filter((c) => c.group === fam.code);
    if (!famCards.length) continue;
    const st = collectionStats(shown.filter((c) => c.family === fam.code), search.basis);
    sections.push({
      key: `fam:${fam.code}`,
      label: fam.name,
      level: 1,
      items: [],
      head: <FamilyHead name={fam.name} owned={fam.owned_printings} printings={fam.printings} copies={fam.owned_copies} value={fam.owned_usd} shownMissing={st.missing} shownMissingUsd={st.missingUsd} />,
    });
    if (section) {
      for (const g of groupCards(famCards.map((c) => ({ ...c, group: section(c) })))) sections.push({ ...g, key: `${fam.code}:${g.key}`, level: 2 });
    } else {
      sections.push({ key: `${fam.code}:all`, label: 'All printings', level: 2, items: famCards });
    }
  }
  return { cards, shown, sections, byId: new Map(shown.map((c) => [c.scryfall_id, c])), stats: collectionStats(shown, search.basis) };
}

function FamilyHead(p: { name: string; owned: number; printings: number; copies: number; value: number; shownMissing: number; shownMissingUsd: number }) {
  const pct = p.printings ? Math.round((p.owned / p.printings) * 100) : 0;
  return (
    <h2 className="flex flex-wrap items-end gap-x-4 gap-y-1 border-b-2 border-rule-strong pb-1 pt-5 text-ink">
      <span className="text-2xl voice-condensed font-bold uppercase leading-none">{p.name}</span>
      <span className="flex items-center gap-2" aria-label={`${pct}% of printings owned`}>
        <span className="relative h-1.5 w-24 overflow-hidden rounded-pill bg-rule">
          <span className="absolute inset-y-0 left-0 bg-highlight-solid" style={{ width: `${pct}%` }} />
        </span>
        <span className="text-sm tabular text-ink">{pct}%</span>
      </span>
      <span className="ml-auto text-sm tabular text-ink-muted">
        {fmtInt(p.owned)}/{fmtInt(p.printings)} printings · {fmtInt(p.copies)} copies · {fmtUsd(p.value)} — {fmtInt(p.shownMissing)} missing shown · {fmtUsd(p.shownMissingUsd)}
      </span>
    </h2>
  );
}

function controlsSummary(search: CollectionSearch, rules: SortRule<CardSortKey>[], fams: { code: string; name: string }[] | undefined): string {
  const names = search.families.map((c) => fams?.find((f) => f.code === c)?.name ?? c.toUpperCase());
  const show = search.show.length === 2 ? 'Owned + missing' : search.show[0] === 'owned' ? 'Owned only' : search.show[0] === 'missing' ? 'Missing only' : 'Nothing shown';

  const parts = [
    names.length > 2 ? `${names[0]} +${names.length - 1}` : names.join(', '),
    show,
    search.exclude.length ? typesSummary(search.exclude) : '',
    rules.map((r) => CARD_SORT[r.key].label).join(' › '),
  ];
  return parts.filter(Boolean).join(' · ');
}

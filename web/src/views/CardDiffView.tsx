import { useQuery } from '@tanstack/react-query';
import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { useMemo } from 'react';
import { cardDiffQuery, familiesQuery } from '../app/queries';
import { useSelection } from '../app/selection';
import { ViewLayout } from '../components/AppShell';
import { CopyButton } from '../components/CopyButton';
import { ChipToggles, Segmented, SideSection, TextField } from '../components/Sidebar';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { VirtualGuide, type GuideSection } from '../components/VirtualGuide';
import { filterTiles, sortTiles } from '../core/cardDiff';
import { fmtInt, fmtUsd } from '../core/format';
import { exportLines, fromCardDiff, groupCards, type GuideCard } from '../core/guideCard';
import type { CardDiffOut, FamilyOption } from '../core/api';
import { POOLS, type CardDiffSearch } from '../core/search';

const route = getRouteApi('/sets');

const POOL_LABEL = { printing: 'Printing', functional: 'Functional', 'variant-chase': 'Variant-chase' } as const;

export function CardDiffView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/sets' });
  const set = (patch: Partial<CardDiffSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const fams = useQuery(familiesQuery());
  const q = useQuery(cardDiffQuery(search.families, search.chase));
  const { selected, toggle, clear } = useSelection('card-diff');
  const data = q.data;

  const view = useMemo(() => {
    if (!data) return null;
    const shown = sortTiles(filterTiles(data.cards, search.q, search.show), search.sort).map(fromCardDiff);
    const sections = familySections(data, shown);
    return { sections, shown, byKey: new Map<string, GuideCard>(shown.map((c) => [c.key, c])) };
  }, [data, search.q, search.show, search.sort]);

  const marked = view ? [...selected].map((k) => view.byKey.get(k)).filter((c) => c != null) : [];
  const exportSet = () => (marked.length ? marked : (view?.shown ?? []));

  const totals = data
    ? {
        owned: data.families.reduce((s, f) => s + f.owned_usd, 0),
        missing: (view?.shown ?? []).reduce((s, c) => s + (c.price ?? 0), 0),
      }
    : null;

  const sidebar = (
    <CardDiffSidebar
      search={search}
      set={set}
      fams={fams}
      data={data}
      marked={marked}
      exportSet={exportSet}
      hasMarks={selected.size > 0}
      clear={clear}
    />
  );

  let body;
  if (!search.families.length) {
    body = (
      <EmptyNote title="Pick a set family">
        Choose one or more families in the sidebar. Each missing printing shows exactly as it was printed, stamped with the pools it belongs to.
      </EmptyNote>
    );
  } else if (q.isPending) {
    body = <GridSkeleton label="Diffing your collection against the set…" />;
  } else if (q.isError) {
    body = <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  } else if (!view || view.shown.length === 0) {
    body = <EmptyNote title="Nothing missing here">No printings match these pools and filters. Try including chase printings or another pool.</EmptyNote>;
  } else {
    body = <VirtualGuide sections={view.sections} density={search.density} selected={selected} onToggle={toggle} label="Missing printings" minCardWidth={128} />;
  }

  const title = data?.families.length ? `Missing from ${data.families.map((f) => f.name).join(', ')}` : 'Missing from set';
  return (
    <ViewLayout label="Missing-set controls" sidebar={sidebar} startOpen={!search.families.length}>
      <GuideSheet
        title={title}
        summary={totals ? `Owned ${fmtUsd(totals.owned)} · missing ${fmtUsd(totals.missing)} across ${fmtInt(view?.shown.length ?? 0)} printings${data?.skipped?.length ? ` · skipped ${data.skipped.join(', ')}` : ''}` : undefined}
      >
        {body}
      </GuideSheet>
    </ViewLayout>
  );
}

/** Family running head (level 1) followed by one subhead group per set code (level 2). */
function familySections(data: CardDiffOut, shown: GuideCard[]): GuideSection[] {
  const sections: GuideSection[] = [];
  for (const fam of data.families) {
    const famCards = shown.filter((c) => c.group === fam.code);
    if (!famCards.length) continue;
    const missingUsd = famCards.reduce((s, c) => s + (c.price ?? 0), 0);
    sections.push({
      key: `fam:${fam.code}`,
      label: fam.name,
      level: 1,
      items: [],
      head: (
        <h3 className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b-2 border-rule-strong pb-1 pt-5 text-ink">
          <span className="text-2xl voice-condensed font-bold uppercase">{fam.name}</span>
          <span className="ml-auto text-sm tabular text-ink-muted">
            owned {fmtInt(fam.owned_prints)} prints · {fmtUsd(fam.owned_usd)} — missing {fmtInt(famCards.length)} shown · {fmtUsd(missingUsd)}
          </span>
        </h3>
      ),
    });
    const bySet = groupCards(famCards.map((c) => ({ ...c, group: c.setCode ?? '—' })));
    for (const g of bySet) sections.push({ ...g, key: `${fam.code}:${g.key}`, level: 2 });
  }
  return sections;
}

type SidebarProps = {
  search: CardDiffSearch;
  set: (patch: Partial<CardDiffSearch>) => void;
  fams: ReturnType<typeof useQuery<FamilyOption[]>>;
  data: CardDiffOut | undefined;
  marked: GuideCard[];
  exportSet: () => GuideCard[];
  hasMarks: boolean;
  clear: () => void;
};

function CardDiffSidebar({ search, set, fams, data, marked, exportSet, hasMarks, clear }: SidebarProps) {
  return (
    <>
      <SideSection title="Set families">
        {fams.isPending ? (
          <div role="status" className="flex flex-wrap items-center gap-1.5">
            <span className="w-full text-sm text-on-chrome-muted">Loading your set families…</span>
            {[5, 8, 6, 9, 7, 5].map((w, i) => (
              <span key={i} className="h-7 animate-pulse rounded-pill bg-chrome-raised" style={{ width: `${w}ch` }} />
            ))}
          </div>
        ) : fams.isError ? (
          <p className="text-sm text-danger">Couldn’t load families: {(fams.error as Error).message}</p>
        ) : fams.data.length === 0 ? (
          <p className="text-sm text-on-chrome-muted">No owned or registered families yet. Add inventory with <code translate="no">uv run mm set ingest</code>.</p>
        ) : (
          <ChipToggles label="Set families" value={search.families} onChange={(families) => set({ families })} options={fams.data.map((f) => ({ value: f.code, label: f.name }))} />
        )}
      </SideSection>
      <SideSection title="Pools">
        <ChipToggles
          label="Pools"
          value={search.show}
          onChange={(show) => set({ show: POOLS.filter((p) => show.includes(p)) })}
          options={POOLS.map((p) => ({ value: p, label: POOL_LABEL[p], count: data?.families.reduce((s, f) => s + (f.pools[p]?.count ?? 0), 0) }))}
        />
        <Segmented label="Chase printings" value={search.chase} onChange={(chase) => set({ chase })} options={[{ value: 'exclude', label: 'No chase' }, { value: 'include', label: '+ Chase' }, { value: 'only', label: 'Only' }]} />
      </SideSection>
      <SideSection title="Display">
        <Segmented label="Density" value={search.density} onChange={(density) => set({ density })} options={[{ value: 'grid', label: 'Grid' }, { value: 'rows', label: 'Rows' }]} />
        <Segmented label="Sort by" value={search.sort} onChange={(sort) => set({ sort })} options={[{ value: 'value', label: 'Value' }, { value: 'cn', label: 'Number' }, { value: 'name', label: 'A–Z' }]} />
        <TextField name="q" label="Card name" value={search.q} placeholder="e.g. Cloud…" onChange={(q) => set({ q })} />
      </SideSection>
      <SideSection title={marked.length ? `Buy list · ${marked.length} marked` : 'Buy list · all shown'}>
        <CopyButton label="Copy ManaPool list" emphasis="primary" getText={() => exportLines(exportSet(), 'manapool')} />
        <CopyButton label="Copy TCGplayer list" getText={() => exportLines(exportSet(), 'tcgplayer')} />
        {hasMarks && (
          <button type="button" onClick={clear} className="self-start cursor-pointer text-sm text-on-chrome-muted underline hover:text-on-chrome">
            Clear marks
          </button>
        )}
      </SideSection>
    </>
  );
}

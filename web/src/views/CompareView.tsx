import { useQuery } from '@tanstack/react-query';
import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { useMemo } from 'react';
import { compareQuery } from '../app/queries';
import { useSelection } from '../app/selection';
import { ViewLayout } from '../components/AppShell';
import { CommanderPicker } from '../components/CommanderPicker';
import { CopyButton } from '../components/CopyButton';
import { GuideColumns, type Column } from '../components/GuideColumns';
import { ChipToggles, Segmented, SideSection, TextField } from '../components/Sidebar';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { VirtualGuide } from '../components/VirtualGuide';
import { bucketCards, matches, sortCards, tagCounts, tagLabel } from '../core/compare';
import { exportLines, fromCompare, groupCards, TYPE_GROUPS } from '../core/guideCard';
import { BUCKETS, type Bucket, type CompareSearch } from '../core/search';

const cleanName = (n: string) => n.replace(/\s*\((?:Commander|Partner)\)\s*$/i, '');
const route = getRouteApi('/commanders');

const shortName = (n: string) => cleanName(n).split(',')[0].split(' // ')[0];

export function CompareView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/commanders' });
  const set = (patch: Partial<CompareSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const q = useQuery(compareQuery(search.a, search.b));
  const { selected, toggle, clear } = useSelection('compare');

  const data = q.data;
  const names = { a: data ? shortName(data.name_a) : 'A', b: data ? shortName(data.name_b) : 'B' };

  const view = useMemo(() => {
    if (!data) return null;
    const shown = sortCards(data.cards.filter((c) => matches(c, search.q, search.tags)), search.sort);
    const buckets = bucketCards(shown);
    const sections = (b: Bucket) =>
      groupCards(buckets[b].map(fromCompare), TYPE_GROUPS).map((g) => ({ ...g, level: 2 as const }));
    return {
      buckets,
      sections: { a_only: sections('a_only'), both: sections('both'), b_only: sections('b_only') },
      tags: tagCounts(data.cards).slice(0, 18),
      byKey: new Map(shown.map((c) => [fromCompare(c).key, fromCompare(c)])),
    };
  }, [data, search.q, search.tags, search.sort]);

  const titles: Record<Bucket, string> = { a_only: `${names.a} only`, both: 'Shared', b_only: `${names.b} only` };
  const columns: Column[] = BUCKETS.map((b) => ({
    id: b,
    title: titles[b],
    count: view?.buckets[b].length ?? 0,
    legend: b === 'both' ? <BarLegend a={names.a} b={names.b} /> : undefined,
    body: view ? (
      <VirtualGuide
        sections={view.sections[b]}
        density={search.density}
        selected={selected}
        onToggle={toggle}
        barLabels={[names.a, names.b]}
        label={`${titles[b]} cards`}
      />
    ) : null,
  }));

  const marked = view ? [...selected].map((k) => view.byKey.get(k)).filter((c) => c != null) : [];

  const sidebar = (
    <>
      <SideSection title="Commanders">
        <div className="flex flex-col gap-3">
          <CommanderPicker name="commander-a" label="Commander A" value={search.a} onCommit={(a) => set({ a })} />
          <CommanderPicker name="commander-b" label="Commander B" value={search.b} onCommit={(b) => set({ b })} />
        </div>
      </SideSection>
      <SideSection title="Columns">
        <ChipToggles
          label="Visible columns"
          value={search.show}
          onChange={(show) => set({ show: BUCKETS.filter((b) => show.includes(b)) })}
          options={BUCKETS.map((b) => ({ value: b, label: titles[b], count: view?.buckets[b].length }))}
        />
      </SideSection>
      <SideSection title="Display">
        <Segmented label="Density" value={search.density} onChange={(density) => set({ density })} options={[{ value: 'grid', label: 'Grid' }, { value: 'rows', label: 'Rows' }]} />
        <Segmented
          label="Sort by"
          value={search.sort}
          onChange={(sort) => set({ sort })}
          options={[{ value: 'inclusion', label: 'Incl.' }, { value: 'synergy', label: 'Syn.' }, { value: 'price', label: 'Price' }, { value: 'name', label: 'A–Z' }]}
        />
      </SideSection>
      <SideSection title="Filter">
        <TextField name="q" label="Card name" value={search.q} placeholder="e.g. Sol Ring…" onChange={(q) => set({ q })} />
        {view && view.tags.length > 0 && (
          <ChipToggles label="EDHREC lists" value={search.tags} onChange={(tags) => set({ tags })} options={view.tags.map(([t, n]) => ({ value: t, label: tagLabel(t), count: n }))} />
        )}
      </SideSection>
      <SideSection title={`Marked · ${marked.length}`}>
        <CopyButton label="Copy marked as list" emphasis="primary" getText={() => exportLines(marked, 'plain')} />
        {selected.size > 0 && (
          <button type="button" onClick={clear} className="self-start cursor-pointer text-sm text-on-chrome-muted underline hover:text-on-chrome">
            Clear marks
          </button>
        )}
      </SideSection>
    </>
  );

  let body;
  if (!search.a || !search.b) {
    body = (
      <EmptyNote title="Pick two commanders">
        Choose a commander in each field. Cards both decks run land in the middle column; each side’s exclusives flank it.
      </EmptyNote>
    );
  } else if (q.isPending) {
    body = <GridSkeleton label={`Loading recommendations for ${search.a} and ${search.b}… uncached commanders are fetched from EDHREC first.`} />;
  } else if (q.isError) {
    body = <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  } else {
    body = <GuideColumns columns={columns} visible={search.show} onHide={(id) => set({ show: search.show.filter((s) => s !== id) })} storageKey="compare" />;
  }

  return (
    <ViewLayout label="Compare controls" sidebar={sidebar} startOpen={!search.a || !search.b}>
      <GuideSheet
        title="Commander compare"
        summary={data ? `${cleanName(data.name_a)} vs ${cleanName(data.name_b)} · ${data.cards.length} recommended cards · cheapest price across printings` : undefined}
      >
        {body}
      </GuideSheet>
    </ViewLayout>
  );
}

/** Identifies the two stacked inclusion bars in the Shared column. */
function BarLegend({ a, b }: { a: string; b: string }) {
  return (
    <p className="flex items-center gap-4 text-xs text-ink-muted">
      <span className="flex items-center gap-1.5"><span className="h-[3px] w-5 rounded-pill bg-rule-strong" />{a} (top)</span>
      <span className="flex items-center gap-1.5"><span className="h-[3px] w-5 rounded-pill bg-ink-muted" />{b} (bottom)</span>
    </p>
  );
}

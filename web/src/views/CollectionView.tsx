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
import { buyFinish, collectionStats, filterCollection, isMissing, type MissingBasis } from '../core/collection';
import { fmtInt, fmtUsd } from '../core/format';
import { fromCollection, groupCards, type GuideCard } from '../core/guideCard';
import { SHOW, type CollectionSearch } from '../core/search';
import { decodeSort, encodeSort, leadSection, sortBy, type SortRule } from '../core/sort';

const route = getRouteApi('/collection');

/** One click to what you'd actually buy: gaps only, no bulk, treatments or chase. */
const SHOPPING: Partial<CollectionSearch> = { show: ['missing'], bulk: 'hide', treatments: 'hide', chase: 'hide' };
const RESET: Partial<CollectionSearch> = { show: [...SHOW], basis: 'either', bulk: 'show', treatments: 'show', chase: 'show', q: '' };
const BASIS_HINT: Record<MissingBasis, string> = {
  either: 'Missing = you own no copy of the printing in any finish.',
  nonfoil: 'Missing = no nonfoil copy (printings with no nonfoil version are skipped).',
  foil: 'Missing = no foil copy (printings with no foil version are skipped).',
};
const LAST_FAMILIES = 'mm.collection.families';

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
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm">
          <button type="button" onClick={() => set(SHOPPING)} className="cursor-pointer text-on-chrome underline decoration-accent decoration-2 underline-offset-4 hover:text-accent">Shopping view</button>
          <button type="button" onClick={() => set(RESET)} className="cursor-pointer text-on-chrome-muted underline hover:text-on-chrome">Reset filters</button>
        </div>
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
          label="Missing means"
          value={search.basis}
          onChange={(basis) => set({ basis })}
          options={[{ value: 'either', label: 'Any finish' }, { value: 'nonfoil', label: 'Nonfoil' }, { value: 'foil', label: 'Foil' }]}
        />
        <p className="text-xs leading-snug text-on-chrome-muted">{BASIS_HINT[search.basis]}</p>
      </SideSection>
      <SideSection title="Layers">
        <Toggle label="Exclude bulk" hint="commons & uncommons" checked={search.bulk === 'hide'} onChange={(on) => set({ bulk: on ? 'hide' : 'show' })} />
        <Toggle label="Exclude treatments" hint="borderless, showcase, ext. art…" checked={search.treatments === 'hide'} onChange={(on) => set({ treatments: on ? 'hide' : 'show' })} />
        <div className="flex flex-col gap-1">
          <span className="text-sm text-on-chrome-muted">Chase cards</span>
          <Segmented label="Chase cards" value={search.chase} onChange={(chase) => set({ chase })} options={[{ value: 'show', label: 'Show' }, { value: 'hide', label: 'Hide' }, { value: 'only', label: 'Only' }]} />
        </div>
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

function Toggle({ label, hint, checked, onChange }: { label: string; hint: string; checked: boolean; onChange: (on: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5 text-md text-on-chrome">
      <input type="checkbox" role="switch" checked={checked} onChange={(e) => onChange(e.target.checked)} className="mt-1 h-4 w-4 shrink-0 cursor-pointer accent-[var(--theme-accent)]" />
      <span className="flex flex-col leading-tight">
        {label}
        <span className="text-xs text-on-chrome-muted">{hint}</span>
      </span>
    </label>
  );
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
  const hidden = [search.bulk === 'hide' && 'bulk', search.treatments === 'hide' && 'treatments', search.chase === 'hide' && 'chase'].filter(Boolean);
  const parts = [
    names.length > 2 ? `${names[0]} +${names.length - 1}` : names.join(', '),
    show,
    hidden.length ? `no ${hidden.join('/')}` : '',
    search.chase === 'only' ? 'chase only' : '',
    rules.map((r) => CARD_SORT[r.key].label).join(' › '),
  ];
  return parts.filter(Boolean).join(' · ');
}

import { useQuery } from '@tanstack/react-query';
import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { useEffect, useMemo } from 'react';
import { collectionQuery, familiesQuery } from '../app/queries';
import { useSelection } from '../app/selection';
import { ViewLayout } from '../components/AppShell';
import { AddCardsDialog } from '../components/addcards/AddCardsDialog';
import { CopyTargets } from '../components/CopyButton';
import { AddCardMark, CardKingdomMark, CountCardsMark, FindProductsMark, ManaPoolMark, TcgplayerMark } from '../components/StoreMarks';
import { IconAction } from '../components/IconAction';
import { FindProductsDialog } from './collection/FindProductsDialog';
import { CollectionTabs } from './collection/CollectionTabs';
import { CartCheckDialog } from './collection/CartCheckDialog';
import { ChecklistActions, ChecklistLeaveGuard, ChecklistNotes, ChecklistTable } from './collection/Checklist';
import { useChecklist } from './collection/useChecklist';
import { SceneDetail, SceneMeta } from './collection/SceneHead';
import { useFeature } from '../app/features';
import { Button } from '../components/Button';
import { MultiSelect } from '../components/MultiSelect';
import { Segmented, SegmentedToggles, SideSection, TextField } from '../components/Sidebar';
import { SortBuilder } from '../components/SortBuilder';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { VirtualGuide, type GuideSection } from '../components/VirtualGuide';
import { collectionBuyList, type CollectionCardOut, type CollectionOut } from '../core/api';
import { activeRules, collectionPresets, collectionSortKeys, COLLECTION_SORT, NO_SCENE, sceneRanks, type CollectionSortKey } from '../core/scenes';
import { buyFinish, buyTotal, collectionStats, filterCollection, functionCounts, isMissing, NO_FUNCTION, setGroupIncluded, sourceKinds, sourceOptions, TRAITS, traitCounts, traitsIn, type TraitGroup } from '../core/collection';
import { InfoTip } from '../components/InfoTip';
import { summaryLine } from '../core/checklist';
import { fmtInt, fmtUsd } from '../core/format';
import { fromCollection, groupCards, type GuideCard } from '../core/guideCard';
import { SHOW, type CollectionSearch } from '../core/search';
import { decodeSort, encodeSort, leadSection, sortBy, type SortRule } from '../core/sort';

const route = getRouteApi('/collection');

const LAST_FAMILIES = 'mm.collection.families';
const RESET: Partial<CollectionSearch> = { show: [...SHOW], exclude: [], q: '', fn: [], src: [] };

export function CollectionView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/collection' });
  const set = (patch: Partial<CollectionSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const fams = useQuery(familiesQuery());
  const q = useQuery(collectionQuery(search.families));
  const { selected, toggle, clear } = useSelection('collection');
  const hasScenes = (q.data?.scenes?.length ?? 0) > 0;
  const rules = useMemo(() => activeRules(decodeSort(search.sort, COLLECTION_SORT), hasScenes), [search.sort, hasScenes]);

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
  const included = (g: TraitGroup) => traitsIn(g).map((t) => t.key).filter((k) => !search.exclude.includes(k));
  /** A group's options present in the data (or currently excluded), with counts. */
  const traitOptions = (g: TraitGroup) =>
    traitsIn(g)
      .filter((t) => !counts || counts.has(t.key) || search.exclude.includes(t.key))
      .map((t) => ({ value: t.key, label: t.label, count: counts?.get(t.key) ?? 0 }));
  const groupSummary = (g: TraitGroup, all: string) => {
    const off = traitsIn(g).filter((t) => search.exclude.includes(t.key)).map((t) => t.label);
    return off.length ? `Hiding ${off.slice(0, 2).join(', ')}${off.length > 2 ? ` +${off.length - 2}` : ''}` : all;
  };
  const fnCounts = useMemo(() => (q.data ? functionCounts(q.data.cards) : null), [q.data]);
  const fnOptions = q.data && fnCounts && fnCounts.size > (fnCounts.has(NO_FUNCTION) ? 1 : 0)
    ? [
        ...(q.data.functions ?? []).filter((r) => fnCounts.has(r.key) || search.fn.includes(r.key)).map((r) => ({ value: r.key, label: r.label, count: fnCounts.get(r.key) ?? 0 })),
        { value: NO_FUNCTION, label: 'No tagged function', count: fnCounts.get(NO_FUNCTION) ?? 0 },
      ]
    : null;

  const srcOptions = useMemo(() => (q.data?.sources?.length ? sourceOptions(q.data.cards, q.data.sources) : null), [q.data]);

  const cartCheck = useFeature('cart_check');
  const checklist = useChecklist();
  const counting = search.count && search.families.length > 0;
  const marked = view ? [...selected].map((k) => view.byId.get(k)).filter((c) => c != null) : [];
  const buyPool = marked.length ? marked : (view?.shown.filter((c) => isMissing(c, search.exclude)) ?? []);
  const buyText = (target: 'manapool' | 'tcgplayer' | 'cardkingdom') => async () => {
    const r = await collectionBuyList({
      body: { target, items: buyPool.map((c) => ({ scryfall_id: c.scryfall_id, finish: buyFinish(c, search.exclude), qty: 1 })) },
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
        <SegmentedToggles
          label="Cards"
          showLabel
          value={search.show}
          onChange={(show) => set({ show: SHOW.filter((s) => show.includes(s)) })}
          options={[
            { value: 'owned', label: 'Owned', count: view?.stats.owned },
            { value: 'missing', label: 'Missing', count: view?.stats.missing },
          ]}
        />
        {search.show.includes('missing') && (
          <Segmented
            label="Missing means"
            showLabel
            labelExtra={
              <InfoTip label="What does missing mean?">
                <b>This printing</b> (default): each exact printing you don’t have — what a collector is missing. <b>The card</b>: only cards you have in no printing from any set — the gaps for deck building.
              </InfoTip>
            }
            value={search.gaps ? 'card' : 'printing'}
            onChange={(v) => set({ gaps: v === 'card' })}
            options={[{ value: 'printing', label: 'This printing' }, { value: 'card', label: 'The card' }]}
          />
        )}
        {srcOptions && (
          <MultiSelect
            label="Acquired from"
            labelExtra={
              <InfoTip label="What does acquired from mean?">
                Where your copies came from: a <b>card pool</b> (land pack, scene box, most Secret Lair drops), a <b>precon deck</b>, cards added as <b>singles</b>, or <b>unknown</b> for copies recorded before tracking began. Picking a source shows only owned cards.
              </InfoTip>
            }
            noun="sources"
            summary={search.src.length ? undefined : 'Any source'}
            value={search.src}
            onChange={(src) => set({ src })}
            options={srcOptions}
          />
        )}
        <MultiSelect
          label="Rarity"
          noun="rarities"
          searchable={false}
          keepOrder
          summary={groupSummary('Rarity', 'All rarities')}
          value={included('Rarity')}
          onChange={(v) => set({ exclude: setGroupIncluded(search.exclude, 'Rarity', v) })}
          options={traitOptions('Rarity')}
        />
        <MultiSelect
          label="Finish"
          noun="finishes"
          searchable={false}
          keepOrder
          summary={groupSummary('Finish', 'All finishes')}
          value={included('Finish')}
          onChange={(v) => set({ exclude: setGroupIncluded(search.exclude, 'Finish', v) })}
          options={traitOptions('Finish')}
        />
        <MultiSelect
          label="Treatment"
          noun="treatments"
          searchable={false}
          keepOrder
          summary={groupSummary('Treatment', 'All treatments')}
          value={included('Treatment')}
          onChange={(v) => set({ exclude: setGroupIncluded(search.exclude, 'Treatment', v) })}
          options={traitOptions('Treatment')}
        />
        <Segmented
          label="Chase"
          showLabel
          labelExtra={
            <InfoTip label="What counts as chase?">
              Chase printings are a set’s ultra-premium variants — raised, galaxy or first-place foils, serialized and headliner cards. They’re rare and expensive, so most collectors leave them out when completing a set.
            </InfoTip>
          }
          value={search.exclude.includes('chase:yes') ? 'exclude' : 'include'}
          onChange={(mode) => set({ exclude: setGroupIncluded(search.exclude, 'Chase', mode === 'exclude' ? ['chase:no'] : ['chase:yes', 'chase:no']) })}
          options={[{ value: 'include', label: 'Include' }, { value: 'exclude', label: 'Exclude' }]}
        />
        {fnOptions && (
          <MultiSelect
            label="Function"
            noun="functions"
            searchable={false}
            summary={search.fn.length ? undefined : 'Any function'}
            value={search.fn}
            onChange={(fn) => set({ fn })}
            options={fnOptions}
          />
        )}
        {(search.exclude.length > 0 || search.show.length < 2 || search.q || search.fn.length > 0 || search.src.length > 0) && (
          <button type="button" onClick={() => set(RESET)} className="self-start cursor-pointer text-sm text-on-chrome-muted underline hover:text-on-chrome">Reset filters</button>
        )}
      </SideSection>
      <SideSection title="Arrange">
        <SortBuilder keys={collectionSortKeys(hasScenes)} rules={rules} presets={collectionPresets(hasScenes)} onChange={(r) => set({ sort: encodeSort(r, COLLECTION_SORT) })} />
        <Segmented label="View type" showLabel value={search.view} onChange={(view) => set({ view })} options={[{ value: 'grid', label: 'Grid' }, { value: 'list', label: 'List' }]} />
        <TextField name="q" label="Card name" value={search.q} placeholder="e.g. Cloud…" onChange={(qv) => set({ q: qv })} />
      </SideSection>
      <SideSection title="Buy">
        <CopyTargets
          lead={`Copy bulk lists · ${marked.length ? `${fmtInt(marked.length)} marked` : `${fmtInt(buyPool.length)} missing shown`} · ≈ ${fmtUsd(buyTotal(buyPool, search.exclude))} at market`}
          targets={[
            { id: 'manapool', name: 'ManaPool', Mark: ManaPoolMark, getText: buyText('manapool') },
            { id: 'tcgplayer', name: 'TCGplayer', Mark: TcgplayerMark, getText: buyText('tcgplayer') },
            {
              id: 'cardkingdom',
              name: 'Card Kingdom',
              Mark: CardKingdomMark,
              getText: buyText('cardkingdom'),
              note: 'Card Kingdom takes names only; pick each printing and foil after Find Cards',
            },
          ]}
        />
        {cartCheck && (
          <CartCheckDialog family={search.families.length === 1 ? search.families[0] : undefined} trigger={<Button>Check my Mana Pool cart</Button>} />
        )}
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
    body = <EmptyNote title="Nothing matches">No printings match these filters. Check a card type back on, or show both owned and missing cards.</EmptyNote>;
  } else if (counting) {
    const familyNames = new Map(q.data.families.map((f) => [f.code, f.name]));
    body = (
      <div className="flex h-full min-h-0 flex-col">
        <ChecklistNotes checklist={checklist} />
        <ChecklistTable sections={view.sections} byId={view.byId} familyNames={familyNames} checklist={checklist} />
      </div>
    );
  } else {
    body = <VirtualGuide sections={view.sections} density={search.view} selected={selected} onToggle={toggle} label="Collection cards" minCardWidth={128} />;
  }

  const s = view?.stats;
  const famN = q.data?.families.length ?? 0;
  return (
    <ViewLayout label="Collection controls" summary={controlsSummary(search, rules, fams.data)} sidebar={sidebar} startOpen={!search.families.length}>
      <GuideSheet
        nav={<CollectionTabs />}
        title="Collection"
        actions={
          <span role="toolbar" aria-label="Collection actions" className="flex items-center gap-0.5">
            {counting && <ChecklistActions checklist={checklist} />}
            <IconAction
              Icon={CountCardsMark}
              aria-pressed={counting}
              label={counting ? 'Done counting' : checklist.dirty ? `Count cards · ${fmtInt(checklist.summary.cells)} unsaved` : 'Count cards'}
              disabled={!search.families.length}
              disabledReason="Choose a set family to count"
              onClick={() => set({ count: !search.count })}
            />
            <AddCardsDialog trigger={<IconAction Icon={AddCardMark} label="Add cards" />} />
            <FindProductsDialog trigger={<IconAction Icon={FindProductsMark} label="Find products in your cards" />} />
          </span>
        }
        summary={
          counting
            ? summaryLine(checklist.summary, checklist.saved)
            : s
            ? `${famN} set ${famN === 1 ? 'family' : 'families'} · showing ${fmtInt(s.printings)} printings: ${fmtInt(s.owned)} owned (${fmtInt(s.copies)} copies), ${search.gaps ? `${fmtInt(s.missingCards)} cards you own in no printing · ${fmtUsd(s.missingCardsUsd)} at the cheapest printing of each` : `${fmtInt(s.missing)} missing · ${fmtUsd(s.missingUsd)} to complete`}${q.data?.skipped?.length ? ` · skipped ${q.data.skipped.join(', ')}` : ''}`
            : undefined
        }
      >
        {body}
      </GuideSheet>
      <ChecklistLeaveGuard checklist={checklist} />
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

/** Filter → map → sort → section (set-family head, then the lead sort key's groups). */
function buildView(data: CollectionOut, search: CollectionSearch, rules: SortRule<CollectionSortKey>[]): Built {
  const shown = filterCollection(data.cards, search, sourceKinds(data.sources));
  const fnLabels = Object.fromEntries((data.functions ?? []).map((r) => [r.key, r.label]));
  const ranks = sceneRanks(data.scenes ?? []);
  const scenes = new Map((data.scenes ?? []).map((sc) => [sc.key, sc]));
  const cards = sortBy(
    shown.map((c) => ({ ...fromCollection(c, isMissing(c, search.exclude), fnLabels), sceneRank: c.scene ? ranks.get(c.scene) ?? null : null })),
    rules,
    COLLECTION_SORT,
  );
  const section = leadSection(rules, COLLECTION_SORT);
  const bySet = rules[0]?.key === 'set';
  const byScene = rules[0]?.key === 'scene';
  const sections: GuideSection[] = [];
  for (const fam of data.families) {
    const famCards = cards.filter((c) => c.group === fam.code);
    if (!famCards.length) continue;
    const setNames = new Map((fam.sets ?? []).map((x) => [x.code.toUpperCase(), x.name]));
    sections.push({
      key: `fam:${fam.code}`,
      label: fam.name,
      level: 1,
      items: [],
      noun: 'set family',
      detail: (
        <>
          <FamilyCodes codes={(fam.sets ?? []).map((x) => x.code)} />
          <OwnedMeter owned={fam.owned_printings} printings={fam.printings} />
        </>
      ),
      meta: `${fmtInt(fam.owned_printings)}/${fmtInt(fam.printings)} printings · ${fmtInt(fam.owned_copies)} copies · ${fmtUsd(fam.owned_usd)}`,
    });
    if (section) {
      for (const g of groupCards(famCards.map((c) => ({ ...c, group: section(c) })))) {
        const scene = byScene ? scenes.get(g.key) : undefined;
        if (byScene) {
          sections.push({
            ...g,
            key: `${fam.code}:${g.key}`,
            label: scene?.name ?? (g.key === NO_SCENE ? 'Not in a scene' : g.label),
            level: 2,
            noun: 'scene',
            detail: scene ? <SceneDetail scene={scene} /> : undefined,
            meta: scene ? <SceneMeta scene={scene} /> : undefined,
          });
          continue;
        }
        const setName = bySet ? setNames.get(g.label) : undefined;
        sections.push({
          ...g,
          key: `${fam.code}:${g.key}`,
          level: 2,
          noun: bySet ? 'set' : 'group',
          detail: setName ? <span className="truncate text-sm normal-case text-ink-muted">{setName}</span> : undefined,
        });
      }
    } else {
      sections.push({ key: `${fam.code}:all`, label: 'All printings', level: 2, items: famCards });
    }
  }
  return { cards, shown, sections, byId: new Map(shown.map((c) => [c.scryfall_id, c])), stats: collectionStats(shown, search.exclude) };
}

/** "Set family · BLB · BLC" printed beside the family name. */
function FamilyCodes({ codes }: { codes: string[] }) {
  const head = codes.slice(0, 8).map((c) => c.toUpperCase());
  return (
    <span className="pb-0.5 text-xs voice-semi font-medium uppercase tracking-[0.08em] text-ink-muted">
      Set family
      {head.length > 0 && (
        <span className="ml-1.5 font-regular tracking-normal tabular">
          · {head.join(' · ')}
          {codes.length > head.length && ` +${codes.length - head.length}`}
        </span>
      )}
    </span>
  );
}

function OwnedMeter({ owned, printings }: { owned: number; printings: number }) {
  const pct = printings ? Math.round((owned / printings) * 100) : 0;
  return (
    <span className="flex items-center gap-2 pb-0.5" role="img" aria-label={`${pct}% of printings owned`}>
      <span className="relative h-1.5 w-24 overflow-hidden rounded-pill bg-rule">
        <span className="absolute inset-y-0 left-0 bg-highlight-solid" style={{ width: `${pct}%` }} />
      </span>
      <span className="text-sm tabular text-ink">{pct}%</span>
    </span>
  );
}

function controlsSummary(search: CollectionSearch, rules: SortRule<CollectionSortKey>[], fams: { code: string; name: string }[] | undefined): string {
  const names = search.families.map((c) => fams?.find((f) => f.code === c)?.name ?? c.toUpperCase());
  const show = search.show.length === 2 ? 'Owned + missing' : search.show[0] === 'owned' ? 'Owned only' : search.show[0] === 'missing' ? 'Missing only' : 'Nothing shown';

  const parts = [
    names.length > 2 ? `${names[0]} +${names.length - 1}` : names.join(', '),
    show,
    search.exclude.length ? typesSummary(search.exclude) : '',
    search.fn.length ? `${search.fn.length} function${search.fn.length > 1 ? 's' : ''}` : '',
    search.src.length ? `${search.src.length} source${search.src.length > 1 ? 's' : ''}` : '',
    rules.map((r) => COLLECTION_SORT[r.key].label).join(' › '),
  ];
  return parts.filter(Boolean).join(' · ');
}

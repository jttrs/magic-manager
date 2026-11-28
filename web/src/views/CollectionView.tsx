import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { oracleTagCardsQuery, collectionQuery, familiesQuery } from '../app/queries';
import { useSelection } from '../app/selection';
import { setUnownedFamilies, useUnownedFamilies } from '../app/unownedFamilies';
import { useJob } from '../app/useJob';
import { ViewLayout } from '../components/AppShell';
import { AddCardsDialog } from '../components/addcards/AddCardsDialog';
import { buyListTargets, type BuyStore } from '../components/buyTargets';
import { CopyListMenu } from '../components/CopyListMenu';
import { AddCardMark, CartCheckMark, CountCardsMark } from '../components/icons/marks';
import { IconAction } from '../components/IconAction';
import { CollectionTabs } from './collection/CollectionTabs';
import { CartCheckDialog } from './collection/CartCheckDialog';
import { CardTagPicker } from './collection/CardTagPicker';
import { draftedIds, summaryLine, onlyDrafted, pendingOf } from '../core/checklist';
import { ChecklistLeaveGuard, ChecklistNotes, ChecklistTable } from './collection/Checklist';
import { PendingBar } from './collection/PendingBar';
import { useChecklist } from './collection/useChecklist';
import { SceneDetail, SceneMeta } from './collection/SceneHead';
import { useFeature } from '../app/features';
import { useSettingsSection } from '../app/settings';
import { SettingsChoice, SettingsRow } from '../components/settings/SettingsControls';
import { setMissingMeans, useMissingMeans, type MissingMeans } from './collection/missingMeans';
import { Button } from '../components/Button';
import { Check } from '../components/controls/Check';
import type { Tally } from '../components/TallyControls';
import { MultiSelect } from '../components/MultiSelect';
import { Segmented, SegmentedToggles, SideSection, TextField } from '../components/Sidebar';
import { SortControl, ViewToggle } from '../components/ArrangeControls';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { VirtualGuide, type GuideSection } from '../components/VirtualGuide';
import { collectionBuyList, type CollectionCardOut, type CollectionOut } from '../core/api';
import { activeRules, collectionPresets, collectionSortKeys, COLLECTION_SORT, NO_SCENE, sceneRanks, type CollectionSortKey } from '../core/scenes';
import { buyFinish, buyTotal, collectionCounts, collectionStats, filterCollection, isMissing, NO_FUNCTION, setGroupIncluded, TRAITS, traitsIn, type TraitGroup } from '../core/collection';
import { InfoTip } from '../components/InfoTip';
import { fmtCount, fmtInt, fmtUsd } from '../core/format';
import { familiesInCardOrder, familyFacts, fromCollection, groupCards, type GuideCard } from '../core/guideCard';
import { SHOW, type CollectionSearch, COLLECTION_SORT_DEFAULT } from '../core/search';
import { decodeSort, encodeSort, leadSection, sortBy, type SortRule } from '../core/sort';

const route = getRouteApi('/collection');

/** "Reset filters" clears what narrows the cards — the card-name search and every
 *  Show filter except the set families you chose. How cards are arranged (sort,
 *  view type) and what "missing" means (a Settings preference) are not filters,
 *  so they stay put. */
const RESET: Partial<CollectionSearch> = { show: ['owned'], exclude: [], q: '', fn: [], ot: [], em: false };

export function CollectionView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/collection' });
  const set = (patch: Partial<CollectionSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true });
  const unowned = useUnownedFamilies();
  const fams = useQuery(familiesQuery());
  // No families chosen = every family you OWN; the query waits for the list in that case.
  const allCodes = useMemo(() => (fams.data ?? []).filter((f) => f.owned !== false).map((f) => f.code), [fams.data]);
  const scope = search.families.length ? search.families : allCodes;
  // Families you don't own are listed only while the switch is on (or one is already chosen, so its name stays).
  const wantAll = unowned || (fams.isSuccess && search.families.some((c) => !allCodes.includes(c)));
  const allFams = useQuery({ ...familiesQuery(true), enabled: wantAll });
  const famOptions = useMemo(() => {
    const own = (fams.data ?? []).map((f) => ({ value: f.code, label: f.name }));
    const have = new Set(own.map((o) => o.value));
    const rest = (allFams.data ?? [])
      .filter((f) => f.owned === false && !have.has(f.code) && (unowned || search.families.includes(f.code)))
      .map((f) => ({ value: f.code, label: f.name, hint: f.year ?? undefined, bulk: false as const }));
    return [...own, ...rest];
  }, [fams.data, allFams.data, unowned, search.families]);
  const famName = useCallback((code: string) => famOptions.find((o) => o.value === code)?.label ?? code.toUpperCase(), [famOptions]);
  // Every family you own spelled out (an old link, or ticking them all) is just "all": drop the list.
  const coversAll = allCodes.length > 0 && search.families.length > 0 && allCodes.every((c) => search.families.includes(c)) && search.families.every((c) => allCodes.includes(c));
  useEffect(() => {
    if (coversAll) set({ families: [] });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `set` is a fresh closure each render
  }, [coversAll]);
  const q = useQuery({ ...collectionQuery(scope), enabled: scope.length > 0 });
  const { selected, toggle, clear } = useSelection('collection');
  const hasScenes = (q.data?.scenes?.length ?? 0) > 0;
  const rules = useMemo(() => activeRules(decodeSort(search.sort, COLLECTION_SORT), hasScenes), [search.sort, hasScenes]);
  const missingMeans = useMissingMeans();
  const gaps = missingMeans === 'card';
  const filtered = search.exclude.length > 0 || !(search.show.length === 1 && search.show[0] === 'owned') || Boolean(search.q) || search.fn.length > 0 || search.ot.length > 0 || search.em;
  const settings = useMemo(() => ({
    id: 'collection',
    title: 'Collection',
    content: (
      <SettingsRow
        label="Missing means"
        description={<><b>This printing</b>: each exact printing you don’t have — what a collector is missing. <b>The card</b>: only cards you own in no printing from any set — the gaps for deck building.</>}
        control={(ids) => (
          <SettingsChoice<MissingMeans>
            {...ids}
            value={missingMeans}
            onChange={setMissingMeans}
            options={[{ value: 'printing', label: 'This printing' }, { value: 'card', label: 'The card' }]}
          />
        )}
      />
    ),
  }), [missingMeans]);
  useSettingsSection(settings);

  // Oracle tags resolve to card ids on the server (each tag rolls up its child tags).
  const tagCards = useQuery({ ...oracleTagCardsQuery(search.ot), enabled: search.ot.length > 0 });
  // Chosen tags never fall back to "no tag filter": while they resolve (or if that
  // fails) nothing matches and the sheet says why; a tag that no longer exists is
  // skipped (and named) instead of emptying the list.
  const missingTags = useMemo(() => (tagCards.data ? search.ot.filter((s) => !tagCards.data.tags.some((t) => t.slug === s)) : []), [search.ot, tagCards.data]);
  const otIds = useMemo(() => {
    if (!search.ot.length) return undefined;
    if (!tagCards.data) return new Set<string>();
    return tagCards.data.tags.length ? new Set(tagCards.data.oracle_ids) : undefined;
  }, [search.ot, tagCards.data]);
  const view = useMemo(() => (q.data ? buildView(q.data, { ...search, gaps, otIds }, rules) : null), [q.data, search, gaps, otIds, rules]);
  // Every control's counts: under all the OTHER filters (core/facets), never its own.
  const facetData = useMemo(
    () => (q.data ? collectionCounts(q.data.cards, { ...search, gaps, otIds }) : null),
    [q.data, search, gaps, otIds],
  );
  const counts = facetData?.traits ?? null;
  const included = (g: TraitGroup) => traitsIn(g).map((t) => t.key).filter((k) => !search.exclude.includes(k));
  /** A group's options present in the data (or currently excluded), with counts. */
  const traitOptions = (g: TraitGroup) =>
    traitsIn(g)
      .filter((t) => !counts || (counts.get(t.key) ?? 0) > 0 || search.exclude.includes(t.key))
      .map((t) => ({ value: t.key, label: t.label, count: counts?.get(t.key) ?? 0 }));
  const fnCounts = facetData?.fn ?? null;
  // The Function shortlist: roots some card carries (or already chosen), plus "No tagged function".
  const hasFunctions = !!q.data?.cards.some((c) => c.functions?.length);
  const fnOptions = q.data && fnCounts && hasFunctions
    ? [
        ...(q.data.functions ?? []).filter((r) => (fnCounts.get(r.key) ?? 0) > 0 || search.fn.includes(r.key)).map((r) => ({ value: r.key, label: r.label, count: fnCounts.get(r.key) ?? 0, tags: r.tags })),
        { value: NO_FUNCTION, label: 'No tagged function', count: fnCounts.get(NO_FUNCTION) ?? 0 },
      ]
    : [];
  // "Loading…" until the payload says which functions exist.
  const tagsLoading = fams.isPending || (scope.length > 0 && q.isPending);

  const cartCheck = useFeature('cart_check');
  const checklist = useChecklist();
  const counting = search.count && scope.length > 0;

  // Picking a family you own nothing from while only Owned shows would read as a blank sheet:
  // turn Missing on in the same URL update and say so once (until the next filter change).
  const filterKey = (x: CollectionSearch) => JSON.stringify([x.families, x.show, x.q, x.exclude, x.fn, x.ot, x.em]);
  const [missingNote, setMissingNote] = useState<{ name: string; key: string } | null>(null);
  const pickFamilies = (families: string[]) => {
    const fresh = families.find((c) => !search.families.includes(c) && !allCodes.includes(c));
    const all = allCodes.length > 0 && families.length === allCodes.length && allCodes.every((c) => families.includes(c));
    const patch: Partial<CollectionSearch> = { families: all ? [] : families };
    if (fresh && !search.show.includes('missing')) {
      patch.show = ['owned', 'missing'];
      setMissingNote({ name: famName(fresh), key: filterKey({ ...search, ...patch }) });
    }
    set(patch);
  };

  // Staging copies to add from the cards (grid and list). The draft is read through a ref, so
  // `tally` keeps its identity and a memoized tile re-renders only when its own numbers change.
  const draftRef = useRef(checklist.draft);
  draftRef.current = checklist.draft;
  const byIdRef = useRef(view?.byId);
  byIdRef.current = view?.byId;
  const familyNamesRef = useRef(new Map<string, string>());
  familyNamesRef.current = new Map((q.data?.families ?? []).map((f) => [f.code, f.name]));
  const { add: draftAdd, setToAdd: draftSetToAdd } = checklist;
  const tally = useMemo<Tally>(() => {
    const row = (card: GuideCard) => byIdRef.current?.get(card.key);
    const family = (c: CollectionCardOut) => familyNamesRef.current.get(c.family) ?? c.family.toUpperCase();
    return {
      pending: (card) => ({ nonfoil: pendingOf(draftRef.current, card.key, 'nonfoil'), foil: pendingOf(draftRef.current, card.key, 'foil') }),
      add: (card, finish, n) => {
        const c = row(card);
        if (c) draftAdd(c, finish, n, family(c));
      },
      setPending: (card, finish, n) => {
        const c = row(card);
        if (c) draftSetToAdd(c, finish, n, family(c));
      },
      unitUsd: (card, finish) => {
        const c = row(card);
        return c ? (finish === 'foil' ? (c.price_usd_foil ?? c.price_usd ?? null) : (c.price_usd ?? null)) : null;
      },
    };
  }, [draftAdd, draftSetToAdd]);

  // Review: only the cards the draft touches.
  const [reviewing, setReviewing] = useState(false);
  useEffect(() => {
    if (!checklist.dirty) setReviewing(false);
  }, [checklist.dirty]);
  const sections = useMemo(() => {
    if (!view) return [];
    return reviewing ? onlyDrafted(view.sections, draftedIds(checklist.draft)) : view.sections;
  }, [view, reviewing, checklist.draft]);
  const reviewCount = useMemo(() => (reviewing ? sections.reduce((n, s) => n + s.items.length, 0) : 0), [reviewing, sections]);

  // A family you picked that has no local printings yet is read for you, once per visit.
  const qc = useQueryClient();
  const { live: readLive, start: startRead, reset: resetRead } = useJob();
  const startedReads = useRef(new Set<string>());
  const [reading, setReading] = useState<string | null>(null);
  const [readError, setReadError] = useState<{ family: string; message: string } | null>(null);
  const unread = useMemo(() => (q.data?.families ?? []).filter((f) => f.catalog_read === false), [q.data]);
  useEffect(() => {
    if (reading || readError) return;
    const next = unread.find((f) => !startedReads.current.has(f.code));
    if (!next) return;
    startedReads.current.add(next.code);
    setReading(next.code);
    resetRead();
    void startRead('collection.read_family', { family: next.code }).then((err) => {
      if (err) {
        setReadError({ family: next.code, message: err });
        setReading(null);
      }
    });
  }, [unread, reading, readError, startRead, resetRead]);
  useEffect(() => {
    if (!reading || !readLive) return;
    if (readLive.status === 'succeeded') {
      setReading(null);
      void qc.invalidateQueries({ queryKey: ['collection'] });
    } else if (readLive.status === 'failed') {
      setReadError({ family: reading, message: readLive.error ?? 'The server couldn’t read this family.' });
      setReading(null);
    }
  }, [readLive, reading, qc]);
  const retryRead = () => {
    if (readError) startedReads.current.delete(readError.family);
    setReadError(null);
  };
  const readingName = reading ? (q.data?.families.find((f) => f.code === reading)?.name ?? reading.toUpperCase()) : null;
  const readStatus = readingName ? `Reading ${readingName}${readLive?.log.at(-1)?.msg ? ` · ${readLive.log.at(-1)!.msg}` : ''}` : null;
  const onlyUnread = unread.length > 0 && unread.length === (q.data?.families.length ?? -1);
  const marked = view ? [...selected].map((k) => view.byId.get(k)).filter((c) => c != null) : [];
  const buyPool = marked.length ? marked : (view?.shown.filter((c) => isMissing(c, search.exclude)) ?? []);
  const buyText = (target: BuyStore) => async () => {
    const r = await collectionBuyList({
      body: { target, items: buyPool.map((c) => ({ scryfall_id: c.scryfall_id, finish: buyFinish(c, search.exclude), qty: 1 })) },
    });
    if (r.error || !r.data) throw new Error('buy-list failed');
    return r.data.text;
  };

  const sidebar = (
    <>
      <SideSection title="Find" quiet>
        <TextField name="q" label="Card name" value={search.q} placeholder="e.g. Cloud…" onChange={(qv) => set({ q: qv })} />
      </SideSection>
      <SideSection title="Show" quiet>
        {fams.isError ? (
          <p role="alert" className="text-sm text-danger">Couldn’t load families: {(fams.error as Error).message}</p>
        ) : (
          <MultiSelect
            label="Set families"
            noun="families"
            loading={fams.isPending}
            value={search.families}
            onChange={pickFamilies}
            options={famOptions}
            headerExtra={<Check checked={unowned} onChange={setUnownedFamilies}>Include families you don’t own</Check>}
            emptyExtra={(query) =>
              unowned ? (
                <p>No families match “{query}”.</p>
              ) : (
                <>
                  <p>No family you own matches “{query}”.</p>
                  <Button emphasis="link" onClick={() => setUnownedFamilies(true)}>Search all families</Button>
                </>
              )
            }
          />
        )}
        <SegmentedToggles
          label="Ownership"
          showLabel
          labelExtra={
            <InfoTip label="What does missing mean?">
              {gaps
                ? <>Missing shows only cards you own in <b>no printing</b> from any set — the gaps for deck building.</>
                : <>Missing shows each exact <b>printing</b> you don’t have — what a collector is missing.</>}{' '}
              Change this in Settings → Collection.
            </InfoTip>
          }
          value={search.show}
          onChange={(show) => set({ show: SHOW.filter((s) => show.includes(s)) })}
          options={[
            { value: 'owned', label: 'Owned', count: facetData?.show.owned },
            { value: 'missing', label: 'Missing', count: facetData?.show.missing },
          ]}
        />
        <MultiSelect
          label="Rarity"
          noun="rarities"
          mode="exclude"
          searchable={false}
          keepOrder
          value={included('Rarity')}
          onChange={(v) => set({ exclude: setGroupIncluded(search.exclude, 'Rarity', v) })}
          options={traitOptions('Rarity')}
        />
        <MultiSelect
          label="Finish"
          noun="finishes"
          mode="exclude"
          searchable={false}
          keepOrder
          value={included('Finish')}
          onChange={(v) => set({ exclude: setGroupIncluded(search.exclude, 'Finish', v) })}
          options={traitOptions('Finish')}
        />
        <MultiSelect
          label="Treatment"
          noun="treatments"
          mode="exclude"
          searchable={false}
          keepOrder
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
        <CardTagPicker
          functions={fnOptions}
          loading={tagsLoading}
          value={{ fn: search.fn, ot: search.ot }}
          onChange={({ fn, ot }) => set({ fn, ot })}
        />
        <Segmented
          label="Earmarked"
          showLabel
          labelExtra={<InfoTip label="What is earmarked?">Cards you earmarked to collect or as a deck idea — any printing of the card. Earmark one from its inspector.</InfoTip>}
          value={search.em ? 'only' : 'all'}
          onChange={(v) => set({ em: v === 'only' })}
          options={[{ value: 'all', label: 'All cards' }, { value: 'only', label: 'Only earmarked' }]}
        />
        {filtered && (
          <Button emphasis="link" onClick={() => set(RESET)} className="self-start text-sm">Reset filters</Button>
        )}
      </SideSection>
    </>
  );

  let body;
  if (fams.isSuccess && !allCodes.length) {
    body = (
      <EmptyNote title="No cards in your collection yet">Use Add cards to put your first cards here.</EmptyNote>
    );
  } else if (q.isPending) {
    body = <GridSkeleton label="Loading your collection…" />;
  } else if (q.isError) {
    body = <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  } else if (onlyUnread && readError) {
    body = <ErrorNote error={new Error(`Couldn’t read ${famName(readError.family)}: ${readError.message}`)} onRetry={retryRead} />;
  } else if (onlyUnread && (reading || !readError)) {
    body = <EmptyNote title={readStatus ?? 'Reading this family…'}>Fetching its printings so they can be listed. This takes a moment.</EmptyNote>;
  } else if (!view || view.cards.length === 0) {
    // An exclude picker with every listed option unchecked hides everything — say which.
    const allHidden = (['Rarity', 'Finish', 'Treatment'] as const).find((g) => {
      const listed = traitOptions(g);
      return listed.length > 0 && listed.every((o) => search.exclude.includes(o.value));
    });
    body = allHidden ? (
      <EmptyNote title={`Every ${allHidden.toLowerCase()} is hidden`}>
        <Button tone="paper" onClick={() => set({ exclude: setGroupIncluded(search.exclude, allHidden, traitsIn(allHidden).map((t) => t.key)) })}>
          Check all
        </Button>
      </EmptyNote>
    ) : (
      <EmptyNote title="Nothing matches">No printings match these filters. Check a card type back on, or show both owned and missing cards.</EmptyNote>
    );
  } else if (counting) {
    const familyNames = new Map(q.data.families.map((f) => [f.code, f.name]));
    body = (
      <div className="flex h-full min-h-0 flex-col">
        {!checklist.dirty && !checklist.saved && (
          <p role="status" aria-live="polite" className="mx-sheet py-2 text-sm tabular text-ink-muted">{summaryLine(checklist.summary, null)}</p>
        )}
        <ChecklistNotes checklist={checklist} />
        <ChecklistTable sections={sections} byId={view.byId} familyNames={familyNames} checklist={checklist} />
      </div>
    );
  } else {
    body = <VirtualGuide sections={sections} density={search.view} selected={selected} onToggle={toggle} label="Collection cards" minCardWidth={128} tally={tally} />;
  }

  return (
    <ViewLayout label="Collection controls" summary={controlsSummary(search, allFams.data ?? fams.data)} sidebar={sidebar} subnav={<CollectionTabs />}>
      <GuideSheet
        title="Collection"
        arrange={
          <>
            <SortControl
              keys={collectionSortKeys(hasScenes)}
              rules={rules}
              presets={collectionPresets(hasScenes)}
              defaultRules={activeRules(decodeSort(COLLECTION_SORT_DEFAULT, COLLECTION_SORT), hasScenes)}
              onChange={(r) => set({ sort: encodeSort(r, COLLECTION_SORT) })}
            />
            <ViewToggle value={search.view} onChange={(view) => set({ view })} />
          </>
        }
        actionsLabel="Collection actions"
        buy={
          <>
            <CopyListMenu
              describe={() => `${marked.length ? fmtCount(marked.length, 'marked card') : fmtCount(buyPool.length, 'missing card')} · ≈ ${fmtUsd(buyTotal(buyPool, search.exclude))} at market`}
              targets={buyListTargets(buyText, { exports: true })}
              disabledReason={view && buyPool.length === 0 ? 'Nothing to buy: no missing or marked cards shown' : undefined}
              marked={{ count: marked.length, onClear: clear }}
            />
            {cartCheck && (
              <CartCheckDialog family={search.families.length === 1 ? search.families[0] : undefined} trigger={<IconAction label="Check my cart" Icon={CartCheckMark} />} />
            )}
          </>
        }
        actions={
          <>
            <IconAction
              Icon={CountCardsMark}
              aria-pressed={counting}
              label={counting ? 'Done modifying counts' : checklist.dirty ? `Bulk modify counts · ${fmtInt(checklist.summary.cells)} unsaved` : 'Bulk modify counts'}
              disabled={!scope.length}
              disabledReason="No set families to modify"
              onClick={() => set({ count: !search.count })}
            />
            <AddCardsDialog trigger={<IconAction Icon={AddCardMark} label="Add cards" />} />
          </>
        }
      >
        <div className="flex h-full min-h-0 flex-col">
          {search.ot.length > 0 && (tagCards.isPending || tagCards.isError || missingTags.length > 0) && (
            <p role={tagCards.isError ? 'alert' : 'status'} className={`mx-sheet py-2 text-sm ${tagCards.isError ? 'text-danger' : 'text-ink-muted'}`}>
              {tagCards.isPending
                ? 'Finding the cards with these card tags…'
                : tagCards.isError
                  ? `Couldn’t look up the card tags: ${(tagCards.error as Error).message}`
                  : `No card tag “${missingTags.join('”, “')}” here (the tag may have been renamed, or card tags aren’t loaded) — left out.`}
            </p>
          )}
          {q.data?.skipped?.length ? (
            <p role="status" className="mx-sheet py-2 text-sm text-ink-muted">
              Couldn’t find a set family for {q.data.skipped.map((c) => c.toUpperCase()).join(', ')}: left out.
            </p>
          ) : null}
          {readStatus && !onlyUnread && <p role="status" aria-live="polite" className="mx-sheet py-2 text-sm text-ink-muted">{readStatus}</p>}
          {readError && !onlyUnread && (
            <p role="alert" className="mx-sheet flex flex-wrap items-center gap-x-3 py-2 text-sm text-danger">
              Couldn’t read {famName(readError.family)}: {readError.message}
              <Button tone="paper" emphasis="link" onClick={retryRead}>Retry</Button>
            </p>
          )}
          {missingNote && missingNote.key === filterKey(search) && (
            <p role="status" className="mx-sheet py-2 text-sm text-ink-muted">Showing missing cards — you don’t own any from {missingNote.name} yet.</p>
          )}
          <div className="min-h-0 flex-1">{body}</div>
          {!counting && <ChecklistNotes checklist={checklist} />}
          <PendingBar checklist={checklist} reviewing={reviewing} reviewCount={reviewCount} onReviewing={setReviewing} />
        </div>
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
function buildView(data: CollectionOut, search: CollectionSearch & { gaps: boolean; otIds?: ReadonlySet<string> }, rules: SortRule<CollectionSortKey>[]): Built {
  const shown = filterCollection(data.cards, search);
  const fnLabels = Object.fromEntries((data.functions ?? []).map((r) => [r.key, r.label]));
  const ranks = sceneRanks(data.scenes ?? []);
  const facts = familyFacts(data.families);
  const scenes = new Map((data.scenes ?? []).map((sc) => [sc.key, sc]));
  const cards = sortBy(
    shown.map((c) => ({ ...fromCollection(c, isMissing(c, search.exclude), fnLabels, facts), sceneRank: c.scene ? ranks.get(c.scene) ?? null : null })),
    rules,
    COLLECTION_SORT,
  );
  // Release date is a family fact: it orders the family heads, and the groups
  // inside each family come from the next rule (one year head per family says nothing).
  const byRelease = rules[0]?.key === 'released';
  const groupRules = byRelease ? rules.slice(1) : rules;
  const section = leadSection(groupRules, COLLECTION_SORT);
  const bySet = groupRules[0]?.key === 'set';
  const byScene = groupRules[0]?.key === 'scene';
  const sections: GuideSection[] = [];
  for (const fam of byRelease ? familiesInCardOrder(data.families, cards) : data.families) {
    const famCards = cards.filter((c) => c.group === fam.code);
    if (!famCards.length) continue;
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
        const setCode = bySet ? g.items[0]?.setCode : undefined;
        sections.push({
          ...g,
          key: `${fam.code}:${g.key}`,
          level: 2,
          noun: bySet ? 'set' : 'group',
          detail: setCode && setCode !== g.label ? <span className="truncate text-sm tabular text-ink-muted">{setCode}</span> : undefined,
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
    <span className="pb-0.5 text-xs voice-semi font-medium uppercase tracking-caps-wide text-ink-muted">
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

function controlsSummary(search: CollectionSearch, fams: { code: string; name: string }[] | undefined): string {
  const names = search.families.map((c) => fams?.find((f) => f.code === c)?.name ?? c.toUpperCase());
  const show = search.show.length === 2 ? 'Owned + missing' : search.show[0] === 'owned' ? 'Owned only' : search.show[0] === 'missing' ? 'Missing only' : 'Nothing shown';

  const parts = [
    !names.length ? 'All families' : names.length > 2 ? `${names[0]} +${names.length - 1}` : names.join(', '),
    show,
    search.exclude.length ? typesSummary(search.exclude) : '',
    search.fn.length ? `${search.fn.length} function${search.fn.length > 1 ? 's' : ''}` : '',
  ];
  return parts.filter(Boolean).join(' · ');
}

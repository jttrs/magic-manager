import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { jumpstartQuery, recipesQuery } from '../app/queries';
import { useJob } from '../app/useJob';
import { useMediaQuery } from '../app/useMediaQuery';
import { ViewLayout } from '../components/AppShell';
import { CopyTargets } from '../components/CopyButton';
import { IconAction } from '../components/IconAction';
import { InfoTip } from '../components/InfoTip';
import { MultiSelect } from '../components/MultiSelect';
import { ProgressRule } from '../components/ProgressRule';
import { Segmented, SegmentedToggles, SelectField, SideSection, TextField } from '../components/Sidebar';
import { SplitPanes } from '../components/SplitPanes';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { buyListTargets } from '../components/buyTargets';
import { ImportDeckMark, NewDeckMark, RereadMark } from '../components/StoreMarks';
import { jumpstartBuyList } from '../core/api';
import { COVER_LABEL, DECK_GROUP_LABEL, DECK_GROUPS, filterRecipes, groupRecipes, jumpstartSet, optionCounts, recipeFileName, recipeSummary, unreadInSet, type Cover, type DeckGroupBy, type Ownership } from '../core/decks';
import { fmtCount, fmtInt } from '../core/format';
import { shopLead, type Shop } from '../core/jumpstart';
import { COVER, type DecksSearch } from '../core/search';
import { DeckInspector } from './decks/DeckInspector';
import { ImportDeckDialog } from './decks/ImportDeckDialog';
import { NewDeckDialog } from './decks/NewDeckDialog';
import { RecipeInspector } from './decks/RecipeInspector';
import { refreshRecipes } from './decks/refresh';
import { RecipeList } from './decks/RecipeList';

const route = getRouteApi('/decks');

/** Decks: every deck recipe — catalog precons and Jumpstart packs plus your own decks —
 *  marked by kind and by what you own, on the left; the chosen recipe's cards on the right. */
export function DecksView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/decks' });
  const set = useCallback((patch: Partial<DecksSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true }), [navigate]);
  const qc = useQueryClient();
  const recipes = useQuery(recipesQuery());
  const narrow = useMediaQuery('(max-width: 47.99rem)');

  const all = useMemo(() => recipes.data?.recipes ?? [], [recipes.data]);
  const { q, kinds, own, cover, types, sets } = search;
  const filters = useMemo(() => ({ q, kinds, own, cover, types, sets }), [q, kinds, own, cover, types, sets]);
  const shown = useMemo(() => filterRecipes(all, filters), [all, filters]);
  const counts = useMemo(() => optionCounts(all, filters), [all, filters]);
  const groups = useMemo(() => groupRecipes(shown, search.group), [shown, search.group]);

  // The open recipe: a deck's slug (any copy) or `fn:<fileName>` — a catalog recipe resolves to
  // your deck once you own it, so adding a pack keeps it open.
  const fn = recipeFileName(search.deck);
  const openRow = search.deck ? all.find((r) => r.key === search.deck || r.slugs.includes(search.deck!) || (fn != null && r.file_name === fn)) : undefined;

  // One set in view: read every recipe in it (Jumpstart's "Read again"), and Jumpstart's shopping lists.
  const oneSet = search.sets.length === 1 ? search.sets[0] : null;
  const jsSet = jumpstartSet(all, search);
  const unread = unreadInSet(all, search);
  const { live: readLive, start: startRead, reset: resetRead } = useJob();
  const [startError, setStartError] = useState<string | null>(null);
  const readError = startError ?? (readLive?.status === 'failed' ? (readLive.error ?? 'Reading the recipes failed.') : null);
  const reading = readLive != null && readLive.status !== 'succeeded' && readLive.status !== 'failed';
  const readSet = () => {
    if (!oneSet) return;
    setStartError(null);
    resetRead();
    void startRead('decks.read_recipes', { set: oneSet }).then((err) => err && setStartError(err));
  };
  useEffect(() => {
    if (readLive?.status === 'succeeded') void refreshRecipes(qc);
  }, [readLive?.status, qc]);

  const sidebar = (
    <>
      <SideSection title="Show">
        <TextField name="q" label="Deck, set or author" value={search.q} placeholder="e.g. Counter Blitz, Angels, fic…" onChange={(q) => set({ q })} />
        <SegmentedToggles<Ownership>
          label="You own"
          showLabel
          value={search.own}
          onChange={(own) => set({ own })}
          options={counts.own.map((o) => ({ value: o.value, label: o.label, count: o.count }))}
        />
        <MultiSelect
          label="Kind"
          noun="kinds"
          searchable={false}
          keepOrder
          summary={search.kinds.length ? undefined : 'Every kind'}
          value={search.kinds}
          onChange={(kinds) => set({ kinds: kinds as DecksSearch['kinds'] })}
          options={counts.kinds}
        />
        <MultiSelect
          label="Deck type"
          noun="deck types"
          searchable={false}
          keepOrder
          summary={search.types.length ? undefined : 'All deck types'}
          value={search.types}
          onChange={(types) => set({ types })}
          options={counts.types}
        />
        <MultiSelect
          label="Set"
          noun="sets"
          keepOrder
          placeholder="Find a set…"
          summary={search.sets.length ? undefined : 'Every set'}
          value={search.sets}
          onChange={(sets) => set({ sets })}
          options={counts.sets}
        />
        <SelectField<Cover>
          label="Free cards"
          value={search.cover}
          onChange={(cover) => set({ cover })}
          options={COVER.map((c) => ({ value: c, label: COVER_LABEL[c], count: counts.cover[c] ?? undefined }))}
        />
      </SideSection>
      <SideSection title="Arrange">
        <SelectField<DeckGroupBy> label="Group by" value={search.group} onChange={(group) => set({ group })} options={DECK_GROUPS.map((g) => ({ value: g, label: DECK_GROUP_LABEL[g] }))} />
        <Segmented label="Card view" showLabel value={search.view} onChange={(view) => set({ view })} options={[{ value: 'grid', label: 'Grid' }, { value: 'list', label: 'List' }]} />
      </SideSection>
      {jsSet && <JumpstartBuy code={jsSet} shop={search.shop} onShop={(shop) => set({ shop })} />}
    </>
  );

  let body;
  if (recipes.isPending) body = <GridSkeleton label="Loading deck recipes…" />;
  else if (recipes.isError) body = <ErrorNote error={recipes.error} onRetry={() => recipes.refetch()} />;
  else if (!all.length) body = <EmptyNote title="No deck recipes">MTGJSON lists no precons yet, and you have no decks. Import one from a link or start a new deck.</EmptyNote>;
  else {
    const list = <RecipeList groups={groups} total={shown.length} active={openRow?.key ?? search.deck} onPick={(deck) => set({ deck })} />;
    const back = narrow ? () => set({ deck: undefined }) : undefined;
    const onView = narrow ? (view: 'grid' | 'list') => set({ view }) : undefined;
    const inspector = !search.deck ? (
      <EmptyNote title="Pick a recipe">Choose a deck or pack on the left to see its cards — which you have free, and which you’d still need.</EmptyNote>
    ) : openRow?.slug ? (
      <DeckInspector key={openRow.slug} slug={openRow.slug} recipe={openRow} view={search.view} autoAdd={search.add === true} onAutoAdded={() => set({ add: undefined })} onView={onView} onBack={back} />
    ) : fn ? (
      <RecipeInspector key={fn} fileName={fn} view={search.view} closeShort={recipes.data.close_short ?? 3} onView={onView} onBack={back} />
    ) : (
      <DeckInspector key={search.deck} slug={search.deck} view={search.view} autoAdd={search.add === true} onAutoAdded={() => set({ add: undefined })} onView={onView} onBack={back} />
    );
    body = narrow ? (search.deck ? inspector : list) : <SplitPanes id="mm.decks.split" detailId="deck" label="Resize recipe list" list={list} inspector={inspector} />;
  }

  const summary = reading ? (
    <ProgressRule label={`Reading ${oneSet?.toUpperCase()} recipes`} verb="Reading" done={readLive?.done ?? 0} total={readLive?.total ?? null} message={readLive?.log.at(-1)?.msg} />
  ) : readError ? (
    <span role="alert" className="text-danger">{readError}</span>
  ) : recipes.data ? (
    recipeSummary(shown)
  ) : undefined;

  return (
    <ViewLayout label="Deck controls" summary={`${fmtInt(shown.length)} recipes · grouped by ${DECK_GROUP_LABEL[search.group].toLowerCase()}`} sidebar={sidebar}>
      <GuideSheet
        title="Decks"
        summary={<span role="status" aria-live="polite">{summary}</span>}
        actions={
          <span role="toolbar" aria-label="Deck list actions" className="flex items-center gap-0.5">
            {oneSet && (
              <IconAction
                label={unread ? `Read ${fmtCount(unread, 'unread recipe')} in ${oneSet.toUpperCase()}` : `Read ${oneSet.toUpperCase()} recipes again`}
                Icon={RereadMark}
                onClick={readSet}
                disabled={reading}
                disabledReason="Reading…"
              />
            )}
            <NewDeckDialog trigger={<IconAction label="New deck" Icon={NewDeckMark} />} />
            <ImportDeckDialog trigger={<IconAction label="Import a deck from a link" Icon={ImportDeckMark} />} />
          </span>
        }
      >
        {body}
      </GuideSheet>
    </ViewLayout>
  );
}

/** Jumpstart's two shopping lists for the one set in view. */
function JumpstartBuy({ code, shop, onShop }: { code: string; shop: Shop; onShop: (s: Shop) => void }) {
  const q = useQuery(jumpstartQuery(code));
  const buyText = (target: 'manapool' | 'tcgplayer' | 'cardkingdom') => async () => {
    const r = await jumpstartBuyList({ path: { code }, body: { shop, target } });
    if (r.error || !r.data) throw new Error('buy-list failed');
    return r.data.text;
  };
  return (
    <SideSection title="Buy · Jumpstart">
      <Segmented<Shop>
        label="Shop for"
        showLabel
        labelExtra={
          <InfoTip label="What do the two lists buy?">
            <b>Every theme</b>: the cards you’re missing to keep one built copy of every theme at once, plus each theme’s cards from its other versions — so any version can be assembled. Copies already in built packs count as yours. <b>Packs I don’t own</b>: each pack version you have no copy of, card for card, with its front card.
          </InfoTip>
        }
        value={shop}
        onChange={onShop}
        options={[{ value: 'buildable', label: 'Every theme' }, { value: 'packs', label: 'Packs I don’t own' }]}
      />
      {q.data?.ready ? (
        <CopyTargets lead={shopLead(shop, q.data)} targets={buyListTargets(buyText)} />
      ) : q.data ? (
        <p className="text-sm text-on-chrome-muted">Read the set’s packs first (the read icon above the list).</p>
      ) : q.isError ? (
        <p role="alert" className="text-sm text-danger">Couldn’t load the shopping lists: {(q.error as Error).message}</p>
      ) : (
        <p role="status" className="text-sm text-on-chrome-muted">Loading the shopping lists…</p>
      )}
    </SideSection>
  );
}

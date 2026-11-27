import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { jumpstartQuery, recipesQuery } from '../app/queries';
import { useJob } from '../app/useJob';
import { useMediaQuery } from '../app/useMediaQuery';
import { ViewLayout } from '../components/AppShell';
import type { MarkedCopy } from '../components/CopyMarked';
import { IconAction } from '../components/IconAction';
import { InfoTip } from '../components/InfoTip';
import { MultiSelect } from '../components/MultiSelect';
import { ProgressRule } from '../components/ProgressRule';
import { ChipToggles, SideSection, TextField } from '../components/Sidebar';
import { SplitPanes } from '../components/SplitPanes';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../components/States';
import { buyListTargets, type BuyStore } from '../components/buyTargets';
import { CopyListMenu } from '../components/CopyListMenu';
import { ImportDeckMark, NewDeckMark, RereadMark } from '../components/icons/marks';
import { jumpstartBuyList } from '../core/api';
import { DECK_GROUP_LABEL, DECK_GROUPS, effectiveTypes, filterRecipes, groupRecipes, jumpstartSet, optionCounts, recipeFileName, typesToSearch, unreadInSet, type DeckGroupBy } from '../core/decks';
import { fmtCount, fmtInt } from '../core/format';
import { shopDescribe, type Shop } from '../core/jumpstart';
import { type DecksSearch, type DeckStatus } from '../core/search';
import { useBuildableShort, useDecksSettings } from '../app/deckPrefs';
import { DeckInspector } from './decks/DeckInspector';
import { ImportDeckDialog } from './decks/ImportDeckDialog';
import { NewDeckDialog } from './decks/NewDeckDialog';
import { RecipeInspector } from './decks/RecipeInspector';
import { refreshRecipes } from './decks/refresh';
import { RecipeList } from './decks/RecipeList';
import { GroupControl, ViewToggle } from '../components/ArrangeControls';

const route = getRouteApi('/decks');

/** Decks: every deck recipe — catalog precons and Jumpstart packs plus your own decks —
 *  marked by source and by status, on the left; the chosen recipe's cards on the right. */
export function DecksView() {
  const search = route.useSearch();
  const navigate = useNavigate({ from: '/decks' });
  const set = useCallback((patch: Partial<DecksSearch>) => navigate({ search: (s) => ({ ...s, ...patch }), replace: true }), [navigate]);
  const qc = useQueryClient();
  const recipes = useQuery(recipesQuery());
  const narrow = useMediaQuery('(max-width: 47.99rem)');

  const all = useMemo(() => recipes.data?.recipes ?? [], [recipes.data]);
  const threshold = useBuildableShort();
  useDecksSettings();
  const { q, origins, status, types, sets } = search;
  const filters = useMemo(() => ({ q, origins, status, types, sets }), [q, origins, status, types, sets]);
  const shown = useMemo(() => filterRecipes(all, filters, threshold), [all, filters, threshold]);
  const counts = useMemo(() => optionCounts(all, filters, threshold), [all, filters, threshold]);
  const groups = useMemo(() => groupRecipes(shown, search.group, threshold), [shown, search.group, threshold]);

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
  const [readCode, setReadCode] = useState<string | null>(null);
  // The open inspector's marked cards, copied from the sheet header.
  const [marked, setMarked] = useState<MarkedCopy | null>(null);
  const readError = startError ?? (readLive?.status === 'failed' ? (readLive.error ?? 'Reading the recipes failed.') : null);
  const reading = readLive != null && readLive.status !== 'succeeded' && readLive.status !== 'failed';
  const readSet = () => {
    if (!oneSet) return;
    setStartError(null);
    setReadCode(oneSet);
    resetRead();
    void startRead('decks.read_recipes', { set: oneSet }).then((err) => err && setStartError(err));
  };
  // A running or failed read says so in the sheet (the strip prints no status text).
  const readNotice = reading ? (
    <div role="status" className="mx-sheet py-2">
      <ProgressRule label={`Reading ${readCode?.toUpperCase() ?? ''} recipes`} verb="Reading" done={readLive?.done ?? 0} total={readLive?.total ?? null} message={readLive?.log.at(-1)?.msg} />
    </div>
  ) : readError ? (
    <p role="alert" className="mx-sheet py-2 text-sm text-danger">{readError}</p>
  ) : null;
  useEffect(() => {
    if (readLive?.status === 'succeeded') void refreshRecipes(qc);
  }, [readLive?.status, qc]);

  const sidebar = (
    <>
      <SideSection title="Find" quiet>
        <TextField name="q" label="Deck, set or author" value={search.q} placeholder="e.g. Counter Blitz, Angels, fic…" onChange={(q) => set({ q })} />
      </SideSection>
      <SideSection title="Show" quiet>
        <div className="flex flex-col gap-1.5">
          <span className="flex items-center gap-1 text-sm voice-semi text-on-chrome-muted">
            Decklist status
            <InfoTip label="What do the statuses mean?">
              <b>Built</b>: you have an assembled copy. <b>Buildable</b>: not built, and your unused cards cover it — or leave it at most {fmtCount(threshold, 'card')} short (change that in Settings → Decks). <b>Unbuilt</b>: everything else, including recipes not read yet.
            </InfoTip>
          </span>
          <ChipToggles<DeckStatus>
            label="Decklist status"
            value={search.status}
            onChange={(status) => set({ status })}
            options={counts.status.map((o) => ({ value: o.value as DeckStatus, label: o.label, count: o.count }))}
          />
        </div>
        <MultiSelect
          label="Source"
          noun="sources"
          searchable={false}
          keepOrder
          value={search.origins}
          onChange={(source) => set({ origins: source as DecksSearch['origins'] })}
          options={counts.origins}
        />
        <MultiSelect
          label="Deck type"
          noun="deck types"
          searchable={false}
          keepOrder
          value={effectiveTypes(search) ?? []}
          onChange={(types) => set({ types: typesToSearch(types) })}
          options={counts.types}
        />
        <MultiSelect
          label="Set"
          noun="sets"
          keepOrder
          placeholder="Find a set…"
          value={search.sets}
          onChange={(sets) => set({ sets })}
          options={counts.sets}
        />
      </SideSection>
    </>
  );

  let body;
  if (recipes.isPending) body = <GridSkeleton label="Loading deck recipes…" />;
  else if (recipes.isError) body = <ErrorNote error={recipes.error} onRetry={() => recipes.refetch()} />;
  else if (!all.length) body = <EmptyNote title="No deck recipes">MTGJSON lists no precons yet, and you have no decks. Import one from a link or start a new deck.</EmptyNote>;
  else {
    const list = <RecipeList groups={groups} total={shown.length} active={openRow?.key ?? search.deck} threshold={threshold} onPick={(deck) => set({ deck })} />;
    const back = narrow ? () => set({ deck: undefined }) : undefined;
    const onView = narrow ? (view: 'grid' | 'list') => set({ view }) : undefined;
    const inspector = !search.deck ? (
      <EmptyNote title="Pick a recipe">Choose a deck or pack on the left to see its cards — which you have unused, and which you’d still need.</EmptyNote>
    ) : openRow?.slug ? (
      <DeckInspector key={openRow.slug} slug={openRow.slug} recipe={openRow} threshold={threshold} view={search.view} autoAdd={search.add === true} onAutoAdded={() => set({ add: undefined })} onView={onView} onBack={back} onMarked={setMarked} />
    ) : fn ? (
      <RecipeInspector key={fn} fileName={fn} view={search.view} closeShort={threshold} onView={onView} onBack={back} onMarked={setMarked} />
    ) : (
      <DeckInspector key={search.deck} slug={search.deck} view={search.view} autoAdd={search.add === true} onAutoAdded={() => set({ add: undefined })} onView={onView} onBack={back} onMarked={setMarked} />
    );
    body = narrow ? (search.deck ? inspector : list) : <SplitPanes id="mm.decks.split" detailId="deck" label="Resize recipe list" list={list} inspector={inspector} />;
  }

  return (
    <ViewLayout label="Deck controls" summary={`${fmtInt(shown.length)} recipes`} sidebar={sidebar}>
      <GuideSheet
        title="Decks"
        arrange={
          <>
            <GroupControl<DeckGroupBy> value={search.group} defaultValue="set" onChange={(group) => set({ group })} options={DECK_GROUPS.map((g) => ({ value: g, label: DECK_GROUP_LABEL[g] }))} />
            <ViewToggle value={search.view} onChange={(view) => set({ view })} />
          </>
        }
        buy={jsSet ? <JumpstartBuy code={jsSet} shop={search.shop} onShop={(shop) => set({ shop })} /> : undefined}
        actionsLabel="Deck list actions"
        marked={marked ?? undefined}
        actions={
          <>
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
          </>
        }
      >
        <div className="flex h-full min-h-0 flex-col">
          {readNotice}
          <div className="min-h-0 flex-1">{body}</div>
        </div>
      </GuideSheet>
    </ViewLayout>
  );
}

/** Jumpstart's two shopping lists for the one set in view, as the strip's copy picker. */
function JumpstartBuy({ code, shop, onShop }: { code: string; shop: Shop; onShop: (s: Shop) => void }) {
  const q = useQuery(jumpstartQuery(code));
  const buyText = (target: BuyStore) => async () => {
    const r = await jumpstartBuyList({ path: { code }, body: { shop, target } });
    if (r.error || !r.data) throw new Error('buy-list failed');
    return r.data.text;
  };
  const why = q.data?.ready ? undefined
    : q.data ? 'Read the set’s packs first (the read icon)'
    : q.isError ? `Couldn’t load the shopping lists: ${(q.error as Error).message}`
    : 'Loading the shopping lists…';
  return (
    <CopyListMenu<Shop>
      describe={() => (q.data ? shopDescribe(shop, q.data) : 'the shopping list')}
      targets={buyListTargets(buyText, { exports: true })}
      disabledReason={why}
      option={{ label: 'Shop for', value: shop, onChange: onShop, hint: 'Every theme: the cards you’re missing to keep one built copy of every theme, plus each theme’s other-version cards. Packs I don’t own: each pack version you have no copy of, card for card.', options: [{ value: 'buildable', label: 'Every theme' }, { value: 'packs', label: 'Packs I don’t own' }] }}
    />
  );
}

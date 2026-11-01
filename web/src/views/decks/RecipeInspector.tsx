import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { recipeQuery } from '../../app/queries';
import { useJob } from '../../app/useJob';
import { useSelection } from '../../app/selection';
import { Chevron } from '../../components/Chevron';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { IconAction } from '../../components/IconAction';
import { InfoTip } from '../../components/InfoTip';
import { ProgressRule } from '../../components/ProgressRule';
import { EmptyNote, ErrorNote, GridSkeleton } from '../../components/States';
import { AddCardMark } from '../../components/StoreMarks';
import { VirtualGuide } from '../../components/VirtualGuide';
import { colorLabel, deckGuideGroups, ownershipLabel } from '../../core/decks';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';
import { KindMark } from './RecipeList';
import type { MarkedCopy } from '../../components/CopyMarked';
import { useReportMarked } from './marked';
import { refreshRecipes } from './refresh';

/** A catalog recipe you don't own (precon or Jumpstart pack): reads its card list
 *  the first time (a short job), then its cards against your unused copies. */
export function RecipeInspector({ fileName, view, closeShort, onView, onBack, onMarked }: { fileName: string; view: 'grid' | 'list'; closeShort: number; onView?: (v: 'grid' | 'list') => void; onBack?: () => void; onMarked?: (m: MarkedCopy | null) => void }) {
  const q = useQuery(recipeQuery(fileName));
  const qc = useQueryClient();
  const { selected, toggle, clear } = useSelection(`recipe:${fileName}`);
  const sections = useMemo(() => (q.data?.ready ? deckGuideGroups(q.data.cards, true).map((g) => ({ ...g, level: 2 as const, noun: 'section' })) : []), [q.data]);

  useReportMarked(sections, selected, clear, onMarked);

  // Never read: fetch its card list once. The parent keys this component by fileName.
  const read = useJob();
  const { start: startJob, reset: resetJob } = read;
  const startedRef = useRef(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [rechecked, setRechecked] = useState(false);
  const startRead = useCallback(() => {
    startedRef.current = true;
    setStartError(null);
    setRechecked(false);
    resetJob();
    void startJob('decks.read_recipes', { file_names: [fileName] }).then((err) => {
      if (err) {
        setStartError(err);
        startedRef.current = false;
      }
    });
  }, [fileName, startJob, resetJob]);
  useEffect(() => {
    if (q.data && !q.data.ready && !q.isFetching && !startedRef.current && !startError) startRead();
  }, [q.data, q.isFetching, startError, startRead]);
  useEffect(() => {
    if (read.live?.status === 'succeeded') void refreshRecipes(qc).then(() => setRechecked(true));
  }, [read.live?.status, qc]);
  const readError = startError ?? (read.live?.status === 'failed' ? (read.live.error ?? 'Reading the card list failed.') : rechecked && q.data && !q.data.ready ? 'The card list was read, but some card prices are still missing. Try again.' : null);

  // Add it to your collection (tracked as a deck) — the same job as Add cards → Precon.
  const add = useJob();
  const [confirm, setConfirm] = useState(false);
  const adding = add.live != null && add.live.status !== 'succeeded' && add.live.status !== 'failed';
  useEffect(() => {
    if (add.live?.status === 'succeeded') void refreshRecipes(qc);
  }, [add.live?.status, qc]);
  const addAs = (state: 'built' | 'deconstructed') => async () => {
    const err = await add.start('ingest.precon', { file_name: fileName, copies: 1, state });
    if (err) throw new Error(err);
  };

  if (q.isPending) return <GridSkeleton label="Loading recipe…" />;
  if (q.isError) return <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  const { recipe: r, cards, unknown, ready } = q.data;
  const pack = r.kind === 'jumpstart';

  return (
    <section aria-labelledby="recipe-h" className="flex h-full min-h-0 flex-col">
      <header className="mx-4 flex flex-col gap-2 border-b-2 border-rule-strong pb-2 pt-1">
        {onBack && (
          <button type="button" onClick={onBack} className="inline-flex w-full cursor-pointer items-center gap-0.5 text-sm voice-semi text-accent-ink">
            <Chevron dir="left" className="size-3.5" /> All recipes
          </button>
        )}
        <div className="flex flex-wrap items-end gap-x-4 gap-y-1">
          <div className="min-w-0">
            <h2 id="recipe-h" className="text-2xl voice-condensed font-bold uppercase leading-none text-ink">{r.name}</h2>
            <p className="mt-1 flex flex-wrap items-baseline gap-x-2 text-sm tabular text-ink-muted">
              <KindMark kind={r.kind} />
              <span>
                {[!pack && r.product_type, r.set_name ?? r.set_code?.toUpperCase(), r.released?.slice(0, 4), r.color && colorLabel(r.color), r.cards != null && fmtCount(r.cards, 'card'), r.read && fmtUsd(r.value_usd)].filter(Boolean).join(' · ')}
              </span>
            </p>
          </div>
          <span className="ml-auto flex items-center gap-1 text-sm">
            <IconAction
              label={`Add ${pack ? 'this pack' : 'this deck'} to your collection`}
              Icon={AddCardMark}
              onClick={() => setConfirm(true)}
              disabled={!ready || adding}
              disabledReason={adding ? 'Adding…' : 'Its card list hasn’t been read yet'}
            />
            {onView && (
              <button type="button" onClick={() => onView(view === 'grid' ? 'list' : 'grid')} className="cursor-pointer px-2 text-ink-muted underline hover:text-ink">
                {view === 'grid' ? 'List view' : 'Grid view'}
              </button>
            )}
          </span>
        </div>
        {ready && r.have != null && r.short != null && (
          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm tabular">
            <Fact label="Unused cards cover" value={`${fmtInt(r.have)} of ${fmtInt(r.have + r.short)}`} strong={r.status === 'build'} />
            {r.short > 0 && <Fact label="Short" value={fmtCount(r.short, 'card')} />}
            <Fact label="You own" value={r.ownership === 'none' ? 'No copy' : ownershipLabel(r)} />
            <span className="inline-flex self-center">
              <InfoTip label="What do unused, ready and close mean?" tone="paper">
                <b>Unused</b> cards are copies you own that aren’t in a built deck. A recipe is <b>ready</b> when your unused cards cover all of it and <b>close</b> when it’s {fmtCount(closeShort, 'card')} or fewer short. Each recipe is checked on its own, so two can count the same unused copy.
              </InfoTip>
            </span>
          </dl>
        )}
        {unknown?.length ? <p className="text-xs text-ink-muted">Not in your card data yet: {unknown.join(', ')}. Read its card list again to fetch them.</p> : null}
        <p role="status" aria-live="polite" className="text-sm empty:hidden">
          {adding ? 'Adding it to your collection…' : add.live?.status === 'succeeded' ? (add.live.summary ?? 'Added.') : ''}
        </p>
        {add.live?.status === 'failed' && <p role="alert" className="text-sm text-danger">{add.live.error ?? 'Adding failed.'}</p>}
      </header>
      <div className="min-h-0 flex-1">
        {ready ? (
          cards.length ? (
            <VirtualGuide sections={sections} density={view} selected={selected} onToggle={toggle} label={`${r.name} cards`} minCardWidth={118} />
          ) : (
            <EmptyNote title="No cards">This recipe’s card list is empty.</EmptyNote>
          )
        ) : (
          <div className="mx-auto mt-[12vh] flex max-w-[52ch] flex-col gap-3 px-6">
            {readError ? (
              <ErrorNote error={new Error(readError)} onRetry={startRead} />
            ) : (
              <div role="status" aria-live="polite" className="flex flex-col gap-3">
                <ProgressRule label="Reading the card list" verb="Reading" done={read.live?.done ?? 0} total={read.live?.total ?? null} message={read.live?.log.at(-1)?.msg ?? r.name} />
                <p className="text-sm text-ink-muted">The first time, its card list is fetched from MTGJSON and its card prices filled in. After that it opens at once.</p>
              </div>
            )}
          </div>
        )}
      </div>
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title={`Add ${r.name} to your collection?`}
        confirmLabel="Add and keep it built"
        onConfirm={addAs('built')}
        alternate={{ label: 'Add it broken down', onConfirm: addAs('deconstructed') }}
      >
        <p>
          Adds its {fmtCount(r.cards ?? 0, 'card')} to your collection and tracks one copy as a deck. <b>Built</b> pledges the cards to it; <b>broken down</b> keeps them unused, for other decks.
        </p>
      </ConfirmDialog>
    </section>
  );
}

function Fact({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="text-xs voice-semi uppercase tracking-[0.06em] text-ink-muted">{label}</dt>
      <dd className={strong ? 'voice-semi font-medium text-accent-ink' : 'text-ink'}>{value}</dd>
    </div>
  );
}

import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { deckQuery } from '../../app/queries';
import { useSelection } from '../../app/selection';
import { AddCardsDialog, type AddCardsSeed } from '../../components/addcards/AddCardsDialog';
import { Chevron } from '../../components/Chevron';
import { IconAction } from '../../components/IconAction';
import { InfoTip } from '../../components/InfoTip';
import { ErrorNote, GridSkeleton } from '../../components/States';
import { AddCardMark } from '../../components/StoreMarks';
import { VirtualGuide } from '../../components/VirtualGuide';
import type { RecipeOut } from '../../core/api';
import { coverage, deckGuideGroups, deckReviewLines } from '../../core/decks';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';
import type { MarkedCopy } from '../../components/CopyMarked';
import { DeckActions } from './DeckActions';
import { useReportMarked } from './marked';
import { KindMark } from './RecipeList';

/** A deck you track: its cards with owned / pledged / unused, and its actions. */
export function DeckInspector({ slug, recipe, view, autoAdd = false, onAutoAdded, onView, onBack, onMarked }: { slug: string; recipe?: RecipeOut; view: 'grid' | 'list'; autoAdd?: boolean; onAutoAdded?: () => void; onView?: (v: 'grid' | 'list') => void; onBack?: () => void; onMarked?: (m: MarkedCopy | null) => void }) {
  const q = useQuery(deckQuery(slug));
  const { selected, toggle, clear } = useSelection(`deck:${slug}`);
  const [seed, setSeed] = useState<AddCardsSeed | null>(null);
  const sections = useMemo(() => (q.data ? deckGuideGroups(q.data.cards).map((g) => ({ ...g, level: 2 as const, noun: 'section' })) : []), [q.data]);
  useReportMarked(sections, selected, clear, onMarked);
  useEffect(() => setSeed(null), [slug]);
  // Arrived from "Import a deck" with "I have these cards": open the add review once.
  useEffect(() => {
    if (!autoAdd || !q.data) return;
    setSeed({ name: q.data.deck.name, lines: deckReviewLines(q.data.cards) });
    onAutoAdded?.();
  }, [autoAdd, q.data, onAutoAdded]);

  if (q.isPending) return <GridSkeleton label="Loading deck…" />;
  if (q.isError) return <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  const { deck, cards } = q.data;
  const marked = selected.size;

  return (
    <section aria-labelledby="deck-h" className="flex h-full min-h-0 flex-col">
      <header className="mx-4 flex flex-wrap items-end gap-x-4 gap-y-1 border-b-2 border-rule-strong pb-1.5 pt-1">
        {onBack && (
          <button type="button" onClick={onBack} className="inline-flex w-full cursor-pointer items-center gap-0.5 text-sm voice-semi text-accent-ink">
            <Chevron dir="left" className="size-3.5" /> All recipes
          </button>
        )}
        <div className="min-w-0">
          <h2 id="deck-h" className="text-2xl voice-condensed font-bold uppercase leading-none text-ink">{deck.name}</h2>
          <p className="mt-1 text-sm tabular text-ink-muted">
            {recipe && <span className="mr-2 inline-flex align-[0.1em]"><KindMark kind={recipe.kind} /></span>}
            {[deck.deck_type, deck.set_name ?? deck.set_code?.toUpperCase(), deck.released?.slice(0, 4), deck.source !== deck.deck_type && deck.source, deck.author && `by ${deck.author}`].filter(Boolean).join(' · ')}
            {' · '}
            {fmtCount(deck.cards, 'card')} · {fmtUsd(deck.value_usd)}
            {deck.built > 0 && ` · ×${deck.built} built (${Math.round(deck.pledged_pct)}% pledged)`}
            {recipe && recipe.loose > 0 && ` · ${fmtInt(recipe.loose)} ${recipe.kind === 'import' || recipe.kind === 'custom' ? 'not built' : 'broken down'}`}
            {recipe && coverage(recipe) && ` · ${coverage(recipe)}`}
            <span className="ml-1 inline-flex align-middle">
              <InfoTip label="What do built, pledged and unused mean?" tone="paper">
                <b>Built</b>: you keep this deck assembled; its cards are <b>pledged</b> to it, so they aren’t counted as unused. <b>Unused</b>: copies you own that aren’t in a built deck. Breaking a deck down returns its cards to your collection.
              </InfoTip>
            </span>
          </p>
        </div>
        <span className="ml-auto flex flex-wrap items-center justify-end gap-x-2">
          {marked > 0 && (
            <span className="flex items-center gap-1">
              <IconAction label={`Add ${fmtCount(marked, 'marked card')} to collection`} Icon={AddCardMark} onClick={() => setSeed({ name: deck.name, lines: deckReviewLines(cards, selected) })} />
              <span aria-hidden="true" className="mx-1 h-5 w-px bg-rule" />
            </span>
          )}
          <DeckActions detail={q.data} slug={slug} onAddToCollection={() => setSeed({ name: deck.name, lines: deckReviewLines(cards) })} />
          {onView && (
            <button type="button" onClick={() => onView(view === 'grid' ? 'list' : 'grid')} className="cursor-pointer px-2 text-sm text-ink-muted underline hover:text-ink">
              {view === 'grid' ? 'List view' : 'Grid view'}
            </button>
          )}
        </span>
      </header>
      <div className="min-h-0 flex-1">
        <VirtualGuide sections={sections} density={view} selected={selected} onToggle={toggle} label={`${deck.name} cards`} minCardWidth={118} />
      </div>
      <AddCardsDialog seed={seed} onSeedDone={() => setSeed(null)} />
    </section>
  );
}

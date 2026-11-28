import { useState } from 'react';
import type { GuideCard } from '../core/guideCard';
import { AmountPicker } from './AmountPicker';
import { TallyButton } from './controls/TallyButton';

type Finish = 'nonfoil' | 'foil';

/** What a card list needs to stage copies to add. `pending` is read per card at render
 *  (the list passes the numbers down as primitives); the rest are stable callbacks. */
export type Tally = {
  pending: (card: GuideCard) => Record<Finish, number>;
  /** Stage n more copies (negative takes some back off, never below 0). */
  add: (card: GuideCard, finish: Finish, n: number) => void;
  /** Stage exactly n copies (0 drops the cell from the draft). */
  setPending: (card: GuideCard, finish: Finish, n: number) => void;
  /** Market price of one copy, for the picker's value line. */
  unitUsd?: (card: GuideCard, finish: Finish) => number | null;
};

/** The finishes a card can be tallied in (etched counts as foil; owned copies always count). */
function finishesOf(card: GuideCard): Finish[] {
  const has = (f: Finish) => (card.owned?.[f] ?? 0) > 0 || !card.finishes || card.finishes.includes(f) || (f === 'foil' && card.finishes.includes('etched'));
  return (['nonfoil', 'foil'] as const).filter(has);
}

type Props = { card: GuideCard; tally: Tally; pendingNf: number; pendingFo: number };

/** Add buttons for a card's finishes: click adds one, hold opens the amount picker. */
export function TallyControls({ card, tally, pendingNf, pendingFo }: Props) {
  const [picker, setPicker] = useState<Finish | null>(null);
  const pending: Record<Finish, number> = { nonfoil: pendingNf, foil: pendingFo };
  return (
    <span className="flex min-w-0 flex-wrap items-center gap-1">
      {finishesOf(card).map((f) => {
        const owned = card.owned?.[f] ?? 0;
        return (
          <AmountPicker
            key={f}
            open={picker === f}
            onOpenChange={(o) => setPicker(o ? f : null)}
            finish={f}
            cardName={card.name}
            owned={owned}
            pending={Math.max(0, pending[f])}
            unitUsd={tally.unitUsd?.(card, f)}
            onApply={(n) => tally.setPending(card, f, n)}
            anchor={
              <span className="inline-flex">
                <TallyButton finish={f} owned={owned} pending={pending[f]} cardName={card.name} onAdd={(n) => tally.add(card, f, n)} onHold={() => setPicker(f)} />
              </span>
            }
          />
        );
      })}
    </span>
  );
}

import { memo } from 'react';
import type { GuideCard } from '../core/guideCard';
import { CardArt, GuideLine, Holdings, InclusionBars, Tags } from './CardFace';
import { GuideNote } from './CardMeta';
import { MarkToggle } from './MarkToggle';

type Props = {
  card: GuideCard;
  selected: boolean;
  onToggle: (key: string) => void;
  onInspect?: (card: GuideCard) => void;
  barLabels?: [string, string];
};

/** Grid view: card art + guide caption. Pressing the art inspects the card; the
 *  caption's list toggle adds it to the marked list (nothing ever sits on the art). */
export const CardTile = memo(function CardTile({ card, selected, onToggle, onInspect, barLabels = ['A', 'B'] }: Props) {
  return (
    <article className="flex min-w-0 flex-col gap-1">
      <button
        type="button"
        aria-label={onInspect ? `Inspect ${card.name}` : `${selected ? 'Unmark' : 'Mark'} ${card.name}`}
        aria-pressed={onInspect ? undefined : selected}
        onClick={() => (onInspect ? onInspect(card) : onToggle(card.key))}
        className="block w-full cursor-pointer rounded-[4.5%/3.2%] transition-transform ease-guide hover:-translate-y-0.5 focus-visible:-translate-y-0.5"
      >
        <CardArt
          card={card}
          className={`${selected ? 'ring-2 ring-highlight-solid ring-offset-2 ring-offset-paper' : ''} ${card.missing ? 'opacity-55 grayscale-[0.7]' : ''}`}
        />
      </button>
      <div className={`flex flex-col gap-0.5 rounded-xs px-0.5 ${selected ? 'highlighter' : ''}`}>
        <span className="truncate text-xs voice-semi font-medium text-ink" title={card.name}>{card.name}</span>
        <GuideLine card={card} />
        {card.note && <GuideNote note={card.note} />}
        {/* Holdings share a line with the list toggle so the name keeps the full width. */}
        {(card.owned || onInspect) && (
          <span className="-my-1 flex min-h-7 items-center gap-1">
            <span className="min-w-0 flex-1">{card.owned && <Holdings card={card} />}</span>
            {onInspect && <MarkToggle name={card.name} marked={selected} onToggle={() => onToggle(card.key)} size="sm" />}
          </span>
        )}
        <Tags tags={card.tags} />
        {card.bars && <InclusionBars a={card.bars.a} b={card.bars.b} labelA={barLabels[0]} labelB={barLabels[1]} />}
      </div>
    </article>
  );
});

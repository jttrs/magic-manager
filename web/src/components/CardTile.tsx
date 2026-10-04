import { HoverCard } from 'radix-ui';
import { memo } from 'react';
import type { GuideCard } from '../core/guideCard';
import { CardArt, GuideLine, Holdings, InclusionBars, Tags } from './CardFace';
import { CardPreview, GuideNote } from './CardMeta';

type Props = {
  card: GuideCard;
  selected: boolean;
  onToggle: (key: string) => void;
  barLabels?: [string, string];
};

/** Grid density: card art + guide caption. Pressing the card marks it with the highlighter. */
export const CardTile = memo(function CardTile({ card, selected, onToggle, barLabels = ['A', 'B'] }: Props) {
  return (
    <article className="group flex min-w-0 flex-col gap-1">
      <div className="relative">
        <button
          type="button"
          aria-pressed={selected}
          aria-label={`${selected ? 'Unmark' : 'Mark'} ${card.name}`}
          onClick={() => onToggle(card.key)}
          className="block w-full cursor-pointer rounded-[4.5%/3.2%] transition-transform ease-guide hover:-translate-y-0.5 focus-visible:-translate-y-0.5"
        >
          <CardArt
            card={card}
            className={`${selected ? 'ring-2 ring-highlight-solid ring-offset-2 ring-offset-paper' : ''} ${card.missing ? 'opacity-55 grayscale-[0.7]' : ''}`}
          />
        </button>
      </div>
      <div className={`flex flex-col gap-0.5 rounded-xs px-0.5 ${selected ? 'highlighter' : ''}`}>
        <span className="flex items-baseline gap-1">
          <HoverCard.Root openDelay={300} closeDelay={80}>
            <HoverCard.Trigger asChild>
              {card.href ? (
                <a href={card.href} target="_blank" rel="noreferrer" className="min-w-0 truncate text-xs voice-semi font-medium text-ink no-underline hover:underline">
                  {card.name}
                </a>
              ) : (
                <span className="min-w-0 truncate text-xs voice-semi font-medium text-ink">{card.name}</span>
              )}
            </HoverCard.Trigger>
            <HoverCard.Portal>
              <HoverCard.Content side="right" align="start" sideOffset={10} collisionPadding={16} className="z-40 w-64 drop-shadow-[0_10px_24px_var(--theme-scrim)]">
                <CardPreview card={card} />
              </HoverCard.Content>
            </HoverCard.Portal>
          </HoverCard.Root>
        </span>
        <GuideLine card={card} />
        {card.note && <GuideNote note={card.note} />}
        {card.owned && <Holdings card={card} />}
        <Tags tags={card.tags} />
        {card.bars && <InclusionBars a={card.bars.a} b={card.bars.b} labelA={barLabels[0]} labelB={barLabels[1]} />}
      </div>
    </article>
  );
});

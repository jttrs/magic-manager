import { HoverCard } from 'radix-ui';
import { memo } from 'react';
import type { GuideCard } from '../core/guideCard';
import { CardArt, GuideLine, Holdings, InclusionBars, Tags } from './CardFace';
import { CardPreview, GuideNote } from './CardMeta';
import { MagnifierMark } from './StoreMarks';

type Props = {
  card: GuideCard;
  selected: boolean;
  onToggle: (key: string) => void;
  onInspect?: (card: GuideCard) => void;
  barLabels?: [string, string];
};

/** Grid view: card art + guide caption. Pressing the card marks it with the highlighter. */
export const CardTile = memo(function CardTile({ card, selected, onToggle, onInspect, barLabels = ['A', 'B'] }: Props) {
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
        {onInspect && (
          // Hover/focus affordance over the art's corner (always shown on touch); the rest of the card still marks.
          <button
            type="button"
            onClick={() => onInspect(card)}
            aria-label={`Inspect ${card.name}`}
            title="Inspect card"
            className="absolute right-1.5 top-1.5 grid size-8 cursor-pointer place-items-center rounded-pill bg-chrome/80 text-accent opacity-0 shadow-[0_2px_8px_-2px_var(--theme-scrim)] backdrop-blur-[2px] transition-[opacity,transform] duration-200 ease-guide hover:scale-110 focus-visible:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100"
          >
            <MagnifierMark className="size-[1.1rem]" />
          </button>
        )}
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

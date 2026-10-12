import { HoverCard } from 'radix-ui';
import type { ReactElement } from 'react';
import type { GuideCard } from '../core/guideCard';
import { CardPreview } from './CardMeta';

/** Hover preview of a card's art beside the hovered NAME — not beside the whole
 *  row — so it opens next to the pointer, past the name and over the row's
 *  right-hand cells, never over the name or the art thumbnail you're pointing
 *  at. Flips to the left near the viewport edge. The trigger must hug its text
 *  (inline / `w-fit`), or the preview drifts to the row's far end. */
export function CardHover({ card, children }: { card: GuideCard; children: ReactElement }) {
  return (
    <HoverCard.Root openDelay={250} closeDelay={80}>
      <HoverCard.Trigger asChild>{children}</HoverCard.Trigger>
      <HoverCard.Portal>
        <HoverCard.Content side="right" align="start" alignOffset={-24} sideOffset={10} collisionPadding={12} className="z-40 w-56 drop-shadow-[0_10px_24px_var(--theme-scrim)]">
          <CardPreview card={card} />
        </HoverCard.Content>
      </HoverCard.Portal>
    </HoverCard.Root>
  );
}

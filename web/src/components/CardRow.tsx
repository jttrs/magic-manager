import { HoverCard } from 'radix-ui';
import { memo } from 'react';
import type { GuideCard } from '../core/guideCard';
import { rarityLetter } from '../core/guideCard';
import { fmtPct, fmtUsd } from '../core/format';
import { CardArt, InclusionBars, Stamps } from './CardFace';
import { CardPreview } from './CardMeta';

type Props = { card: GuideCard; selected: boolean; onToggle: (key: string) => void; barLabels?: [string, string] };

/** Rows density: one ruled checklist line per card; hovering/focusing the name previews the art. */
export const CardRow = memo(function CardRow({ card, selected, onToggle, barLabels = ['A', 'B'] }: Props) {
  return (
    <div className={`grid min-h-[var(--size-row-h)] grid-cols-[1rem_minmax(4rem,1fr)_auto_auto] @[18rem]:grid-cols-[1rem_var(--size-thumb)_minmax(5.5rem,1fr)_auto_auto] items-center gap-2 ruled px-1 ${selected ? 'highlighter' : ''}`}>
      <input
        type="checkbox"
        checked={selected}
        onChange={() => onToggle(card.key)}
        aria-label={`Mark ${card.name}`}
        className="h-3.5 w-3.5 cursor-pointer accent-[var(--theme-accent)]"
      />
      <span className="hidden h-[var(--size-thumb)] w-[var(--size-thumb)] overflow-hidden rounded-xs @[18rem]:block">
        <CardArt card={card} crop />
      </span>
      <HoverCard.Root openDelay={250} closeDelay={80}>
        <HoverCard.Trigger asChild>
          <a
            href={card.href ?? undefined}
            target="_blank"
            rel="noreferrer"
            className="flex min-w-0 items-baseline gap-2 text-sm text-ink no-underline hover:underline"
          >
            <span className="truncate voice-semi">{card.name}</span>
            <span className="hidden shrink-0 text-2xs tabular text-ink-muted @[30rem]:inline" translate="no">
              {[card.setCode, card.cn, rarityLetter(card.rarity)].filter(Boolean).join(' · ')}
              {card.finish === 'foil' ? ' ✦' : ''}
            </span>
            {card.note && <span className="hidden min-w-0 truncate text-2xs text-ink-muted @[24rem]:inline">{card.note}</span>}
          </a>
        </HoverCard.Trigger>
        <HoverCard.Portal>
          <HoverCard.Content side="right" align="center" sideOffset={12} collisionPadding={16} className="z-40 w-56 drop-shadow-[0_10px_24px_var(--theme-scrim)]">
            <CardPreview card={card} />
          </HoverCard.Content>
        </HoverCard.Portal>
      </HoverCard.Root>
      <span className="flex items-center justify-end gap-2">
        {card.bars ? (
          <>
            <span className="hidden w-20 @[22rem]:block @[30rem]:w-32"><InclusionBars a={card.bars.a} b={card.bars.b} labelA={barLabels[0]} labelB={barLabels[1]} compact /></span>
            <span className="flex w-8 flex-col text-right text-2xs tabular leading-tight @[22rem]:hidden" aria-label={`${barLabels[0]} ${fmtPct(card.bars.a)}, ${barLabels[1]} ${fmtPct(card.bars.b)}`}>
              <span className="text-ink">{fmtPct(card.bars.a)}</span>
              <span className="text-ink-muted">{fmtPct(card.bars.b)}</span>
            </span>
          </>
        ) : card.pct != null ? (
          <span className="flex items-center gap-1.5">
            <span className="relative hidden h-[3px] w-12 overflow-hidden rounded-pill bg-rule @[22rem]:block @[30rem]:w-24">
              <span className="absolute inset-y-0 left-0 rounded-pill bg-rule-strong" style={{ width: `${Math.min(100, card.pct)}%` }} />
            </span>
            <span className="w-8 text-right text-2xs tabular text-ink">{fmtPct(card.pct)}</span>
          </span>
        ) : (
          <Stamps stamps={card.stamps} />
        )}
      </span>
      <span className="w-12 text-right text-sm tabular voice-semi font-medium text-ink @[22rem]:w-14">{fmtUsd(card.price)}</span>
    </div>
  );
});

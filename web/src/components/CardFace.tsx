import type { GuideCard } from '../core/guideCard';
import { rarityLetter } from '../core/guideCard';
import { fmtPct, fmtUsd } from '../core/format';

const IMG_W = 488;
const IMG_H = 680;

/** Card art at the guide's fixed 488×680 aspect; a ruled placeholder when Scryfall has no image. */
/** Scryfall serves the same card at /normal/ and as an art-only crop at /art_crop/. */
const artCrop = (url: string) => url.replace('/normal/', '/art_crop/');

export function CardArt({ card, className = '', eager = false, crop = false }: { card: GuideCard; className?: string; eager?: boolean; crop?: boolean }) {
  if (!card.image) {
    return (
      <div className={`grid aspect-[488/680] place-items-center rounded-sm border border-rule bg-paper-sunk p-2 text-center text-xs text-ink-muted ${className}`}>
        {card.name}
      </div>
    );
  }
  if (crop) {
    return (
      <img src={artCrop(card.image)} alt="" width={626} height={457} loading="lazy" decoding="async" draggable={false}
        className={`aspect-square h-auto w-full object-cover ${className}`} />
    );
  }
  return (
    <img
      src={card.image}
      alt={card.name}
      width={IMG_W}
      height={IMG_H}
      loading={eager ? 'eager' : 'lazy'}
      decoding="async"
      draggable={false}
      className={`aspect-[488/680] h-auto w-full rounded-[4.5%/3.2%] bg-paper-sunk ${className}`}
    />
  );
}

/** The guide line: CN · SET · rarity · finish … metric · price, in tabular figures. */
export function GuideLine({ card }: { card: GuideCard }) {
  const ident = [card.cn, card.setCode, rarityLetter(card.rarity)].filter(Boolean).join(' · ');
  return (
    <span className="flex min-w-0 items-baseline gap-1.5 text-2xs tabular leading-tight">
      <span className="min-w-0 truncate text-ink-muted" translate="no">{ident}</span>
      {card.finish === 'foil' && <span className="text-accent-ink voice-semi" aria-label="foil">✦</span>}
      <span className="ml-auto flex shrink-0 items-baseline gap-1.5">
        {card.pct != null && !card.bars && <span className="text-ink">{fmtPct(card.pct)}</span>}
        <span className="text-ink voice-semi font-medium">{fmtUsd(card.price)}</span>
      </span>
    </span>
  );
}

/** Two stacked inclusion bars (A over B) for shared cards. */
export function InclusionBars({ a, b, labelA, labelB, compact = false }: { a: number | null; b: number | null; labelA: string; labelB: string; compact?: boolean }) {
  const bar = (v: number | null, label: string, strong: boolean) => (
    <span className="flex items-center gap-1.5" title={`${label}: ${fmtPct(v)}`}>
      <span className={`relative h-[3px] flex-1 overflow-hidden rounded-pill bg-rule ${compact ? 'min-w-10' : ''}`}>
        <span
          className={`absolute inset-y-0 left-0 rounded-pill ${strong ? 'bg-rule-strong' : 'bg-ink-muted'}`}
          style={{ width: `${Math.max(0, Math.min(100, v ?? 0))}%` }}
        />
      </span>
      <span className="w-8 text-right text-2xs tabular text-ink">{fmtPct(v)}</span>
    </span>
  );
  return (
    <span className="flex flex-col gap-0.5" aria-label={`${labelA} ${fmtPct(a)}, ${labelB} ${fmtPct(b)}`}>
      {bar(a, labelA, true)}
      {bar(b, labelB, false)}
    </span>
  );
}

export function Stamps({ stamps }: { stamps: string[] }) {
  if (!stamps.length) return null;
  const names: Record<string, string> = { P: 'printing', F: 'functional', V: 'variant-chase' };
  return (
    <span className="flex gap-0.5" aria-label={`pools: ${stamps.map((s) => names[s] ?? s).join(', ')}`}>
      {stamps.map((s) => (
        <span key={s} className="grid h-4 w-4 place-items-center rounded-xs border border-rule-strong bg-paper-raised text-2xs voice-condensed font-bold leading-none text-ink">
          {s}
        </span>
      ))}
    </span>
  );
}

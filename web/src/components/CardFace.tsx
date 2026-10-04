import type { GuideCard } from '../core/guideCard';
import { rarityLetter } from '../core/guideCard';
import { fmtPct, fmtUsd } from '../core/format';

const IMG_W = 488;
const IMG_H = 680;

/** Card art at the guide's fixed 488×680 aspect; a ruled placeholder when Scryfall has no image. */
/** Scryfall serves the same card at /normal/ and as an art-only crop at /art_crop/. */
const artCrop = (url: string) => url.replace('/normal/', '/art_crop/');

// Card images already decoded this session. The guide is virtualized, so a tile
// scrolled back into view is a fresh <img>; for a seen URL we skip lazy/async so
// the browser paints it from its memory cache in the same frame (no blank flash).
const seen = new Set<string>();

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
      loading={eager || seen.has(card.image) ? 'eager' : 'lazy'}
      decoding={seen.has(card.image) ? 'sync' : 'async'}
      onLoad={() => seen.add(card.image!)}
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

/** Owned copies per finish (×N plain, ✦×N foil) or the missing mark — printed
 *  in the guide line, never over the art. */
export function Holdings({ card }: { card: GuideCard }) {
  if (!card.owned) return null;
  const nf = card.owned.nonfoil ?? 0;
  const fo = card.owned.foil ?? 0;
  const label = [nf ? `${nf} nonfoil` : '', fo ? `${fo} foil` : ''].filter(Boolean).join(', ');
  return (
    <span className="flex shrink-0 items-baseline gap-1.5 text-2xs tabular" aria-label={card.missing && !label ? 'Missing' : `Owned: ${label || 'none'}${card.missing ? ' (missing in this finish)' : ''}`}>
      {nf > 0 && <span className="font-bold text-ink">×{nf}</span>}
      {fo > 0 && <span className="font-bold text-accent-ink">✦×{fo}</span>}
      {card.missing && <span className="voice-condensed font-bold uppercase tracking-[0.06em] text-danger">Missing</span>}
    </span>
  );
}

/** Small facts (Chase, Borderless…) as ruled text tags under the name. */
export function Tags({ tags }: { tags: string[] }) {
  if (!tags.length) return null;
  return (
    <span className="block min-w-0 truncate text-2xs voice-semi uppercase tracking-[0.04em] text-ink-muted" title={tags.join(' · ')}>
      {tags.map((t, i) => (
        <span key={t} className={t === 'Chase' ? 'font-bold text-accent-ink' : ''}>{i ? ' · ' : ''}{t}</span>
      ))}
    </span>
  );
}

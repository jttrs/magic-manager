import type { GuideCard } from '../core/guideCard';
import { CardArt } from './CardFace';

/** Hover preview: card art, then (never over the art) its Tagger functions + top tags. */
export function CardPreview({ card }: { card: GuideCard }) {
  const fns = card.functions ?? [];
  const tags = card.tags ?? [];
  return (
    <div className="flex flex-col gap-1.5">
      <CardArt card={card} eager />
      {(fns.length > 0 || tags.length > 0) && (
        <div className="flex flex-col gap-1.5 rounded-sm border border-rule bg-paper-raised px-2.5 py-2 text-ink">
          {fns.length > 0 && (
            <p className="flex flex-col gap-0.5">
              <span className="text-2xs voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">Functions</span>
              <span className="text-sm voice-semi font-medium leading-snug">{fns.join(' · ')}</span>
            </p>
          )}
          {tags.length > 0 && (
            <ul aria-label="Scryfall tags" className="flex flex-wrap gap-1">
              {tags.map((t) => (
                <li key={t} className="rounded-xs border border-rule px-1 py-px text-2xs leading-tight text-ink-muted">{t}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

/** A short guide-line annotation under the caption (e.g. "also: Removal"). */
export function GuideNote({ note }: { note: string }) {
  return <span className="min-w-0 truncate text-2xs leading-tight text-ink-muted" title={note}>{note}</span>;
}

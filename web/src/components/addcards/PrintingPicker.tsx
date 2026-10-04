import { Popover } from 'radix-ui';
import type { PrintingOut } from '../../core/api';
import { fmtUsd } from '../../core/format';
import { rarityLetter, treatmentLabels } from '../../core/guideCard';
import { Chevron } from '../Chevron';

const crop = (url: string) => url.replace('/normal/', '/art_crop/');

/** "BLB · 1 · R · Borderless" — the printing's identity in guide-line order. */
export function printingLabel(p: PrintingOut): string {
  const treat = treatmentLabels(p.treatment).join(', ');
  return [p.set_code.toUpperCase(), p.collector_number, rarityLetter(p.rarity), treat].filter(Boolean).join(' · ');
}

export function ownedLabel(p: PrintingOut): string {
  const nf = p.owned?.nonfoil ?? 0;
  const fo = p.owned?.foil ?? 0;
  if (!nf && !fo) return '';
  return [nf ? `×${nf}` : '', fo ? `✦×${fo}` : ''].filter(Boolean).join(' ');
}

/** Small art crop for list rows; a ruled blank when there's no image. */
export function PrintingThumb({ p, className = 'size-9' }: { p?: PrintingOut; className?: string }) {
  if (!p?.image_uri) return <span aria-hidden className={`block shrink-0 rounded-xs border border-rule bg-paper-sunk ${className}`} />;
  return <img src={crop(p.image_uri)} alt="" loading="lazy" decoding="async" className={`shrink-0 rounded-xs object-cover ${className}`} />;
}

/** Choose one printing of a name: a trigger naming the pick, a popover grid of every candidate. */
export function PrintingPicker({ name, candidates, value, onChange }: { name: string; candidates: PrintingOut[]; value: string | null; onChange: (id: string) => void }) {
  const cur = candidates.find((c) => c.scryfall_id === value);
  if (candidates.length <= 1) {
    return <span className="truncate text-sm tabular text-ink-muted">{cur ? printingLabel(cur) : '—'}</span>;
  }
  return (
    <Popover.Root>
      <Popover.Trigger
        aria-label={`Printing of ${name}: ${cur ? printingLabel(cur) : 'none'}. ${candidates.length} printings`}
        className="flex min-h-8 min-w-0 max-w-full cursor-pointer items-center gap-1.5 rounded-sm border border-rule px-2 text-left text-sm tabular text-ink transition-colors ease-guide hover:border-rule-strong hover:bg-paper-sunk data-[state=open]:border-accent"
      >
        <span className="min-w-0 truncate">{cur ? printingLabel(cur) : 'Choose a printing'}</span>
        <span className="shrink-0 text-xs text-ink-muted">{candidates.length}</span>
        <Chevron className="size-3.5 shrink-0 text-ink-muted" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={4}
          collisionPadding={12}
          aria-label={`Printings of ${name}`}
          className="z-[60] max-h-[min(30rem,70dvh)] w-[min(40rem,calc(100vw-1.5rem))] overflow-y-auto rounded-sm border border-rule-strong bg-paper-raised p-2 pr-3 [scrollbar-gutter:stable] text-ink shadow-[0_14px_32px_-14px_var(--theme-scrim)]"
        >
          <ul aria-label={`Printings of ${name}`} className="grid grid-cols-[repeat(auto-fill,minmax(7.5rem,1fr))] gap-2">
            {candidates.map((c) => {
              const on = c.scryfall_id === value;
              return (
                <li key={c.scryfall_id}>
                  <Popover.Close asChild>
                    <button
                      type="button"
                      onClick={() => onChange(c.scryfall_id)}
                      aria-pressed={on}
                      aria-label={`${printingLabel(c)}, ${fmtUsd(c.price_usd ?? c.price_usd_foil)}${ownedLabel(c) ? `, own ${ownedLabel(c)}` : ''}`}
                      className={`flex w-full cursor-pointer flex-col gap-1 rounded-sm p-1 text-left transition-colors ease-guide hover:bg-paper-sunk ${on ? 'outline-2 outline-accent' : ''}`}
                    >
                      {c.image_uri ? (
                        <img src={c.image_uri} alt="" loading="lazy" decoding="async" className="aspect-[488/680] w-full rounded-[4.5%/3.2%] bg-paper-sunk" />
                      ) : (
                        <span className="grid aspect-[488/680] w-full place-items-center rounded-sm bg-paper-sunk text-2xs text-ink-muted">{c.name}</span>
                      )}
                      <span className="truncate text-2xs tabular text-ink">{printingLabel(c)}</span>
                      <span className="flex gap-2 text-2xs tabular text-ink-muted">
                        <span>{fmtUsd(c.price_usd ?? c.price_usd_foil)}</span>
                        <span className="ml-auto text-accent-ink">{ownedLabel(c)}</span>
                      </span>
                    </button>
                  </Popover.Close>
                </li>
              );
            })}
          </ul>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

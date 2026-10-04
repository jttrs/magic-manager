import { Dialog } from 'radix-ui';
import { fmtUsd } from '../core/format';
import { rarityLetter, type GuideCard } from '../core/guideCard';
import type { ComponentType, SVGProps } from 'react';
import { Holdings, Tags } from './CardFace';
import { ScryfallMark, TcgplayerMark } from './StoreMarks';

const RARITY_NAME: Record<string, string> = { common: 'Common', uncommon: 'Uncommon', rare: 'Rare', mythic: 'Mythic', special: 'Special', bonus: 'Bonus' };

const large = (url: string) => url.replace('/normal/', '/large/');
const tcgplayerSearch = (name: string) =>
  `https://www.tcgplayer.com/search/magic/product?productLineName=magic&q=${encodeURIComponent(name.split(' // ')[0])}`;

/** Inspect one card: large art, then its facts and outbound links — never over the art. */
export function CardInspector({ card, onClose }: { card: GuideCard | null; onClose: () => void }) {
  return (
    <Dialog.Root open={card != null} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        {card && (
          <Dialog.Content className="paper-grain fixed left-1/2 top-1/2 z-50 flex max-h-[94dvh] w-[min(52rem,calc(100vw-1rem))] -translate-x-1/2 -translate-y-1/2 flex-col gap-5 overflow-y-auto rounded-sm bg-paper p-5 text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none sm:flex-row">
            <div className="mx-auto w-full max-w-[22rem] shrink-0 sm:mx-0 sm:w-[min(22rem,45%)]">
              {card.image ? (
                <img src={large(card.image)} alt={card.name} width={672} height={936} className="aspect-[488/680] h-auto w-full rounded-[4.5%/3.2%] bg-paper-sunk shadow-[0_10px_28px_-14px_var(--theme-scrim)]" />
              ) : (
                <div className="grid aspect-[488/680] w-full place-items-center rounded-sm border border-rule bg-paper-sunk p-4 text-center text-sm text-ink-muted">{card.name}</div>
              )}
            </div>
            <div className="flex min-w-0 flex-1 flex-col gap-4">
              <div className="flex items-start gap-3 border-b-2 border-rule-strong pb-2">
                <div className="min-w-0">
                  <Dialog.Title className="text-3xl voice-condensed font-bold leading-none">{card.name}</Dialog.Title>
                  <Dialog.Description className="mt-1.5 text-sm text-ink-muted">{card.typeLine ?? card.typeGroup}</Dialog.Description>
                </div>
                <Dialog.Close aria-label="Close" className="ml-auto grid size-8 shrink-0 cursor-pointer place-items-center rounded-sm text-xl text-ink-muted hover:bg-paper-sunk hover:text-ink">×</Dialog.Close>
              </div>

              <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-1.5 text-sm">
                {card.setCode && (
                  <>
                    <dt className="text-ink-muted">Printing</dt>
                    <dd className="tabular">{[card.setCode, card.cn && `#${card.cn}`, card.rarity && (RARITY_NAME[card.rarity] ?? rarityLetter(card.rarity))].filter(Boolean).join(' · ')}</dd>
                  </>
                )}
                {card.cmc != null && (
                  <>
                    <dt className="text-ink-muted">Mana value</dt>
                    <dd className="tabular">{card.cmc}</dd>
                  </>
                )}
                <dt className="text-ink-muted">Price</dt>
                <dd className="flex gap-4 tabular">
                  {card.prices ? (
                    <>
                      {card.prices.nonfoil != null && <span>{fmtUsd(card.prices.nonfoil)} <span className="text-ink-muted">nonfoil</span></span>}
                      {card.prices.foil != null && <span>{fmtUsd(card.prices.foil)} <span className="text-ink-muted">✦ foil</span></span>}
                      {card.prices.nonfoil == null && card.prices.foil == null && '—'}
                    </>
                  ) : (
                    fmtUsd(card.price)
                  )}
                </dd>
                {card.owned && (
                  <>
                    <dt className="text-ink-muted">Owned</dt>
                    <dd><Holdings card={card} /></dd>
                  </>
                )}
                {card.functions && card.functions.length > 0 && (
                  <>
                    <dt className="text-ink-muted">Functions</dt>
                    <dd>{card.functions.join(' · ')}</dd>
                  </>
                )}
              </dl>

              {card.tags.length > 0 && <Tags tags={card.tags} />}
              {card.oracleTags && card.oracleTags.length > 0 && (
                <ul aria-label="Scryfall tags" className="flex flex-wrap gap-1">
                  {card.oracleTags.map((t) => (
                    <li key={t} className="rounded-xs border border-rule px-1.5 py-0.5 text-xs text-ink-muted">{t}</li>
                  ))}
                </ul>
              )}

              <div className="mt-auto flex flex-wrap gap-2 pt-2">
                {card.href && <OutLink href={card.href} label="Scryfall" Mark={ScryfallMark} />}
                <OutLink href={tcgplayerSearch(card.name)} label="TCGplayer" Mark={TcgplayerMark} />
              </div>
            </div>
          </Dialog.Content>
        )}
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** A link to another site: that site's monochrome mark + its name (the mark replaces a generic ↗). */
function OutLink({ href, label, Mark }: { href: string; label: string; Mark: ComponentType<SVGProps<SVGSVGElement>> }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      title={`Open on ${label}`}
      className="group inline-flex min-h-9 items-center gap-2 rounded-pill border border-rule-strong bg-paper-raised pl-2.5 pr-3.5 text-sm voice-condensed font-bold uppercase tracking-[0.06em] text-ink no-underline transition-colors ease-guide hover:border-accent hover:bg-paper-sunk"
    >
      <Mark className="size-[1.15rem] text-accent-ink transition-transform duration-300 ease-guide group-hover:-translate-y-px" />
      {label}
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  );
}

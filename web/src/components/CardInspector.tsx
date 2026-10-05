import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { Dialog } from 'radix-ui';
import { holdingsQuery } from '../app/queries';
import type { HoldingsOut } from '../core/api';
import { fmtInt, fmtUsd } from '../core/format';
import { rarityLetter, type GuideCard } from '../core/guideCard';
import type { ComponentType, SVGProps } from 'react';
import { Holdings, Tags } from './CardFace';
import { ExploreMark, ScryfallMark, TcgplayerMark } from './StoreMarks';

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
                {card.owned && !card.scryfallId && (
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

              {card.scryfallId && <YourCopies scryfallId={card.scryfallId} onLeave={onClose} />}

              <nav aria-labelledby="inspect-view-on" className="mt-auto flex flex-col gap-1 pt-2">
                <span id="inspect-view-on" className="text-xs voice-semi text-ink-muted">View on</span>
                <div className="flex flex-wrap gap-x-4 gap-y-1">
                  {card.href && <OutLink href={card.href} label="Scryfall" Mark={ScryfallMark} />}
                  <OutLink href={tcgplayerSearch(card.name)} label="TCGplayer" Mark={TcgplayerMark} />
                </div>
                <Link
                  to="/explore"
                  search={{ a: card.name.split(' // ')[0] } as never}
                  onClick={onClose}
                  className="-ml-2 inline-flex min-h-9 items-center gap-1.5 self-start rounded-sm px-2 text-md voice-semi font-medium text-accent-ink transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk"
                >
                  <ExploreMark className="size-[1.15rem]" />
                  Explore this card
                </Link>
              </nav>
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
      className="-ml-2 inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-sm px-2 text-md voice-semi font-medium text-accent-ink no-underline transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk"
    >
      <Mark className="size-[1.15rem]" />
      {label}
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  );
}

const FINISHES = [
  { key: 'nonfoil', label: 'Nonfoil' },
  { key: 'foil', label: '✦ Foil' },
] as const;
const KIND_NOTE: Record<string, string> = { pool: 'card pool', deck: 'precon deck' };

/** This printing in your collection: per-finish owned / pledged / free, the built
 *  decks holding it, where the copies came from, and other printings you own. */
function YourCopies({ scryfallId, onLeave }: { scryfallId: string; onLeave: () => void }) {
  const q = useQuery(holdingsQuery(scryfallId));
  return (
    <section aria-labelledby="inspect-copies" className="flex flex-col gap-2">
      <h3 id="inspect-copies" className="border-b border-rule pb-1 text-sm voice-semi font-medium text-ink">Your copies</h3>
      {q.isPending ? (
        <p role="status" className="text-sm text-ink-muted">Checking your collection…</p>
      ) : q.isError ? (
        <p className="text-sm text-danger">Couldn’t load your copies: {(q.error as Error).message}</p>
      ) : (
        <CopiesBody h={q.data} onLeave={onLeave} />
      )}
    </section>
  );
}

function CopiesBody({ h, onLeave }: { h: HoldingsOut; onLeave: () => void }) {
  const finishes = FINISHES.filter((f) => (h.owned[f.key] ?? 0) > 0);
  const other = h.other_printings_owned;
  const otherNote = other > 0 && (
    <p className="text-sm text-ink-muted">You also own {fmtInt(other)} {other === 1 ? 'copy' : 'copies'} in other printings.</p>
  );
  if (!finishes.length) {
    return (
      <>
        <p className="text-sm text-ink">You don’t own this printing.</p>
        {otherNote}
      </>
    );
  }
  return (
    <>
      <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-1 text-sm">
        {finishes.map((f) => {
          const owned = h.owned[f.key] ?? 0;
          const pledged = h.pledged[f.key] ?? 0;
          return (
            <div key={f.key} className="contents">
              <dt className="text-ink-muted">{f.label}</dt>
              <dd className="tabular">
                <b className="font-bold">{fmtInt(owned)}</b> owned
                {pledged > 0 && <> · {fmtInt(pledged)} pledged</>}
                {' · '}<span className={h.free[f.key] ? 'text-accent-ink' : 'text-ink-muted'}>{fmtInt(h.free[f.key] ?? 0)} free</span>
              </dd>
            </div>
          );
        })}
        {h.decks.length > 0 && (
          <>
            <dt className="text-ink-muted">Pledged to</dt>
            <dd>
              <ul className="flex flex-col gap-0.5">
                {h.decks.map((d) => (
                  <li key={`${d.slug}|${d.finish}`} className="flex items-baseline gap-2">
                    <Link to="/decks" search={(s) => ({ ...s, deck: d.slug })} onClick={onLeave} className="min-w-0 truncate text-accent-ink underline-offset-4 hover:underline">
                      {d.name}
                    </Link>
                    <span className="shrink-0 text-xs tabular text-ink-muted">×{d.count}{d.finish === 'foil' ? ' ✦' : ''}</span>
                  </li>
                ))}
              </ul>
            </dd>
          </>
        )}
        {h.sources.length > 0 && (
          <>
            <dt className="text-ink-muted">Acquired from</dt>
            <dd>
              <ul className="flex flex-col gap-0.5">
                {h.sources.map((cs) => (
                  <li key={`${cs.source.key}|${cs.finish}`} className="flex items-baseline gap-2">
                    <span className="min-w-0 truncate">
                      {cs.source.label}
                      {cs.source.set_code && <span className="tabular text-ink-muted"> · {cs.source.set_code.toUpperCase()}</span>}
                    </span>
                    {KIND_NOTE[cs.source.kind] && <span className="shrink-0 text-xs text-ink-muted">{KIND_NOTE[cs.source.kind]}</span>}
                    <span className="ml-auto shrink-0 text-xs tabular text-ink-muted">
                      ×{cs.copies}{cs.finish === 'foil' ? ' ✦' : ''}{(cs.acquisitions ?? 1) > 1 && ` · added ${cs.acquisitions} times`}
                    </span>
                  </li>
                ))}
              </ul>
            </dd>
          </>
        )}
      </dl>
      {otherNote}
    </>
  );
}

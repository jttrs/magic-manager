import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { OutLink } from '../../../components/CardInspector';
import { ExploreMark, ScryfallMark, TcgplayerMark } from '../../../components/StoreMarks';
import type { SurfCardOut } from '../../../core/api';
import { fmtUsd } from '../../../core/format';
import { artists, ownedLine, printingLine, textFaces } from '../../../core/surf';

const tcgplayerSearch = (name: string) =>
  `https://www.tcgplayer.com/search/magic/product?productLineName=magic&q=${encodeURIComponent(name.split(' // ')[0])}`;

/** One card in the feed: the card large, then its words — name, type, the
 *  flavor text set to be read, the artist, where it was printed. The art tags
 *  under it narrow the feed to more art like it. */
export function SurfCardEntry({ card, onTag, onLeave, eager = false }: { card: SurfCardOut; onTag: (slug: string) => void; onLeave: () => void; eager?: boolean }) {
  const faced = card.faces.filter((f) => f.image);
  const [face, setFace] = useState(0);
  const image = faced.length > 1 ? faced[face]?.image : card.image;
  const faces = textFaces(card);
  const by = artists(card);
  const owned = ownedLine(card);
  const price = [card.prices.nonfoil != null && fmtUsd(card.prices.nonfoil), card.prices.foil != null && `✦ ${fmtUsd(card.prices.foil)}`].filter(Boolean).join(' · ');
  const rules = faces.filter((f) => f.oracle_text);
  return (
    <article
      aria-label={card.name}
      data-surf-card
      className="grid min-h-full snap-start content-center justify-items-center gap-x-12 gap-y-6 px-4 py-8 sm:px-8 lg:grid-cols-[auto_minmax(16rem,32rem)] lg:justify-center lg:justify-items-start"
    >
      <div className="relative">
        {image ? (
          <img
            src={image}
            alt={card.name}
            width={672}
            height={936}
            loading={eager ? 'eager' : 'lazy'}
            decoding="async"
            className="aspect-[488/680] h-auto w-[min(100%,calc((100dvh-10rem)*0.7176),30rem)] lg:w-[min(calc((100dvh-10rem)*0.7176),30rem,calc(100vw-var(--size-sidebar)-26rem))] rounded-[4.5%/3.2%] bg-paper-sunk shadow-[0_18px_40px_-22px_var(--theme-scrim)]"
          />
        ) : (
          <div className="grid aspect-[488/680] w-[min(100%,20rem)] place-items-center rounded-sm border border-rule bg-paper-sunk p-4 text-center text-sm text-ink-muted">{card.name}</div>
        )}
        {faced.length > 1 && (
          <button
            type="button"
            onClick={() => setFace((f) => (f + 1) % faced.length)}
            className="mt-2 inline-flex min-h-9 cursor-pointer items-center rounded-sm px-2 text-sm voice-semi font-medium text-accent-ink transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk"
          >
            Turn over · {faced[(face + 1) % faced.length].name}
          </button>
        )}
      </div>

      <div className="flex w-full max-w-[34rem] min-w-0 flex-col gap-5 lg:max-w-none">
        {faces.map((f, i) => (
          <section key={`${f.name}-${i}`} className="flex flex-col gap-3">
            <header className="border-b-2 border-rule-strong pb-2">
              <h3 className="text-2xl voice-condensed font-bold leading-none text-balance sm:text-3xl">{f.name}</h3>
              {f.type_line && <p className="mt-1.5 text-sm text-ink-muted">{f.type_line}</p>}
            </header>
            {f.flavor_text ? (
              <p className="max-w-[46ch] whitespace-pre-line text-lg leading-relaxed text-ink text-pretty">{f.flavor_text}</p>
            ) : (
              i === 0 && faces.length === 1 && <p className="text-sm text-ink-muted">No flavor text on this card.</p>
            )}
          </section>
        ))}

        <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-1.5 text-sm">
          {by && (
            <>
              <dt className="text-ink-muted">Artist</dt>
              <dd>{by}</dd>
            </>
          )}
          <dt className="text-ink-muted">Printed in</dt>
          <dd className="tabular">{printingLine(card)}</dd>
          {price && (
            <>
              <dt className="text-ink-muted">Price</dt>
              <dd className="tabular">{price}</dd>
            </>
          )}
          {owned && (
            <>
              <dt className="text-ink-muted">Yours</dt>
              <dd className="text-accent-ink">{owned}</dd>
            </>
          )}
        </dl>

        {card.art_tags.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="text-xs voice-semi text-ink-muted">More art like this</span>
            <ul aria-label={`Art tags of ${card.name}`} className="flex flex-wrap gap-1">
              {card.art_tags.map((t) => (
                <li key={t.slug}>
                  <button
                    type="button"
                    onClick={() => onTag(t.slug)}
                    title={`Surf cards with ${t.label} art`}
                    className="min-h-7 cursor-pointer rounded-xs border border-rule px-1.5 text-xs text-ink-muted transition-colors duration-150 ease-guide hover:border-rule-strong hover:bg-paper-sunk hover:text-ink focus-visible:border-accent"
                  >
                    {t.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {rules.length > 0 && (
          <details className="group text-sm">
            <summary className="cursor-pointer select-none text-ink-muted hover:text-ink">Rules text</summary>
            <div className="mt-2 flex flex-col gap-2">
              {rules.map((f, i) => (
                <p key={i} className="max-w-[60ch] whitespace-pre-line leading-relaxed">{f.oracle_text}</p>
              ))}
            </div>
          </details>
        )}

        <nav aria-label={`${card.name} elsewhere`} className="flex flex-wrap gap-x-4 gap-y-1">
          {card.scryfall_uri && <OutLink href={card.scryfall_uri} label="Scryfall" Mark={ScryfallMark} />}
          <OutLink href={tcgplayerSearch(card.name)} label="TCGplayer" Mark={TcgplayerMark} />
          <Link
            to="/explore"
            search={{ a: card.name.split(' // ')[0], mode: 'card' } as never}
            onClick={onLeave}
            className="-ml-2 inline-flex min-h-9 items-center gap-1.5 rounded-sm px-2 text-md voice-semi font-medium text-accent-ink transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk"
          >
            <ExploreMark className="size-[1.15rem]" />
            Explore this card
          </Link>
        </nav>
      </div>
    </article>
  );
}

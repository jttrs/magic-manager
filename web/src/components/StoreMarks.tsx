// Monochrome marks drawn for this guide (currentColor, 24px stroke grid): the
// stores after their own logos — ManaPool's lettered cube, TCGplayer's fanned
// cards with a bolt, Card Kingdom's castle in a roundel, Scryfall's scrying orb —
// plus the add-card and magnifier marks. External links carry their site's mark.
import { useId, type SVGProps } from 'react';

type MarkProps = SVGProps<SVGSVGElement>;
const base = { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true } as const;

export function ManaPoolMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <path d="M12 2.6 20.4 7.3v9.4L12 21.4l-8.4-4.7V7.3Z" />
      <path d="M3.6 7.3 12 12l8.4-4.7M12 12v9.4" />
      <path d="M14.6 19.4v-7.2L18 10.3v3.5l-3.4 1.9" />
    </svg>
  );
}

export function TcgplayerMark(p: MarkProps) {
  const id = useId();
  return (
    <svg {...base} {...p}>
      <mask id={id}>
        <rect width="24" height="24" fill="#fff" />
        <rect x="7.6" y="2.6" width="8.8" height="18.8" rx="1.6" fill="#000" />
      </mask>
      <g mask={`url(#${id})`}>
        <rect x="2.6" y="5.2" width="7" height="14" rx="1.2" transform="rotate(-14 6.1 12.2)" />
        <rect x="14.4" y="5.2" width="7" height="14" rx="1.2" transform="rotate(14 17.9 12.2)" />
      </g>
      <rect x="8.5" y="3.5" width="7" height="17" rx="1.2" />
      <path d="M12.9 7.4 10.4 12.6h2.1l-1.2 4.2 2.6-5.4h-2.1Z" fill="currentColor" strokeWidth="0.8" />
    </svg>
  );
}

export function CardKingdomMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <circle cx="12" cy="12" r="9.4" />
      <path d="M7.4 16.6V9.2h2.1v1.7h1.45V9.2h2.1v1.7h1.45V9.2h2.1v7.4Z" />
      <path d="M11 16.6v-2.2a1 1 0 0 1 2 0v2.2" />
    </svg>
  );
}

/** A card with a plus badge overlapping its corner (the add-cards action). */
export function AddCardMark(p: MarkProps) {
  const id = useId();
  return (
    <svg {...base} {...p}>
      <mask id={id}>
        <rect width="24" height="24" fill="#fff" />
        <circle cx="17.5" cy="17.5" r="6.4" fill="#000" />
      </mask>
      <g mask={`url(#${id})`}>
        <rect x="3.2" y="2.6" width="12.4" height="17.2" rx="1.6" />
        <path d="M6 6.4h6.8M6 9.2h4.6" />
      </g>
      <circle cx="17.5" cy="17.5" r="4.9" />
      <path d="M17.5 15.3v4.4M15.3 17.5h4.4" />
    </svg>
  );
}

/** Scryfall: a scrying orb on its stand. */
export function ScryfallMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <circle cx="12" cy="10" r="7" />
      <path d="M8.6 7.6a4.2 4.2 0 0 1 3.4-1.8" />
      <path d="M7 16.4 5.6 20.4h12.8L17 16.4" />
    </svg>
  );
}

/** Deck actions share one card silhouette so they read as a family. */
function CardBody({ maskId, x = 3.2 }: { maskId?: string; x?: number }) {
  return <rect x={x} y="2.6" width="12.4" height="17.2" rx="1.6" mask={maskId ? `url(#${maskId})` : undefined} />;
}

/** A card with a pencil across its corner (edit the deck). */
export function EditDeckMark(p: MarkProps) {
  const id = useId();
  return (
    <svg {...base} {...p}>
      <mask id={id}>
        <rect width="24" height="24" fill="#fff" />
        <path d="M21.6 9.4 11.4 19.6l-3.6 1.2 1.2-3.6L19.2 7Z" fill="#000" stroke="#000" strokeWidth="3.4" />
      </mask>
      <CardBody maskId={id} />
      <path d="M20.6 8.4 11 18l-2.6.9.9-2.6L18.9 6.7a1.2 1.2 0 0 1 1.7 1.7Z" />
      <path d="M17.6 8l1.7 1.7" />
    </svg>
  );
}

/** Two offset cards (copy the recipe). */
export function CopyDeckMark(p: MarkProps) {
  const id = useId();
  return (
    <svg {...base} {...p}>
      <mask id={id}>
        <rect width="24" height="24" fill="#fff" />
        <rect x="7.4" y="5.6" width="13.6" height="18.4" rx="2.4" fill="#000" />
      </mask>
      <rect x="3" y="2.4" width="11.6" height="15.8" rx="1.6" mask={`url(#${id})`} />
      <rect x="8.4" y="6.6" width="11.6" height="15.8" rx="1.6" />
    </svg>
  );
}

/** A deck box with cards dropping in (build the deck from your cards). */
export function BuildDeckMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <path d="M4 10.4h16v9.4a1.6 1.6 0 0 1-1.6 1.6H5.6A1.6 1.6 0 0 1 4 19.8Z" />
      <path d="M4 14.2h16" />
      <path d="M12 2.6v6.2M9.4 6.4 12 9l2.6-2.6" />
    </svg>
  );
}

/** A deck box with cards lifting out (break the deck down). */
export function BreakDownMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <path d="M4 10.4h16v9.4a1.6 1.6 0 0 1-1.6 1.6H5.6A1.6 1.6 0 0 1 4 19.8Z" />
      <path d="M4 14.2h16" />
      <path d="M12 8.8V2.6M9.4 5.2 12 2.6l2.6 2.6" />
    </svg>
  );
}

/** A deck box with a plus (start a new deck). */
export function NewDeckMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <path d="M3.4 8.6h12v11.2a1.6 1.6 0 0 1-1.6 1.6H5a1.6 1.6 0 0 1-1.6-1.6Z" />
      <path d="M3.4 12.4h12" />
      <path d="M18.6 2.6v7M15.1 6.1h7" />
    </svg>
  );
}

/** A card arriving from a link (import a deck from a deck-builder URL). */
export function ImportDeckMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <rect x="3.2" y="5.6" width="12.4" height="15.8" rx="1.6" />
      <path d="M6 10h6.8M6 12.8h4.6" />
      <path d="M21 2.8 15 8.8M15 4.8v4h4" />
    </svg>
  );
}

/** EDHREC: a commander's crown over a card (their deck-data pages). */
export function EdhrecMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <rect x="5.4" y="8.6" width="13.2" height="12.8" rx="1.6" />
      <path d="M5.4 6.6 8 3.6l2.6 2.4L12 2.8l1.4 3.2L16 3.6l2.6 3H5.4Z" />
      <path d="M8.6 13h6.8M8.6 16.4h4.4" />
    </svg>
  );
}

/** A magnifier over a card (explore this card). */
export function ExploreMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <rect x="3.2" y="2.6" width="11.4" height="16" rx="1.6" />
      <circle cx="15.4" cy="15.2" r="4" />
      <path d="m18.3 18.1 2.9 2.9" />
    </svg>
  );
}

/** A price tag (what this costs). */
export function PriceMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <path d="M3.4 12.6V4.8a1.4 1.4 0 0 1 1.4-1.4h7.8l8 8a1.6 1.6 0 0 1 0 2.3l-6.9 6.9a1.6 1.6 0 0 1-2.3 0Z" />
      <circle cx="8.2" cy="8.2" r="1.5" />
    </svg>
  );
}

/** A product box under a magnifier (find the products your cards came from). */
export function FindProductsMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <path d="M3 8.2 9.6 5l6.6 3.2v7.4L9.6 18.8 3 15.6Z" />
      <path d="M3 8.2l6.6 3.2 6.6-3.2M9.6 11.4v7.4" />
      <circle cx="17.2" cy="16.6" r="3.2" />
      <path d="m19.6 19 2.2 2.2" />
    </svg>
  );
}

/** A card with tally marks (count the cards you have). */
export function CountCardsMark(p: MarkProps) {
  return (
    <svg {...base} {...p}>
      <rect x="4.6" y="2.8" width="12.2" height="17.4" rx="1.4" />
      <path d="M7.8 7.6v6.8M10.2 7.6v6.8M12.6 7.6v6.8" />
      <path d="M6.6 13.2 14.4 8.8" />
      <path d="m15.8 17.6 2 2 3.6-4.4" />
    </svg>
  );
}

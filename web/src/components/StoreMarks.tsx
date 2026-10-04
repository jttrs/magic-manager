// Monochrome store marks drawn for this guide (currentColor, 24px grid), after
// each store's own logo: ManaPool's lettered cube, TCGplayer's fanned cards
// with a bolt, Card Kingdom's castle in a roundel.
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

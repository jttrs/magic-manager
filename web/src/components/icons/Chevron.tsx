const ROT = { down: '', right: '-rotate-90', up: 'rotate-180', left: 'rotate-90' } as const;

/** Stroke chevron; inherits currentColor. Decorative. */
export function Chevron({ dir = 'down', className = '' }: { dir?: keyof typeof ROT; className?: string }) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className={`${ROT[dir]} ${className}`}>
      <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

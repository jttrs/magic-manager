/** Add a card to the marked list (buy lists today; bulk collection/deck/tag actions later): list-plus at rest, amber list-check when on the list. */
export function MarkToggle({ name, marked, onToggle, size = 'md' }: { name: string; marked: boolean; onToggle: () => void; size?: 'sm' | 'md' }) {
  return (
    <button
      type="button"
      aria-pressed={marked}
      aria-label={`${marked ? 'Unmark' : 'Mark'} ${name}`}
      title={marked ? 'Remove from list' : 'Add to list'}
      onClick={onToggle}
      className={`touch-hit grid shrink-0 cursor-pointer place-items-center rounded-sm transition-colors duration-200 ease-guide hover:bg-paper-sunk ${size === 'sm' ? 'size-7' : 'size-8'} ${marked ? 'text-accent-ink' : 'text-ink-muted hover:text-ink'}`}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true" className={size === 'sm' ? 'size-4' : 'size-[1.15rem]'} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 6h11M4 11h11M4 16h6" />
        {marked ? <path d="M13.5 17l2.5 2.5 5-5.5" /> : <path d="M17 13.5v7M13.5 17h7" />}
      </svg>
    </button>
  );
}

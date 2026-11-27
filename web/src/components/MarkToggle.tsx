import { MarkListMark } from './icons/marks';

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
      <MarkListMark on={marked} className={size === 'sm' ? 'size-icon-sm' : 'size-icon-md'} />
    </button>
  );
}

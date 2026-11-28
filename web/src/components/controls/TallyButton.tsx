import { PlusMark } from '../icons/marks';
import { usePressHold } from './usePressHold';

type Props = {
  finish: 'nonfoil' | 'foil';
  owned: number;
  /** The draft's change to this finish: copies to add, or negative for a count lowered in Bulk modify counts. */
  pending: number;
  cardName: string;
  /** +1 on click, −1 on shift-click. */
  onAdd: (n: number) => void;
  /** Hold / long-press / Shift+Enter: open the amount picker. */
  onHold: () => void;
};

/** A compact "+ owned" chip that adds one copy of a finish: click adds, shift-click takes one
 *  back off the draft, hold opens the amount picker. An amber rule grows under it while you hold. */
export function TallyButton({ finish, owned, pending, cardName, onAdd, onHold }: Props) {
  const press = usePressHold({ onPress: (e) => onAdd(e.shiftKey ? -1 : 1), onHold });
  const { holding, ...handlers } = press;
  const change = pending > 0 ? `, ${pending} to add` : pending < 0 ? `, lowered by ${-pending}` : '';
  const label = `Add one ${finish} — ${owned} owned${change}`;
  return (
    <button
      type="button"
      {...handlers}
      aria-label={`${label} (${cardName})`}
      title="Click to add one · hold for more · shift-click to remove one"
      className={`relative inline-flex h-6 min-w-0 cursor-pointer select-none items-center gap-1 rounded-xs border px-1.5 text-2xs voice-semi text-ink transition-colors ease-guide ${pending !== 0 ? 'border-highlight-solid bg-highlight' : 'border-rule bg-transparent hover:bg-paper-sunk'}`}
    >
      {finish === 'foil' && <span aria-hidden>✦</span>}
      <PlusMark className="size-icon-xs shrink-0" />
      <span className="tabular">{owned}</span>
      {/* A corner badge, so staging never changes the button's width (the caption doesn't reflow). */}
      {pending !== 0 && (
        <span aria-hidden className={`pointer-events-none absolute -bottom-2 -right-1.5 rounded-pill bg-paper px-1 text-2xs font-semibold leading-tight tabular ring-1 ring-highlight-solid ${pending > 0 ? 'text-accent-ink' : 'text-danger'}`}>
          {pending > 0 ? `+${pending}` : `−${-pending}`}
        </span>
      )}
      <span
        aria-hidden
        className={`pointer-events-none absolute inset-x-0 bottom-0 overflow-hidden h-underline-quiet origin-left bg-accent ${holding ? 'scale-x-100 transition-transform ease-linear duration-400 motion-reduce:transition-none' : 'scale-x-0'}`}
      />
    </button>
  );
}

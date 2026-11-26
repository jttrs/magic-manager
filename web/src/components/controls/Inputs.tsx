import { forwardRef, type InputHTMLAttributes } from 'react';

type Base = Omit<InputHTMLAttributes<HTMLInputElement>, 'className' | 'type'>;

/** A compact count cell for dense tables (the checklist grid): right-aligned digits,
 *  a state border — `invalid` (danger), `moved` (accent ring: changed under you) — and
 *  `changed` (bold: differs from what you started with). */
export const CountInput = forwardRef<HTMLInputElement, Base & { state?: 'ok' | 'invalid' | 'moved'; changed?: boolean }>(
  function CountInput({ state = 'ok', changed = false, ...rest }, ref) {
    const border = state === 'invalid' ? 'border-danger' : state === 'moved' ? 'border-accent ring-2 ring-accent' : 'border-rule';
    return (
      <input
        ref={ref}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        className={`h-7 w-11 rounded-xs border bg-paper-raised px-1.5 text-right text-sm tabular text-ink outline-none transition-[border-color,background-color] duration-150 ease-guide focus:border-accent focus:bg-paper ${border} ${changed ? 'font-semibold' : ''}`}
        {...rest}
      />
    );
  },
);

/** An editable display title (a deck's name): reads as the heading, shows a ruled box
 *  only on hover/focus. */
export const TitleInput = forwardRef<HTMLInputElement, Base>(function TitleInput(props, ref) {
  return (
    <input
      ref={ref}
      type="text"
      className="-mx-1 min-w-0 rounded-sm border border-transparent bg-transparent px-1 text-3xl voice-condensed font-bold leading-tight text-ink hover:border-rule focus-visible:border-accent"
      {...props}
    />
  );
});

/** A whole-number slider in the accent colour. */
export function RangeInput({ value, onChange, min, max, step = 1, ...rest }: Omit<Base, 'value' | 'onChange' | 'min' | 'max' | 'step'> & {
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
}) {
  return <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="min-w-0 flex-1 cursor-pointer accent-accent" {...rest} />;
}

/** The hidden file input behind a "Choose a file" button: never shown or tabbed to —
 *  the button calls `ref.current.click()`. */
export const FileInput = forwardRef<HTMLInputElement, Omit<Base, 'tabIndex' | 'hidden'>>(function FileInput(props, ref) {
  return <input ref={ref} type="file" tabIndex={-1} aria-hidden className="sr-only" {...props} />;
});

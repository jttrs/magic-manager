import { forwardRef, useState, type InputHTMLAttributes } from 'react';
import { clampWhole, parseWhole } from './numbers';
import { fieldClass, type FieldTone } from './fieldClass';

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'className'> & { tone?: FieldTone; width?: 'full' | 'auto' };

/** The one native text input (search, text, email, url, date). Label it with a
 *  `RailField`/`<label>` around it, or `aria-label`. */
export const TextInput = forwardRef<HTMLInputElement, Props>(function TextInput({ tone = 'chrome', width = 'full', type = 'text', ...rest }, ref) {
  return <input ref={ref} type={type} className={`${fieldClass(tone)} ${width === 'full' ? 'w-full' : ''}`} {...rest} />;
});

/** A whole-number field with bounds. While you type it keeps your text as a draft
 *  (so you can clear it and type a new number); a whole number inside the bounds is
 *  committed as you type, and leaving the field clamps (or restores) it. */
export function NumberField({ value, onChange, min, max, tone = 'paper', onBlur, ...rest }: Omit<InputHTMLAttributes<HTMLInputElement>, 'className' | 'value' | 'onChange' | 'type' | 'min' | 'max'> & {
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  tone?: FieldTone;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  return (
    <input
      type="number"
      inputMode="numeric"
      min={min}
      max={max}
      value={draft ?? String(value)}
      onChange={(e) => {
        setDraft(e.target.value);
        const n = parseWhole(e.target.value);
        if (n != null && n >= min && n <= max && n !== value) onChange(n);
      }}
      onBlur={(e) => {
        const n = clampWhole(e.target.value, min, max, value);
        setDraft(null);
        if (n !== value) onChange(n);
        onBlur?.(e);
      }}
      className={`${fieldClass(tone)} w-20 tabular`}
      {...rest}
    />
  );
}

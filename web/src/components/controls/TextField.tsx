import { forwardRef, type InputHTMLAttributes } from 'react';
import { fieldClass, type FieldTone } from './fieldClass';

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'className'> & { tone?: FieldTone; width?: 'full' | 'auto' };

/** The one native text input (search, text, email, url, date). Label it with a
 *  `RailField`/`<label>` around it, or `aria-label`. */
export const TextInput = forwardRef<HTMLInputElement, Props>(function TextInput({ tone = 'chrome', width = 'full', type = 'text', ...rest }, ref) {
  return <input ref={ref} type={type} className={`${fieldClass(tone)} ${width === 'full' ? 'w-full' : ''}`} {...rest} />;
});

/** A whole-number field with bounds; the value is clamped on change. */
export function NumberField({ value, onChange, min, max, tone = 'paper', ...rest }: Omit<InputHTMLAttributes<HTMLInputElement>, 'className' | 'value' | 'onChange' | 'type' | 'min' | 'max'> & {
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  tone?: FieldTone;
}) {
  return (
    <input
      type="number"
      inputMode="numeric"
      min={min}
      max={max}
      value={value}
      onChange={(e) => onChange(Math.max(min, Math.min(max, Math.trunc(Number(e.target.value)) || min)))}
      className={`${fieldClass(tone)} w-20 tabular`}
      {...rest}
    />
  );
}

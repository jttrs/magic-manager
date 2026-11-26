import { forwardRef, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import { fieldClass, type FieldTone } from './fieldClass';

/** The one native <select> (short inline choices inside a sheet or dialog; rails use
 *  `SelectField`). Label it with a `<label>`/`RailField` or `aria-label`. */
export const SelectInput = forwardRef<HTMLSelectElement, Omit<SelectHTMLAttributes<HTMLSelectElement>, 'className'> & { tone?: FieldTone; width?: 'full' | 'auto' }>(
  function SelectInput({ tone = 'paper', width = 'auto', ...rest }, ref) {
    return <select ref={ref} className={`${fieldClass(tone)} cursor-pointer pr-7 ${width === 'full' ? 'w-full' : ''}`} {...rest} />;
  },
);

/** The one multi-line text box (pasted lists, notes). */
export const TextArea = forwardRef<HTMLTextAreaElement, Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'className'> & { tone?: FieldTone; rows?: number }>(
  function TextArea({ tone = 'paper', rows = 8, ...rest }, ref) {
    return <textarea ref={ref} rows={rows} className={`${fieldClass(tone)} w-full resize-y py-2 font-guide tabular leading-snug`} {...rest} />;
  },
);

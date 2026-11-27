import type { InputHTMLAttributes, ReactNode } from 'react';

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'className' | 'type' | 'onChange'> & {
  type?: 'checkbox' | 'radio';
  onChange: (checked: boolean) => void;
  /** The words beside the box; omit only with an `aria-label`. */
  children?: ReactNode;
  /** A muted second line under the words. */
  hint?: ReactNode;
};

const BOX = 'size-4 shrink-0 cursor-pointer accent-accent disabled:cursor-not-allowed';

/** The one checkbox / radio: the native control in the accent colour, with its words
 *  beside it (the whole row is the hit target). */
export function Check({ type = 'checkbox', onChange, children, hint, ...rest }: Props) {
  const input = <input type={type} onChange={(e) => onChange(e.target.checked)} className={`${BOX} ${hint ? 'mt-0.5' : ''}`} {...rest} />;
  if (children == null) return input;
  return (
    <label className={`inline-flex cursor-pointer gap-2 ${hint ? 'items-start' : 'items-center'}`}>
      {input}
      <span className="min-w-0">
        {children}
        {hint && <span className="block text-sm text-ink-muted">{hint}</span>}
      </span>
    </label>
  );
}

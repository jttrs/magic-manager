import type { ButtonHTMLAttributes } from 'react';
import { buttonClass } from './buttonClass';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { tone?: 'chrome' | 'paper'; emphasis?: 'primary' | 'quiet' };

/** The one button. On chrome it reads as a ruled outline; primary fills amber. */
export function Button({ tone = 'chrome', emphasis = 'quiet', className = '', type = 'button', ...rest }: Props) {
  return <button type={type} className={`${buttonClass(tone, emphasis)} ${className}`} {...rest} />;
}

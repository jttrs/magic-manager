import { forwardRef, type ButtonHTMLAttributes } from 'react';

/** A clickable REGION whose look is its content — a card tile's art, a group heading,
 *  a whole table cell. No box, no colour of its own (it inherits the surrounding text
 *  colour; a colour class you pass wins): cursor, focus ring and a reset. Not for
 *  actions with words (Button / Button link), icons (IconAction) or list rows (ListRow).
 *  `className` is for layout (flex, grid, padding, width) and its own text colour. */
export const Pressable = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement>>(function Pressable({ className = '', type = 'button', ...rest }, ref) {
  return <button ref={ref} type={type} className={`cursor-pointer bg-transparent p-0 text-left disabled:cursor-not-allowed ${className}`} {...rest} />;
});

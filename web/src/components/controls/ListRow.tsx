import { forwardRef, type ButtonHTMLAttributes } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  /** The row open in the inspector: a flat amber fill, square corners. */
  active?: boolean;
};

/** A selectable list row (History, Decks, People, Rankings…): ruled, hover-sunk, and
 *  flat-filled while active (`.list-row` in the components CSS layer, so a class you pass
 *  wins). `className` is for the row's own layout (padding, grid columns). The inline `highlighter` stroke is for text, not rows. */
export const ListRow = forwardRef<HTMLButtonElement, Props>(function ListRow({ active = false, className = '', type = 'button', ...rest }, ref) {
  return (
    <button
      ref={ref}
      type={type}
      aria-current={active ? 'true' : undefined}
      className={`list-row ${className}`}
      {...rest}
    />
  );
});

import { forwardRef, type ButtonHTMLAttributes } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  /** The row open in the inspector: a flat amber fill, square corners. */
  active?: boolean;
};

/** A selectable list row (History, Decks, People, Rankings…): ruled, hover-sunk, and
 *  flat-filled while active. `className` is for the row's own layout only (padding,
 *  grid columns) — never colour. The inline `highlighter` stroke is for text, not rows. */
export const ListRow = forwardRef<HTMLButtonElement, Props>(function ListRow({ active = false, className = '', type = 'button', ...rest }, ref) {
  return (
    <button
      ref={ref}
      type={type}
      aria-current={active ? 'true' : undefined}
      className={`ruled flex w-full cursor-pointer items-center gap-3 px-1 text-left transition-colors ease-guide hover:bg-paper-sunk aria-[current=true]:bg-highlight ${className}`}
      {...rest}
    />
  );
});

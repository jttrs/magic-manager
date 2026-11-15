import { createContext, useContext, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

/** The sheet header's summary element, provided by `GuideSheet`. */
export const SheetSummarySlot = createContext<HTMLElement | null>(null);

/**
 * A live summary (`12 of 17 products · compared to …`) rendered by a panel deep in
 * the sheet but shown in the sheet header, on the row the arrange controls and
 * actions share. The header summary is live state, never a tagline. Outside a
 * `GuideSheet` it renders in place.
 */
export function SheetSummary({ children }: { children: ReactNode }) {
  const slot = useContext(SheetSummarySlot);
  const line = <span role="status" aria-live="polite">{children}</span>;
  return slot ? createPortal(line, slot) : <p className="text-sm tabular text-ink-muted">{line}</p>;
}

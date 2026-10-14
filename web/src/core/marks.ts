// Copy-marked header action: the words for its tooltip / accessible name.

/** "Mark cards to copy them as a list" at 0; "Copy 7 marked cards as a list". */
export function copyMarkedLabel(count: number, noun = 'card'): string {
  if (count <= 0) return `Mark ${noun}s to copy them as a list`;
  return `Copy ${count} marked ${count === 1 ? noun : `${noun}s`} as a list`;
}

/** The tooltip, in precedence order: just copied, building, a failure, else the label. */
export function copyMarkedTip(s: { copied: boolean; busy: boolean; failure: string | null; label: string }): string {
  if (s.copied) return 'Copied';
  if (s.busy) return 'Building list…';
  return s.failure ?? s.label;
}

/** The count badge: a small number; anything past 99 reads 99+. */
export const markBadge = (count: number): string => (count > 99 ? '99+' : String(count));

// The one restore point: plain-language description of what restoring changes.
import type { UndoSummary } from './api';

const fmt = new Intl.NumberFormat('en-US');

const NOUNS: [keyof UndoSummary, string, string][] = [
  ['copies', 'copy', 'copies'],
  ['printings', 'printing', 'printings'],
  ['decks', 'deck', 'decks'],
  ['built', 'built deck', 'built decks'],
  ['wishlist', 'wishlist card', 'wishlist cards'],
  ['earmarks', 'earmarked product', 'earmarked products'],
];

/** "3 more copies", "1 fewer deck" — what your data looks like after restoring. */
export function changeLines(changes: UndoSummary): string[] {
  return NOUNS.flatMap(([k, one, many]) => {
    const n = changes[k];
    if (!n) return [];
    const abs = Math.abs(n);
    return [`${fmt.format(abs)} ${n > 0 ? 'more' : 'fewer'} ${abs === 1 ? one : many}`];
  });
}

/** "3:02 PM" today, else "Oct 4, 3:02 PM". */
export function whenLabel(iso: string, now = new Date()): string {
  const d = new Date(iso);
  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  return d.toDateString() === now.toDateString() ? time : `${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}, ${time}`;
}

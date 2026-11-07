// Feature-flag picker view-model (framework-free): plain-words labels for where a
// flag's value comes from, and the two controls (everyone switch, just-me choice).
import { choiceValue, seenLabel, type FlagChoice } from './admin';
import type { FlagRowOut } from './api';

export { choiceValue };

const SOURCE: Record<FlagRowOut['source'], string> = {
  default: 'Default',
  local_file: 'This machine’s file',
  everyone: 'Set for everyone',
  env: 'Pinned by environment',
  user: 'Just you',
};

export const sourceLabel = (row: Pick<FlagRowOut, 'source'>): string => SOURCE[row.source] ?? row.source;

/** "On · Set for everyone by Jared · 3 h ago". */
export function changedLabel(row: Pick<FlagRowOut, 'effective' | 'source' | 'changed_at' | 'changed_by'>, now: Date = new Date()): string {
  const base = `${row.effective ? 'On' : 'Off'} · ${sourceLabel(row)}`;
  if (!row.changed_at) return base;
  return `${base}${row.changed_by ? ` by ${row.changed_by}` : ''} · ${seenLabel(row.changed_at, now)}`;
}

/** The switch's checked state: what everyone gets. */
export const everyoneValue = (row: Pick<FlagRowOut, 'everyone' | 'default'>): boolean => row.everyone ?? row.default;

export const mineChoice = (row: Pick<FlagRowOut, 'mine'>): FlagChoice => (row.mine == null ? 'default' : row.mine ? 'on' : 'off');

/** Replace one row by name (for setQueryData). */
export const applyRow = (list: readonly FlagRowOut[], row: FlagRowOut): FlagRowOut[] => list.map((r) => (r.name === row.name ? row : r));

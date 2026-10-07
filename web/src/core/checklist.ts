// Checklist mode (Collection): an in-browser draft of owned counts per printing
// + finish, its running diff, and the save payload. Framework-free; the engine
// (sets.apply_counts) does the write.
import type { ChecklistOut, CollectionCardOut, CountIn } from './api';
import { fmtInt, fmtUsd } from './format';

export type Finish = 'nonfoil' | 'foil';
const FINISHES: readonly Finish[] = ['nonfoil', 'foil'];

/** One edited cell. Carries what the diff needs so the draft stands alone
 *  (it survives reloads and family switches, and saves in one go). */
type DraftEntry = {
  id: string;
  finish: Finish;
  /** The new count. */
  qty: number;
  /** Owned when the cell was first edited (the save refuses if it moved). */
  was: number;
  /** Copies pledged to built decks — the floor. */
  min: number;
  /** Market price for one copy of this finish, when known. */
  unit: number | null;
  name: string;
  family: string;
  /** The collection moved under this cell (a save came back stale): `was` was
   *  rebased to the current count and the cell waits for you to recheck it. */
  moved?: boolean;
};

export type Draft = Readonly<Record<string, DraftEntry>>;

export const cellKey = (id: string, finish: Finish) => `${id}|${finish}`;

/** Finishes a printing can be counted in (etched counts as foil, like the ledger). */
export function countFinishes(c: Pick<CollectionCardOut, 'finishes' | 'owned'>): Finish[] {
  const has = (f: Finish) =>
    (c.owned[f] ?? 0) > 0 || c.finishes.includes(f) || (f === 'foil' && c.finishes.includes('etched'));
  return FINISHES.filter(has);
}

export const ownedOf = (c: Pick<CollectionCardOut, 'owned'>, f: Finish) => c.owned[f] ?? 0;
export const pledgedOf = (c: Pick<CollectionCardOut, 'pledged'>, f: Finish) => c.pledged[f] ?? 0;
const unitOf = (c: Pick<CollectionCardOut, 'price_usd' | 'price_usd_foil'>, f: Finish) =>
  f === 'foil' ? (c.price_usd_foil ?? c.price_usd ?? null) : (c.price_usd ?? null);

/** The count shown in a cell: the draft's, else what you own. */
export function cellValue(draft: Draft, c: CollectionCardOut, f: Finish): number {
  return draft[cellKey(c.scryfall_id, f)]?.qty ?? ownedOf(c, f);
}

/** Parse a typed cell: whole numbers 0–9999; '' = back to what you own; anything else = invalid. */
export function parseCount(text: string): number | null | 'invalid' {
  const t = text.trim();
  if (t === '') return null;
  if (!/^\d{1,4}$/.test(t)) return 'invalid';
  return Number(t);
}

/** Set one cell (null = revert). An entry equal to its starting count is dropped. */
export function setCell(draft: Draft, c: CollectionCardOut, f: Finish, qty: number | null, familyName: string): Draft {
  const key = cellKey(c.scryfall_id, f);
  const prev = draft[key];
  const was = prev?.was ?? ownedOf(c, f);
  const next = { ...draft };
  if (qty == null || qty === was) {
    delete next[key];
    return next;
  }
  next[key] = { id: c.scryfall_id, finish: f, qty, was, min: pledgedOf(c, f), unit: unitOf(c, f), name: c.name, family: familyName };
  return next;
}

export type DraftSummary = {
  /** Cells changed. */
  cells: number;
  added: number;
  removed: number;
  /** Market value of the change (unpriced copies count $0). */
  value: number;
  /** Changed copies with no price. */
  unpriced: number;
  /** Cells below their pledged floor (Save stays off until fixed). */
  belowPledged: DraftEntry[];
  /** Cells to recheck because the collection moved under them (Save stays off). */
  moved: number;
  families: string[];
};

export function summarize(draft: Draft): DraftSummary {
  const s: DraftSummary = { cells: 0, added: 0, removed: 0, value: 0, unpriced: 0, belowPledged: [], moved: 0, families: [] };
  const fams = new Set<string>();
  for (const e of Object.values(draft)) {
    const d = e.qty - e.was;
    if (d === 0) continue;
    s.cells += 1;
    if (d > 0) s.added += d;
    else s.removed -= d;
    if (e.unit == null) s.unpriced += Math.abs(d);
    else s.value += d * e.unit;
    if (e.qty < e.min) s.belowPledged.push(e);
    if (e.moved) s.moved += 1;
    fams.add(e.family);
  }
  s.families = [...fams].sort();
  s.value = Math.round(s.value * 100) / 100;
  return s;
}

export type StaleRow = { scryfall_id: string; finish: string; expected: number; current: number };

/** A save came back stale: rebase each listed cell on the collection's current
 *  count and flag it for a recheck (a cell that now already matches is dropped). */
export function rebaseStale(draft: Draft, rows: readonly StaleRow[]): Draft {
  const next = { ...draft };
  for (const r of rows) {
    if (r.finish !== 'nonfoil' && r.finish !== 'foil') continue;
    const key = cellKey(r.scryfall_id, r.finish);
    const e = next[key];
    if (!e) continue;
    if (e.qty === r.current) delete next[key];
    else next[key] = { ...e, was: r.current, moved: true };
  }
  return next;
}

/** Keep your count in a flagged cell (or every flagged cell with no key). */
export function confirmMoved(draft: Draft, key?: string): Draft {
  const keys = key ? [key] : Object.keys(draft);
  if (!keys.some((k) => draft[k]?.moved)) return draft;
  const next = { ...draft };
  for (const k of keys) if (next[k]?.moved) next[k] = { ...next[k], moved: false };
  return next;
}

/** After a save: drop the cells that were sent, but keep any you changed while it
 *  was in flight — rebased on the count just saved, so the next save isn't stale. */
export function dropSaved(draft: Draft, sent: Draft): Draft {
  const next = { ...draft };
  for (const [k, s] of Object.entries(sent)) {
    const e = next[k];
    if (!e) continue;
    if (e.qty === s.qty) delete next[k];
    else next[k] = { ...e, was: s.qty, moved: false };
  }
  return next;
}

/** The save body for POST /api/collection/checklist. */
export function toChanges(draft: Draft): CountIn[] {
  return Object.values(draft)
    .filter((e) => e.qty !== e.was)
    .map((e) => ({ scryfall_id: e.id, finish: e.finish, qty: e.qty, expected: e.was }));
}

/** "Final Fantasy" · "Final Fantasy, Bloomburrow" · "Final Fantasy +2". */
export function familyLabel(families: readonly string[]): string {
  if (families.length <= 2) return families.join(', ') || 'Collection';
  return `${families[0]} +${families.length - 1}`;
}

/** Restore a stored draft, dropping anything malformed (old shapes, hand edits). */
export function readDraft(raw: string | null): Draft {
  if (!raw) return {};
  try {
    const obj = JSON.parse(raw) as unknown;
    if (!obj || typeof obj !== 'object') return {};
    const out: Record<string, DraftEntry> = {};
    for (const [k, v] of Object.entries(obj as Record<string, Partial<DraftEntry>>)) {
      if (
        v && typeof v.id === 'string' && (v.finish === 'nonfoil' || v.finish === 'foil') &&
        Number.isInteger(v.qty) && Number.isInteger(v.was) && k === cellKey(v.id, v.finish)
      ) {
        out[k] = {
          id: v.id, finish: v.finish, qty: v.qty as number, was: v.was as number,
          min: Number.isInteger(v.min) ? (v.min as number) : 0,
          unit: typeof v.unit === 'number' ? v.unit : null,
          name: typeof v.name === 'string' ? v.name : v.id,
          family: typeof v.family === 'string' ? v.family : '',
          ...(v.moved === true ? { moved: true } : {}),
        };
      }
    }
    return out;
  } catch {
    return {};
  }
}

/** Where keyboard focus goes from a cell. Enter/Tab walk DOWN the same finish
 *  (skipping printings without it); ←/→ switch finish within the row. */
export function nextCell(
  rows: readonly { finishes: readonly Finish[] }[],
  row: number,
  finish: Finish,
  move: 'down' | 'up' | 'left' | 'right',
): { row: number; finish: Finish } | null {
  if (move === 'left' || move === 'right') {
    const fs = rows[row]?.finishes ?? [];
    const i = fs.indexOf(finish) + (move === 'right' ? 1 : -1);
    return i >= 0 && i < fs.length ? { row, finish: fs[i] } : null;
  }
  const step = move === 'down' ? 1 : -1;
  for (let r = row + step; r >= 0 && r < rows.length; r += step) {
    if (rows[r].finishes.includes(finish)) return { row: r, finish };
  }
  return null;
}

const copies = (plus: number, minus: number) =>
  `${[plus ? `+${fmtInt(plus)}` : '', minus ? `−${fmtInt(minus)}` : ''].filter(Boolean).join(' ') || '±0'} ${plus + minus === 1 ? 'copy' : 'copies'}`;

/** The sheet summary while counting: the running diff (or the last save) in plain numbers. */
export function summaryLine(s: DraftSummary, saved: ChecklistOut | null): string {
  if (saved && !s.cells) {
    const n = saved.rows.length;
    return n
      ? `Saved ${fmtInt(n)} ${n === 1 ? 'count' : 'counts'} · ${copies(saved.copies_added, saved.copies_removed)}`
      : 'Nothing to save — every count matched';
  }
  if (!s.cells) return 'Counting · type how many you have; Enter moves down, ←/→ switch finish, Esc undoes a cell';
  const val = `${s.value >= 0 ? '+' : '−'}${fmtUsd(Math.abs(s.value))}`;
  return `Counting · ${fmtInt(s.cells)} ${s.cells === 1 ? 'change' : 'changes'} · ${copies(s.added, s.removed)} · ${val} at market${s.unpriced ? ` (${fmtInt(s.unpriced)} unpriced)` : ''}`;
}

// Collection import (Add cards → Import a collection): what a read — a Moxfield
// collection or binder through the companion, or another app's exported file —
// would do to your inventory, under the mode you pick for this
// import. Pure — the engine (collection_sync.preview_lines / apply_lines) is
// the source of truth; this mirrors its one rule for display:
//   add     → you'll own current + incoming
//   replace → you'll own incoming (3 → 5 nets +2, 3 → 1 nets −2)
// Printings the read doesn't list are never touched either way.
import type { CollectionPreviewOut, ImportRowOut } from './api';

export type ImportMode = 'add' | 'replace';

export const afterImport = (r: Pick<ImportRowOut, 'current' | 'incoming'>, mode: ImportMode): number =>
  mode === 'add' ? r.current + r.incoming : r.incoming;

export type ChangeRow = ImportRowOut & { after: number; delta: number };

/** The rows whose count changes under `mode`, biggest moves first, then by set and number. */
export function changedRows(rows: readonly ImportRowOut[], mode: ImportMode): ChangeRow[] {
  const out: ChangeRow[] = [];
  for (const r of rows) {
    const after = afterImport(r, mode);
    if (after !== r.current) out.push({ ...r, after, delta: after - r.current });
  }
  return out;
}

export type Effect = {
  /** Printings whose count changes. */
  printings: number;
  /** Printings you don't own yet. */
  newPrintings: number;
  copiesIn: number;
  copiesOut: number;
};

export function effectOf(rows: readonly ImportRowOut[], mode: ImportMode): Effect {
  const e: Effect = { printings: 0, newPrintings: 0, copiesIn: 0, copiesOut: 0 };
  for (const r of rows) {
    const d = afterImport(r, mode) - r.current;
    if (!d) continue;
    e.printings += 1;
    if (r.current === 0) e.newPrintings += 1;
    if (d > 0) e.copiesIn += d;
    else e.copiesOut -= d;
  }
  return e;
}

const n = (x: number) => x.toLocaleString('en-US');
const plural = (x: number, one: string, many = `${one}s`) => `${n(x)} ${x === 1 ? one : many}`;

/** "+212 copies · 40 new printings" / "−3 copies" / "No change". */
export function effectLine(e: Effect): string {
  if (!e.printings) return 'No change';
  const parts: string[] = [];
  if (e.copiesIn) parts.push(`+${plural(e.copiesIn, 'copy', 'copies')}`);
  if (e.copiesOut) parts.push(`−${plural(e.copiesOut, 'copy', 'copies')}`);
  if (e.newPrintings) parts.push(plural(e.newPrintings, 'new printing'));
  return parts.join(' · ');
}

/** Rows replace would set below the copies pledged to built decks (the server refuses those). */
export const belowPledged = (rows: readonly Pick<ImportRowOut, 'incoming' | 'pledged'>[]): number =>
  rows.filter((r) => r.incoming < (r.pledged ?? 0)).length;

/** A Moxfield share link → what it is, or null. */
export function shareLinkKind(url: string): 'collection' | 'binder' | null {
  const u = url.trim();
  if (/^https:\/\/(?:www\.)?moxfield\.com\/collection\/[A-Za-z0-9_-]{4,64}(?:[/?#]|$)/i.test(u)) return 'collection';
  if (/^https:\/\/(?:www\.)?moxfield\.com\/binders\/[A-Za-z0-9_-]{4,64}(?:[/?#]|$)/i.test(u)) return 'binder';
  return null;
}

/** The review's heading: what was read, in the owner's words. */
export function readTitle(scope: 'collection' | 'binder', id: string | null, name: string | null): string {
  if (scope === 'binder') return name ? `Moxfield binder · ${name}` : 'Moxfield binder';
  return id ? 'Moxfield collection (shared link)' : 'Your Moxfield collection';
}

/** The review's heading for an exported file: `ManaBox export · collection.csv`. */
export const fileTitle = (formatName: string, filename: string): string => `${formatName} export · ${filename}`;

/** The import's history entry, in words: `web:moxfield binder · X` → `Moxfield binder · X`,
 *  `web:file ManaBox · a.csv` → `ManaBox file · a.csv`. */
export function importedLabel(label: string): string {
  const s = label.replace(/^web:/, '');
  const file = /^file (.+?) · (.+)$/.exec(s);
  if (file) return `${file[1]} file · ${file[2]}`;
  return s.replace(/^moxfield /, 'Moxfield ');
}

/** Exported files are read in the browser and posted whole; the server caps them (25M characters). */
export const MAX_FILE_BYTES = 25_000_000;

/** Notes under the review: what was left out and what stays as it is. */
export function previewNotes(p: Pick<CollectionPreviewOut, 'skipped' | 'not_in_read' | 'not_found'>): string[] {
  const out: string[] = [];
  const skipped = [p.skipped.proxy ? plural(p.skipped.proxy, 'proxy', 'proxies') : '', p.skipped.digital ? `${plural(p.skipped.digital, 'digital copy', 'digital copies')} (Arena/MTGO)` : ''].filter(Boolean);
  if (skipped.length) out.push(`Skipped ${skipped.join(' and ')}.`);
  if (p.not_found.length) out.push(`${plural(p.not_found.length, 'line')} didn’t match a printing and will be left out.`);
  if (p.not_in_read) out.push(`${plural(p.not_in_read, 'printing')} you own ${p.not_in_read === 1 ? 'isn’t' : 'aren’t'} in this read — left as ${p.not_in_read === 1 ? 'it is' : 'they are'}.`);
  return out;
}

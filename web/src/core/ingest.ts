// Add-cards review model: every mode (search, paste, deck) stages ReviewLines;
// the user fixes printing / finish / qty per line, then one commit adds them.
// Framework-free.
import type { CommitItem, PrintingOut, ResolvedLineOut } from './api';

export type Finish = 'nonfoil' | 'foil';
type LineStatus = ResolvedLineOut['status'];

export type ReviewLine = {
  key: string;
  raw: string;
  name: string;
  qty: number;
  finish: Finish;
  status: LineStatus;
  candidates: PrintingOut[];
  chosen: string | null;
  note: string | null;
  /** The list section the line sat under (mainboard, commander, sideboard…); decks map it to a board. */
  section?: string;
  /** The user can drop a line without deleting it from the paste. */
  include: boolean;
};

export const chosenPrinting = (l: ReviewLine): PrintingOut | undefined =>
  l.candidates.find((c) => c.scryfall_id === l.chosen);

/** A finish the chosen printing actually has: keep the wish when possible. */
export function fitFinish(p: PrintingOut | undefined, want: Finish): Finish {
  if (!p || p.finishes.includes(want)) return want;
  return (p.finishes[0] as Finish | undefined) ?? 'nonfoil';
}

export function fromResolved(lines: readonly ResolvedLineOut[], prefix = 'r'): ReviewLine[] {
  return lines.map((l, i) => {
    const chosen = l.chosen ?? null;
    const finish = fitFinish(l.candidates.find((c) => c.scryfall_id === chosen), l.finish);
    return {
      key: `${prefix}${i}`, raw: l.raw, name: l.name, qty: l.qty, finish, status: l.status,
      candidates: l.candidates, chosen, note: l.note ?? null, section: l.section, include: l.status !== 'unresolved',
    };
  });
}

/** Stage one picked printing (search mode). Same printing + finish bumps qty. */
export function stagePrinting(lines: readonly ReviewLine[], p: PrintingOut, finish: Finish = 'nonfoil'): ReviewLine[] {
  const f = fitFinish(p, finish);
  const hit = lines.find((l) => l.chosen === p.scryfall_id && l.finish === f);
  if (hit) return lines.map((l) => (l === hit ? { ...l, qty: l.qty + 1, include: true } : l));
  const line: ReviewLine = {
    key: `s:${p.scryfall_id}:${f}:${lines.length}`, raw: p.set_name ?? p.set_code.toUpperCase(), name: p.name, qty: 1, finish: f,
    status: 'exact', candidates: [p], chosen: p.scryfall_id, note: null, include: true,
  };
  return [...lines, line];
}

/** Change one line; switching printing re-fits the finish. */
export function updateLine(lines: readonly ReviewLine[], key: string, patch: Partial<Pick<ReviewLine, 'qty' | 'finish' | 'chosen' | 'include'>>): ReviewLine[] {
  return lines.map((l) => {
    if (l.key !== key) return l;
    const next = { ...l, ...patch };
    if (patch.chosen !== undefined) next.finish = fitFinish(chosenPrinting(next), next.finish);
    if (patch.qty !== undefined) next.qty = Math.max(1, Math.min(9999, Math.trunc(patch.qty) || 1));
    return next;
  });
}

/** Included, resolved lines as commit items, merged per printing × finish. */
export function commitItems(lines: readonly ReviewLine[]): CommitItem[] {
  const m = new Map<string, CommitItem>();
  for (const l of lines) {
    if (!l.include || !l.chosen) continue;
    const k = `${l.chosen}|${l.finish}`;
    const cur = m.get(k);
    if (cur) cur.qty += l.qty;
    else m.set(k, { scryfall_id: l.chosen, finish: l.finish, qty: l.qty });
  }
  return [...m.values()];
}

export type ReviewStats = { copies: number; lines: number; picked: number; unresolved: number; skipped: number };

export function reviewStats(lines: readonly ReviewLine[]): ReviewStats {
  let copies = 0, picked = 0, unresolved = 0, skipped = 0;
  for (const l of lines) {
    if (l.status === 'unresolved') unresolved++;
    else if (!l.include) skipped++;
    else {
      copies += l.qty;
      if (l.status === 'ambiguous') picked++;
    }
  }
  return { copies, lines: lines.length, picked, unresolved, skipped };
}

const norm = (s: string) => s.toLowerCase().replace(/[’']/g, "'").replace(/\s+/g, ' ').trim();

/** The muted line under a row's name: the engine's note, else the source line only
 *  when it says something the row doesn't — a misspelling, a flavor name, a set name
 *  from search, or a printing asked for on a line that only matched a best guess.
 *  `1 Insist` under *Insist* (count, set and number already shown) is noise. */
export function sourceLine(l: Pick<ReviewLine, 'raw' | 'name' | 'note' | 'status'>): string | null {
  if (l.note) return l.note;
  const named = l.raw.replace(/^\s*\d+\s*x?\s+/i, '');
  const bare = named
    .replace(/(\s+\*[a-z]+\*)+\s*$/i, '')
    .replace(/\s+[([][a-z0-9]{2,6}[)\]](\s+\S+)?\s*$/i, '');
  if (bare !== named && l.status !== 'exact') return l.raw;
  const want = norm(bare);
  if (!want) return null;
  const names = [l.name, ...l.name.split(' // ')].map(norm);
  return names.includes(want) ? null : l.raw;
}

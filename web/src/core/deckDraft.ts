// Deck editor draft: a pure, framework-free model of an in-progress decklist.
// The editor renders it; every edit is a function returning a new draft, so the
// diff against the saved version (and Save's payload) is always derivable.
import type { DeckCardOut, DraftCardIn, PrintingOut } from './api';
import { DECK_SECTIONS, deckSection } from './decks';

export type Board = DraftCardIn['board'];
export type DraftFinish = DraftCardIn['finish'];

export type DraftRow = {
  key: string;
  printing: PrintingOut;
  board: Board;
  finish: DraftFinish;
  count: number;
  /** Count in the saved version (0 = newly added). */
  saved: number;
};

export type Draft = { rows: DraftRow[] };

const rowKey = (sid: string, board: Board, finish: DraftFinish) => `${sid}|${board}|${finish}`;

/** Boards that count toward the deck's size. */
const COUNTED: readonly Board[] = ['commander', 'main', 'companion'];

export function draftFromDeck(cards: readonly DeckCardOut[]): Draft {
  return {
    rows: cards
      .filter((c) => c.board !== 'token')
      .map((c) => ({
        key: rowKey(c.printing.scryfall_id, c.board, c.finish),
        printing: { ...c.printing, type_line: c.printing.type_line ?? c.type_line, cmc: c.printing.cmc ?? c.cmc },
        board: c.board,
        finish: c.finish,
        count: c.count,
        saved: c.count,
      })),
  };
}

/** Add one copy of a printing to a board (sums into an existing row). Defaults
 *  to 'either' finish so building picks whichever copy is free. */
export function addCard(d: Draft, p: PrintingOut, board: Board = 'main', finish: DraftFinish = 'either'): Draft {
  const key = rowKey(p.scryfall_id, board, finish);
  const hit = d.rows.find((r) => r.key === key);
  if (hit) return setCount(d, key, hit.count + 1);
  return { rows: [...d.rows, { key, printing: p, board, finish, count: 1, saved: 0 }] };
}

/** Set a row's count. A new row dropped to 0 disappears; a saved row stays (count 0 = removed, undoable). */
export function setCount(d: Draft, key: string, count: number): Draft {
  const n = Math.max(0, Math.min(999, Math.floor(count)));
  return {
    rows: d.rows
      .map((r) => (r.key === key ? { ...r, count: n } : r))
      .filter((r) => r.count > 0 || r.saved > 0),
  };
}

/** Re-key a row onto another board/finish, merging into a row that already sits there. */
function rekey(d: Draft, key: string, board: Board, finish: DraftFinish): Draft {
  const row = d.rows.find((r) => r.key === key);
  if (!row) return d;
  const next = rowKey(row.printing.scryfall_id, board, finish);
  if (next === key) return d;
  const moved = row.count;
  let rows = d.rows.map((r) => (r.key === key ? { ...r, count: 0 } : r));
  const target = rows.find((r) => r.key === next);
  rows = target
    ? rows.map((r) => (r.key === next ? { ...r, count: r.count + moved } : r))
    : [...rows, { ...row, key: next, board, finish, count: moved, saved: 0 }];
  return { rows: rows.filter((r) => r.count > 0 || r.saved > 0) };
}

export const moveCard = (d: Draft, key: string, board: Board) => {
  const row = d.rows.find((r) => r.key === key);
  return row ? rekey(d, key, board, row.finish) : d;
};

export const setFinish = (d: Draft, key: string, finish: DraftFinish) => {
  const row = d.rows.find((r) => r.key === key);
  return row ? rekey(d, key, row.board, finish) : d;
};

export type DraftStats = { size: number; target: number | null; added: number; removed: number; dirty: boolean };

/** Deck size (commander + main + companion) vs the format's target, and the
 *  card-quantity diff vs the saved version. */
export function draftStats(d: Draft, format: string | null | undefined): DraftStats {
  let size = 0, added = 0, removed = 0;
  for (const r of d.rows) {
    if (COUNTED.includes(r.board)) size += r.count;
    const delta = r.count - r.saved;
    if (delta > 0) added += delta;
    else removed -= delta;
  }
  const f = (format ?? '').toLowerCase();
  const target = ['commander', 'edh', 'brawl', 'paupercommander'].includes(f) ? 100 : f === 'oathbreaker' ? 60 : f ? 60 : null;
  return { size, target, added, removed, dirty: added + removed > 0 };
}

export type DraftSection = { key: string; label: string; count: number; rows: DraftRow[] };

/** Rows grouped like the deck view (Commander · Creatures · … · Sideboard · Maybe), name order within. */
export function draftSections(d: Draft): DraftSection[] {
  const m = new Map<string, DraftRow[]>();
  for (const r of d.rows) {
    const s = deckSection({ board: r.board, type_line: r.printing.type_line ?? null });
    m.set(s, [...(m.get(s) ?? []), r]);
  }
  return DECK_SECTIONS.filter((s) => m.has(s)).map((s) => {
    const rows = m.get(s)!.sort((a, b) => a.printing.name.localeCompare(b.printing.name));
    return { key: s, label: s, count: rows.reduce((t, r) => t + r.count, 0), rows };
  });
}

/** Save payload: every live row (count 0 rows are dropped = removed). */
export const draftCards = (d: Draft): DraftCardIn[] =>
  d.rows.filter((r) => r.count > 0).map((r) => ({ scryfall_id: r.printing.scryfall_id, board: r.board, finish: r.finish, count: r.count }));

/** Oracle ids already in the deck (any board), to mark search/suggestion hits. */
export const draftOracles = (d: Draft): Set<string> =>
  new Set(d.rows.filter((r) => r.count > 0 && r.printing.oracle_id).map((r) => r.printing.oracle_id!));

export const commanderName = (d: Draft): string | null =>
  d.rows.find((r) => r.board === 'commander' && r.count > 0)?.printing.name ?? null;

/** Could this printing lead a Commander deck? (legendary creature / "can be your commander"). */
export const canCommand = (p: Pick<PrintingOut, 'type_line'>): boolean =>
  /\bLegendary\b.*\b(Creature|Planeswalker)\b/.test(p.type_line ?? '') || /\bBackground\b/.test(p.type_line ?? '');

/** Owned-and-free first, then owned, then the rest (stable). */
export function collectionFirst(items: readonly PrintingOut[]): PrintingOut[] {
  const rank = (p: PrintingOut) => ((p.free ?? 0) > 0 ? 0 : Object.values(p.owned ?? {}).some((n) => n > 0) ? 1 : 2);
  return [...items].map((x, i) => [x, i] as const).sort((a, b) => rank(a[0]) - rank(b[0]) || a[1] - b[1]).map(([x]) => x);
}

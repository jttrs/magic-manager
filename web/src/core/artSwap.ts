// On-theme art swaps: joins the engine's per-printing answer (`/api/art/swaps`)
// to the editor's draft rows. Pure — the Art tab renders it, edits go through
// deckDraft.swapPrinting.
import type { ArtSwapsOut, PrintingOut } from './api';
import { fmtUsd } from './format';
import { swapPrinting, type Draft, type DraftFinish, type DraftRow } from './deckDraft';

type ArtStatus = 'swap' | 'on_theme' | 'swapped' | 'none';

type FreeByFinish = NonNullable<ArtSwapsOut['free_by_finish']>;

/** Where a swap would land: the finish to put the row on and how many copies
 *  are free in it. `covered` = those free copies fill the whole row, so the
 *  swap pledges nothing you'd have to take from another deck. */
export type SwapChoice = { finish: DraftFinish | undefined; free: number; covered: boolean };

export type ArtRow = {
  row: DraftRow;
  status: ArtStatus;
  /** The best on-theme printing (yours with the most free copies, else the cheapest). */
  pick: PrintingOut | null;
  /** Every on-theme printing of the card, best first. */
  candidates: PrintingOut[];
  /** Per-finish free copies, for judging any candidate (see `choiceFor`). */
  freeBy: FreeByFinish;
  /** How the best printing would land (null without one). */
  pickChoice: SwapChoice | null;
};

export type ArtView = { swap: ArtRow[]; onTheme: ArtRow[]; none: ArtRow[]; freeSwaps: number };

/** Distinct printings the draft uses now — the query's input, sorted so the key is stable. */
export const draftPrintingIds = (d: Draft): string[] =>
  [...new Set(d.rows.filter((r) => r.count > 0).map((r) => r.printing.scryfall_id))].sort();

const owned = (p: PrintingOut) => Object.values(p.owned ?? {}).reduce((s, n) => s + n, 0);

/** Pick the finish for swapping `row` onto `p`: the row's own finish when its
 *  free copies cover the count, else another finish of `p` that does ('either'
 *  tries nonfoil first); when none covers it, the usual fallback (finish
 *  undefined) with the most free copies of any finish reported. */
export function swapChoice(row: DraftRow, p: PrintingOut, freeBy: FreeByFinish): SwapChoice {
  const f = freeBy[p.scryfall_id] ?? {};
  const have = (fin: string) => (p.finishes.includes(fin as never) ? f[fin] ?? 0 : 0);
  const order: DraftFinish[] = row.finish === 'either' ? ['nonfoil', 'foil'] : [row.finish, ...(['nonfoil', 'foil'] as const).filter((x) => x !== row.finish)];
  const hit = order.find((fin) => fin !== 'either' && have(fin) >= row.count && have(fin) > 0);
  if (hit) return { finish: hit, free: have(hit), covered: true };
  return { finish: undefined, free: Math.max(have('nonfoil'), have('foil')), covered: false };
}

/** A candidate's choice for a row (free only when it covers the row). */
export const choiceFor = (r: ArtRow, p: PrintingOut): SwapChoice => swapChoice(r.row, p, r.freeBy);

/** The printing an undoable row came from. */
export const wasPrinting = (row: DraftRow): PrintingOut | undefined => row.origin?.printing ?? row.absorbed?.[0]?.printing;

/** Each live draft row with its on-theme answer. A row already swapped stays
 *  'swapped' (undoable) even before the next answer arrives. */
export function artView(d: Draft, data: ArtSwapsOut | undefined): ArtView {
  const out: ArtView = { swap: [], onTheme: [], none: [], freeSwaps: 0 };
  if (!data) return out;
  const freeBy = data.free_by_finish ?? {};
  const bySid = new Map(data.rows.map((r) => [r.scryfall_id, r]));
  const pr = (sid: string | null | undefined) => (sid ? data.printings[sid] ?? null : null);
  for (const row of d.rows) {
    if (row.count <= 0) continue;
    const ans = bySid.get(row.printing.scryfall_id) ?? (row.origin ? bySid.get(row.origin.printing.scryfall_id) : undefined);
    const candidates = (ans?.candidates ?? []).map(pr).filter((p): p is PrintingOut => p != null);
    if ((row.origin || row.absorbed?.length) && (ans?.status === 'on_theme' || candidates.some((c) => c.scryfall_id === row.printing.scryfall_id) || !ans)) {
      out.onTheme.push({ row, status: 'swapped', pick: row.printing, candidates, freeBy, pickChoice: null });
    } else if (ans?.status === 'on_theme') {
      out.onTheme.push({ row, status: 'on_theme', pick: row.printing, candidates, freeBy, pickChoice: null });
    } else if (ans?.status === 'swap') {
      const pick = pr(ans.pick);
      const pickChoice = pick ? swapChoice(row, pick, freeBy) : null;
      out.swap.push({ row, status: 'swap', pick, candidates, freeBy, pickChoice });
      if (pickChoice?.covered) out.freeSwaps += 1;
    } else {
      out.none.push({ row, status: 'none', pick: null, candidates: [], freeBy, pickChoice: null });
    }
  }
  const name = (a: ArtRow, b: ArtRow) => a.row.printing.name.localeCompare(b.row.printing.name);
  out.swap.sort((a, b) => Number(!!b.pickChoice?.covered) - Number(!!a.pickChoice?.covered) || name(a, b));
  out.onTheme.sort(name);
  out.none.sort(name);
  return out;
}

/** Swap every row whose best on-theme printing you have enough free copies of (in one finish) to fill it. */
export function swapAllFree(d: Draft, view: ArtView): Draft {
  return view.swap.reduce((acc, r) => (r.pick && r.pickChoice?.covered ? swapPrinting(acc, r.row.key, r.pick, r.pickChoice.finish) : acc), d);
}

/** One short fact for a printing choice: free copies (`free`, default the
 *  printing's total), else its price. */
export function choiceNote(p: PrintingOut, free: number = p.free ?? 0): string {
  if (free > 0) return `${free} free`;
  const price = p.price_usd ?? p.price_usd_foil;
  const usd = price != null ? fmtUsd(price) : 'no price';
  return owned(p) > 0 ? `${usd} · yours, all in decks` : usd;
}

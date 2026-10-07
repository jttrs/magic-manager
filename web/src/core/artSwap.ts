// On-theme art swaps: joins the engine's per-printing answer (`/api/art/swaps`)
// to the editor's draft rows. Pure — the Art tab renders it, edits go through
// deckDraft.swapPrinting.
import type { ArtSwapsOut, PrintingOut } from './api';
import { fmtUsd } from './format';
import { swapPrinting, type Draft, type DraftRow } from './deckDraft';

type ArtStatus = 'swap' | 'on_theme' | 'swapped' | 'none';

export type ArtRow = {
  row: DraftRow;
  status: ArtStatus;
  /** The best on-theme printing (yours with the most free copies, else the cheapest). */
  pick: PrintingOut | null;
  /** Every on-theme printing of the card, best first. */
  candidates: PrintingOut[];
};

export type ArtView = { swap: ArtRow[]; onTheme: ArtRow[]; none: ArtRow[]; freeSwaps: number };

/** Distinct printings the draft uses now — the query's input, sorted so the key is stable. */
export const draftPrintingIds = (d: Draft): string[] =>
  [...new Set(d.rows.filter((r) => r.count > 0).map((r) => r.printing.scryfall_id))].sort();

const owned = (p: PrintingOut) => Object.values(p.owned ?? {}).reduce((s, n) => s + n, 0);
export const isFree = (p: PrintingOut | null | undefined) => (p?.free ?? 0) > 0;

/** Each live draft row with its on-theme answer. A row already swapped stays
 *  'swapped' (undoable) even before the next answer arrives. */
export function artView(d: Draft, data: ArtSwapsOut | undefined): ArtView {
  const out: ArtView = { swap: [], onTheme: [], none: [], freeSwaps: 0 };
  if (!data) return out;
  const bySid = new Map(data.rows.map((r) => [r.scryfall_id, r]));
  const pr = (sid: string | null | undefined) => (sid ? data.printings[sid] ?? null : null);
  for (const row of d.rows) {
    if (row.count <= 0) continue;
    const ans = bySid.get(row.printing.scryfall_id) ?? (row.origin ? bySid.get(row.origin.printing.scryfall_id) : undefined);
    const candidates = (ans?.candidates ?? []).map(pr).filter((p): p is PrintingOut => p != null);
    if (row.origin && (ans?.status === 'on_theme' || candidates.some((c) => c.scryfall_id === row.printing.scryfall_id) || !ans)) {
      out.onTheme.push({ row, status: 'swapped', pick: row.printing, candidates });
    } else if (ans?.status === 'on_theme') {
      out.onTheme.push({ row, status: 'on_theme', pick: row.printing, candidates });
    } else if (ans?.status === 'swap') {
      const pick = pr(ans.pick);
      out.swap.push({ row, status: 'swap', pick, candidates });
      if (isFree(pick)) out.freeSwaps += 1;
    } else {
      out.none.push({ row, status: 'none', pick: null, candidates: [] });
    }
  }
  const name = (a: ArtRow, b: ArtRow) => a.row.printing.name.localeCompare(b.row.printing.name);
  out.swap.sort((a, b) => Number(isFree(b.pick)) - Number(isFree(a.pick)) || name(a, b));
  out.onTheme.sort(name);
  out.none.sort(name);
  return out;
}

/** Swap every row whose best on-theme printing you have free copies of. */
export function swapAllFree(d: Draft, view: ArtView): Draft {
  return view.swap.reduce((acc, r) => (r.pick && isFree(r.pick) ? swapPrinting(acc, r.row.key, r.pick) : acc), d);
}

/** One short fact for a printing choice: free copies, else its price. */
export function choiceNote(p: PrintingOut): string {
  if (isFree(p)) return `${p.free} free`;
  const price = p.price_usd ?? p.price_usd_foil;
  const usd = price != null ? fmtUsd(price) : 'no price';
  return owned(p) > 0 ? `${usd} · yours, all in decks` : usd;
}

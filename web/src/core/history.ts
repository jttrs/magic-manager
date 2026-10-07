// Purchase history view-model: the acquisition timeline over the provenance ledger.
// Framework-free — filter, month grouping, deck-move runs, and the drill-in cards.
import { z } from 'zod';
import type { HistoryEntryOut, HistoryLineOut } from './api';
import { typeGroup, TYPE_GROUPS } from './cardFacts';
import { fromPrinting, groupCards, type GuideCard, type GuideGroup } from './guideCard';

const KINDS = ['deck', 'pool', 'singles', 'checklist', 'unknown', 'move'] as const;
export type HistoryKind = (typeof KINDS)[number];

export const KIND_LABEL: Record<HistoryKind, string> = {
  deck: 'Precon',
  pool: 'Card pool',
  singles: 'Singles',
  checklist: 'Checklist',
  unknown: 'Unknown',
  move: 'Deck move',
};

export const KIND_HELP: Record<HistoryKind, string> = {
  deck: 'A playable product: a precon or Jumpstart pack you bought, or one Find products identified in your cards.',
  pool: 'A card pool: land pack, scene box, Secret Lair drop and the like.',
  singles: 'Cards added one by one: search, pasted lists, scans, by hand.',
  checklist: 'A bulk checklist ingest. Which product the cards came out of was not recorded.',
  unknown: 'Copies reconstructed when the ledger began, with no known source.',
  move: 'Cards pledged to a built deck or released from one. What you own does not change.',
};

const list = <T extends z.ZodTypeAny>(item: T) =>
  z.preprocess((v) => (v == null ? undefined : Array.isArray(v) ? v : [v]), z.array(item));
const isoDay = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

export const historySearch = z.object({
  q: z.string().catch('').default(''),
  /** Kinds to keep; empty = all. */
  kinds: list(z.enum(KINDS)).catch([]).default([]),
  /** Inclusive day bounds (YYYY-MM-DD). */
  from: isoDay.optional().catch(undefined),
  to: isoDay.optional().catch(undefined),
  /** The entry open in the inspector (ingest id). */
  entry: z.coerce.number().int().positive().optional().catch(undefined),
  view: z.enum(['grid', 'list']).catch('list').default('list'),
});
export type HistorySearch = z.infer<typeof historySearch>;

export type HistoryFilters = Pick<HistorySearch, 'q' | 'kinds' | 'from' | 'to'>;

const day = (at: string) => at.slice(0, 10);

export function filterHistory(entries: readonly HistoryEntryOut[], f: HistoryFilters): HistoryEntryOut[] {
  const q = f.q.trim().toLowerCase();
  return entries.filter((e) => {
    if (f.kinds.length && !f.kinds.includes(e.kind)) return false;
    const d = day(e.at);
    if (f.from && d < f.from) return false;
    if (f.to && d > f.to) return false;
    if (!q) return true;
    return [e.title, e.detail, e.product, e.set_code, KIND_LABEL[e.kind]].some((s) => s?.toLowerCase().includes(q));
  });
}

export function kindCounts(entries: readonly HistoryEntryOut[]): { value: HistoryKind; label: string; count: number }[] {
  const n = new Map<HistoryKind, number>();
  for (const e of entries) n.set(e.kind, (n.get(e.kind) ?? 0) + 1);
  return KINDS.filter((k) => n.has(k)).map((k) => ({ value: k, label: KIND_LABEL[k], count: n.get(k)! }));
}

/** A timeline row: one entry, or a run of consecutive same-day deck moves shown as one quiet line. */
export type TimelineRow =
  | { type: 'entry'; key: string; entry: HistoryEntryOut }
  | { type: 'moves'; key: string; entries: HistoryEntryOut[] };

export type MonthGroup = { key: string; label: string; rows: TimelineRow[]; copiesIn: number; valueUsd: number };

const MONTH = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' });
const monthLabel = (ym: string) => MONTH.format(new Date(`${ym}-01T00:00:00Z`));

/** Newest-first entries → month groups. A day's deck moves gather into ONE quiet run row (≥ 2),
 *  placed where the day's newest move falls — they interleave with the precons they build. */
export function groupTimeline(entries: readonly HistoryEntryOut[]): MonthGroup[] {
  const groups: MonthGroup[] = [];
  const runs = new Map<string, Extract<TimelineRow, { type: 'moves' }>>();
  const moveCount = new Map<string, number>();
  for (const e of entries) if (e.kind === 'move') moveCount.set(day(e.at), (moveCount.get(day(e.at)) ?? 0) + 1);
  for (const e of entries) {
    const ym = e.at.slice(0, 7);
    let g = groups[groups.length - 1];
    if (!g || g.key !== ym) groups.push((g = { key: ym, label: monthLabel(ym), rows: [], copiesIn: 0, valueUsd: 0 }));
    if (e.kind !== 'move') {
      g.copiesIn += e.held;
      g.valueUsd += e.value_usd;
    } else if ((moveCount.get(day(e.at)) ?? 0) > 1) {
      const run = runs.get(day(e.at));
      if (run) run.entries.push(e);
      else {
        const row = { type: 'moves' as const, key: `moves:${day(e.at)}`, entries: [e] };
        runs.set(day(e.at), row);
        g.rows.push(row);
      }
      continue;
    }
    g.rows.push({ type: 'entry', key: String(e.ingest_id), entry: e });
  }
  for (const g of groups) g.valueUsd = Math.round(g.valueUsd * 100) / 100;
  return groups;
}

/** "Built 12 decks · broke down 1" for a run of moves. */
export function movesSummary(entries: readonly HistoryEntryOut[]): string {
  const built = entries.filter((e) => e.method === 'deck-assign').length;
  const broke = entries.length - built;
  const parts = [built && `Built ${built} deck${built === 1 ? '' : 's'}`, broke && `broke down ${broke}`].filter(Boolean) as string[];
  const s = parts.join(' · ');
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** When the entry is dated, in plain words. */
export function datedNote(e: Pick<HistoryEntryOut, 'dated'>): string | null {
  if (e.dated === 'identified') return 'Identified in your cards by Find products — not the purchase date';
  if (e.dated === 'reconstructed') return 'Reconstructed when the ledger began';
  return null;
}

/** One drill-in line → the shared card model: the exact printing + finish, its held copies as "owned". */
export function fromHistoryLine(l: HistoryLineOut): GuideCard {
  const base = fromPrinting(l.printing);
  // In/out only when the line moved after it came in; otherwise the held count says it all.
  const moved = l.copies_out ? [`+${l.copies_in} in`, `−${l.copies_out} out`] : [];
  return {
    ...base,
    key: `${l.printing.scryfall_id}|${l.finish}`,
    finish: l.finish,
    price: l.unit_usd,
    owned: { [l.finish]: Math.max(l.held, 0) } as GuideCard['owned'],
    missing: l.held <= 0,
    tags: [...moved, ...base.tags],
    lines: { plain: `${Math.max(l.held, 0)} ${l.printing.name}`, manapool: '', tcgplayer: '' },
  };
}

export function historyCardGroups(lines: readonly HistoryLineOut[]): GuideGroup[] {
  const cards = lines.map(fromHistoryLine).map((c) => ({ ...c, group: typeGroup(c.typeLine ?? null) }));
  return groupCards(cards, TYPE_GROUPS).map((g) => {
    const copies = lines.filter((l) => typeGroup(l.printing.type_line ?? null) === g.key).reduce((t, l) => t + Math.max(l.held, 0), 0);
    return { ...g, label: copies === g.items.length ? g.label : `${g.label} · ${copies}` };
  });
}

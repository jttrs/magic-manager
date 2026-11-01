// Purchase history view-model: the acquisition timeline over the provenance ledger.
// Framework-free — filter, month grouping, deck-move runs, and the drill-in cards.
import { z } from 'zod';
import type { HistoryEntryOut, HistoryLineOut, PurchaseOut, RevertLineOut, RevertPlanOut } from './api';
import { typeGroup, TYPE_GROUPS } from './cardFacts';
import { fmtCount } from './format';
import { fromPrinting, groupCards, type GuideCard, type GuideGroup } from './guideCard';
import { STATUS_LABEL } from './purchases';

const KINDS = ['deck', 'pool', 'singles', 'checklist', 'unknown', 'move', 'purchase', 'revert'] as const;
export type HistoryKind = (typeof KINDS)[number];

export const KIND_LABEL: Record<HistoryKind, string> = {
  deck: 'Precon',
  pool: 'Card pool',
  singles: 'Singles',
  checklist: 'Checklist',
  unknown: 'Unknown',
  move: 'Deck move',
  purchase: 'Store order',
  revert: 'Revert',
};

export const KIND_HELP: Record<HistoryKind, string> = {
  deck: 'A playable product: a precon or Jumpstart pack you bought, or one Find products identified in your cards.',
  pool: 'A card pool: land pack, scene box, Secret Lair drop and the like.',
  singles: 'Cards added one by one: search, pasted lists, scans, by hand.',
  checklist: 'A bulk checklist ingest. Which product the cards came out of was not recorded.',
  unknown: 'Copies reconstructed when the ledger began, with no known source.',
  move: 'Cards pledged to a built deck or released from one. What you own does not change.',
  purchase: 'An order read from your store order history (Mana Pool, TCGplayer, Card Kingdom) with what you paid. Orders not in your collection yet wait under Needs review.',
  revert: 'An import you took back out: the copies it added were removed (and any it removed put back). The original entry stays, marked reverted.',
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
  /** The store order open in the inspector (purchase id); wins over `entry`. */
  order: z.coerce.number().int().positive().optional().catch(undefined),
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

/** Kinds present, in canonical order; `orders` = store orders shown outside the ledger entries (Needs review, recorded only). */
export function kindCounts(entries: readonly HistoryEntryOut[], orders = 0): { value: HistoryKind; label: string; count: number }[] {
  const n = new Map<HistoryKind, number>();
  for (const e of entries) n.set(e.kind, (n.get(e.kind) ?? 0) + 1);
  if (orders) n.set('purchase', (n.get('purchase') ?? 0) + orders);
  return KINDS.filter((k) => n.has(k)).map((k) => ({ value: k, label: KIND_LABEL[k], count: n.get(k)! }));
}

// ---------- store orders, merged into the timeline ----------

/** Store orders that still need a decision: nothing added yet, or only part of it. */
const needsReview = (p: Pick<PurchaseOut, 'status'>): boolean => p.status === 'new' || p.status === 'partial';

export type MergedHistory = {
  /** Orders waiting for a decision, newest first — pinned above the timeline. */
  review: PurchaseOut[];
  /** Ledger entries to list: a partly-added order's entry is left out (the order shows once, under Needs review). */
  entries: HistoryEntryOut[];
  /** Those left-out entries: their copies are held, so totals still count them (and the order review links to them). */
  pending: HistoryEntryOut[];
  /** Settled orders with no ledger entry (nothing assignable — recorded only): a timeline row of their own. */
  orders: PurchaseOut[];
  /** Ledger entry (ingest id) → the store order it applied, so the row shows once with the order's facts. */
  orderOf: Map<number, PurchaseOut>;
};

const byOrderedDesc = (a: PurchaseOut, b: PurchaseOut) => (a.ordered_at < b.ordered_at ? 1 : a.ordered_at > b.ordered_at ? -1 : b.purchase_id - a.purchase_id);

/** One list from the ledger and the store orders: every order appears exactly once. */
export function mergeOrders(entries: readonly HistoryEntryOut[], purchases: readonly PurchaseOut[] = []): MergedHistory {
  const byId = new Map(purchases.map((p) => [p.purchase_id, p]));
  const orderOf = new Map<number, PurchaseOut>();
  const placed = new Set<number>();
  const kept: HistoryEntryOut[] = [];
  const pending: HistoryEntryOut[] = [];
  for (const e of entries) {
    const p = e.kind === 'purchase' && e.purchase_id != null ? byId.get(e.purchase_id) : undefined;
    if (p && needsReview(p)) {
      pending.push(e);
      continue;
    }
    if (p) {
      orderOf.set(e.ingest_id, p);
      placed.add(p.purchase_id);
    }
    kept.push(e);
  }
  const review = purchases.filter(needsReview).sort(byOrderedDesc);
  const orders = purchases.filter((p) => !needsReview(p) && !placed.has(p.purchase_id)).sort(byOrderedDesc);
  return { review, entries: kept, pending, orders, orderOf };
}

export const orderTitle = (p: Pick<PurchaseOut, 'store_name' | 'order_id'>): string => `${p.store_name} order #${p.order_id}`;

/** The same filters as the ledger entries: kind (Store order), order day, and text (store, order number, status). */
export function filterOrders(orders: readonly PurchaseOut[], f: HistoryFilters): PurchaseOut[] {
  if (f.kinds.length && !f.kinds.includes('purchase')) return [];
  const q = f.q.trim().toLowerCase();
  return orders.filter((p) => {
    const d = day(p.ordered_at);
    if (f.from && d < f.from) return false;
    if (f.to && d > f.to) return false;
    if (!q) return true;
    return [orderTitle(p), p.store_name, p.order_id, STATUS_LABEL[p.status], KIND_LABEL.purchase].some((s) => s.toLowerCase().includes(q));
  });
}

/** A timeline row: one entry, a store order with no ledger entry, or a run of consecutive same-day deck moves shown as one quiet line. */
export type TimelineRow =
  | { type: 'entry'; key: string; entry: HistoryEntryOut }
  | { type: 'order'; key: string; order: PurchaseOut }
  | { type: 'moves'; key: string; entries: HistoryEntryOut[] };

export type MonthGroup = { key: string; label: string; rows: TimelineRow[]; copiesIn: number; valueUsd: number };

const MONTH = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' });
const monthLabel = (ym: string) => MONTH.format(new Date(`${ym}-01T00:00:00Z`));

/** Newest-first entries → month groups. A day's deck moves gather into ONE quiet run row (≥ 2),
 *  placed where the day's newest move falls — they interleave with the precons they build.
 *  `orders` (newest first) interleave by order date as rows of their own; they hold no copies.
 *  `counted` entries add to their month's totals without a row (a partly-added order's entry). */
export function groupTimeline(entries: readonly HistoryEntryOut[], orders: readonly PurchaseOut[] = [], counted: readonly HistoryEntryOut[] = []): MonthGroup[] {
  const groups: MonthGroup[] = [];
  const runs = new Map<string, Extract<TimelineRow, { type: 'moves' }>>();
  const moveCount = new Map<string, number>();
  for (const e of entries) if (e.kind === 'move') moveCount.set(day(e.at), (moveCount.get(day(e.at)) ?? 0) + 1);
  const month = (at: string) => {
    const ym = at.slice(0, 7);
    let g = groups[groups.length - 1];
    if (!g || g.key !== ym) groups.push((g = { key: ym, label: monthLabel(ym), rows: [], copiesIn: 0, valueUsd: 0 }));
    return g;
  };
  let oi = 0;
  const ordersUpTo = (at: string | null) => {
    // An order goes before the first entry on an earlier day (same day: after that day's entries).
    while (oi < orders.length && (at == null || day(orders[oi].ordered_at) > day(at))) {
      const o = orders[oi++];
      month(o.ordered_at).rows.push({ type: 'order', key: `order:${o.purchase_id}`, order: o });
    }
  };
  for (const e of entries) {
    ordersUpTo(e.at);
    const g = month(e.at);
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
  ordersUpTo(null);
  for (const e of counted) {
    const g = groups.find((x) => x.key === e.at.slice(0, 7));
    if (!g) continue;
    g.copiesIn += e.held;
    g.valueUsd += e.value_usd;
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

// ---------- revert one import ----------

/** The confirm button: names exactly what goes. */
export function revertActionLabel(plan: Pick<RevertPlanOut, 'copies_removed' | 'copies_restored' | 'decks'>): string {
  if (plan.copies_removed) return `Remove ${fmtCount(plan.copies_removed, 'copy', 'copies')}`;
  if (plan.copies_restored) return `Put back ${fmtCount(plan.copies_restored, 'copy', 'copies')}`;
  return plan.decks.length ? 'Delete the decklist' : 'Revert';
}

/** One plain sentence: what the revert does to the collection and Decks. */
export function revertLead(plan: RevertPlanOut): string {
  const removed = plan.lines.filter((l) => l.remove > 0).length;
  const restored = plan.lines.filter((l) => l.restore > 0).length;
  const parts: string[] = [];
  if (plan.copies_removed) parts.push(`removes ${fmtCount(plan.copies_removed, 'copy', 'copies')} (${fmtCount(removed, 'printing', 'printings')}) from your collection`);
  if (plan.copies_restored) parts.push(`puts back ${fmtCount(plan.copies_restored, 'copy', 'copies')} (${fmtCount(restored, 'printing', 'printings')}) it took out`);
  if (plan.decks.length) parts.push(`deletes the decklist ${plan.decks.map((d) => d.name).join(', ')} it saved`);
  if (!parts.length) return 'Nothing to change.';
  const s = parts.length > 1 ? `${parts.slice(0, -1).join(', ')} and ${parts.at(-1)}` : parts[0];
  return `This ${s}.`;
}

/** Why a line blocks the revert, and the way out. */
export function revertBlockNote(l: RevertLineOut): string | null {
  if (l.blocker === 'removed') {
    return `Only ${l.held} of ${fmtCount(l.remove, 'copy', 'copies')} still came from this import — the rest were removed or moved since.`;
  }
  if (l.blocker === 'pledged') {
    const to = l.pledged_to ?? [];
    return `${fmtCount(l.pledged, 'copy is', 'copies are')} in ${to.length ? to.join(', ') : 'a built deck'} — break ${to.length > 1 ? 'those decks' : 'that deck'} down first.`;
  }
  return null;
}

/** The plan a refused revert answered with (409 detail), when the server sent one. */
export function planFromError(detail: unknown): RevertPlanOut | null {
  if (detail && typeof detail === 'object' && 'plan' in detail) {
    const p = (detail as { plan: unknown }).plan;
    if (p && typeof p === 'object' && 'lines' in p && 'ok' in p) return p as RevertPlanOut;
  }
  return null;
}

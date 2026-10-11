// Store orders view-model: what each order's status says, and the per-line
// "match what I own / add as new" decisions. Framework-free.
import type { PurchaseOut, ReviewLineOut } from './api';
import type { OrderStore } from './companion';

export type PurchaseStatus = PurchaseOut['status'];
export type Store = OrderStore;
export type Decision = { match: number; add: number };
export type Decisions = Record<number, Decision>;

export const STATUS_LABEL: Record<PurchaseStatus, string> = {
  new: 'Not added yet',
  partial: 'Partly added',
  done: 'In your collection',
  nothing: 'Recorded only',
};

/** Where an order stands, for the "read my orders" checklist: never read, or its saved status. */
export function listStatus(orderId: string, store: Store, purchases: readonly PurchaseOut[]): 'unread' | PurchaseStatus {
  return purchases.find((p) => p.store === store && p.order_id === orderId)?.status ?? 'unread';
}

/** Only exact single-card lines with copies left can be matched or added. */
export const isAssignable = (l: Pick<ReviewLineOut, 'kind' | 'printing' | 'remaining'>): boolean =>
  l.kind === 'single' && l.printing != null && l.remaining > 0;

const maxMatch = (l: ReviewLineOut) => Math.max(0, Math.min(l.remaining, l.matchable));

/** Fill every assignable line: match mode pairs the order with copies you own (nothing new);
 *  add mode brings the whole order in as new copies. */
export function defaultDecisions(lines: readonly ReviewLineOut[], mode: 'match' | 'add'): Decisions {
  const out: Decisions = {};
  for (const l of lines) {
    if (!isAssignable(l)) continue;
    out[l.line_no] = mode === 'match' ? { match: maxMatch(l), add: 0 } : { match: 0, add: l.remaining };
  }
  return out;
}

const whole = (n: number) => (Number.isFinite(n) ? Math.floor(n) : 0);

/** Keep a decision inside what the line allows: match ≤ min(remaining, matchable), add ≤ what is left after matching. */
export function clampDecision(l: ReviewLineOut, d: Decision): Decision {
  const match = Math.min(Math.max(0, whole(d.match)), maxMatch(l));
  const add = Math.min(Math.max(0, whole(d.add)), Math.max(0, l.remaining - match));
  return { match, add };
}

/** The request body for applying: lines with something to do. */
export function decisionsBody(decisions: Decisions): { line_no: number; match: number; add: number }[] {
  return Object.entries(decisions)
    .map(([no, d]) => ({ line_no: Number(no), match: d.match, add: d.add }))
    .filter((d) => d.match > 0 || d.add > 0)
    .sort((a, b) => a.line_no - b.line_no);
}

/** Copies matched, copies added, and what was paid for them (unit price × copies). */
export function decisionTotals(lines: readonly ReviewLineOut[], decisions: Decisions): { matched: number; added: number; paid: number } {
  let matched = 0;
  let added = 0;
  let paid = 0;
  for (const l of lines) {
    const d = decisions[l.line_no];
    if (!d) continue;
    matched += d.match;
    added += d.add;
    paid += (d.match + d.add) * (l.unit_usd ?? 0);
  }
  return { matched, added, paid: Math.round(paid * 100) / 100 };
}

/** Split into batches (the companion reads at most 100 orders per request). */
export function chunk<T>(items: readonly T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

/** "+$4.20" / "−$1.10" / "$0.00": a gain or loss with its sign. */
export function signedParts(v: number): { sign: '+' | '−' | ''; abs: number } {
  const r = Math.round(v * 100) / 100;
  return { sign: r > 0 ? '+' : r < 0 ? '−' : '', abs: Math.abs(r) };
}

/** paid − the store's own subtotal when they differ by a cent or more (replacements, refunds); otherwise null. */
export function subtotalGap(p: Pick<PurchaseOut, 'paid_usd' | 'subtotal_usd'>): number | null {
  if (p.subtotal_usd == null) return null;
  const gap = Math.round((p.paid_usd - p.subtotal_usd) * 100) / 100;
  return Math.abs(gap) >= 0.01 ? gap : null;
}

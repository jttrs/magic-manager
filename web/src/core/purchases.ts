// Store orders view-model: what each order's status says, what "Add to your collection" would add,
// and the paid-vs-worth summary. Framework-free.
import type { PurchaseOut, ReviewLineOut, TotalsOut } from './api';
import type { OrderStore } from './companion';

export type PurchaseStatus = PurchaseOut['status'];
export type Store = OrderStore;

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

/** Only exact single-card lines with copies left are added to your collection. */
export const isAddable = (l: Pick<ReviewLineOut, 'kind' | 'printing' | 'remaining'>): boolean =>
  l.kind === 'single' && l.printing != null && l.remaining > 0;

/** How many cards "Add to your collection" would bring in: every addable line's remaining copies. */
export const addableCopies = (lines: readonly ReviewLineOut[]): number =>
  lines.reduce((n, l) => n + (isAddable(l) ? l.remaining : 0), 0);

/** How many addable lines are for a printing you already own (adding counts those copies again). */
export const addableOwnedLines = (lines: readonly Pick<ReviewLineOut, 'kind' | 'printing' | 'remaining' | 'owned'>[]): number =>
  lines.filter((l) => isAddable(l) && l.owned > 0).length;

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

export type Valuation =
  | { kind: 'none' }
  | { kind: 'full'; worth: number; gain: number }
  | { kind: 'partial'; worth: number; gain: number; comparedPaid: number };

/** What "worth today" can honestly say: it values only lines with a price today (compared_paid_usd).
 *  No such lines → nothing to show; some lines unvalued → show it as a partial figure. */
export function valuation(p: { paid_usd: number; compared_paid_usd: number; worth_usd: number; gain_usd: number }): Valuation {
  if (p.compared_paid_usd <= 0.005) return { kind: 'none' };
  if (p.compared_paid_usd < p.paid_usd - 0.005) return { kind: 'partial', worth: p.worth_usd, gain: p.gain_usd, comparedPaid: p.compared_paid_usd };
  return { kind: 'full', worth: p.worth_usd, gain: p.gain_usd };
}

/** The header line: everything paid vs. what the whole collection is worth now. Copies aren't tied to
 *  orders, so this is a rough return — `gain` is signed ('+' only when positive). */
export function roiSummary(t: Pick<TotalsOut, 'orders' | 'paid_usd' | 'collection_value_usd' | 'gain_usd'>): { paid: number; orders: number; value: number; sign: '+' | '−' | ''; gain: number; title: string } {
  const { sign, abs } = signedParts(t.gain_usd);
  return {
    paid: t.paid_usd, orders: t.orders, value: t.collection_value_usd, sign, gain: abs,
    title: 'Everything you paid for the items in your orders (before shipping and tax), against what your whole collection is worth at today’s prices. Cards aren’t tied to individual orders, so treat the difference as a rough estimate.',
  };
}

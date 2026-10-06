// Deals view-model: framework-free.
import type { PriceOut } from './api';

/** One product page's reading (the deals.read_prices job artifact, or a confirm result). */
export type PriceRow = PriceOut;

/** The `prices` artifact of a finished read_prices job, keyed by URL. */
export function pricesFrom(artifacts: unknown): Map<string, PriceRow> {
  const art = (artifacts as { label: string; data: PriceRow[] }[] | undefined)?.find((a) => a.label === 'prices');
  return new Map((art?.data ?? []).map((r) => [r.url, r]));
}

/** Errors that apply to the whole read (e.g. Chrome's JavaScript setting), shown once. */
export function sharedErrors(rows: Iterable<PriceRow>): string[] {
  const counts = new Map<string, number>();
  for (const r of rows) if (r.error) counts.set(r.error, (counts.get(r.error) ?? 0) + 1);
  return [...counts].filter(([msg, n]) => n > 1 || /Apple Events/.test(msg)).map(([msg]) => msg);
}

/** "In stock" / "Sold out" / "" (page doesn't say). */
export function stockLabel(r: PriceRow | undefined): string {
  if (!r || r.available == null) return '';
  return r.available ? 'In stock' : 'Sold out';
}

/** "$2.93 under market (−2%)" / "$6.99 over market (+13%)" / "at market". */
export function deltaLabel(r: PriceRow): { text: string; tone: 'good' | 'bad' | 'even' } | null {
  if (r.delta == null) return null;
  const abs = Math.abs(r.delta);
  if (abs < 0.005) return { text: 'at market', tone: 'even' };
  const pct = r.pct == null || Math.abs(r.pct) < 1 ? '' : ` (${r.delta < 0 ? '−' : '+'}${Math.abs(Math.round(r.pct))}%)`;
  const money = abs.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  return r.delta < 0 ? { text: `${money} under market${pct}`, tone: 'good' } : { text: `${money} over market${pct}`, tone: 'bad' };
}

/** Rows below market first (biggest discount first), then the rest in page order. */
export function bestDeals(rows: readonly PriceRow[]): PriceRow[] {
  return rows.filter((r) => r.delta != null && r.delta < 0 && r.available !== false).sort((a, b) => (a.pct ?? 0) - (b.pct ?? 0));
}

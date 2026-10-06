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
export function stockLabel(r: Pick<PriceRow, 'available'> | undefined): string {
  if (!r || r.available == null) return '';
  return r.available ? 'In stock' : 'Sold out';
}

/** "$2.93 under market (−2%)" / "$6.99 over market (+13%)" / "at market". */
export function deltaLabel(r: Pick<PriceRow, 'delta' | 'pct'>): { text: string; tone: 'good' | 'bad' | 'even' } | null {
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

/** Watch sealed products and Secret Lair drops once we know what they are; singles aren't watched yet. */
export function canWatch(r: PriceRow): boolean {
  return r.match != null && (r.kind === 'sealed' || r.kind === 'sld') && (r.status === 'matched' || r.status === 'confirmed');
}

type PricePoint = { price: number | null; at: string };
export type WatchStore = {
  url: string; store: string | null; price: number | null; available: boolean | null; read_at: string;
  /** False while the latest price is still the asking price saved when it was watched. */
  read: boolean;
  first_price: number | null; first_at: string; change: number | null; history: PricePoint[];
};
/** One watched product (the deals.watchlist job's `watchlist` artifact). */
export type Watched = {
  set_code: string; name: string; kind: 'sealed' | 'sld'; category: string | null; release_date: string | null;
  market: number | null; contents: number | null; partial: boolean;
  best_price: number | null; best_store: string | null; best_url: string | null;
  delta: number | null; pct: number | null; stores: WatchStore[]; error?: string | null;
};

export function watchlistFrom(artifacts: unknown): { watched: Watched[]; errors: PriceRow[] } {
  const arts = artifacts as { label: string; data: unknown[] }[] | undefined;
  const pick = <T,>(label: string) => (arts?.find((a) => a.label === label)?.data ?? []) as T[];
  return { watched: pick<Watched>('watchlist'), errors: pick<PriceRow>('errors') };
}

const DAY = 86_400_000;
const shortDate = (iso: string) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

/** "↓ $5.00 since Sep 5" / "↑ $2.00 since Sep 5" / "no change since Sep 5" / null with one reading. */
export function trendLabel(s: WatchStore): { text: string; tone: 'good' | 'bad' | 'even' } | null {
  if (s.change == null || s.history.length < 2) return null;
  const since = `since ${shortDate(s.first_at)}`;
  if (Math.abs(s.change) < 0.005) return { text: `no change ${since}`, tone: 'even' };
  const money = Math.abs(s.change).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  return s.change < 0 ? { text: `↓ ${money} ${since}`, tone: 'good' } : { text: `↑ ${money} ${since}`, tone: 'bad' };
}

/** "read today" / "read yesterday" / "read 4 days ago" / "saved Sep 5" (the watched-at asking price). */
export function readAge(s: Pick<WatchStore, 'read' | 'read_at'>, now: Date = new Date()): string {
  if (!s.read) return `saved ${shortDate(s.read_at)}`;
  const days = Math.floor((new Date(now).setHours(0, 0, 0, 0) - new Date(s.read_at).setHours(0, 0, 0, 0)) / DAY);
  return days <= 0 ? 'read today' : days === 1 ? 'read yesterday' : `read ${days} days ago`;
}

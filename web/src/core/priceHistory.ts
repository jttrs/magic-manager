// Price-history chart geometry for a watched product: framework-free.
import type { Offer } from './deals';

/** A store's line, in a 0–100 box (x = time, y = price; 0 is the top). */
export type Series = {
  store: string;
  url: string;
  /** Stroke style index: 0 = solid (the store with today's best price), then dash patterns. */
  style: number;
  /** Step-after path (a price holds until the next reading), extended to the latest reading. */
  path: string;
  /** One point per reading, for dots. */
  points: { x: number; y: number }[];
  now: number | null; first: number | null; low: number | null; high: number | null;
  readings: number;
};

export type HistoryChart = {
  series: Series[];
  /** Price axis: top and bottom labels. */
  hi: number; lo: number;
  /** First and latest reading dates (ISO). */
  from: string; to: string;
  /** The target's line (0–100 from the top) when it falls inside the axis. */
  targetY: number | null;
  /** Every reading, newest first — the chart's table alternative. */
  rows: { at: string; store: string; price: number }[];
  /** One sentence for the chart's accessible name. */
  summary: string;
};

export const DASHES = ['', '5 3', '1.5 3', '8 3 1.5 3'];

const usd = (v: number) => v.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
const day = (iso: string) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
const r1 = (v: number) => Math.round(v * 10) / 10;

/** Null when there's nothing to draw yet (fewer than two readings across every store). */
export function historyChart(offers: Offer[], targetPrice: number | null = null): HistoryChart | null {
  const stores = offers
    .map((o) => ({ o, h: (o.history ?? []).filter((p): p is { price: number; at: string } => p.price != null) }))
    .filter((s) => s.h.length > 0);
  const all = stores.flatMap((s) => s.h);
  if (all.length < 2) return null;
  const times = all.map((p) => Date.parse(p.at));
  const t0 = Math.min(...times);
  const t1 = Math.max(...times);
  const prices = all.map((p) => p.price);
  const withTarget = targetPrice != null ? [...prices, targetPrice] : prices;
  let lo = Math.min(...withTarget);
  let hi = Math.max(...withTarget);
  const pad = hi === lo ? Math.max(hi * 0.05, 1) : (hi - lo) * 0.08;
  lo = Math.max(0, lo - pad);
  hi += pad;
  const x = (iso: string) => (t1 === t0 ? 50 : r1(((Date.parse(iso) - t0) / (t1 - t0)) * 100));
  const y = (price: number) => r1(((hi - price) / (hi - lo)) * 100);
  // The store with today's cheapest price draws solid; the rest take dash patterns in offer order.
  const nowPrice = (h: { price: number }[]) => h[h.length - 1].price;
  const bestIdx = stores.reduce((b, s, i) => (nowPrice(s.h) < nowPrice(stores[b].h) ? i : b), 0);
  let dash = 1;
  const series: Series[] = stores.map((s, i) => {
    const pts = s.h.map((p) => ({ x: x(p.at), y: y(p.price) }));
    let path = `M${pts[0].x} ${pts[0].y}`;
    for (let k = 1; k < pts.length; k++) path += ` H${pts[k].x} V${pts[k].y}`;
    if (pts[pts.length - 1].x < 100 && t1 !== t0) path += ' H100';
    const name = s.o.store ?? new URL(s.o.url).hostname.replace(/^www\./, '');
    return {
      store: name, url: s.o.url, style: i === bestIdx ? 0 : Math.min(dash++, DASHES.length - 1), path, points: pts,
      now: nowPrice(s.h), first: s.o.first ?? s.h[0].price, low: s.o.low ?? Math.min(...s.h.map((p) => p.price)),
      high: s.o.high ?? Math.max(...s.h.map((p) => p.price)), readings: s.h.length,
    };
  });
  const rows = stores
    .flatMap((s, i) => s.h.map((p) => ({ at: p.at, store: series[i].store, price: p.price })))
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at) || a.store.localeCompare(b.store));
  const lowest = rows.reduce((m, r) => (r.price < m.price ? r : m), rows[0]);
  const from = new Date(t0).toISOString();
  const to = new Date(t1).toISOString();
  const summary = `Prices at ${series.length} ${series.length === 1 ? 'store' : 'stores'} from ${day(from)} to ${day(to)}; lowest ${usd(lowest.price)} at ${lowest.store} on ${day(lowest.at)}.`
    + (targetPrice != null ? ` Target ${usd(targetPrice)}.` : '');
  return {
    series, hi, lo, from, to, rows, summary,
    targetY: targetPrice != null && targetPrice >= lo && targetPrice <= hi ? y(targetPrice) : null,
  };
}

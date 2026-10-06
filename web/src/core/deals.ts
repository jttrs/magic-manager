// Deals view-model: framework-free.
import type { MatchOut, PriceOut, ProductCostOut, WatchedOut, WatchStoreOut } from './api';

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

/** The `errors` artifact of a finished deals.watchlist job. */
export function watchlistErrors(artifacts: unknown): PriceRow[] {
  const arts = artifacts as { label: string; data: unknown[] }[] | undefined;
  return (arts?.find((a) => a.label === 'errors')?.data ?? []) as PriceRow[];
}

const DAY = 86_400_000;
const shortDate = (iso: string) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

/** "↓ $5.00 since Sep 5" / "↑ $2.00 since Sep 5" / "no change since Sep 5" / null with one reading. */
export function trendLabel(s: WatchStoreOut): { text: string; tone: 'good' | 'bad' | 'even' } | null {
  if (s.change == null || s.history.length < 2) return null;
  const since = `since ${shortDate(s.first_at)}`;
  if (Math.abs(s.change) < 0.005) return { text: `no change ${since}`, tone: 'even' };
  const money = Math.abs(s.change).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  return s.change < 0 ? { text: `↓ ${money} ${since}`, tone: 'good' } : { text: `↑ ${money} ${since}`, tone: 'bad' };
}

/** "read today" / "read yesterday" / "read 4 days ago" / "saved Sep 5" (the watched-at asking price). */
export function readAge(s: Pick<WatchStoreOut, 'read' | 'read_at'>, now: Date = new Date()): string {
  if (!s.read) return `saved ${shortDate(s.read_at)}`;
  const days = Math.floor((new Date(now).setHours(0, 0, 0, 0) - new Date(s.read_at).setHours(0, 0, 0, 0)) / DAY);
  return days <= 0 ? 'read today' : days === 1 ? 'read yesterday' : `read ${days} days ago`;
}

// ---------- products: one row per product, one offer per store ----------

export const PRODUCT_TYPES = ['deck', 'booster', 'bundle', 'box_set', 'secret_lair', 'single', 'other'] as const;
export type ProductType = (typeof PRODUCT_TYPES)[number];
export const PRODUCT_TYPE_LABEL: Record<ProductType, string> = {
  deck: 'Decks', booster: 'Boosters', bundle: 'Bundles', box_set: 'Box sets', secret_lair: 'Secret Lair', single: 'Singles', other: 'Other',
};

export function productType(kind: 'sealed' | 'sld' | 'single', category: string | null | undefined): ProductType {
  if (kind === 'sld') return 'secret_lair';
  if (kind === 'single') return 'single';
  switch (category) {
    case 'deck': case 'deck_box': return 'deck';
    case 'booster_pack': case 'booster_box': case 'booster_case': case 'draft_set': return 'booster';
    case 'bundle': case 'bundle_case': return 'bundle';
    case 'box_set': return 'box_set';
    default: return 'other';
  }
}

export const BASES = ['market', 'exact', 'floor'] as const;
export type Basis = (typeof BASES)[number];
export const BASIS_LABEL: Record<Basis, string> = { market: 'sealed price', exact: 'cards, exact printings', floor: 'cards, cheapest printings' };

export const DEAL_SORTS = ['gap_pct', 'gap_usd', 'price', 'market', 'exact', 'floor', 'name'] as const;
export type DealSort = (typeof DEAL_SORTS)[number];

export type Offer = {
  url: string; store: string | null; price: number | null; available: boolean | null;
  readAge?: string; trend?: ReturnType<typeof trendLabel>; error?: string | null; title?: string | null;
};

export type DealProduct = {
  key: string;
  kind: 'sealed' | 'sld' | 'single';
  set_code: string;
  name: string;
  finish: string | null;
  category: string | null;
  type: ProductType;
  /** In-stock priced cheapest first, then sold out, then unpriced. */
  offers: Offer[];
  /** Cheapest in-stock priced offer, else the cheapest priced one. */
  best: Offer | null;
  watching: boolean;
  /** Singles only: the printing's price. */
  singleMarket?: number | null;
  /** Open tabs: what the listing was matched to. */
  match?: MatchOut;
};

const productKey = (kind: string, set: string, name: string, finish: string | null | undefined) => `${kind}|${set}|${name}|${finish ?? ''}`;

const rank = (o: Offer) => (o.price == null ? 2 : o.available === false ? 1 : 0);

function sortOffers(offers: Offer[]): Offer[] {
  return [...offers].sort((a, b) => rank(a) - rank(b) || (a.price ?? 0) - (b.price ?? 0));
}

const bestOf = (offers: Offer[]): Offer | null => (offers[0]?.price != null ? offers[0] : null);

export function productsFromWatched(rows: WatchedOut[], errors: PriceRow[] = []): DealProduct[] {
  const errorOf = new Map(errors.map((e) => [e.url, e.error]));
  return rows.map((w) => {
    const offers = sortOffers(w.stores.map((s) => ({
      url: s.url, store: s.store, price: s.price, available: s.available,
      readAge: readAge(s), trend: trendLabel(s), error: errorOf.get(s.url) ?? null,
    })));
    return {
      key: productKey(w.kind, w.set_code, w.name, w.finish), kind: w.kind, set_code: w.set_code, name: w.name, finish: w.finish ?? null,
      category: w.category, type: productType(w.kind, w.category), offers, best: bestOf(offers), watching: true,
    };
  });
}

const GROUPABLE = new Set<string>(['sealed', 'sld', 'single']);

export function productsFromTabs(prices: Map<string, PriceRow>, storeOf: Map<string, string>): { products: DealProduct[]; needsLook: PriceRow[] } {
  const byKey = new Map<string, DealProduct>();
  const needsLook: PriceRow[] = [];
  for (const r of prices.values()) {
    const m = r.match;
    const ok = m != null && !r.error && (r.status === 'matched' || r.status === 'confirmed') && GROUPABLE.has(r.kind ?? '');
    if (!ok || !m) { needsLook.push(r); continue; }
    const kind = r.kind as 'sealed' | 'sld' | 'single';
    const key = kind === 'single' ? `single|${m.scryfall_id}|${m.finish ?? ''}` : productKey(kind, m.set_code, m.name, m.finish);
    const offer: Offer = { url: r.url, store: storeOf.get(r.url) ?? r.vendor ?? null, price: r.price ?? null, available: r.available ?? null, title: r.title };
    let p = byKey.get(key);
    if (!p) {
      p = {
        key, kind, set_code: m.set_code, name: m.name, finish: m.finish ?? null, category: null, type: productType(kind, null),
        offers: [], best: null, watching: false, match: m, ...(kind === 'single' ? { singleMarket: r.market ?? null } : {}),
      };
      byKey.set(key, p);
    }
    p.offers.push(offer);
    if (r.watching) p.watching = true;
  }
  const products = [...byKey.values()].map((p) => {
    const offers = sortOffers(p.offers);
    return { ...p, offers, best: bestOf(offers) };
  });
  return { products, needsLook };
}

export function basisValue(p: DealProduct, cost: ProductCostOut | undefined, basis: Basis): number | null {
  if (p.kind === 'single') return basis === 'floor' ? null : p.singleMarket ?? null;
  return cost?.[basis] ?? null;
}

export function gapOf(p: DealProduct, cost: ProductCostOut | undefined, basis: Basis): { usd: number; pct: number } | null {
  const base = basisValue(p, cost, basis);
  const price = p.best?.price;
  if (base == null || base === 0 || price == null) return null;
  const usd = price - base;
  return { usd, pct: (usd / base) * 100 };
}

/** Tab products don't know their category until the cost loads. */
export function effectiveType(p: DealProduct, cost: ProductCostOut | undefined): ProductType {
  return p.type === 'other' && cost?.category ? productType(p.kind, cost.category) : p.type;
}

export type DealFilters = { q: string; stores: string[]; types: ProductType[]; minOff: number; basis: Basis; sort: DealSort; inStock: boolean };

export function filterSortProducts(products: DealProduct[], costs: Map<string, ProductCostOut | undefined>, o: DealFilters): DealProduct[] {
  const q = o.q.trim().toLowerCase();
  const kept = products.filter((p) => {
    const cost = costs.get(p.key);
    if (q && !p.name.toLowerCase().includes(q) && !p.set_code.toLowerCase().includes(q)) return false;
    if (o.stores.length && !p.offers.some((x) => x.store != null && o.stores.includes(x.store))) return false;
    if (o.types.length && !o.types.includes(effectiveType(p, cost))) return false;
    if (o.inStock && (!p.best || p.best.available === false)) return false;
    if (o.minOff > 0) {
      const g = gapOf(p, cost, o.basis);
      if (!g || g.pct > -o.minOff) return false;
    }
    return true;
  });
  const value = (p: DealProduct): number | null => {
    const cost = costs.get(p.key);
    switch (o.sort) {
      case 'gap_pct': return gapOf(p, cost, o.basis)?.pct ?? null;
      case 'gap_usd': return gapOf(p, cost, o.basis)?.usd ?? null;
      case 'price': return p.best?.price ?? null;
      case 'market': case 'exact': case 'floor': return basisValue(p, cost, o.sort);
      case 'name': return null;
    }
  };
  const dir = o.sort === 'market' || o.sort === 'exact' || o.sort === 'floor' ? -1 : 1;
  return kept
    .map((p) => ({ p, v: value(p) }))
    .sort((a, b) => {
      if (o.sort !== 'name' && a.v !== b.v) {
        if (a.v == null) return 1;
        if (b.v == null) return -1;
        return (a.v - b.v) * dir;
      }
      return a.p.name.localeCompare(b.p.name);
    })
    .map((x) => x.p);
}

/** Counts per product type for the sidebar chips. */
export function typeCounts(products: DealProduct[], costs: Map<string, ProductCostOut | undefined>): Record<ProductType, number> {
  const out = Object.fromEntries(PRODUCT_TYPES.map((t) => [t, 0])) as Record<ProductType, number>;
  for (const p of products) out[effectiveType(p, costs.get(p.key))] += 1;
  return out;
}

/** Store names present across the products, sorted. */
export function storeNames(products: DealProduct[]): string[] {
  return [...new Set(products.flatMap((p) => p.offers.map((o) => o.store).filter((s): s is string => s != null)))].sort((a, b) => a.localeCompare(b));
}

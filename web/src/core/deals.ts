// Deals view-model: framework-free.
import type { MatchOut, PriceOut, PricePointOut, ProductCostOut, TargetOut, WatchedOut, WatchStoreOut } from './api';

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
export const BASIS_LABEL: Record<Basis, string> = { market: 'sealed value', exact: 'cards, exact printings', floor: 'cards, cheapest printings' };

export const DEAL_SORTS = ['gap_pct', 'gap_usd', 'price', 'market', 'exact', 'floor', 'name'] as const;
export type DealSort = (typeof DEAL_SORTS)[number];

export type Offer = {
  url: string; store: string | null; price: number | null; available: boolean | null;
  readAge?: string; trend?: ReturnType<typeof trendLabel>; error?: string | null; title?: string | null;
  /** Watched links: when this price was read (or saved). */
  readAt?: string;
  /** Watched links: the latest read of this link failed (the price shown is the last good one). */
  readFailed?: boolean;
  /** Watched links: every price seen there, oldest first, and its first / low / high. */
  history?: PricePointOut[]; first?: number | null; low?: number | null; high?: number | null;
  /** A watched product's price at a store you don't watch it at yet, read from your open tabs. */
  fromTab?: boolean;
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
  /** Watching: the earmark's id, its price target, and the target's price when the server knows it. */
  productId?: number;
  target?: TargetOut | null;
  targetPrice?: number | null;
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
      readAge: readAge(s), readAt: s.read_at, readFailed: s.read_failed, trend: trendLabel(s), error: errorOf.get(s.url) ?? null,
      history: s.history, first: s.first_price, low: s.low ?? null, high: s.high ?? null,
    })));
    return {
      key: w.kind === 'single' ? `single|${w.scryfall_id}|${w.finish ?? ''}` : productKey(w.kind, w.set_code, w.name, w.finish),
      kind: w.kind, set_code: w.set_code, name: w.name, finish: w.finish ?? null,
      category: w.category, type: productType(w.kind, w.category), offers, best: bestOf(offers), watching: true,
      productId: w.product_id, target: w.target ?? null, targetPrice: w.target_price ?? null,
      ...(w.kind === 'single' ? { singleMarket: w.market ?? null } : {}),
    };
  });
}

/** The product key a matched listing groups under (the same key its watched row has). */
export const tabProductKey = (kind: string, m: MatchOut): string =>
  kind === 'single' ? `single|${m.scryfall_id}|${m.finish ?? ''}` : productKey(kind, m.set_code, m.name, m.finish);

const GROUPABLE = new Set<string>(['sealed', 'sld', 'single']);

export function productsFromTabs(prices: Map<string, PriceRow>, storeOf: Map<string, string>): { products: DealProduct[]; needsLook: PriceRow[] } {
  const byKey = new Map<string, DealProduct>();
  const needsLook: PriceRow[] = [];
  for (const r of prices.values()) {
    const m = r.match;
    const ok = m != null && !r.error && (r.status === 'matched' || r.status === 'confirmed') && GROUPABLE.has(r.kind ?? '');
    if (!ok || !m) { needsLook.push(r); continue; }
    const kind = r.kind as 'sealed' | 'sld' | 'single';
    const key = tabProductKey(kind, m);
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

// ---------- price targets (watching) ----------

/** The price at or under which a target is met. Mirrors `earmarks.target_threshold`: the instant
 *  watchlist can't price a % target on a sealed product, so it's finished here from the product's
 *  sealed market price (the same `product-cost` figure the server would use). */
export function targetPriceOf(p: DealProduct, cost: ProductCostOut | undefined): number | null {
  if (p.targetPrice != null) return p.targetPrice;
  const t = p.target;
  if (!t || t.mode !== 'pct_under' || p.kind === 'single' || cost?.market == null) return null;
  return Math.round(cost.market * (1 - t.value / 100) * 100) / 100;
}

/** The cheapest in-stock (or stock-unknown) price — the only one that can meet a target. */
export function inStockBest(p: DealProduct): Offer | null {
  return p.offers.find((o) => o.price != null && o.available !== false) ?? null;
}

/** A store price older than this can't meet a target (mirrors `earmarks.TARGET_FRESH_DAYS`). */
const TARGET_FRESH_DAYS = 7;

/** The cheapest in-stock price we can trust: from a store whose latest read didn't fail, read or saved
 *  within TARGET_FRESH_DAYS (mirrors `deals._trusted`). */
export function trustedBest(p: DealProduct, now: Date = new Date()): Offer | null {
  const fresh = (o: Offer) => o.readAt == null || now.getTime() - new Date(o.readAt).getTime() <= TARGET_FRESH_DAYS * DAY;
  return p.offers.find((o) => o.price != null && o.available !== false && !o.error && !o.readFailed && fresh(o)) ?? null;
}

/** Met: the trusted best in-stock price is at or under the target's price. Null when that price isn't known
 *  (mirrors `deals._target_met`). */
export function targetMet(p: DealProduct, cost: ProductCostOut | undefined, now: Date = new Date()): boolean | null {
  const at = targetPriceOf(p, cost);
  if (at == null) return null;
  const best = trustedBest(p, now);
  return best?.price != null && best.price <= at + 1e-9;
}

/** "$72.00" or "10% under the sealed value" — how the owner set it. */
export function targetText(t: TargetOut, kind: DealProduct['kind']): string {
  return t.mode === 'price' ? usd(t.value) : `${fmtPct(t.value)} under ${kind === 'single' ? 'the printing’s value' : 'the sealed value'}`;
}

const usd = (v: number) => v.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
const fmtPct = (v: number) => `${Number.isInteger(v) ? v : v.toFixed(1)}%`;

/** One product whose target the last read met (the `newly_met` artifact of deals.watchlist). */
export type NewlyMet = { product_id: number; name: string; price: number; store: string | null; url: string; target_price: number };

export function newlyMetFrom(artifacts: unknown): NewlyMet[] {
  const arts = artifacts as { label: string; data: unknown[] }[] | undefined;
  return (arts?.find((a) => a.label === 'newly_met')?.data ?? []) as NewlyMet[];
}

export type DealFilters = { q: string; stores: string[]; types: ProductType[]; minOff: number; basis: Basis; sort: DealSort; inStock: boolean; atTarget?: boolean };

export function filterSortProducts(products: DealProduct[], costs: Map<string, ProductCostOut | undefined>, o: DealFilters): DealProduct[] {
  const q = o.q.trim().toLowerCase();
  const kept = products.filter((p) => {
    const cost = costs.get(p.key);
    if (q && !p.name.toLowerCase().includes(q) && !p.set_code.toLowerCase().includes(q)) return false;
    if (o.stores.length && !p.offers.some((x) => x.store != null && o.stores.includes(x.store))) return false;
    if (o.types.length && !o.types.includes(effectiveType(p, cost))) return false;
    if (o.inStock && (!p.best || p.best.available === false)) return false;
    if (o.atTarget && targetMet(p, cost) !== true) return false;
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

/** The most watched pages one companion read may cover (the extension's MAX_WATCHED). */
export const MAX_BROWSER_READS = 50;

/** Watched links on open-tab stores (read in a browser tab), deduped, at most MAX_BROWSER_READS;
 *  `skipped` = how many more there were (reported as not read this time). */
export function browserReadUrls(rows: readonly WatchedOut[]): { urls: string[]; skipped: number } {
  const all = [...new Set(rows.flatMap((r) => r.stores.filter((s) => s.read_in_browser).map((s) => s.url)))];
  return { urls: all.slice(0, MAX_BROWSER_READS), skipped: Math.max(0, all.length - MAX_BROWSER_READS) };
}

// ---------- open tabs, pinned above the watchlist ----------

/** A listing read from your open tabs that isn't a known product yet: ambiguous, unmatched or unreadable. */
export type TabListing = { key: string; url: string; title: string; store: string | null; row: PriceRow };

const listingKey = (url: string) => `tab|${url}`;

export type TabsMerge = {
  /** The watchlist; a watched product also read at a store you don't watch it at gets that offer too. */
  watched: DealProduct[];
  /** Matched products from your open tabs you don't watch yet, pinned above the watchlist. */
  pinned: DealProduct[];
  /** Listings from your open tabs that need a look before they can be watched. */
  listings: TabListing[];
};

/** Recomposes a read of your open tabs around the watchlist: products you already watch merge into
 *  their row (the read of a watched link is recorded server-side, so only new stores are added here),
 *  the rest are pinned until you Watch or Dismiss them. `dismissed` holds product / listing keys. */
export function mergeTabs(
  watched: DealProduct[], prices: Map<string, PriceRow>, storeOf: Map<string, string>,
  titleOf: Map<string, string> = new Map(), dismissed: ReadonlySet<string> = new Set(),
): TabsMerge {
  if (!prices.size) return { watched, pinned: [], listings: [] };
  const { products, needsLook } = productsFromTabs(prices, storeOf);
  const byKey = new Map(watched.map((p) => [p.key, p]));
  const extra = new Map<string, Offer[]>();
  const pinned: DealProduct[] = [];
  for (const p of products) {
    const w = byKey.get(p.key);
    if (w) {
      const known = new Set(w.offers.map((o) => o.url));
      const fresh = p.offers.filter((o) => !known.has(o.url)).map((o) => ({ ...o, fromTab: true }));
      if (fresh.length) extra.set(p.key, fresh);
    } else if (!p.watching && !dismissed.has(p.key)) {
      pinned.push(p);
    }
  }
  const merged = extra.size
    ? watched.map((w) => {
        const add = extra.get(w.key);
        if (!add) return w;
        const offers = sortOffers([...w.offers, ...add]);
        return { ...w, offers, best: bestOf(offers) };
      })
    : watched;
  const listings = needsLook
    .filter((r) => !r.watching && !dismissed.has(listingKey(r.url)))
    .map((r) => ({ key: listingKey(r.url), url: r.url, title: r.title || titleOf.get(r.url) || r.url, store: storeOf.get(r.url) ?? r.vendor ?? null, row: r }));
  return { watched: merged, pinned, listings };
}

/** What a pinned listing needs, in a few words. */
export function listingStatus(l: TabListing): string {
  const r = l.row;
  if (r.error) return 'Couldn’t read this page';
  if (r.status === 'ambiguous') return 'Which product is this? Pick it in the detail';
  if (r.status === 'skipped') return 'Not counted';
  return 'Not a product we know';
}

/** Listings kept by the filters: name/set search and stores; filters that need a value or target
 *  (discount, at target) hide them, since a listing has neither yet. */
export function filterListings(listings: TabListing[], o: DealFilters): TabListing[] {
  const q = o.q.trim().toLowerCase();
  if (o.atTarget || o.minOff > 0 || o.types.length) return [];
  return listings.filter((l) =>
    (!q || l.title.toLowerCase().includes(q))
    && (!o.stores.length || (l.store != null && o.stores.includes(l.store)))
    && (!o.inStock || l.row.available !== false));
}

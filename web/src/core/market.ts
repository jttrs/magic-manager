// Market view-model derivations: framework-free, unit-tested.
import type { CardPriceOut, DeckCostOut, DeckLineOut, ProductOut, ProductValueOut } from './api';
import type { MarketSearch } from './search';

const CATEGORY_LABEL: Record<string, string> = {
  booster_box: 'Booster boxes',
  booster_case: 'Booster cases',
  booster_pack: 'Booster packs',
  bundle: 'Bundles',
  bundle_case: 'Bundle cases',
  box_set: 'Box sets',
  deck: 'Decks',
  deck_box: 'Deck boxes',
  draft_set: 'Draft sets',
  prerelease_pack: 'Prerelease packs',
  starter_kit: 'Starter kits',
  two_player_starter_set: 'Starter sets',
  land_station: 'Land stations',
  case: 'Cases',
  subset: 'Subsets',
};

/** "booster_box" → "Booster boxes"; unknown categories are humanized. */
export function categoryLabel(cat: string | null | undefined): string {
  if (!cat) return 'Other';
  return CATEGORY_LABEL[cat] ?? cat.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

export type ProductRow = ProductOut & { value?: ProductValueOut };
export type ProductGroup = { key: string; label: string; rows: ProductRow[] };

/** Products joined to their valuation (when priced), grouped by category in a
 *  stable order: the order categories first appear in the list. */
export function productGroups(products: ProductOut[], values: ProductValueOut[] | undefined, q = ''): ProductGroup[] {
  const byKey = new Map((values ?? []).map((v) => [`${v.set_code}|${v.name}`, v]));
  const ql = q.trim().toLowerCase();
  const groups = new Map<string, ProductGroup>();
  for (const p of products) {
    if (ql && !p.name.toLowerCase().includes(ql)) continue;
    const key = p.category ?? 'other';
    const g = groups.get(key) ?? { key, label: categoryLabel(p.category), rows: [] };
    g.rows.push({ ...p, value: byKey.get(`${p.set_code}|${p.name}`) });
    groups.set(key, g);
  }
  return [...groups.values()];
}

/** Contents value minus sealed price: positive = the cards inside are worth more. */
export function contentsGap(v: ProductValueOut | undefined): number | null {
  if (!v || v.sealed_market == null || v.contents_value == null) return null;
  return v.contents_value - v.sealed_market;
}

/** What a printing costs over the card's cheapest printing anywhere (nonfoil). */
export function premium(c: CardPriceOut): number | null {
  if (c.price_usd == null || c.floor_usd == null) return null;
  return Math.max(0, c.price_usd - c.floor_usd);
}

/** Keeps a printing under the foil-premium cap: its plain foil costs at most
 *  that % over nonfoil ('cheaper' = foil no dearer than nonfoil). A printing
 *  without both plain finishes priced never passes an active cap. */
export function withinFoilMax(c: CardPriceOut, max: MarketSearch['foilMax']): boolean {
  if (max === 'any') return true;
  if (c.foil_gap_status !== 'ok' || c.foil_gap_pct == null) return false;
  const pct = Math.round(c.foil_gap_pct * 10000) / 100;
  return pct <= (max === 'cheaper' ? 0 : Number(max));
}

/** "+504%" / "−12%" — the foil premium as a whole percent. */
export function fmtFoilGap(pct: number): string {
  const v = Math.round(pct * 100);
  return v > 0 ? `+${v}%` : v < 0 ? `−${Math.abs(v)}%` : '0%';
}

export function filterCardPrices(cards: CardPriceOut[], s: Pick<MarketSearch, 'q' | 'cheaper' | 'sort'> & { foilMax?: MarketSearch['foilMax'] }): CardPriceOut[] {
  const ql = s.q.trim().toLowerCase();
  const shown = cards.filter(
    (c) => (!ql || c.name.toLowerCase().includes(ql)) && (!s.cheaper || (premium(c) ?? 0) >= 0.01) && withinFoilMax(c, s.foilMax ?? 'any'),
  );
  const gap = (c: CardPriceOut) => (c.foil_gap_status === 'ok' && c.foil_gap_pct != null ? Math.round(c.foil_gap_pct * 10000) : Infinity);
  const cmp: Record<MarketSearch['sort'], (a: CardPriceOut, b: CardPriceOut) => number> = {
    savings: (a, b) => (premium(b) ?? -1) - (premium(a) ?? -1),
    price: (a, b) => (b.price_usd ?? -1) - (a.price_usd ?? -1),
    foil: (a, b) => (gap(a) === gap(b) ? 0 : gap(a) - gap(b)),
    set: (a, b) => a.set_code.localeCompare(b.set_code) || a.collector_number.localeCompare(b.collector_number, undefined, { numeric: true }),
  };
  return [...shown].sort((a, b) => cmp[s.sort](a, b) || a.name.localeCompare(b.name));
}

type LedgerCell = { value: number | null; best: boolean };
export type LedgerRow = { key: 'sealed' | 'new' | 'free'; label: string; exact: LedgerCell; floor: LedgerCell };

/** The three ways to get a deck × exact printing vs cheapest printing; the
 *  cheapest priced cell is marked best. Sealed has one price (both columns). */
export function deckLedger(d: DeckCostOut): LedgerRow[] {
  const rows: Omit<LedgerRow, 'exact' | 'floor'>[] = [];
  const raw: Record<LedgerRow['key'], [number | null, number | null]> = {
    sealed: [d.sealed ?? null, null],
    new: [d.scratch ?? null, d.scratch_floor],
    free: [d.with_collection ?? null, d.with_collection_floor],
  };
  if (d.sealed != null) rows.push({ key: 'sealed', label: 'Buy it sealed' });
  rows.push({ key: 'new', label: 'Buy every card' }, { key: 'free', label: 'Use your free cards first' });
  const priced = rows.flatMap((r) => raw[r.key]).filter((v): v is number => v != null);
  const min = priced.length ? Math.min(...priced) : null;
  return rows.map((r) => {
    const [exact, floor] = raw[r.key];
    return { ...r, exact: { value: exact, best: exact != null && exact === min }, floor: { value: floor, best: floor != null && floor === min } };
  });
}

/** Lines still to buy, as buy-list items at the chosen printing basis. */
export function deckBuyItems(lines: DeckLineOut[], at: MarketSearch['buyAt']) {
  return lines
    .filter((l) => l.buy > 0)
    .map((l) => (at === 'floor' ? { scryfall_id: l.floor_scryfall_id, finish: 'nonfoil' as const, qty: l.buy } : { scryfall_id: l.scryfall_id, finish: l.finish as 'nonfoil' | 'foil', qty: l.buy }));
}

/** "11 of 100 cards priced" when some fixed cards have no price at their exact printing. */
export function partialNote(v: ProductValueOut | undefined): string | null {
  if (!v || !v.unpriced_cards || !v.total_cards) return null;
  return `${v.total_cards - v.unpriced_cards} of ${v.total_cards} cards have a price at this printing — the rest count as unknown, so the real value is higher`;
}

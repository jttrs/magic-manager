import { describe, expect, it } from 'vitest';
import type { CardPriceOut, DeckCostOut, DeckLineOut, ProductValueOut } from './api';
import { categoryLabel, contentsGap, partialNote, deckBuyItems, deckLedger, filterCardPrices, fmtFoilGap, premium, productGroups, withinFoilMax } from './market';

const card = (p: Partial<CardPriceOut>): CardPriceOut => ({
  scryfall_id: 'x', oracle_id: 'o', name: 'Card', set_code: 'fin', collector_number: '1', rarity: 'rare', type_line: null,
  finishes: ['nonfoil'], treatment: '', image_uri: null, is_chase: false, price_usd: 1, price_usd_foil: null, floor_usd: 1, foil_gap_status: 'nonfoil_only', owned: 0, ...p,
});
const line = (p: Partial<DeckLineOut>): DeckLineOut => ({
  scryfall_id: 's', finish: 'nonfoil', name: 'L', set_code: 'fic', collector_number: '1', need: 1, free: 0, buy: 1,
  unit_usd: 5, floor_usd: 2, floor_scryfall_id: 'cheap', ...p,
});
const deck = (p: Partial<DeckCostOut>): DeckCostOut => ({
  slug: 'd', sealed: null, scratch: 70, with_collection: 30, scratch_floor: 60, with_collection_floor: 25, coverage: 1, unpriced: 0, total_need: 100, lines: [], ...p,
});

describe('market view-model', () => {
  it('labels categories, humanizing unknown ones', () => {
    expect(categoryLabel('booster_box')).toBe('Booster boxes');
    expect(categoryLabel('limited_aid_tool')).toBe('Limited aid tool');
    expect(categoryLabel(null)).toBe('Other');
  });

  it('groups products by category in first-seen order and joins their values', () => {
    const v = { set_code: 'fin', name: 'Bundle', sealed_market: 50, contents_value: 60 } as ProductValueOut;
    const groups = productGroups(
      [{ set_code: 'fin', name: 'Play Box', category: 'booster_box' }, { set_code: 'fin', name: 'Bundle', category: 'bundle' }, { set_code: 'fin', name: 'Collector Box', category: 'booster_box' }],
      [v],
    );
    expect(groups.map((g) => [g.label, g.rows.length])).toEqual([['Booster boxes', 2], ['Bundles', 1]]);
    expect(groups[1].rows[0].value).toBe(v);
    expect(productGroups([{ set_code: 'fin', name: 'Bundle', category: 'bundle' }], undefined, 'box')).toEqual([]);
    expect(contentsGap(v)).toBe(10);
    expect(contentsGap({ ...v, sealed_market: null })).toBeNull();
    expect(partialNote(v)).toBeNull();
    expect(partialNote({ ...v, unpriced_cards: 89, total_cards: 100 })).toMatch(/^11 of 100 cards have a price/);
  });

  it('filters printings that cost more than the cheapest and sorts by premium', () => {
    const cards = [card({ scryfall_id: 'a', name: 'A', price_usd: 3, floor_usd: 3 }), card({ scryfall_id: 'b', name: 'B', price_usd: 9, floor_usd: 1 }), card({ scryfall_id: 'c', name: 'C', price_usd: 4, floor_usd: 2 })];
    expect(premium(cards[1])).toBe(8);
    expect(filterCardPrices(cards, { q: '', cheaper: true, sort: 'savings' }).map((c) => c.name)).toEqual(['B', 'C']);
    expect(filterCardPrices(cards, { q: '', cheaper: false, sort: 'price' }).map((c) => c.name)).toEqual(['B', 'C', 'A']);
  });

  it('caps the foil premium and sorts by the smallest premium', () => {
    const ok = (id: string, pct: number) => card({ scryfall_id: id, name: id, finishes: ['nonfoil', 'foil'], foil_gap_status: 'ok', foil_gap_pct: pct, foil_gap_usd: pct });
    const cards = [ok('big', 1.5), ok('cheaper', -0.1), ok('quarter', 0.25), card({ scryfall_id: 'fancy', name: 'fancy', foil_gap_status: 'fancy' })];
    expect(withinFoilMax(cards[3], 'any')).toBe(true);
    expect(withinFoilMax(cards[3], '100')).toBe(false);
    expect(withinFoilMax(cards[2], '25')).toBe(true);
    expect(filterCardPrices(cards, { q: '', cheaper: false, sort: 'foil', foilMax: '50' }).map((c) => c.name)).toEqual(['cheaper', 'quarter']);
    expect(filterCardPrices(cards, { q: '', cheaper: false, sort: 'foil', foilMax: 'cheaper' }).map((c) => c.name)).toEqual(['cheaper']);
    expect(filterCardPrices(cards, { q: '', cheaper: false, sort: 'foil' }).map((c) => c.name)).toEqual(['cheaper', 'quarter', 'big', 'fancy']);
    expect([fmtFoilGap(1.5), fmtFoilGap(-0.1), fmtFoilGap(0.001)]).toEqual(['+150%', '−10%', '0%']);
  });

  it('builds the three-way ledger and marks the lowest cell', () => {
    const rows = deckLedger(deck({ sealed: 20, sealed_product: 'Box' }));
    expect(rows.map((r) => r.key)).toEqual(['sealed', 'new', 'free']);
    expect(rows[0].exact).toEqual({ value: 20, best: true });
    expect(rows.flatMap((r) => [r.exact.best, r.floor.best]).filter(Boolean)).toHaveLength(1);
    const noSealed = deckLedger(deck({}));
    expect(noSealed.map((r) => r.key)).toEqual(['new', 'free']);
    expect(noSealed[1].floor.best).toBe(true);
  });

  it('lists only lines to buy, at the cheapest or the deck printing', () => {
    const lines = [line({ buy: 2, finish: 'foil' }), line({ scryfall_id: 'covered', buy: 0 })];
    expect(deckBuyItems(lines, 'floor')).toEqual([{ scryfall_id: 'cheap', finish: 'nonfoil', qty: 2 }]);
    expect(deckBuyItems(lines, 'exact')).toEqual([{ scryfall_id: 's', finish: 'foil', qty: 2 }]);
  });
});

import { describe, expect, it } from 'vitest';
import type { ArtSwapsOut, DeckCardOut, PrintingOut } from './api';
import { artView, choiceNote, draftPrintingIds, swapAllFree } from './artSwap';
import { draftCards, draftFromDeck, draftStats, restorePrinting, swapPrinting } from './deckDraft';

const pr = (id: string, o: Partial<PrintingOut> = {}): PrintingOut => ({
  scryfall_id: id, oracle_id: `o-${id[0]}`, name: id[0], set_code: id, set_name: null, collector_number: '1', rarity: 'rare',
  finishes: ['nonfoil'], treatment: '', image_uri: null, price_usd: 1, price_usd_foil: null, released_at: null,
  type_line: 'Creature — Cat', cmc: 2, owned: {}, free: 0, ...o,
});
const dc = (p: PrintingOut, o: Partial<DeckCardOut> = {}): DeckCardOut => ({
  printing: p, board: 'main', finish: 'nonfoil', count: 1, type_line: 'Creature — Cat', cmc: 2, color_identity: [], pledged_here: 0, free: 0, ...o,
});

// a1 → a2 (2 free); b1 → b2 (not owned, $3); c1 already on theme; d1 no art.
const P = {
  a1: pr('a1'), a2: pr('a2', { free: 2, owned: { nonfoil: 2 } }), a3: pr('a3', { price_usd: 0.5 }),
  b1: pr('b1'), b2: pr('b2', { price_usd: 3, finishes: ['foil'] }), c1: pr('c1'), d1: pr('d1'),
};
const saved = draftFromDeck([dc(P.a1), dc(P.b1, { count: 2 }), dc(P.c1), dc(P.d1)]);
const data: ArtSwapsOut = {
  tag: { id: 't', label: 'cat' },
  rows: [
    { scryfall_id: 'a1', status: 'swap', pick: 'a2', candidates: ['a2', 'a3'] },
    { scryfall_id: 'b1', status: 'swap', pick: 'b2', candidates: ['b2'] },
    { scryfall_id: 'c1', status: 'on_theme', pick: 'c1', candidates: ['c1'] },
    { scryfall_id: 'd1', status: 'none', pick: null, candidates: [] },
  ],
  printings: P,
  matched: { a2: ['cat'], a3: ['housecat'], b2: ['cat'], c1: ['cat'] },
};

describe('art swaps', () => {
  it('splits the draft into can-swap (free first), on-theme and none', () => {
    const v = artView(saved, data);
    expect(v.swap.map((r) => [r.row.printing.scryfall_id, r.pick?.scryfall_id])).toEqual([['a1', 'a2'], ['b1', 'b2']]);
    expect(v.swap[0].candidates.map((c) => c.scryfall_id)).toEqual(['a2', 'a3']);
    expect(v.onTheme.map((r) => r.status)).toEqual(['on_theme']);
    expect(v.none.map((r) => r.row.printing.scryfall_id)).toEqual(['d1']);
    expect(v.freeSwaps).toBe(1);
    expect(draftPrintingIds(saved)).toEqual(['a1', 'b1', 'c1', 'd1']);
  });

  it('swaps a printing in place, marks it, and undoes back to the saved one', () => {
    const key = saved.rows.find((r) => r.printing.scryfall_id === 'b1')!.key;
    const d = swapPrinting(saved, key, P.b2);
    const row = d.rows.find((r) => r.printing.scryfall_id === 'b2')!;
    expect(row).toMatchObject({ key: 'b2|main|either', count: 2, saved: 2, finish: 'either' }); // b2 has no nonfoil
    expect(row.origin?.printing.scryfall_id).toBe('b1');
    expect(draftStats(d, 'commander')).toMatchObject({ added: 0, removed: 0, swapped: 2, dirty: true });
    expect(draftCards(d).find((c) => c.scryfall_id === 'b2')).toEqual({ scryfall_id: 'b2', board: 'main', finish: 'either', count: 2 });
    const back = restorePrinting(d, row.key);
    expect(back.rows.find((r) => r.printing.scryfall_id === 'b1')).toMatchObject({ key: 'b1|main|nonfoil', origin: undefined });
    expect(draftStats(back, 'commander').dirty).toBe(false);
  });

  it('keeps a swapped row as swapped while the next answer is pending', () => {
    const d = swapPrinting(saved, 'a1|main|nonfoil', P.a3);
    const r = artView(d, data).onTheme.find((x) => x.status === 'swapped')!;
    expect(r.row.printing.scryfall_id).toBe('a3');
    expect(r.candidates.map((c) => c.scryfall_id)).toEqual(['a2', 'a3']);
  });

  it('counts printing swaps that merge rows as swapped, not added/removed', () => {
    const lands = draftFromDeck([dc(pr('p1'), { count: 3 }), dc(pr('p2'), { count: 2 })]);
    const onTheme = pr('p9', { free: 9 });
    let d = swapPrinting(lands, 'p1|main|nonfoil', onTheme);
    d = swapPrinting(d, 'p2|main|nonfoil', onTheme);
    expect(draftCards(d)).toEqual([{ scryfall_id: 'p9', board: 'main', finish: 'nonfoil', count: 5 }]);
    expect(draftStats(d, 'commander')).toMatchObject({ added: 0, removed: 0, swapped: 5 });
  });

  it('swap all free only takes printings you have free', () => {
    const d = swapAllFree(saved, artView(saved, data));
    expect(draftPrintingIds(d)).toEqual(['a2', 'b1', 'c1', 'd1']);
  });

  it('notes free copies, else the price', () => {
    expect(choiceNote(P.a2)).toBe('2 free');
    expect(choiceNote(P.b2)).toBe('$3.00');
    expect(choiceNote(pr('x', { price_usd: null, owned: { foil: 1 } }))).toBe('no price · yours, all in decks');
  });
});

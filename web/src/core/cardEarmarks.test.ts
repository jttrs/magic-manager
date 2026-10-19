import { describe, expect, it } from 'vitest';
import type { CardEarmarkOut, DeckEarmarkOut, EarmarkEntryOut, PrintingOut } from './api';
import { earmarkDecks, earmarkLine, earmarkSections, reasonsText, filterEarmarks, findEarmark, hiddenSummary } from './cardEarmarks';

const mark = (name: string, o: Partial<CardEarmarkOut> = {}): CardEarmarkOut => ({
  oracle_id: `o-${name}`, name, scryfall_id: null, finish: null, reason: null, deck_slug: null, deck_name: null, note: null,
  earmarked_at: '2026-01-01', updated_at: '2026-01-01', ...o,
});
const entry = (name: string, o: Partial<CardEarmarkOut> = {}, owned = 0): EarmarkEntryOut => ({ earmark: mark(name, o), printing: null, owned, free: owned });

describe('card earmarks', () => {
  const list = [
    entry('Esper Sentinel', { reason: 'collect', note: 'MH2 foil' }, 1),
    entry('Mother of Runes', { reason: 'deck', deck_slug: 'squall', deck_name: 'Squall' }),
    entry('Giant Killer // Chop Down'),
  ];

  it('finds a card by name, a double-faced card by its front face too', () => {
    expect(findEarmark(list, 'esper sentinel')?.earmark.name).toBe('Esper Sentinel');
    expect(findEarmark(list, 'Giant Killer')?.earmark.name).toBe('Giant Killer // Chop Down');
    expect(findEarmark(list, 'Sol Ring')).toBeUndefined();
    expect(findEarmark(undefined, 'x')).toBeUndefined();
  });

  it('says what an earmark records, in order', () => {
    expect(earmarkLine(list[1].earmark)).toBe('Deck idea · for Squall');
    expect(earmarkLine(list[0].earmark)).toBe('To collect · MH2 foil');
    expect(earmarkLine(list[2].earmark)).toBe('');
  });

  it('filters by reason, deck, ownership and text', () => {
    const names = (f: Parameters<typeof filterEarmarks>[1]) => filterEarmarks(list, f).map((e) => e.earmark.name);
    expect(names({ reason: 'collect' })).toEqual(['Esper Sentinel']);
    expect(names({ reason: 'none' })).toEqual(['Giant Killer // Chop Down']);
    expect(names({ deck: 'squall' })).toEqual(['Mother of Runes']);
    expect(names({ own: 'owned' })).toEqual(['Esper Sentinel']);
    expect(names({ own: 'free' })).toEqual(['Esper Sentinel']);
    expect(names({ q: 'foil' })).toEqual(['Esper Sentinel']);
    expect(earmarkDecks(list)).toEqual([{ slug: 'squall', name: 'Squall' }]);
  });

  it('groups the grid by reason and skips cards with no local printing', () => {
    const p: PrintingOut = { scryfall_id: 's1', oracle_id: 'o', name: 'Esper Sentinel', set_code: 'mh2', set_name: null, collector_number: '12', rarity: 'rare', finishes: ['nonfoil'], treatment: '', image_uri: null, price_usd: 1, price_usd_foil: null, released_at: null, type_line: 'Artifact Creature', cmc: 1, owned: {}, free: 0 };
    const withArt = [{ ...list[0], printing: p }, list[1]];
    expect(earmarkSections(withArt).map((g) => [g.label, g.items.map((c) => c.key)])).toEqual([['To collect', ['o-Esper Sentinel']]]);
  });

  it('summarises why cards are hidden from a deck, most common reason first', () => {
    type Code = DeckEarmarkOut['reasons'][number]['code'];
    const h = (...codes: Code[]): DeckEarmarkOut => ({ ...entry('x'), in_deck: false, reasons: codes.map((code) => ({ code, message: code })) });
    expect(hiddenSummary([])).toBe('');
    expect(hiddenSummary([h('banned'), h('colour_identity'), h('colour_identity', 'not_legal')]))
      .toBe('3 hidden · 2 outside the commander’s colours · 1 banned · 1 not legal in this format');
    expect(reasonsText(h('banned', 'not_legal'))).toBe('banned · not_legal');
  });
});

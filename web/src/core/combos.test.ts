import { describe, expect, it } from 'vitest';
import type { ComboOut, DeckCombosOut, PieceOut } from './api';
import { deckCombosSummary, decksLine, nearMisses, ownNote, piecesOwned, producesLine, steps } from './combos';

const facts = (owned: number, free: number) => ({ oracle_id: null, type_line: null, cmc: null, color_identity: [], lowest_usd: 1, scryfall_id: null, image_uri: null, set_code: null, collector_number: null, scryfall_url: null, owned, free });
const piece = (name: string, inDeck: boolean, owned = 0, free = 0): PieceOut => ({ name, oracle_id: `o-${name}`, in_deck: inDeck, facts: facts(owned, free), image_uri: null, printing: null });
const combo = (id: string, pieces: PieceOut[], o: Partial<ComboOut> = {}): ComboOut => ({
  id, url: `https://commanderspellbook.com/combo/${id}/`, pieces, produces: ['Infinite mana'], requires: [], description: 'Tap.\n\nUntap.\n', prerequisites: '', mana_needed: '', popularity: 1200, identity: 'U', missing: null, ...o,
});

describe('combos view-model', () => {
  it('describes what you own of a piece', () => {
    expect(ownNote(piece('A', false, 2, 1))).toEqual({ text: '1 free', free: true });
    expect(ownNote(piece('A', false, 2, 0))).toEqual({ text: 'owned, all pledged', free: false });
    expect(ownNote(piece('A', false))).toEqual({ text: 'not in your collection', free: false });
  });

  it('summarises a combo', () => {
    const c = combo('1', [piece('A', true, 1), piece('B', false)], { produces: ['X', 'Y', 'Z', 'W'] });
    expect(producesLine(c)).toBe('X · Y +2 more');
    expect(steps(c)).toEqual(['Tap.', 'Untap.']);
    expect(decksLine(c)).toMatch(/^in 1.?200 decks$/);
    expect(decksLine({ ...c, popularity: null })).toBeNull();
    expect(piecesOwned(c)).toEqual({ owned: 1, total: 2 });
  });

  it('groups near-misses under the missing card, keeping roll-up order', () => {
    const lattice = piece('Lattice', false);
    const d: DeckCombosOut = {
      available: true, identity: 'U', off_color: 3,
      included: [combo('in', [piece('A', true), piece('B', true)])],
      almost: [combo('n1', [piece('A', true), lattice]), combo('n2', [piece('B', true), lattice]), combo('n3', [piece('C', false)])],
      missing_cards: [
        { piece: lattice, combos: ['n2', 'n1', 'gone'], popularity: 10 },
        { piece: piece('C', false), combos: ['n3'], popularity: 1 },
      ],
    };
    const nm = nearMisses(d);
    expect(nm.map((m) => [m.card.piece.name, m.combos.map((c) => c.id)])).toEqual([['Lattice', ['n2', 'n1']], ['C', ['n3']]]);
    expect(deckCombosSummary(d)).toBe('1 in this deck · 3 one card away · 3 more need another colour');
  });
});

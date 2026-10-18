import { describe, expect, it } from 'vitest';
import type { DeckCardOut, PrintingOut } from './api';
import type { ReviewLine } from './ingest';
import { addCard, addLines, addsFromReview, boardOfSection, canCommand, collectionFirst, draftCards, draftFromDeck, draftSections, draftStats, moveCard, setCount, setFinish } from './deckDraft';

const pr = (id: string, o: Partial<PrintingOut> = {}): PrintingOut => ({
  scryfall_id: id, oracle_id: `o-${id}`, name: id, set_code: 'tst', set_name: null, collector_number: '1', rarity: 'rare',
  finishes: ['nonfoil'], treatment: '', image_uri: null, price_usd: 1, price_usd_foil: null, released_at: null,
  type_line: 'Creature — Elf', cmc: 2, owned: {}, free: 0, ...o,
});
const dc = (id: string, o: Partial<DeckCardOut> = {}): DeckCardOut => ({
  printing: pr(id, { type_line: o.type_line ?? 'Creature — Elf' }), board: 'main', finish: 'nonfoil', count: 1, type_line: 'Creature — Elf', cmc: 2, color_identity: [], pledged_here: 0, free: 0, ...o,
});

describe('deck draft', () => {
  const saved = draftFromDeck([
    dc('Cmd', { board: 'commander', type_line: 'Legendary Creature — Elf' }),
    dc('Elf', { count: 2 }),
    dc('Bolt', { type_line: 'Instant' }),
    dc('Tok', { board: 'token' }),
  ]);

  it('starts clean, drops tokens, sizes the deck against the format target', () => {
    expect(saved.rows.map((r) => r.key)).toEqual(['Cmd|commander|nonfoil', 'Elf|main|nonfoil', 'Bolt|main|nonfoil']);
    expect(draftStats(saved, 'commander')).toEqual({ size: 4, target: 100, added: 0, removed: 0, swapped: 0, dirty: false });
    expect(draftStats(saved, 'modern').target).toBe(60);
  });

  it('adds, counts, removes and diffs by card quantity', () => {
    let d = addCard(saved, pr('Sol', { type_line: 'Artifact' }));
    d = addCard(d, pr('Sol', { type_line: 'Artifact' }));
    d = setCount(d, 'Elf|main|nonfoil', 0);
    expect(draftStats(d, 'commander')).toMatchObject({ size: 4, added: 2, removed: 2, dirty: true });
    expect(d.rows.find((r) => r.key === 'Elf|main|nonfoil')?.count).toBe(0);       // removed rows stay (undoable)
    expect(setCount(d, 'Sol|main|either', 0).rows.some((r) => r.key.startsWith('Sol'))).toBe(false); // new rows vanish
    expect(draftCards(d).map((c) => [c.scryfall_id, c.count])).toEqual([['Cmd', 1], ['Bolt', 1], ['Sol', 2], ['Tok', 1]]);
  });

  it('bulk-adds reviewed paste lines onto boards by section, summing into existing rows', () => {
    const rl = (id: string, o: Partial<ReviewLine> = {}): ReviewLine => ({
      key: id, raw: id, name: id, qty: 1, finish: 'nonfoil', status: 'exact', candidates: [pr(id)], chosen: id, note: null, include: true, ...o,
    });
    const adds = addsFromReview([
      rl('Elf', { qty: 2, section: 'mainboard', finish: 'nonfoil' }),
      rl('Squall', { section: 'commander' }),
      rl('Opt', { section: 'sideboard', finish: 'foil' }),
      rl('Skip', { include: false }),
      rl('Gone', { status: 'unresolved', candidates: [], chosen: null }),
    ]);
    expect(adds.map((a) => [a.printing.scryfall_id, a.board, a.finish, a.count])).toEqual([
      ['Elf', 'main', 'either', 2], ['Squall', 'commander', 'either', 1], ['Opt', 'side', 'foil', 1],
    ]);
    let d = addLines(saved, adds);
    d = addLines(d, [{ printing: pr('Elf'), board: 'main', finish: 'either', count: 1 }]);
    expect(d.rows.find((r) => r.key === 'Elf|main|either')).toMatchObject({ count: 3, saved: 0 });
    expect(d.rows.find((r) => r.key === 'Elf|main|nonfoil')?.count).toBe(2);   // the saved row is untouched
    expect(draftStats(d, 'commander')).toMatchObject({ added: 5, dirty: true });
    expect(addLines(saved, [])).toBe(saved);
    expect([boardOfSection('maybeboard'), boardOfSection('companion'), boardOfSection(undefined)]).toEqual(['maybe', 'companion', 'main']);
  });

  it('carries the saved token board unchanged through every edit into the save payload', () => {
    let d = addCard(saved, pr('Sol'));
    d = setCount(d, 'Elf|main|nonfoil', 0);
    d = moveCard(d, 'Bolt|main|nonfoil', 'side');
    d = setFinish(d, 'Cmd|commander|nonfoil', 'either');
    expect(d.rows.some((r) => r.board === 'token')).toBe(false);                     // never shown or edited
    expect(draftCards(d).filter((c) => c.board === 'token')).toEqual([{ scryfall_id: 'Tok', board: 'token', finish: 'nonfoil', count: 1 }]);
    expect(draftStats(saved, 'commander').dirty).toBe(false);
  });

  it('moves boards and switches finish by re-keying (merging into an existing row)', () => {
    let d = moveCard(saved, 'Bolt|main|nonfoil', 'side');
    expect(d.rows.find((r) => r.key === 'Bolt|side|nonfoil')).toMatchObject({ count: 1, saved: 0 });
    expect(draftStats(d, 'commander')).toMatchObject({ size: 3, added: 1, removed: 1 });
    d = setFinish(saved, 'Elf|main|nonfoil', 'foil');
    expect(d.rows.find((r) => r.key === 'Elf|main|foil')?.count).toBe(2);
  });

  it('sections like the deck view and ranks the collection first', () => {
    expect(draftSections(saved).map((s) => [s.label, s.count])).toEqual([['Commander', 1], ['Creatures', 2], ['Instants', 1]]);
    const hits = [pr('a'), pr('b', { owned: { nonfoil: 1 } }), pr('c', { owned: { nonfoil: 1 }, free: 1 })];
    expect(collectionFirst(hits).map((p) => p.scryfall_id)).toEqual(['c', 'b', 'a']);
    expect(canCommand({ type_line: 'Legendary Creature — Human' })).toBe(true);
    expect(canCommand({ type_line: 'Creature — Human' })).toBe(false);
  });
});

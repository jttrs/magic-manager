import { describe, expect, it } from 'vitest';
import type { CollectionCardOut } from './api';
import { confirmMoved, dropSaved, rebaseStale, summaryLine, cellValue, countFinishes, familyLabel, nextCell, parseCount, readDraft, setCell, summarize, toChanges, type Draft } from './checklist';

const card = (over: Partial<CollectionCardOut> = {}): CollectionCardOut => ({
  scryfall_id: 'a', oracle_id: null, name: 'Alpha', family: 'tst', set_code: 'tst', collector_number: '1', rarity: 'rare',
  type_line: null, cmc: null, color_identity: [], released_at: null, finishes: ['nonfoil', 'foil'],
  owned: { nonfoil: 3 }, pledged: {}, price_usd: 2, price_usd_foil: 5, image_uri: null, scryfall_url: null,
  treatment: '', standard_frame: true, is_bulk: false, is_chase: false, functions: [], card_owned: 3, sources: [],
  ...over,
});

describe('checklist draft', () => {
  it('counts etched as foil and keeps owned finishes', () => {
    expect(countFinishes(card({ finishes: ['etched'], owned: {} }))).toEqual(['foil']);
    expect(countFinishes(card({ finishes: ['foil'], owned: { nonfoil: 1 } }))).toEqual(['nonfoil', 'foil']);
  });

  it('parses typed counts', () => {
    expect(parseCount(' 12 ')).toBe(12);
    expect(parseCount('')).toBeNull();
    expect(parseCount('-1')).toBe('invalid');
    expect(parseCount('1.5')).toBe('invalid');
    expect(parseCount('12345')).toBe('invalid');
  });

  it('sets, reverts and summarizes cells', () => {
    const c = card();
    let d: Draft = {};
    d = setCell(d, c, 'nonfoil', 5, 'Test');
    d = setCell(d, c, 'foil', 1, 'Test');
    expect(cellValue(d, c, 'nonfoil')).toBe(5);
    expect(summarize(d)).toMatchObject({ cells: 2, added: 3, removed: 0, value: 9, families: ['Test'] });
    d = setCell(d, c, 'nonfoil', 3, 'Test'); // back to owned → dropped
    expect(Object.keys(d)).toEqual(['a|foil']);
    d = setCell(d, c, 'foil', null, 'Test');
    expect(d).toEqual({});
  });

  it('keeps the starting count across edits and builds the save body', () => {
    const c = card();
    let d = setCell({}, c, 'nonfoil', 1, 'Test');
    d = setCell(d, card({ owned: { nonfoil: 9 } }), 'nonfoil', 2, 'Test'); // refetched data doesn't move `was`
    expect(toChanges(d)).toEqual([{ scryfall_id: 'a', finish: 'nonfoil', qty: 2, expected: 3 }]);
    expect(summarize(d)).toMatchObject({ removed: 1, value: -2 });
  });

  it('flags counts below pledged copies and unpriced copies', () => {
    const d = setCell({}, card({ pledged: { nonfoil: 2 }, price_usd: null }), 'nonfoil', 1, 'Test');
    const s = summarize(d);
    expect(s.belowPledged).toHaveLength(1);
    expect(s.unpriced).toBe(2);
    expect(s.value).toBe(0);
  });

  it('restores a stored draft and drops malformed entries', () => {
    const good = setCell({}, card(), 'foil', 2, 'Test');
    expect(readDraft(JSON.stringify(good))).toEqual(good);
    const flagged = rebaseStale(good, [{ scryfall_id: 'a', finish: 'foil', expected: 0, current: 1 }]);
    expect(readDraft(JSON.stringify(flagged))).toEqual(flagged);
    expect(readDraft(JSON.stringify({ x: { id: 'a', finish: 'etched', qty: 1, was: 0 } }))).toEqual({});
    expect(readDraft('{nope')).toEqual({});
    expect(readDraft(null)).toEqual({});
  });

  it('walks down a finish column, skipping printings without it', () => {
    const rows = [{ finishes: ['nonfoil', 'foil'] as const }, { finishes: ['foil'] as const }, { finishes: ['nonfoil'] as const }];
    expect(nextCell(rows, 0, 'nonfoil', 'down')).toEqual({ row: 2, finish: 'nonfoil' });
    expect(nextCell(rows, 2, 'nonfoil', 'up')).toEqual({ row: 0, finish: 'nonfoil' });
    expect(nextCell(rows, 2, 'nonfoil', 'down')).toBeNull();
    expect(nextCell(rows, 0, 'nonfoil', 'right')).toEqual({ row: 0, finish: 'foil' });
    expect(nextCell(rows, 1, 'foil', 'left')).toBeNull();
  });

  it('rebases stale cells on the current count and flags them', () => {
    let d = setCell({}, card(), 'nonfoil', 5, 'T');                       // was 3
    d = setCell(d, card({ scryfall_id: 'b', owned: { foil: 1 } }), 'foil', 4, 'T');
    d = rebaseStale(d, [
      { scryfall_id: 'a', finish: 'nonfoil', expected: 3, current: 4 },    // moved under the cell
      { scryfall_id: 'b', finish: 'foil', expected: 1, current: 4 },       // now already matches
    ]);
    expect(Object.keys(d)).toEqual(['a|nonfoil']);
    expect(d['a|nonfoil']).toMatchObject({ qty: 5, was: 4, moved: true });
    expect(summarize(d)).toMatchObject({ moved: 1, added: 1 });
    expect(toChanges(d)).toEqual([{ scryfall_id: 'a', finish: 'nonfoil', qty: 5, expected: 4 }]);
    d = confirmMoved(d, 'a|nonfoil');
    expect(summarize(d).moved).toBe(0);
    expect(confirmMoved(d)).toBe(d); // nothing flagged → same object
    // Retyping a flagged cell also clears the flag and keeps the new baseline.
    const again = setCell(rebaseStale(setCell({}, card(), 'nonfoil', 5, 'T'), [{ scryfall_id: 'a', finish: 'nonfoil', expected: 3, current: 4 }]), card(), 'nonfoil', 6, 'T');
    expect(again['a|nonfoil']).toMatchObject({ qty: 6, was: 4 });
    expect(again['a|nonfoil'].moved).toBeUndefined();
  });

  it('after a save keeps only cells changed while it was in flight, rebased on the saved count', () => {
    const sent = setCell(setCell({}, card(), 'nonfoil', 5, 'T'), card(), 'foil', 2, 'T');
    let live = setCell(sent, card(), 'foil', 3, 'T');                       // typed during the save
    live = setCell(live, card({ scryfall_id: 'b' }), 'nonfoil', 1, 'T');   // a new cell during the save
    const after = dropSaved(live, sent);
    expect(Object.keys(after).sort()).toEqual(['a|foil', 'b|nonfoil']);
    expect(after['a|foil']).toMatchObject({ qty: 3, was: 2 });
    expect(dropSaved(sent, sent)).toEqual({});
  });

  it('writes the running diff line', () => {
    const d = setCell(setCell({}, card(), 'nonfoil', 5, 'T'), card({ scryfall_id: 'b', owned: { foil: 1 } }), 'foil', 0, 'T');
    expect(summaryLine(summarize(d), null)).toBe('Counting · 2 changes · +2 −1 copies · −$1.00 at market');
    expect(summaryLine(summarize({}), { ingest_id: 1, added: 0, updated: 1, zeroed: 0, copies_added: 2, copies_removed: 0, rows: [{ scryfall_id: 'a', finish: 'nonfoil', old_qty: 3, new_qty: 5 }] })).toBe('Saved 1 count · +2 copies');
  });

  it('labels families for the ingest event', () => {
    expect(familyLabel(['A'])).toBe('A');
    expect(familyLabel(['A', 'B'])).toBe('A, B');
    expect(familyLabel(['A', 'B', 'C'])).toBe('A +2');
  });
});

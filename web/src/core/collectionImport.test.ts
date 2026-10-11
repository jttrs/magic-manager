import { describe, expect, it } from 'vitest';
import { afterImport, changedRows, effectLine, effectOf, previewNotes, readTitle, shareLinkKind } from './collectionImport';

const row = (id: string, current: number, incoming: number) => ({
  scryfall_id: id, finish: 'nonfoil' as const, name: id, set: 'tst', collector_number: '1', current, incoming,
});
const rows = [row('a', 3, 5), row('b', 0, 2), row('c', 4, 1), row('d', 1, 1)];

describe('collection import view-model', () => {
  it('add sums; replace sets to the read', () => {
    expect(afterImport(rows[0], 'add')).toBe(8);
    expect(afterImport(rows[0], 'replace')).toBe(5);
    expect(afterImport(rows[2], 'replace')).toBe(1);
  });

  it('lists only rows whose count changes', () => {
    expect(changedRows(rows, 'replace').map((r) => [r.scryfall_id, r.delta])).toEqual([['a', 2], ['b', 2], ['c', -3]]);
    expect(changedRows(rows, 'add').map((r) => r.scryfall_id)).toEqual(['a', 'b', 'c', 'd']);
  });

  it('sums the effect per mode', () => {
    expect(effectOf(rows, 'replace')).toEqual({ printings: 3, newPrintings: 1, copiesIn: 4, copiesOut: 3 });
    expect(effectLine(effectOf(rows, 'replace'))).toBe('+4 copies · −3 copies · 1 new printing');
    expect(effectLine(effectOf(rows, 'add'))).toBe('+9 copies · 1 new printing');
    expect(effectLine(effectOf([row('x', 2, 2)], 'replace'))).toBe('No change');
  });

  it('recognises share links', () => {
    expect(shareLinkKind('https://moxfield.com/collection/hgsItGBwRUybHyN0WZR41w')).toBe('collection');
    expect(shareLinkKind(' https://www.moxfield.com/binders/LbwVB1hSiU2THiRQeR2QlQ/ ')).toBe('binder');
    expect(shareLinkKind('https://moxfield.com/decks/abcd1234')).toBeNull();
    expect(shareLinkKind('https://evil.example/collection/abcd1234')).toBeNull();
  });

  it('titles and notes', () => {
    expect(readTitle('binder', 'x', 'Trade Box 1')).toBe('Moxfield binder · Trade Box 1');
    expect(readTitle('collection', null, null)).toBe('Your Moxfield collection');
    expect(previewNotes({ skipped: { proxy: 2, digital: 1 }, not_in_read: 1, not_found: [] })).toEqual([
      'Skipped 2 proxies and 1 digital copy (Arena/MTGO).',
      '1 printing you own isn’t in this read — left as it is.',
    ]);
  });
});

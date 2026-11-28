import { describe, expect, it } from 'vitest';
import { bulkActions, pickCount, pickSummary, type PickOption } from './multiSelect';

const opts = (...labels: string[]): PickOption[] => labels.map((l) => ({ value: l.toLowerCase(), label: l }));
const rarities = opts('Mythic', 'Rare', 'Uncommon', 'Common');

describe('pickSummary', () => {
  it('scope: empty asks, one names it, several count, everything says all', () => {
    const fams = opts('Aetherdrift', 'Bloomburrow', 'Fallout');
    expect(pickSummary('scope', fams, [], 'families')).toBe('Choose families…');
    expect(pickSummary('scope', fams, ['aetherdrift'], 'families')).toBe('Aetherdrift');
    expect(pickSummary('scope', fams, ['aetherdrift', 'fallout'], 'families')).toBe('2 families');
    expect(pickSummary('scope', fams, ['aetherdrift', 'bloomburrow', 'fallout'], 'families')).toBe('All 3 families');
  });

  it('include: empty is no filter', () => {
    const stores = opts('A', 'B', 'C');
    expect(pickSummary('include', stores, [], 'stores')).toBe('All stores');
    expect(pickSummary('include', stores, ['b'], 'stores')).toBe('B');
    expect(pickSummary('include', stores, ['a', 'b', 'c'], 'stores')).toBe('3 stores');
  });

  it('exclude: counts what is hidden among the listed options', () => {
    expect(pickSummary('exclude', rarities, ['mythic', 'rare', 'uncommon', 'common'], 'rarities')).toBe('All rarities');
    expect(pickSummary('exclude', rarities, ['mythic', 'rare', 'uncommon'], 'rarities')).toBe('Common hidden');
    expect(pickSummary('exclude', rarities, ['mythic', 'rare'], 'rarities')).toBe('2 rarities hidden');
    expect(pickSummary('exclude', rarities, [], 'rarities')).toBe('All rarities hidden');
    // an unlisted (zero-count) option still checked doesn't change the text
    expect(pickSummary('exclude', rarities, ['mythic', 'rare', 'uncommon', 'common', 'special'], 'rarities')).toBe('All rarities');
  });
});

describe('pickCount', () => {
  it('selected for scope/include, hidden for exclude', () => {
    expect(pickCount('scope', rarities, ['rare'])).toBe('1 selected');
    expect(pickCount('exclude', rarities, ['rare'])).toBe('3 hidden');
  });
});

describe('bulkActions', () => {
  const labels = (a: { label: string }[]) => a.map((x) => x.label);

  it('exclude: Uncheck all never hides an unlisted option', () => {
    const value = ['mythic', 'rare', 'uncommon', 'common', 'special'];
    const acts = bulkActions('exclude', rarities, value, false);
    expect(labels(acts)).toEqual(['Uncheck all']);
    expect(acts[0].next).toEqual(['special']);
  });

  it('exclude: Check all brings back only listed options', () => {
    const acts = bulkActions('exclude', rarities, ['special'], false);
    expect(labels(acts)).toEqual(['Check all']);
    expect(acts[0].next.sort()).toEqual(['common', 'mythic', 'rare', 'special', 'uncommon']);
  });

  it('scope: Clear all empties the selection', () => {
    const acts = bulkActions('scope', rarities, ['rare'], false);
    expect(labels(acts)).toEqual(['Select all', 'Clear all']);
    expect(acts[1].next).toEqual([]);
  });

  it('include: Show all only when something is chosen', () => {
    expect(bulkActions('include', rarities, [], false)).toEqual([]);
    expect(bulkActions('include', rarities, ['rare'], false)).toEqual([{ label: 'Show all', next: [] }]);
  });

  it('a filter box narrows the bulk buttons to what it shows', () => {
    const shown = opts('Rare');
    const acts = bulkActions('include', shown, ['mythic'], true);
    expect(labels(acts)).toEqual(['Select shown']);
    expect(acts[0].next).toEqual(['mythic', 'rare']);
    expect(bulkActions('exclude', shown, ['rare', 'common'], true).map((a) => [a.label, a.next])).toEqual([['Uncheck shown', ['common']]]);
  });
});

describe('bulkActions with hand-picked options', () => {
  const fams: PickOption[] = [...opts('Aetherdrift', 'Bloomburrow'), { value: 'zzz', label: 'Zendikar', bulk: false }];
  it('Select all and Select shown never reach an option marked bulk: false', () => {
    expect(bulkActions('scope', fams, [], false)).toEqual([{ label: 'Select all', next: ['aetherdrift', 'bloomburrow'] }]);
    expect(bulkActions('scope', fams, [], true)).toEqual([{ label: 'Select shown', next: ['aetherdrift', 'bloomburrow'] }]);
  });
  it('Clear all and Clear shown leave a hand-picked option chosen', () => {
    const value = ['aetherdrift', 'zzz'];
    expect(bulkActions('scope', fams, value, false).find((b) => b.label === 'Clear all')?.next).toEqual(['zzz']);
    expect(bulkActions('scope', fams, value, true).find((b) => b.label === 'Clear shown')?.next).toEqual(['zzz']);
  });
  it('offers no Clear all when only hand-picked options are chosen', () => {
    expect(bulkActions('scope', fams, ['zzz'], false).map((b) => b.label)).toEqual(['Select all']);
  });
});

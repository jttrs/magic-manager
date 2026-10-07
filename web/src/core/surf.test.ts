import { describe, expect, it } from 'vitest';
import type { SurfCardOut, SurfDrawOut } from './api';
import {
  activeFilters, artists, decodeSurf, drawRequest, EMPTY_FILTERS, encodeSurf, feedCards, feedSummary, nextPage, ownedLine, printingLine, textFaces, toggleColor,
} from './surf';

const card = (id: string, o: Partial<SurfCardOut> = {}): SurfCardOut => ({
  scryfall_id: id, name: `Card ${id}`, set_code: 'blb', set_name: 'Bloomburrow', collector_number: '12', rarity: 'rare', released_at: '2024-08-02',
  faces: [], prices: { nonfoil: 1, foil: null }, owned: 0, owned_any: 0, art_tags: [], color_identity: [], ...o,
});
const page = (ids: string[], o: Partial<SurfDrawOut> = {}): SurfDrawOut => ({ source: 'scryfall', query: 'q', cards: ids.map((i) => card(i)), exhausted: false, ...o });

describe('surf URL codec', () => {
  it('round-trips every filter and keeps defaults out of the URL', () => {
    const s = { source: 'owned' as const, filters: { ...EMPTY_FILTERS, art: ['dragon', 'moon'], families: ['fin'], colors: 'wu', color_match: 'within' as const, flavor: 'has' as const, types: ['creature'], legendary: 'only' as const, rarity: ['rare'], artist: ' Guay ', treatments: ['borderless'] } };
    const raw = encodeSurf(s);
    expect(decodeSurf(raw)).toEqual({ ...s, filters: { ...s.filters, artist: 'Guay' } });
    expect(encodeSurf({ source: 'scryfall', filters: EMPTY_FILTERS })).toBe('on');
    expect(encodeSurf({ source: 'scryfall', filters: { ...EMPTY_FILTERS, color_match: 'within' } })).toBe('on');
  });

  it('falls back to defaults on junk', () => {
    expect(decodeSurf('src=nope&fl=maybe&ci=xyzW')).toEqual({ source: 'scryfall', filters: { ...EMPTY_FILTERS, colors: 'w' } });
    expect(decodeSurf(undefined)).toEqual({ source: 'scryfall', filters: EMPTY_FILTERS });
  });
});

describe('filters', () => {
  it('counts active filters', () => {
    expect(activeFilters(EMPTY_FILTERS)).toBe(0);
    expect(activeFilters({ ...EMPTY_FILTERS, art: ['x'], flavor: 'none', artist: '  ' })).toBe(2);
  });

  it('toggles colours in WUBRG order; colourless excludes colours', () => {
    expect(toggleColor('', 'u')).toBe('u');
    expect(toggleColor('u', 'w')).toBe('wu');
    expect(toggleColor('wu', 'w')).toBe('u');
    expect(toggleColor('wu', 'c')).toBe('c');
    expect(toggleColor('c', 'r')).toBe('r');
    expect(toggleColor('c', 'c')).toBe('');
  });

  it('builds the draw request; the total is asked only on the first All-of-Magic page', () => {
    const s = { source: 'scryfall' as const, filters: { ...EMPTY_FILTERS, artist: ' Guay ' } };
    expect(drawRequest(s, 7, { offset: 0, first: true })).toMatchObject({ n: 3, seed: 7, with_total: true, filters: { artist: 'Guay' } });
    expect(drawRequest(s, 7, { offset: 0, first: false }).with_total).toBe(false);
    expect(drawRequest({ ...s, source: 'owned' }, 7, { offset: 6, first: true })).toMatchObject({ source: 'owned', offset: 6, with_total: false });
  });
});

describe('feed', () => {
  it('dedupes repeats across pages in draw order', () => {
    expect(feedCards([page(['a', 'b']), page(['b', 'c'])]).map((c) => c.scryfall_id)).toEqual(['a', 'b', 'c']);
  });

  it('stops when exhausted, when every match was seen, or after three dry pages', () => {
    expect(nextPage([page(['a'], { exhausted: true })])).toBeUndefined();
    expect(nextPage([page(['a', 'b'], { total: 2 })])).toBeUndefined();
    expect(nextPage([page(['a'], { total: 5 })])).toEqual({ offset: 0, first: false });
    const dry = [page(['a'], { total: 50 }), page(['a']), page(['a'])];
    expect(nextPage(dry)).toEqual({ offset: 0, first: false });
    expect(nextPage([...dry, page(['a'])])).toBeUndefined();
    expect(nextPage([...dry, page(['b'])])).toEqual({ offset: 0, first: false });
  });

  it('keeps paging your cards through empty, unexhausted pages until the server says done', () => {
    const empty = page([], { source: 'owned', next_offset: 120, total: 500 });
    expect(nextPage([empty])).toEqual({ offset: 120, first: false });
    expect(nextPage([empty, page([], { source: 'owned', next_offset: 500, exhausted: true })])).toBeUndefined();
  });

  it('pages your cards by offset', () => {
    expect(nextPage([page(['a'], { source: 'owned', next_offset: 24, total: 40 })])).toEqual({ offset: 24, first: false });
    expect(nextPage([page(['a'], { source: 'owned', next_offset: 40, exhausted: true })])).toBeUndefined();
  });
});

describe('card text', () => {
  it('prints the printing, ownership, faces and artists', () => {
    expect(printingLine(card('a'))).toBe('Bloomburrow · BLB #12 · Rare · 2024');
    expect(ownedLine(card('a'))).toBeNull();
    expect(ownedLine(card('a', { owned: 2, owned_any: 2 }))).toBe('You own 2 of this printing');
    expect(ownedLine(card('a', { owned: 2, owned_any: 5 }))).toBe('You own 2 of this printing · 5 in every printing');
    expect(ownedLine(card('a', { owned_any: 3 }))).toBe('You own 3 in other printings');
    expect(textFaces(card('a', { flavor_text: 'Fire.' }))).toEqual([{ name: 'Card a', type_line: undefined, flavor_text: 'Fire.', oracle_text: undefined }]);
    const dfc = card('d', { artist: 'Ann', faces: [{ name: 'Up', artist: 'Ann' }, { name: 'Down', artist: 'Bo' }] });
    expect(textFaces(dfc).map((f) => f.name)).toEqual(['Up', 'Down']);
    expect(artists(dfc)).toBe('Ann & Bo');
  });

  it('summarizes the feed', () => {
    const fmt = (n: number) => n.toLocaleString('en-US');
    expect(feedSummary('scryfall', 1470, 12, fmt)).toBe('1,470 match · 12 seen');
    expect(feedSummary('scryfall', null, 3, fmt)).toBe('3 seen');
    expect(feedSummary('owned', 214, 0, fmt)).toBe('up to 214 of your cards · 0 seen');
  });
});

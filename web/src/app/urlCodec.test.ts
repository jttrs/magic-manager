import { describe, expect, it } from 'vitest';
import { collectionSearch } from '../core/search';
import { canonicalizeAddressBar, parseSearch, stringifySearch } from './urlCodec';

const roundTrip = (search: Record<string, unknown>) => parseSearch(stringifySearch(search));

describe('urlCodec', () => {
  it('writes plain lists as a comma list', () => {
    expect(stringifySearch({ families: ['dft', 'tla', 'blb'] })).toBe('?families=dft%2Ctla%2Cblb');
  });

  it('reads a comma list, a bare value and an old JSON list into the same array', () => {
    const parse = (q: string) => collectionSearch.parse(parseSearch(q)).families;
    expect(parse('?families=dft,tla')).toEqual(['dft', 'tla']);
    expect(parse('?families=dft')).toEqual(['dft']);
    expect(parse('?families=%5B%22dft%22%2C%22tla%22%5D')).toEqual(['dft', 'tla']);
  });

  it('keeps JSON where a comma list would not round-trip', () => {
    expect(roundTrip({ src: ['precon:Squall, SeeD'] })).toEqual({ src: ['precon:Squall, SeeD'] });
    expect(roundTrip({ sets: ['123'] })).toEqual({ sets: ['123'] });
    expect(roundTrip({ q: 'Squall, SeeD' })).toEqual({ q: 'Squall, SeeD' });
    expect(roundTrip({ q: '123' })).toEqual({ q: '123' });
  });
});

describe('every route reads back the lists it writes', () => {
  it('history kinds, decks status and collection show survive a round trip', async () => {
    const { historySearch } = await import('../core/history');
    const { decksSearch } = await import('../core/search');
    const h = historySearch.parse(parseSearch(stringifySearch({ kinds: ['deck', 'pool'] })));
    expect(h.kinds).toEqual(['deck', 'pool']);
    const d = decksSearch.parse(parseSearch(stringifySearch({ status: ['built', 'buildable'] })));
    expect(d.status).toEqual(['built', 'buildable']);
    const c = collectionSearch.parse(parseSearch(stringifySearch({ show: ['owned', 'missing'] })));
    expect(c.show).toEqual(['owned', 'missing']);
  });
});

describe('canonicalizeAddressBar', () => {
  const run = (search: string) => {
    let wrote: string | null = null;
    canonicalizeAddressBar({ pathname: '/collection', search, hash: '' }, { state: null, replaceState: (_s, _t, url) => { wrote = String(url); } });
    return wrote;
  };
  it('rewrites JSON lists to the short form', () => {
    expect(run('?families=%5B%22dft%22%2C%22tla%22%5D')).toBe('/collection?families=dft%2Ctla');
  });
  it('leaves a short link, an empty search and a re-encoded search alone', () => {
    expect(run('?families=dft%2Ctla')).toBeNull();
    expect(run('')).toBeNull();
    expect(run('?q=Ahoy%20Mateys%27')).toBeNull();
  });
});

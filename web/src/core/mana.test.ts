import { describe, expect, it } from 'vitest';
import { identitySymbols, parseMana, spokenMana, symbolUrl } from './mana';

describe('mana symbols', () => {
  it('parses a cost, front face only', () => {
    expect(parseMana('{2}{U}{R}')).toEqual(['2', 'U', 'R']);
    expect(parseMana('{1}{G} // {3}')).toEqual(['1', 'G']);
    expect(parseMana(null)).toEqual([]);
  });
  it('names symbols for screen readers', () => {
    expect(spokenMana(['2', 'W/U', 'G/P', 'X'])).toBe('2, white or blue, Phyrexian green, X');
    expect(spokenMana([])).toBe('none');
  });
  it('points at Scryfall symbol files', () => {
    expect(symbolUrl('W/U')).toBe('https://svgs.scryfall.io/card-symbols/WU.svg');
    expect(symbolUrl('10')).toBe('https://svgs.scryfall.io/card-symbols/10.svg');
  });
  it('orders colour identity WUBRG, colourless as C', () => {
    expect(identitySymbols(['G', 'W', 'B'])).toEqual(['W', 'B', 'G']);
    expect(identitySymbols([])).toEqual(['C']);
  });
});

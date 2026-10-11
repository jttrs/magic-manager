import { describe, expect, it } from 'vitest';
import { cartAllowed, cartSwitchHint, lineQualifier } from './cartCheck';

const hello = (features: Record<string, boolean>) => ({ version: '0.3.0', features: { cart: true, deals: false, moxfield: false, ...features } });

describe('cart check view-model', () => {
  it('a store is readable only with its own permission (older companions: Mana Pool only)', () => {
    expect(cartAllowed('manapool', hello({}))).toBe(true);
    expect(cartAllowed('tcgplayer', hello({}))).toBe(false);
    expect(cartAllowed('tcgplayer', hello({ cart_tcgplayer: true }))).toBe(true);
    expect(cartAllowed('cardkingdom', hello({ cart_tcgplayer: true }))).toBe(false);
    expect(cartAllowed('manapool', null)).toBe(false);
    expect(cartSwitchHint('cardkingdom')).toContain('Card Kingdom cart');
  });

  it('names only what differs from Near Mint English', () => {
    expect(lineQualifier({ condition: 'NM', language: 'English' })).toBe('');
    expect(lineQualifier({ condition: null })).toBe('');
    expect(lineQualifier({ condition: 'lp', language: 'Japanese' })).toBe('LP · Japanese');
    expect(lineQualifier({ condition: 'EX', language: 'English' })).toBe('EX');
  });
});

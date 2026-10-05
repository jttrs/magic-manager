import { describe, expect, it } from 'vitest';
import { cartBookmarkletHref } from './cartBookmarklet';
import { buyTotal } from './collection';
import type { CollectionCardOut } from './api';

describe('cart bookmarklet', () => {
  it('is a single javascript: URL that parses, and never touches login state', () => {
    const href = cartBookmarkletHref();
    expect(href.startsWith('javascript:')).toBe(true);
    const code = decodeURIComponent(href.slice('javascript:'.length));
    expect(() => new Function(code)).not.toThrow();
    expect(code).not.toMatch(/localStorage|document\.cookie|fetch\(|XMLHttpRequest|auth-token/);
  });
});

describe('buy list total', () => {
  it('prices each printing at the finish its line names', () => {
    const c = (p: Partial<CollectionCardOut>) => ({ finishes: ['nonfoil', 'foil'], owned: {}, price_usd: 1, price_usd_foil: 4, ...p }) as CollectionCardOut;
    expect(buyTotal([c({}), c({ finishes: ['foil'] })], [])).toBe(5);
  });
});

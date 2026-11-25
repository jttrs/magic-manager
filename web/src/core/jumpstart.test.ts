import { describe, expect, it } from 'vitest';
import { jumpstartToDecks, legacyJumpstartSearch, shopDescribe } from './jumpstart';

describe('jumpstart view-model', () => {
  it('maps old Collection → Jumpstart links onto the same packs in Decks', () => {
    expect(jumpstartToDecks(legacyJumpstartSearch.parse({ set: 'j25', pack: 'Angels2_J25', show: 'close' }))).toEqual({
      types: ['Jumpstart'], status: ['buildable'], sets: ['j25'], deck: 'fn:Angels2_J25', group: 'color', q: '', shop: 'buildable', view: 'list',
    });
    expect(jumpstartToDecks(legacyJumpstartSearch.parse({ show: 'own', shop: 'packs' }))).toMatchObject({ status: ['built'], sets: [], deck: undefined, shop: 'packs' });
    expect(jumpstartToDecks(legacyJumpstartSearch.parse({ show: 'nope' })).status).toEqual(['built', 'buildable', 'unbuilt']);
  });

  it('labels both shopping lists, and their empty states', () => {
    const d = { buildable: { cards: 3, copies: 4, usd: 2.5 }, whole: { cards: 40, copies: 60, usd: 30 }, whole_packs: 3 };
    expect(shopDescribe('buildable', d)).toMatch(/^4 cards to build every theme · ≈ \$2\.50 at market$/);
    expect(shopDescribe('packs', d)).toMatch(/3 packs you don’t own · 60 cards · ≈ \$30\.00/);
    expect(shopDescribe('buildable', { ...d, buildable: { cards: 0, copies: 0, usd: 0 } })).toBe('Every theme is buildable from cards you own');
    expect(shopDescribe('packs', { ...d, whole_packs: 0 })).toBe('You own every pack version');
  });
});

// Cart check view-model: which carts the companion may read, and how a cart line's
// condition / language reads beside it. Framework-free (see dependency-cruiser).

import { ALLOW_ACCESS_HINT, type CartStore, type CompanionHello } from './companion';

export const CART_STORES: CartStore[] = ['manapool', 'tcgplayer', 'cardkingdom'];

/** Whether the paired companion may read this store's cart (its Chrome permission is on). */
export function cartAllowed(store: CartStore, hello: CompanionHello | null): boolean {
  if (!hello) return false;
  const f = hello.features;
  return store === 'manapool' ? f.cart : store === 'tcgplayer' ? f.cart_tcgplayer === true : f.cart_cardkingdom === true;
}

/** What lets the companion read a store's cart. */
export function cartSwitchHint(store: CartStore): string {
  return store === 'manapool' ? 'Allow manapool.com in the companion’s Chrome site access.' : ALLOW_ACCESS_HINT;
}

/** "LP · Japanese" for a played or non-English line; '' for Near Mint English (what market prices mean). */
export function lineQualifier(line: { condition?: string | null; language?: string | null }): string {
  const parts: string[] = [];
  if (line.condition && line.condition.toUpperCase() !== 'NM') parts.push(line.condition.toUpperCase());
  if (line.language && !/^(english|en)$/i.test(line.language)) parts.push(line.language);
  return parts.join(' · ');
}

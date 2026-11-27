import type { CopyTarget } from './CopyButton';
import { CardKingdomMark, CopyListMark, ManaPoolMark, TcgplayerMark } from './icons/marks';

/** Every list format the server's `exports` engine writes for a buy list. */
export type BuyStore = 'manapool' | 'tcgplayer' | 'cardkingdom' | 'moxfield' | 'plain';

const CARD_KINGDOM_NOTE = 'Card Kingdom takes names only; pick each printing and foil after Find Cards';

/** The bulk buy-list destinations as CopyTargets, in display order: the three stores,
 *  then (with `exports`) Moxfield and a plain list. */
export function buyListTargets(getText: (store: BuyStore) => CopyTarget['getText'], opts: { cardKingdomNote?: string; exports?: boolean } = {}): CopyTarget[] {
  const stores: CopyTarget[] = [
    { id: 'manapool', name: 'ManaPool', format: 'Bulk add', Mark: ManaPoolMark, getText: getText('manapool') },
    { id: 'tcgplayer', name: 'TCGplayer', format: 'Mass Entry', Mark: TcgplayerMark, getText: getText('tcgplayer') },
    { id: 'cardkingdom', name: 'Card Kingdom', format: 'Names only', Mark: CardKingdomMark, getText: getText('cardkingdom'), note: opts.cardKingdomNote ?? CARD_KINGDOM_NOTE },
  ];
  if (!opts.exports) return stores;
  return [
    ...stores,
    { id: 'moxfield', name: 'Moxfield', format: 'Import (set + number)', Mark: CopyListMark, getText: getText('moxfield') },
    { id: 'plain', name: 'Plain list', format: 'Quantity and name', Mark: CopyListMark, getText: getText('plain') },
  ];
}

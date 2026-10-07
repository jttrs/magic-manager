import type { CopyTarget } from './CopyButton';
import { CardKingdomMark, ManaPoolMark, TcgplayerMark } from './StoreMarks';

export type BuyStore = 'manapool' | 'tcgplayer' | 'cardkingdom';

const CARD_KINGDOM_NOTE = 'Card Kingdom takes names only; pick each printing and foil after Find Cards';

/** The bulk buy-list stores as CopyTargets, in display order. */
export function buyListTargets(getText: (store: BuyStore) => CopyTarget['getText'], opts: { cardKingdomNote?: string } = {}): CopyTarget[] {
  return [
    { id: 'manapool', name: 'ManaPool', Mark: ManaPoolMark, getText: getText('manapool') },
    { id: 'tcgplayer', name: 'TCGplayer', Mark: TcgplayerMark, getText: getText('tcgplayer') },
    { id: 'cardkingdom', name: 'Card Kingdom', Mark: CardKingdomMark, getText: getText('cardkingdom'), note: opts.cardKingdomNote ?? CARD_KINGDOM_NOTE },
  ];
}

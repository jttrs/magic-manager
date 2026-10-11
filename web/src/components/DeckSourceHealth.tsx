import { useEffect } from 'react';
import { useDownScrapers, useRefreshScraperHealth } from '../app/scraperHealth';
import { ARCHIDEKT_READER_KEY, deckKey, deckSourceOf, MOXFIELD_READER_KEY } from '../core/scraperHealth';
import { ScraperNotice } from './ScraperNotice';

/**
 * The "temporarily down" notice for the deck builder a pasted link belongs to —
 * the server import, or the companion's reader when it will read the deck.
 * Re-reads health when a fetch settles (a read that works clears the flag).
 */
export function DeckSourceHealth({ url, viaBrowser, settled }: { url: string; viaBrowser: boolean; settled: string }) {
  const source = deckSourceOf(url);
  const reader = source === 'moxfield' ? MOXFIELD_READER_KEY : source === 'archidekt' ? ARCHIDEKT_READER_KEY : null;
  const keys = source ? [viaBrowser && reader ? reader : deckKey(source)] : [];
  const down = useDownScrapers(keys);
  const refresh = useRefreshScraperHealth();
  useEffect(() => {
    if (settled) void refresh();
  }, [settled, refresh]);
  return <ScraperNotice down={down} />;
}

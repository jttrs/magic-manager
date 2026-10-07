import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { ingestDeckFromBrowser, type ResolveOut } from '../core/api';
import { useFeature } from './features';
import { unwrap } from './queries';
import { useCompanion } from './useCompanion';

const MOXFIELD_DECK = /^https:\/\/(?:www\.)?moxfield\.com\/decks\/[A-Za-z0-9_-]{4,64}(?:[/?#]|$)/i;

/** Moxfield decks read in YOUR browser by the companion (when connected) instead
 *  of the server's own browser window; lands as the same review lines. */
export function useBrowserDeck() {
  const on = useFeature('companion');
  const c = useCompanion();
  const [awaiting, setAwaiting] = useState<string | null>(null);
  const m = useMutation({
    mutationFn: async (url: string): Promise<ResolveOut> => {
      const d = await c.read('moxfield', { url }, (summary) => setAwaiting(summary));
      setAwaiting(null);
      return unwrap(await ingestDeckFromBrowser({ body: { source: 'moxfield', deck: d.deck } }));
    },
    onSettled: () => setAwaiting(null),
  });
  return {
    /** This URL will be read by the companion. */
    handles: (url: string) => on && c.status === 'ready' && MOXFIELD_DECK.test(url.trim()),
    read: m.mutateAsync,
    pending: m.isPending,
    awaiting,
    error: m.error,
    reset: m.reset,
  };
}

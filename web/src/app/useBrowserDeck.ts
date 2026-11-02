import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { ingestDeckFromBrowser, type ResolveOut } from '../core/api';
import { useFeature } from './features';
import { ownerPathsQuery, unwrap } from './queries';
import { useCompanion } from './useCompanion';

const MOXFIELD_DECK = /^https:\/\/(?:www\.)?moxfield\.com\/decks\/[A-Za-z0-9_-]{4,64}(?:[/?#]|$)/i;
/** The server's rule for a Moxfield link (decksource.source_of: "moxfield.com" in the host). */
function isMoxfieldHost(url: string): boolean {
  try {
    const u = new URL(url.trim());
    return `${u.username}:${u.password}@${u.host}`.toLowerCase().includes('moxfield.com');   // netloc, like the server
  } catch { return false; }
}
const ARCHIDEKT_DECK = /^https:\/\/(?:www\.)?archidekt\.com\/decks\/\d{1,12}(?:[/?#-]|$)/i;

/** Moxfield and Archidekt decks read in YOUR browser by the companion (when
 *  connected — Archidekt once its switch is on) instead of on the server, so
 *  your private decks work; lands as the same review lines. */
export function useBrowserDeck() {
  const on = useFeature('companion');
  // Reading Moxfield on the server drives a browser there: admins only when hosted
  // (owner_machine "decks.moxfield_server"); everyone else reads it with the companion.
  // Hosted only, and only once /api/features said so: locally (or while it loads) the server path stays.
  const paths = useQuery(ownerPathsQuery()).data;
  const companionOnly = Boolean(paths?.hosted && !paths.paths['decks.moxfield_server']);
  const c = useCompanion();
  const [awaiting, setAwaiting] = useState<string | null>(null);
  const m = useMutation({
    mutationFn: async (url: string): Promise<ResolveOut> => {
      if (ARCHIDEKT_DECK.test(url)) {
        const d = await c.read('archidekt', { url }, (summary) => setAwaiting(summary));
        setAwaiting(null);
        return unwrap(await ingestDeckFromBrowser({ body: { source: 'archidekt', deck: d.deck } }));
      }
      const d = await c.read('moxfield', { url }, (summary) => setAwaiting(summary));
      setAwaiting(null);
      return unwrap(await ingestDeckFromBrowser({ body: { source: 'moxfield', deck: d.deck } }));
    },
    onSettled: () => setAwaiting(null),
  });
  const ready = on && c.status === 'ready';
  return {
    /** This URL will be read by the companion. */
    handles: (url: string) => ready && (MOXFIELD_DECK.test(url.trim()) || (Boolean(c.hello?.features.archidekt) && ARCHIDEKT_DECK.test(url.trim()))),
    /** Only the companion may read this URL for you here (a Moxfield deck, when the server's
     *  browser is the owner's): offer its setup, never the server fetch. */
    needsCompanion: (url: string) => companionOnly && isMoxfieldHost(url),
    read: m.mutateAsync,
    pending: m.isPending,
    awaiting,
    error: m.error,
    reset: m.reset,
  };
}

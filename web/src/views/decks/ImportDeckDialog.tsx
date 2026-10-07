import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Dialog } from 'radix-ui';
import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { unwrap } from '../../app/queries';
import { useJob } from '../../app/useJob';
import { Button } from '../../components/Button';
import { useBrowserDeck } from '../../app/useBrowserDeck';
import { AwaitingNote, FailureNote } from '../../components/companion/CompanionNotes';
import { deckImport, type ResolveOut } from '../../core/api';

const DECK_URL = /^https?:\/\/([\w-]+\.)*(archidekt\.com|moxfield\.com|mtggoldfish\.com|manabox\.app|scryfall\.com)\//i;

/** Import a decklist from a deck builder. Saves the RECIPE only (never built);
 *  "I have these cards" continues into the add-to-collection review. */
export function ImportDeckDialog({ trigger }: { trigger: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState('');
  const [haveCards, setHaveCards] = useState(false);
  const [error, setError] = useState('');
  const { live, start } = useJob();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const browser = useBrowserDeck();
  const [saving, setSaving] = useState(false);
  const running = saving || browser.pending || (live != null && live.status !== 'succeeded' && live.status !== 'failed');

  /** Save a fetched deck's recipe (server fetch or companion read), then open it. */
  const save = useCallback(async (resolved: ResolveOut, isCancelled: () => boolean = () => false) => {
    if (!resolved.deck) return;
    setSaving(true);
    try {
      const r = unwrap(await deckImport({ body: { deck: resolved.deck } }));
      if (isCancelled()) return;
      await qc.invalidateQueries({ queryKey: ['decks'] });
      setOpen(false);
      setUrl('');
      navigate({ to: '/decks', search: (s) => ({ ...s, deck: r.slug, types: [], add: haveCards || undefined }) });
    } catch (e) {
      if (!isCancelled()) setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }, [haveCards, navigate, qc]);

  useEffect(() => {
    if (live?.status === 'failed') setError(live.error ?? 'Couldn’t read that deck.');
    if (live?.status !== 'succeeded') return;
    const art = (live.artifacts as { label: string; data: ResolveOut }[] | undefined)?.find((a) => a.label === 'lines');
    if (!art?.data.deck) return;
    let cancelled = false;
    void save(art.data, () => cancelled);
    return () => { cancelled = true; };
  }, [live?.status, live?.artifacts, live?.error, save]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!DECK_URL.test(url.trim())) {
      setError('Paste a deck link from Archidekt, Moxfield, MTGGoldfish, ManaBox or Scryfall.');
      return;
    }
    setError('');
    browser.reset();
    if (browser.handles(url)) {
      try {
        await save(await browser.read(url.trim()));
      } catch {
        // shown by FailureNote below
      }
      return;
    }
    const err = await start('ingest.fetch_deck', { url: url.trim() });
    if (err) setError(err);
  };

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !running && setOpen(o)}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        <Dialog.Content className="paper-grain fixed left-1/2 top-1/2 z-50 w-[min(30rem,calc(100vw-1.5rem))] -translate-x-1/2 -translate-y-1/2 rounded-sm bg-paper p-5 text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none">
          <form onSubmit={submit} className="flex flex-col gap-4">
            <Dialog.Title className="border-b-2 border-rule-strong pb-2 text-2xl voice-condensed font-bold leading-none">Import a deck</Dialog.Title>
            <Dialog.Description className="text-md leading-relaxed">Saves the decklist to Decks. It isn’t marked built — build it from your cards whenever you assemble it.</Dialog.Description>
            <label className="flex flex-col gap-1.5 text-sm voice-semi text-ink-muted">
              Deck link — Archidekt, Moxfield, MTGGoldfish, ManaBox or Scryfall
              <input
                autoFocus
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://archidekt.com/decks/…"
                className="h-10 rounded-sm border border-rule-strong bg-paper-raised px-3 text-md text-ink placeholder:text-ink-muted focus-visible:border-accent"
              />
            </label>
            <label className="inline-flex cursor-pointer items-start gap-2 text-md">
              <input type="checkbox" checked={haveCards} onChange={(e) => setHaveCards(e.target.checked)} className="mt-1 accent-[var(--theme-accent)]" />
              <span>Also add these cards to my collection <span className="block text-sm text-ink-muted">You’ll review the printings before anything is added.</span></span>
            </label>
            {url.includes('moxfield') && (
              <p className="text-xs text-ink-muted">{browser.handles(url) ? 'Read in this browser by the companion — you approve what it sends.' : 'Moxfield opens a Chrome window to read the deck.'}</p>
            )}
            {browser.awaiting != null && <AwaitingNote summary={browser.awaiting} />}
            {browser.error && <FailureNote error={browser.error} />}
            {running && <p aria-live="polite" className="text-sm text-ink-muted">{live?.log.at(-1)?.msg ?? 'Reading the deck…'}</p>}
            {error && <p role="alert" className="text-sm text-danger">{error}</p>}
            <div className="flex justify-end gap-2">
              <Dialog.Close asChild>
                <Button tone="paper" disabled={running}>Cancel</Button>
              </Dialog.Close>
              <Button type="submit" emphasis="primary" disabled={running || !url.trim()}>{running ? 'Importing…' : 'Import deck'}</Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Dialog } from 'radix-ui';
import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { unwrap } from '../../app/queries';
import { useJob } from '../../app/useJob';
import { Button } from '../../components/Button';
import { useBrowserDeck } from '../../app/useBrowserDeck';
import { DeckSourceHealth } from '../../components/DeckSourceHealth';
import { AwaitingNote, FailureNote } from '../../components/companion/CompanionNotes';
import { CompanionRequired } from '../../components/companion/CompanionRequired';
import { Check } from '../../components/controls/Check';
import { TextInput } from '../../components/controls/TextField';
import { dialogContentClass, dialogOverlayClass, dialogTitleClass } from '../../components/controls/surfaces';
import { deckImport, type ResolveOut } from '../../core/api';

const DECK_URL = /^https?:\/\/([\w-]+\.)*(archidekt\.com|moxfield\.com|mtggoldfish\.com|manabox\.app|scryfall\.com)\//i;

/** Import a decklist from a deck builder. Saves the RECIPE only (never built);
 *  "I have these cards" continues into the add-to-collection review. */
export function ImportDeckDialog({ trigger }: { trigger: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState('');
  const [haveCards, setHaveCards] = useState(false);
  const [error, setError] = useState('');
  const { live, start, reset } = useJob();
  // Read at save time, not a dependency: ticking the box must not re-run the
  // job effect (which would re-import the last deck).
  const haveCardsRef = useRef(haveCards);
  // The job result already imported — never imported twice.
  const consumed = useRef<unknown>(null);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const browser = useBrowserDeck();
  const [saving, setSaving] = useState(false);
  const blocked = !browser.handles(url) && browser.needsCompanion(url.trim());
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
      navigate({ to: '/decks', search: (s) => ({ ...s, deck: r.slug, types: [], add: haveCardsRef.current || undefined }) });
    } catch (e) {
      if (!isCancelled()) setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }, [navigate, qc]);

  useEffect(() => {
    if (live?.status === 'failed') setError(live.error ?? 'Couldn’t read that deck.');
    if (live?.status !== 'succeeded') return;
    const art = (live.artifacts as { label: string; data: ResolveOut }[] | undefined)?.find((a) => a.label === 'lines');
    if (!art?.data.deck || consumed.current === live.artifacts) return;
    consumed.current = live.artifacts;
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
    if (blocked) return;
    setError('');
    browser.reset();
    reset();
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
    <Dialog.Root open={open} onOpenChange={(o) => {
      if (running) return;
      if (o) { reset(); setError(''); }
      setOpen(o);
    }}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className={dialogOverlayClass} />
        <Dialog.Content className={dialogContentClass('sm')}>
          <form onSubmit={submit} className="flex flex-col gap-4">
            <Dialog.Title className={dialogTitleClass}>Import a deck</Dialog.Title>
            <Dialog.Description className="text-md leading-relaxed">Saves the decklist to Decks. It isn’t marked built — build it from your cards whenever you assemble it.</Dialog.Description>
            <label className="flex flex-col gap-1.5 text-sm voice-semi text-ink-muted">
              Deck link — Archidekt, Moxfield, MTGGoldfish, ManaBox or Scryfall
              <TextInput
                tone="paper"
                autoFocus
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://archidekt.com/decks/…"
              />
            </label>
            <Check checked={haveCards} onChange={(c) => { haveCardsRef.current = c; setHaveCards(c); }} hint="You’ll review the printings before anything is added.">Also add these cards to my collection</Check>
            <DeckSourceHealth url={url} viaBrowser={browser.handles(url)} settled={live?.status === 'succeeded' || live?.status === 'failed' ? live.status : browser.error ? 'error' : ''} />
            {blocked && <CompanionRequired what="Moxfield decks" />}
            {url.includes('moxfield') && !blocked && (
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
              <Button type="submit" emphasis="primary" disabled={running || !url.trim() || blocked}>{running ? 'Importing…' : 'Import deck'}</Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

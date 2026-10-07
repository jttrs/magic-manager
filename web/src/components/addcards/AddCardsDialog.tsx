import { useQueryClient } from '@tanstack/react-query';
import { Dialog, Tabs } from 'radix-ui';
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { unwrap } from '../../app/queries';
import { deckImport, ingestCommit, type DeckSourceOut, type PrintingOut, type ResolvedLineOut, type ResolveOut } from '../../core/api';
import { fmtInt } from '../../core/format';
import { commitItems, fromResolved, reviewStats, stagePrinting, updateLine, type Finish, type ReviewLine } from '../../core/ingest';
import { Button } from '../Button';
import { Chevron } from '../Chevron';
import { DeckPane } from './DeckPane';
import { PastePane } from './PastePane';
import { ReviewTable } from './ReviewTable';
import { SearchPane } from './SearchPane';

type Mode = 'search' | 'paste' | 'deck';
type Done = { summary: string; mode: Mode };

export type AddCardsSeed = { name: string; lines: ResolvedLineOut[] };

/** "Add cards": search one printing, paste a list, or bring a deck/precon —
 *  every path ends in the same review checklist and one commit. A `seed`
 *  (e.g. from the Deck Manager) opens straight into that review. */
export function AddCardsDialog({ trigger, seed, onSeedDone }: { trigger?: ReactNode; seed?: AddCardsSeed | null; onSeedDone?: () => void }) {
  const qc = useQueryClient();
  const [open, setOpenState] = useState(false);
  const [mode, setMode] = useState<Mode>('search');
  const [staged, setStaged] = useState<ReviewLine[]>([]);
  const [pasteText, setPasteText] = useState('');
  const [pasted, setPasted] = useState<{ lines: ReviewLine[]; warnings: string[] } | null>(null);
  const [deck, setDeck] = useState<{ lines: ReviewLine[]; warnings: string[]; name: string | null; source?: DeckSourceOut | null } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState<Done | null>(null);

  useEffect(() => {
    if (!seed) return;
    setMode('deck');
    setDone(null);
    setError('');
    setDeck({ lines: fromResolved(seed.lines, 'k'), warnings: [], name: seed.name });
    setOpenState(true);
  }, [seed]);
  const setOpen = (o: boolean) => {
    setOpenState(o);
    if (!o) onSeedDone?.();
  };

  const lines = mode === 'search' ? staged : mode === 'paste' ? pasted?.lines : deck?.lines;
  const setLines = (fn: (ls: ReviewLine[]) => ReviewLine[]) => {
    if (mode === 'search') setStaged(fn);
    else if (mode === 'paste') setPasted((p) => (p ? { ...p, lines: fn(p.lines) } : p));
    else setDeck((d) => (d ? { ...d, lines: fn(d.lines) } : d));
  };
  const onFetched = useCallback((r: ResolveOut) => setDeck({ lines: fromResolved(r.lines, 'd'), warnings: r.warnings ?? [], name: r.deck_name ?? null, source: r.deck ?? null }), []);
  const [saveList, setSaveList] = useState(true);

  async function commit() {
    if (!lines) return;
    const items = commitItems(lines);
    if (!items.length) return;
    setBusy(true);
    setError('');
    try {
      const r = unwrap(await ingestCommit({ body: { items, source: mode, label: mode === 'deck' ? deck?.name ?? null : null } }));
      let summary = r.summary;
      if (mode === 'deck' && saveList && deck?.source) {
        try {
          const saved = unwrap(await deckImport({ body: { deck: deck.source } }));
          summary += saved.duplicate ? ' · decklist already in Decks' : ' · decklist saved to Decks';
          await qc.invalidateQueries({ queryKey: ['decks'] });
        } catch (e) {
          summary += ` · decklist not saved: ${(e as Error).message}`;
        }
      }
      setDone({ summary, mode });
      if (mode === 'search') setStaged([]);
      else if (mode === 'paste') { setPasted(null); setPasteText(''); }
      else setDeck(null);
      await qc.invalidateQueries({ queryKey: ['collection'] });
      await qc.invalidateQueries({ queryKey: ['history'] });
    } catch (e) {
      setError(`Nothing was added: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  const stats = lines ? reviewStats(lines) : null;
  const reviewing = mode === 'search' ? staged.length > 0 : mode === 'paste' ? pasted != null : deck != null;

  return (
    <Dialog.Root open={open} onOpenChange={(o) => { setOpen(o); if (!o) { setDone(null); setError(''); } }}>
      {trigger && <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>}
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        <Dialog.Content
          className="paper-grain fixed inset-x-2 top-[3dvh] bottom-[3dvh] z-50 mx-auto flex max-w-6xl flex-col rounded-sm bg-paper text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none sm:inset-x-6 @container"
        >
          <Tabs.Root value={mode} onValueChange={(m) => { setMode(m as Mode); setDone(null); setError(''); }} className="flex min-h-0 flex-1 flex-col">
            <header className="flex flex-wrap items-end gap-x-6 gap-y-2 border-b-2 border-rule-strong px-5 pt-4">
              <Dialog.Title className="pb-2 text-3xl voice-condensed font-bold leading-none">Add cards</Dialog.Title>
              <Dialog.Description className="sr-only">Search for a printing, paste a card list, or bring a deck or precon. Review every line, then add the copies to your collection.</Dialog.Description>
              <Tabs.List aria-label="How to add" className="flex gap-5">
                {(
                  [
                    ['search', 'Search'],
                    ['paste', 'Paste a list'],
                    ['deck', 'Deck or precon'],
                  ] as const
                ).map(([v, label]) => (
                  <Tabs.Trigger
                    key={v}
                    value={v}
                    className="-mb-0.5 cursor-pointer border-b-2 border-transparent pb-2 text-md voice-semi text-ink-muted transition-colors ease-guide hover:text-ink data-[state=active]:border-accent data-[state=active]:text-ink"
                  >
                    {label}
                  </Tabs.Trigger>
                ))}
              </Tabs.List>
              <Dialog.Close aria-label="Close" className="ml-auto mb-2 grid size-8 cursor-pointer place-items-center rounded-sm text-xl text-ink-muted hover:bg-paper-sunk hover:text-ink">×</Dialog.Close>
            </header>

            <div className="flex min-h-0 flex-1 flex-col px-5 py-4">
              {done && (
                <p role="status" className="mb-3 flex flex-wrap items-baseline gap-3 rounded-sm bg-paper-sunk px-3 py-2 text-md">
                  <span className="highlighter px-1 voice-semi font-medium">Added {done.summary.replace(/^\+/, '')}</span>
                  <span className="text-sm text-ink-muted">Your collection is refreshing behind this dialog.</span>
                </p>
              )}

              <Tabs.Content value="search" className="grid min-h-0 flex-1 gap-5 data-[state=inactive]:hidden @[52rem]:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
                <SearchPane onPick={(p: PrintingOut, f: Finish) => { setDone(null); setStaged((s) => stagePrinting(s, p, f)); }} />
                <section aria-labelledby="staged-h" className="flex min-h-0 flex-col @container">
                  <h3 id="staged-h" className="border-b-2 border-rule-strong pb-1 text-lg voice-condensed font-bold uppercase">To add</h3>
                  {staged.length ? (
                    <div className="min-h-0 flex-1 overflow-y-auto pr-3 [scrollbar-gutter:stable]">
                      <ReviewTable label="Cards to add" lines={staged} onChange={(k, p) => setStaged((s) => updateLine(s, k, p))} onRemove={(k) => setStaged((s) => s.filter((l) => l.key !== k))} />
                    </div>
                  ) : (
                    <p className="py-4 text-sm text-ink-muted">Press a card on the left to add it here. Press again for another copy.</p>
                  )}
                </section>
              </Tabs.Content>

              <Tabs.Content value="paste" className="flex min-h-0 flex-1 flex-col data-[state=inactive]:hidden">
                {pasted ? (
                  <Review
                    title={readTitle(pasted.lines)}
                    warnings={pasted.warnings}
                    back={{ label: 'Edit list', onClick: () => setPasted(null) }}
                  >
                    <ReviewTable label="Pasted cards" lines={pasted.lines} onChange={(k, p) => setLines((ls) => updateLine(ls, k, p))} />
                  </Review>
                ) : (
                  <PastePane text={pasteText} onText={setPasteText} onResolved={(r) => { setDone(null); setPasted({ lines: fromResolved(r.lines, 'p'), warnings: r.warnings ?? [] }); }} />
                )}
              </Tabs.Content>

              <Tabs.Content value="deck" className="flex min-h-0 flex-1 flex-col data-[state=inactive]:hidden">
                {deck ? (
                  <Review title={deck.name ?? 'Fetched deck'} warnings={deck.warnings} back={{ label: 'Choose another', onClick: () => setDeck(null) }}>
                    <ReviewTable label="Deck cards" lines={deck.lines} onChange={(k, p) => setLines((ls) => updateLine(ls, k, p))} />
                  </Review>
                ) : (
                  <DeckPane onFetched={onFetched} />
                )}
              </Tabs.Content>
            </div>

            {reviewing && stats && (
              <footer className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-rule px-5 py-3">
                <p className="text-sm tabular text-ink-muted">
                  <span className="text-ink">{fmtInt(stats.copies)} {stats.copies === 1 ? 'copy' : 'copies'}</span>
                  {stats.picked > 0 && ` · ${fmtInt(stats.picked)} best-guess printings to check`}
                  {stats.unresolved > 0 && <span className="text-danger"> · {fmtInt(stats.unresolved)} not found</span>}
                  {stats.skipped > 0 && ` · ${fmtInt(stats.skipped)} left out`}
                </p>
                {error && <p role="alert" className="text-sm text-danger">{error}</p>}
                {mode === 'deck' && deck?.source && (
                  <label className="ml-auto inline-flex cursor-pointer items-center gap-1.5 text-sm text-ink">
                    <input type="checkbox" checked={saveList} onChange={(e) => setSaveList(e.target.checked)} className="accent-[var(--theme-accent)]" />
                    Also save the decklist to Decks
                  </label>
                )}
                <Button tone="paper" emphasis="primary" onClick={commit} disabled={busy || stats.copies === 0} className="ml-auto">
                  {busy ? 'Adding…' : `Add ${fmtInt(stats.copies)} ${stats.copies === 1 ? 'copy' : 'copies'}`}
                </Button>
              </footer>
            )}
          </Tabs.Root>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** "4 of 5 lines matched" — the outcome, not the parse count. */
function readTitle(lines: ReviewLine[]): string {
  const ok = lines.filter((l) => l.status !== 'unresolved').length;
  return ok === lines.length ? `${fmtInt(ok)} ${ok === 1 ? 'line' : 'lines'} matched` : `${fmtInt(ok)} of ${fmtInt(lines.length)} lines matched`;
}

function Review({ title, warnings, back, children }: { title: string; warnings: string[]; back: { label: string; onClick: () => void }; children: ReactNode }) {
  return (
    <section aria-label={title} className="flex min-h-0 flex-1 flex-col @container">
      <div className="flex items-baseline gap-4 border-b-2 border-rule-strong pb-1">
        <h3 className="text-lg voice-condensed font-bold uppercase">{title}</h3>
        <button
          type="button"
          onClick={back.onClick}
          className="inline-flex cursor-pointer items-center gap-0.5 self-center rounded-sm px-1 text-sm voice-semi font-medium text-accent-ink underline decoration-1 underline-offset-2 hover:decoration-2"
        >
          <Chevron dir="left" className="size-3.5" />
          {back.label}
        </button>
      </div>
      {warnings.length > 0 && (
        <details className="border-b border-rule py-1.5 text-sm text-ink-muted">
          <summary className="cursor-pointer">{fmtInt(warnings.length)} {warnings.length === 1 ? 'line needs' : 'lines need'} a look</summary>
          <ul className="mt-1 flex flex-col gap-0.5 text-xs">{warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </details>
      )}
      <div className="min-h-0 flex-1 overflow-y-auto pr-3 [scrollbar-gutter:stable]">{children}</div>
    </section>
  );
}

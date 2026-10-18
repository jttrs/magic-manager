import { Button } from '../../components/Button';
import { PastePane } from '../../components/addcards/PastePane';
import { Review, ReviewTally, readTitle } from '../../components/addcards/Review';
import { ReviewTable } from '../../components/addcards/ReviewTable';
import { addLines, addsFromReview, boardOfSection, type Board, type Draft } from '../../core/deckDraft';
import { fmtInt } from '../../core/format';
import { fromResolved, reviewStats, updateLine, type ReviewLine } from '../../core/ingest';

/** The tab's state lives with the editor so switching tabs keeps a half-reviewed list. */
export type BulkState = { text: string; read: { lines: ReviewLine[]; warnings: string[] } | null; done: string | null };
export const BULK_EMPTY: BulkState = { text: '', read: null, done: null };

const BOARD_LABEL: Record<Board, string> = { commander: 'Commander', main: 'Main deck', companion: 'Companion', side: 'Sideboard', maybe: 'Maybe', token: 'Tokens' };
const BOARD_ORDER: Board[] = ['commander', 'companion', 'main', 'side', 'maybe'];

/** Bulk add: paste a list, check every line's printing, then add it all to the draft
 *  (same reader and checklist as Add cards → Paste a list; nothing touches your collection). */
export function BulkAddTab({ state, onState, onEdit }: { state: BulkState; onState: (fn: (s: BulkState) => BulkState) => void; onEdit: (fn: (d: Draft) => Draft) => void }) {
  const { read } = state;
  const stats = read ? reviewStats(read.lines) : null;

  function add() {
    if (!read) return;
    const adds = addsFromReview(read.lines);
    const copies = adds.reduce((t, a) => t + a.count, 0);
    if (!copies) return;
    onEdit((d) => addLines(d, adds));
    onState(() => ({ ...BULK_EMPTY, done: `Added ${fmtInt(copies)} ${copies === 1 ? 'card' : 'cards'} to the deck. Save deck to keep them.` }));
  }

  const setLines = (fn: (ls: ReviewLine[]) => ReviewLine[]) => onState((s) => (s.read ? { ...s, read: { ...s.read, lines: fn(s.read.lines) } } : s));
  const groups = read ? BOARD_ORDER.map((b) => [b, read.lines.filter((l) => boardOfSection(l.section) === b)] as const).filter(([, ls]) => ls.length) : [];

  return (
    <div className="mt-3 flex min-h-0 flex-1 flex-col px-4 pb-4">
      {state.done && <p role="status" className="mb-3 rounded-sm bg-paper-sunk px-3 py-2 text-sm"><span className="highlighter px-1 voice-semi font-medium">{state.done}</span></p>}
      {read ? (
        <>
          <Review title={readTitle(read.lines)} warnings={read.warnings} back={{ label: 'Edit list', onClick: () => onState((s) => ({ ...s, read: null })) }}>
            {groups.map(([board, lines]) => (
              <section key={board} aria-label={BOARD_LABEL[board]}>
                {groups.length > 1 && <h4 className="mt-3 text-sm voice-condensed font-bold uppercase tracking-[0.04em] text-ink-muted">{BOARD_LABEL[board]}</h4>}
                <ReviewTable label={`${BOARD_LABEL[board]} cards`} lines={lines} onChange={(k, p) => setLines((ls) => updateLine(ls, k, p))} onRemove={(k) => setLines((ls) => ls.filter((l) => l.key !== k))} />
              </section>
            ))}
          </Review>
          {stats && (
            <footer className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-rule pt-3">
              <ReviewTally stats={stats} />
              <Button tone="paper" emphasis="primary" onClick={add} disabled={stats.copies === 0} className="ml-auto">
                Add {fmtInt(stats.copies)} {stats.copies === 1 ? 'card' : 'cards'} to deck
              </Button>
            </footer>
          )}
        </>
      ) : (
        <>
          <p className="mb-2 text-sm text-ink-muted">Paste a decklist. Lines under <span className="tabular">Commander</span>, <span className="tabular">Sideboard</span> or <span className="tabular">Maybeboard</span> headers (or marked <span className="tabular">*CMDR*</span>) go to that board. Your collection isn’t changed.</p>
          <PastePane
            text={state.text}
            onText={(text) => onState((s) => ({ ...s, text, done: null }))}
            onResolved={(r) => onState((s) => ({ ...s, done: null, read: { lines: fromResolved(r.lines, 'b'), warnings: r.warnings ?? [] } }))}
          />
        </>
      )}
    </div>
  );
}

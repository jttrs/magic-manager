import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useId, useRef, useState, type ReactNode, type RefObject } from 'react';
import { preconCatalogQuery } from '../../app/queries';
import { useJob, type JobLive } from '../../app/useJob';
import type { PreconOptionOut, ResolveOut } from '../../core/api';
import { fmtInt } from '../../core/format';
import { DECK_SITES, deckFacts, productOwned, readDeckQuery, type DeckQuery } from '../../core/ingest';
import { Button } from '../Button';
import { useBrowserDeck } from '../../app/useBrowserDeck';
import { DeckSourceHealth } from '../DeckSourceHealth';
import { AwaitingNote, FailureNote } from '../companion/CompanionNotes';

const crop = (url: string) => url.replace('/normal/', '/art_crop/');

/** "Add decklist or product": ONE field. A deck link from a supported builder
 *  becomes a single result row you read, then review; anything else searches the
 *  product catalog. Every result ends in the same `Add…` — a read deck opens the
 *  review checklist, a product its copies/keep form (added directly as a job). */
export function DeckPane({ onFetched }: { onFetched: (r: ResolveOut) => void }) {
  const [text, setText] = useState('');
  const query = readDeckQuery(text);
  const reader = useRef<DeckReader | null>(null);
  const hintId = useId();
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <label className="flex flex-col gap-1.5 text-sm voice-semi text-ink-muted">
        Deck link or product
        <input
          type="search"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.repeat && query.kind === 'deck') reader.current?.(); }}
          placeholder="https://moxfield.com/decks/…  or  Final Fantasy, fic, Commander Deck…"
          aria-describedby={hintId}
          aria-invalid={query.kind === 'link' || undefined}
          className="h-10 max-w-2xl rounded-sm border border-rule-strong bg-paper-raised px-3 text-md text-ink placeholder:text-ink-muted focus-visible:border-accent aria-[invalid]:border-danger"
        />
      </label>
      <p id={hintId} className={`-mt-1 text-xs ${query.kind === 'link' ? 'text-danger' : 'text-ink-muted'}`}>
        {query.kind === 'link'
          ? `That link isn’t a deck from ${DECK_SITES}.`
          : `Paste a deck link from ${DECK_SITES} — or search products by name, set code or type.`}
      </p>
      <div className="relative min-h-0 flex-1 overflow-y-auto pr-3 [scrollbar-gutter:stable]">
        {query.kind === 'deck' ? (
          <DeckLink key={query.url} query={query} onFetched={onFetched} reader={reader} />
        ) : query.kind === 'search' ? (
          <Products q={query.q} />
        ) : null}
      </div>
    </div>
  );
}

type DeckReader = () => void;

function JobLine({ live }: { live: JobLive | null }) {
  if (!live) return null;
  const last = live.error ?? live.summary ?? live.log.at(-1)?.msg ?? 'Queued…';
  const failed = live.status === 'failed' || Boolean(live.error);
  return <p aria-live="polite" className={`text-sm ${failed ? 'text-danger' : live.status === 'succeeded' ? 'highlighter self-start px-1 text-ink' : 'text-ink-muted'}`}>{last}</p>;
}

function Thumb({ uri }: { uri: string | null | undefined }) {
  return uri ? (
    <img src={crop(uri)} alt="" loading="lazy" decoding="async" className="size-10 shrink-0 rounded-xs object-cover" />
  ) : (
    <span aria-hidden className="size-10 shrink-0 rounded-xs border border-rule bg-paper-sunk" />
  );
}

function ResultsHead({ children }: { children: ReactNode }) {
  return <h3 className="border-b-2 border-rule-strong pb-1 text-lg voice-condensed font-bold uppercase text-ink">{children}</h3>;
}

/** The pasted deck link as one result: read it (server job, or the companion in
 *  this browser), then `Add…` opens the review. */
function DeckLink({ query, onFetched, reader }: { query: Extract<DeckQuery, { kind: 'deck' }>; onFetched: (r: ResolveOut) => void; reader: RefObject<DeckReader | null> }) {
  const [deck, setDeck] = useState<ResolveOut | null>(null);
  const [error, setError] = useState('');
  const { live, start } = useJob();
  const browser = useBrowserDeck();
  const viaBrowser = browser.handles(query.url);
  const running = browser.pending || (live != null && live.status !== 'succeeded' && live.status !== 'failed');
  // Set synchronously: `running` only turns true once the job is enqueued, so a
  // double press could otherwise start a second read (another Chrome window for Moxfield).
  const starting = useRef(false);

  useEffect(() => {
    if (live?.status !== 'succeeded') return;
    const art = (live.artifacts as { label: string; data: ResolveOut }[] | undefined)?.find((a) => a.label === 'lines');
    if (art) setDeck(art.data);
  }, [live?.status, live?.artifacts]);

  async function readDeck() {
    if (starting.current || running || deck) return;
    starting.current = true;
    setError('');
    browser.reset();
    try {
      if (viaBrowser) {
        try {
          setDeck(await browser.read(query.url));
        } catch {
          // shown by FailureNote below
        }
        return;
      }
      const err = await start('ingest.fetch_deck', { url: query.url });
      if (err) setError(err);
    } finally {
      starting.current = false;
    }
  }
  useEffect(() => {
    reader.current = readDeck;
    return () => { reader.current = null; };
  });

  const title = deck?.deck_name ?? `Deck on ${query.site}`;
  return (
    <section aria-label="Deck link" className="flex flex-col gap-2">
      <ResultsHead>Deck link</ResultsHead>
      <ul aria-label="Results" className="flex flex-col">
        <li className="ruled flex items-center gap-3 py-2">
          {deck ? <Thumb uri={deck.deck_image_uri} /> : <LinkTile />}
          <div className="min-w-0 flex-1">
            <p className="truncate text-md voice-semi font-medium text-ink">{title}</p>
            <p className="truncate text-xs tabular text-ink-muted">{deck ? deckFacts(deck, query.site) : query.url}</p>
          </div>
          {deck ? (
            <Button tone="paper" onClick={() => onFetched(deck)} className="shrink-0">Add…</Button>
          ) : (
            <Button tone="paper" onClick={readDeck} disabled={running} className="shrink-0">{running ? 'Reading…' : 'Read deck'}</Button>
          )}
        </li>
      </ul>
      <DeckSourceHealth url={query.url} viaBrowser={viaBrowser} settled={live?.status === 'succeeded' || live?.status === 'failed' ? live.status : browser.error ? 'error' : ''} />
      {!deck && (viaBrowser ? (
        <p className="text-xs text-ink-muted">Read in this browser by the companion, so your private decks work too. You approve what it sends.</p>
      ) : query.site === 'Moxfield' ? (
        <p className="text-xs text-ink-muted">Moxfield opens a Chrome window to read the deck.</p>
      ) : null)}
      {deck && <p className="text-xs text-ink-muted">Nothing is added yet — <span className="voice-semi">Add…</span> opens the cards to check printings first.</p>}
      {browser.awaiting != null && <AwaitingNote summary={browser.awaiting} />}
      {browser.error && <FailureNote error={browser.error} />}
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      {!deck && <JobLine live={live} />}
    </section>
  );
}

function LinkTile() {
  return (
    <span aria-hidden className="grid size-10 shrink-0 place-items-center rounded-xs border border-rule bg-paper-sunk text-ink-muted">
      <svg viewBox="0 0 20 20" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M8.5 11.5a3 3 0 0 0 4.2 0l2.6-2.6a3 3 0 0 0-4.2-4.2L10 5.8" />
        <path d="M11.5 8.5a3 3 0 0 0-4.2 0l-2.6 2.6a3 3 0 0 0 4.2 4.2l1.1-1.1" />
      </svg>
    </span>
  );
}

function Products({ q }: { q: string }) {
  const [dq, setDq] = useState(q);
  useEffect(() => {
    const t = window.setTimeout(() => setDq(q), 250);
    return () => window.clearTimeout(t);
  }, [q]);
  const res = useQuery(preconCatalogQuery(dq));
  const settled = !res.isPlaceholderData && !res.isFetching && dq === q;
  const [open, setOpen] = useState<string | null>(null);
  const n = res.data?.length ?? 0;
  return (
    <section aria-label="Products" className="flex flex-col gap-2">
      <ResultsHead>{q ? 'Products' : 'Products · newest first'}</ResultsHead>
      <p aria-live="polite" className="sr-only">{settled ? `${n} ${n === 1 ? 'product' : 'products'}` : 'Searching…'}</p>
      {!settled && <p className="text-xs text-ink-muted">Searching…</p>}
      {res.isError && <p role="alert" className="text-sm text-danger">Couldn’t load the product list: {(res.error as Error).message}</p>}
      <ul aria-label="Results" className="flex flex-col">
        {(res.data ?? []).map((p) => (
          <ProductRow key={p.file_name} p={p} open={open === p.file_name} onOpen={(o) => setOpen(o ? p.file_name : null)} />
        ))}
        {settled && n === 0 && !res.isError && <li className="py-3 text-sm text-ink-muted">No products match “{q}”.</li>}
      </ul>
    </section>
  );
}

const STATES = [
  { value: 'auto', label: 'Suggested' },
  { value: 'built', label: 'Keep it assembled' },
  { value: 'deconstructed', label: 'Just add the cards' },
] as const;

function ProductRow({ p, open, onOpen }: { p: PreconOptionOut; open: boolean; onOpen: (o: boolean) => void }) {
  const qc = useQueryClient();
  const [copies, setCopies] = useState(1);
  const [state, setState] = useState<(typeof STATES)[number]['value']>('auto');
  const [error, setError] = useState('');
  const { live, start } = useJob();
  const running = live != null && live.status !== 'succeeded' && live.status !== 'failed';

  useEffect(() => {
    if (live?.status === 'succeeded') qc.invalidateQueries({ queryKey: ['collection'] }).then(() => Promise.all([qc.invalidateQueries({ queryKey: ['ingest', 'precons'] }), qc.invalidateQueries({ queryKey: ['history'] }), qc.invalidateQueries({ queryKey: ['holdings'] })]));
  }, [live?.status, qc]);

  async function add() {
    setError('');
    const err = await start('ingest.precon', { file_name: p.file_name, copies, state });
    if (err) setError(err);
  }

  const owned = productOwned(p.owned_built, p.owned_deconstructed);
  return (
    <li className="ruled py-2">
      <div className="flex items-center gap-3">
        <Thumb uri={p.image_uri} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-md voice-semi font-medium text-ink">{p.name}</p>
          <p className="text-xs tabular text-ink-muted">
            {[p.type, p.set_code.toUpperCase(), p.release_date?.slice(0, 4)].filter(Boolean).join(' · ')}
            {owned && <span className="voice-semi whitespace-nowrap text-accent-ink"> · {owned}</span>}
          </p>
        </div>
        <Button tone="paper" onClick={() => onOpen(!open)} aria-expanded={open} className="shrink-0">{open ? 'Cancel' : 'Add…'}</Button>
      </div>
      {open && (
        <div className="mt-2 flex flex-col gap-2 rounded-sm bg-paper-sunk p-3 sm:ml-13">
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-xs voice-semi text-ink-muted">
              Copies
              <input type="number" min={1} max={50} value={copies} onChange={(e) => setCopies(Math.max(1, Math.min(50, Number(e.target.value) || 1)))} className="h-8 w-16 rounded-sm border border-rule bg-paper-raised px-1.5 text-right text-sm tabular text-ink focus-visible:border-accent" />
            </label>
            <label className="flex flex-col gap-1 text-xs voice-semi text-ink-muted">
              Keep it
              <select value={state} onChange={(e) => setState(e.target.value as typeof state)} className="h-8 cursor-pointer rounded-sm border border-rule bg-paper-raised px-2 text-sm text-ink focus-visible:border-accent">
                {STATES.map((s) => <option key={s.value} value={s.value}>{s.value === 'auto' ? `Suggested (${p.default_state === 'built' ? 'keep assembled' : 'just the cards'})` : s.label}</option>)}
              </select>
            </label>
            <Button tone="paper" emphasis="primary" onClick={add} disabled={running} className="ml-auto">{running ? 'Adding…' : `Add ${copies > 1 ? `${fmtInt(copies)} copies` : 'to collection'}`}</Button>
          </div>
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <JobLine live={live} />
        </div>
      )}
    </li>
  );
}

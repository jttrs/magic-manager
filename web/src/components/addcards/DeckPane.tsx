import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { preconCatalogQuery } from '../../app/queries';
import { useJob, type JobLive } from '../../app/useJob';
import type { PreconOptionOut, ResolveOut } from '../../core/api';
import { fmtInt } from '../../core/format';
import { Button } from '../Button';

/** Bring a whole deck: a deck-builder URL (reviewed before adding) or a precon (added directly). */
export function DeckPane({ onFetched }: { onFetched: (r: ResolveOut) => void }) {
  return (
    <div className="grid min-h-0 flex-1 gap-6 overflow-y-auto pr-3 [scrollbar-gutter:stable] lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
      <DeckUrl onFetched={onFetched} />
      <PreconCatalog />
    </div>
  );
}

function JobLine({ live }: { live: JobLive | null }) {
  if (!live) return null;
  const last = live.error ?? live.summary ?? live.log.at(-1)?.msg ?? 'Queued…';
  const failed = live.status === 'failed' || Boolean(live.error);
  return <p aria-live="polite" className={`text-sm ${failed ? 'text-danger' : live.status === 'succeeded' ? 'highlighter self-start px-1 text-ink' : 'text-ink-muted'}`}>{last}</p>;
}

function DeckUrl({ onFetched }: { onFetched: (r: ResolveOut) => void }) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const { live, start } = useJob();
  const running = live != null && live.status !== 'succeeded' && live.status !== 'failed';

  useEffect(() => {
    if (live?.status !== 'succeeded') return;
    const art = (live.artifacts as { label: string; data: ResolveOut }[] | undefined)?.find((a) => a.label === 'lines');
    if (art) onFetched(art.data);
  }, [live?.status, live?.artifacts, onFetched]);

  async function fetchDeck() {
    if (!/^https?:\/\/([\w-]+\.)*(archidekt\.com|moxfield\.com|mtggoldfish\.com|manabox\.app|scryfall\.com)\//i.test(url.trim())) {
      setError('Paste a deck link from Archidekt, Moxfield, MTGGoldfish, ManaBox or Scryfall.');
      return;
    }
    setError('');
    const err = await start('ingest.fetch_deck', { url: url.trim() });
    if (err) setError(err);
  }

  return (
    <section aria-labelledby="deck-url-h" className="flex flex-col gap-3">
      <h3 id="deck-url-h" className="border-b-2 border-rule-strong pb-1 text-lg voice-condensed font-bold uppercase text-ink">From a deck URL</h3>
      <label className="flex flex-col gap-1.5 text-sm voice-semi text-ink-muted">
        Archidekt, Moxfield, MTGGoldfish, ManaBox or Scryfall
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchDeck()}
          placeholder="https://archidekt.com/decks/…"
          className="h-10 rounded-sm border border-rule-strong bg-paper-raised px-3 text-md text-ink placeholder:text-ink-muted focus-visible:border-accent"
        />
      </label>
      <Button tone="paper" onClick={fetchDeck} disabled={running} className="self-start">{running ? 'Fetching…' : 'Fetch deck'}</Button>
      {url.includes('moxfield') && <p className="text-xs text-ink-muted">Moxfield opens a Chrome window to read the deck.</p>}
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      <JobLine live={live} />
    </section>
  );
}

function PreconCatalog() {
  const [q, setQ] = useState('');
  const [dq, setDq] = useState('');
  useEffect(() => {
    const t = window.setTimeout(() => setDq(q), 250);
    return () => window.clearTimeout(t);
  }, [q]);
  const res = useQuery(preconCatalogQuery(dq));
  const settled = !res.isPlaceholderData && !res.isFetching && dq === q;
  const [open, setOpen] = useState<string | null>(null);
  return (
    <section aria-labelledby="precon-h" className="flex min-h-0 flex-col gap-3">
      <h3 id="precon-h" className="border-b-2 border-rule-strong pb-1 text-lg voice-condensed font-bold uppercase text-ink">Preconstructed products</h3>
      <label className="flex flex-col gap-1.5 text-sm voice-semi text-ink-muted">
        Search by name, set code or type
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. Final Fantasy, fic, Commander Deck…"
          className="h-10 rounded-sm border border-rule-strong bg-paper-raised px-3 text-md text-ink placeholder:text-ink-muted focus-visible:border-accent"
        />
      </label>
      <p aria-live="polite" className="sr-only">{settled ? `${res.data?.length ?? 0} precons` : 'Searching…'}</p>
      {!settled && <p className="text-xs text-ink-muted">Searching…</p>}
      {res.isError && <p role="alert" className="text-sm text-danger">Couldn’t load the precon list: {(res.error as Error).message}</p>}
      <ul aria-label="Precons" className="flex flex-col">
        {(res.data ?? []).map((p) => (
          <PreconRow key={p.file_name} p={p} open={open === p.file_name} onOpen={(o) => setOpen(o ? p.file_name : null)} />
        ))}
        {settled && res.data?.length === 0 && <li className="py-3 text-sm text-ink-muted">No precons match “{q}”.</li>}
      </ul>
    </section>
  );
}

const STATES = [
  { value: 'auto', label: 'Suggested' },
  { value: 'built', label: 'Keep built' },
  { value: 'deconstructed', label: 'Break into loose cards' },
] as const;

function PreconRow({ p, open, onOpen }: { p: PreconOptionOut; open: boolean; onOpen: (o: boolean) => void }) {
  const qc = useQueryClient();
  const [copies, setCopies] = useState(1);
  const [state, setState] = useState<(typeof STATES)[number]['value']>('auto');
  const [error, setError] = useState('');
  const { live, start } = useJob();
  const running = live != null && live.status !== 'succeeded' && live.status !== 'failed';

  useEffect(() => {
    if (live?.status === 'succeeded') qc.invalidateQueries({ queryKey: ['collection'] }).then(() => qc.invalidateQueries({ queryKey: ['ingest', 'precons'] }));
  }, [live?.status, qc]);

  async function add() {
    setError('');
    const err = await start('ingest.precon', { file_name: p.file_name, copies, state });
    if (err) setError(err);
  }

  const owned = p.owned_built + p.owned_deconstructed;
  return (
    <li className="ruled py-2">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-md voice-semi font-medium text-ink">{p.name}</p>
          <p className="truncate text-xs tabular text-ink-muted">
            {[p.set_code.toUpperCase(), p.type, p.release_date?.slice(0, 4)].filter(Boolean).join(' · ')}
            {owned > 0 && <span className="text-accent-ink"> · own {fmtInt(p.owned_built)} built, {fmtInt(p.owned_deconstructed)} loose</span>}
          </p>
        </div>
        <Button tone="paper" onClick={() => onOpen(!open)} aria-expanded={open} className="shrink-0">{open ? 'Cancel' : 'Add…'}</Button>
      </div>
      {open && (
        <div className="mt-2 flex flex-col gap-2 rounded-sm bg-paper-sunk p-3">
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-xs voice-semi text-ink-muted">
              Copies
              <input type="number" min={1} max={50} value={copies} onChange={(e) => setCopies(Math.max(1, Math.min(50, Number(e.target.value) || 1)))} className="h-8 w-16 rounded-sm border border-rule bg-paper-raised px-1.5 text-right text-sm tabular text-ink focus-visible:border-accent" />
            </label>
            <label className="flex flex-col gap-1 text-xs voice-semi text-ink-muted">
              Keep it
              <select value={state} onChange={(e) => setState(e.target.value as typeof state)} className="h-8 cursor-pointer rounded-sm border border-rule bg-paper-raised px-2 text-sm text-ink focus-visible:border-accent">
                {STATES.map((s) => <option key={s.value} value={s.value}>{s.value === 'auto' ? `Suggested (${p.default_state === 'built' ? 'built' : 'loose'})` : s.label}</option>)}
              </select>
            </label>
            <Button tone="paper" emphasis="primary" onClick={add} disabled={running} className="ml-auto">{running ? 'Adding…' : `Add ${copies > 1 ? `${copies} copies` : 'to collection'}`}</Button>
          </div>
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <JobLine live={live} />
        </div>
      )}
    </li>
  );
}

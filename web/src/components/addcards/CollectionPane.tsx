import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useId, useMemo, useRef, useState } from 'react';
import { unwrap } from '../../app/queries';
import { useDownScrapers } from '../../app/scraperHealth';
import { useCompanion } from '../../app/useCompanion';
import { collectionImportApply, collectionImportPreview, type CollectionApplyOut, type CollectionPreviewOut, type CollectionReadIn } from '../../core/api';
import { belowPledged, changedRows, effectLine, effectOf, previewNotes, readTitle, shareLinkKind, type ImportMode, type ImportScope } from '../../core/collectionImport';
import { ALLOW_ACCESS_HINT, type MoxfieldBinder } from '../../core/companion';
import { fmtInt } from '../../core/format';
import { MOXFIELD_COLLECTION_KEY } from '../../core/scraperHealth';
import { Button } from '../Button';
import { Chevron } from '../Chevron';
import { AwaitingNote, FailureNote } from '../companion/CompanionNotes';
import { ScraperNotice } from '../ScraperNotice';

const H3 = 'border-b-2 border-rule-strong pb-1 text-lg voice-condensed font-bold uppercase text-ink';
/** A whole collection is read before the approval window opens. */
const READ_TIMEOUT_MS = 5 * 60_000;

const DOWN_KEYS = [MOXFIELD_COLLECTION_KEY] as const;

type Read = { body: CollectionReadIn; preview: CollectionPreviewOut };

/** Add cards → Collection: your Moxfield collection or one binder, read in your
 *  browser by the companion, reviewed as a diff, imported as ONE ingest event —
 *  adding to or setting your counts, chosen per import. */
export function CollectionPane() {
  const c = useCompanion();
  const qc = useQueryClient();
  const [scope, setScope] = useState<ImportScope>('collection');
  const [binders, setBinders] = useState<MoxfieldBinder[] | null>(null);
  const [binder, setBinder] = useState('');
  const [link, setLink] = useState('');
  const [awaiting, setAwaiting] = useState<string | null>(null);
  const [read, setRead] = useState<Read | null>(null);
  const [mode, setMode] = useState<ImportMode | null>(null);
  const [again, setAgain] = useState(false);
  const [done, setDone] = useState<CollectionApplyOut | null>(null);
  const down = useDownScrapers(DOWN_KEYS);
  const ready = c.status === 'ready';
  const moxOn = Boolean(c.hello?.features.moxfield);

  const listBinders = useMutation({
    mutationFn: async () => (await c.read('moxfield_binders', {}, setAwaiting)).binders,
    onSuccess: (b) => { setBinders(b); setBinder(b[0]?.id ?? ''); },
    onSettled: () => setAwaiting(null),
  });

  const readColl = useMutation({
    mutationFn: async (): Promise<Read> => {
      const params = scope === 'link' ? { url: link.trim() } : scope === 'binder' ? { what: 'binder' as const, binder } : { what: 'collection' as const };
      const d = await c.read('moxfield_collection', params, setAwaiting, { ackTimeoutMs: READ_TIMEOUT_MS });
      setAwaiting(null);
      const x = d.collection;
      const body: CollectionReadIn = { source: 'moxfield', scope: x.scope, id: x.id, name: x.name ?? binders?.find((b) => b.id === x.id)?.name ?? null, lines: x.lines };
      return { body, preview: unwrap(await collectionImportPreview({ body })) };
    },
    onSuccess: (r) => { setRead(r); setMode(null); setAgain(false); setDone(null); },
    onSettled: () => setAwaiting(null),
  });

  const apply = useMutation({
    mutationFn: async () => unwrap(await collectionImportApply({ body: { ...read!.body, mode: mode!, force: again } })),
    onSuccess: async (r) => {
      setDone(r);
      setRead(null);
      await qc.invalidateQueries({ queryKey: ['collection'] });
      await qc.invalidateQueries({ queryKey: ['history'] });
    },
  });

  const linkKind = shareLinkKind(link);
  const canRead = ready && moxOn && !readColl.isPending && !listBinders.isPending && (scope === 'collection' || (scope === 'binder' && Boolean(binder)) || (scope === 'link' && linkKind != null));

  if (read) {
    return <Review read={read} mode={mode} onMode={setMode} again={again} onAgain={setAgain} onBack={() => setRead(null)}
      onImport={() => apply.mutate()} busy={apply.isPending} error={apply.error} />;
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto pr-3 [scrollbar-gutter:stable]">
      {done && (
        <p role="status" className="flex flex-wrap items-baseline gap-3 rounded-sm bg-paper-sunk px-3 py-2 text-md">
          <span className="highlighter px-1 voice-semi font-medium">
            Imported: {fmtInt(done.added)} new {done.added === 1 ? 'printing' : 'printings'}, {fmtInt(done.updated)} changed
          </span>
          <span className="text-sm text-ink-muted">One entry in Purchase history · {done.label.replace(/^web:moxfield /, 'Moxfield ')}</span>
        </p>
      )}
      <ScraperNotice down={down} />
      <fieldset className="flex flex-col gap-1" disabled={readColl.isPending || listBinders.isPending}>
        <legend className={`${H3} w-full`}>1. Choose what to import from Moxfield</legend>
        <Choice name="mx-scope" checked={scope === 'collection'} onPick={() => setScope('collection')} title="Your whole collection"
          note="Every card in your Moxfield collection — you need to be signed in to Moxfield in this browser." />
        <Choice name="mx-scope" checked={scope === 'binder'} onPick={() => setScope('binder')} title="One of your binders"
          note="Only the cards in one binder. The binder’s name goes on the import’s history entry.">
          {scope === 'binder' && (
            <span className="mt-1.5 flex flex-wrap items-center gap-2">
              {binders?.length ? (
                <select aria-label="Binder" value={binder} onChange={(e) => setBinder(e.target.value)}
                  className="h-9 min-w-[14rem] cursor-pointer rounded-sm border border-rule-strong bg-paper-raised px-2 text-md text-ink focus-visible:border-accent">
                  {binders.map((b) => <option key={b.id} value={b.id}>{b.name ?? b.id}{b.cards != null ? ` · ${fmtInt(b.cards)} cards` : ''}</option>)}
                </select>
              ) : binders ? (
                <span className="text-sm text-ink-muted">You have no binders on Moxfield.</span>
              ) : null}
              <Button tone="paper" onClick={() => listBinders.mutate()} disabled={!ready || !moxOn || listBinders.isPending || readColl.isPending}>
                {listBinders.isPending ? (awaiting != null ? 'Waiting for approval…' : 'Listing…') : binders ? 'List again' : 'List my binders'}
              </Button>
            </span>
          )}
        </Choice>
        <Choice name="mx-scope" checked={scope === 'link'} onPick={() => setScope('link')} title="A shared link"
          note="A collection or binder someone shared (Public or Unlisted on Moxfield) — read without signing in.">
          {scope === 'link' && (
            <span className="mt-1.5 flex flex-col gap-1">
              <input type="url" aria-label="Moxfield collection or binder link" value={link} onChange={(e) => setLink(e.target.value)}
                placeholder="https://moxfield.com/binders/…"
                className="h-9 w-full max-w-[34rem] rounded-sm border border-rule-strong bg-paper-raised px-3 text-md text-ink placeholder:text-ink-muted focus-visible:border-accent" />
              {link.trim() && !linkKind && <span className="text-xs text-danger">Paste a moxfield.com/collection/… or moxfield.com/binders/… link.</span>}
            </span>
          )}
        </Choice>
      </fieldset>

      <section aria-labelledby="mx-read" className="flex flex-col gap-2">
        <h3 id="mx-read" className={H3}>2. Read it</h3>
        <p className="max-w-[62ch] text-md leading-relaxed text-ink-muted">
          {!ready
            ? c.status === 'checking' ? 'Looking for the browser companion…' : 'Set up the browser companion first — the plug icon at the top of the app.'
            : !moxOn
              ? ALLOW_ACCESS_HINT
              : 'The companion reads it in this browser — every page of it — and shows you exactly what it would send before anything leaves. Nothing changes in your collection until you review and import.'}
        </p>
        <Button tone="paper" emphasis="primary" className="self-start" disabled={!canRead} onClick={() => readColl.mutate()}>
          {readColl.isPending ? (awaiting != null ? 'Waiting for approval…' : 'Reading Moxfield…') : 'Read from Moxfield'}
        </Button>
        {awaiting != null && <AwaitingNote summary={awaiting} />}
        {(readColl.error ?? listBinders.error) && <FailureNote error={readColl.error ?? listBinders.error} />}
      </section>
    </div>
  );
}

function Choice({ name, checked, onPick, title, note, children }: { name: string; checked: boolean; onPick: () => void; title: string; note: string; children?: React.ReactNode }) {
  return (
    <label className="ruled flex cursor-pointer items-start gap-3 px-1 py-2">
      <input type="radio" name={name} checked={checked} onChange={onPick} className="mt-1 accent-accent" />
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="text-md voice-semi font-medium text-ink">{title}</span>
        <span className="max-w-[62ch] text-xs leading-snug text-ink-muted">{note}</span>
        {children}
      </span>
    </label>
  );
}

const MODES: { mode: ImportMode; title: string; note: string }[] = [
  { mode: 'add', title: 'Add to what you own', note: 'Moxfield’s count is added on top of yours — for new cards, like a binder of fresh pulls.' },
  { mode: 'replace', title: 'Set your counts to Moxfield’s', note: 'Each listed printing becomes Moxfield’s count, which can lower it. Cards not in this read stay as they are.' },
];

function Review({ read, mode, onMode, again, onAgain, onBack, onImport, busy, error }: {
  read: Read; mode: ImportMode | null; onMode: (m: ImportMode) => void; again: boolean; onAgain: (b: boolean) => void;
  onBack: () => void; onImport: () => void; busy: boolean; error: unknown;
}) {
  const { preview: p, body } = read;
  const effects = useMemo(() => ({ add: effectOf(p.rows, 'add'), replace: effectOf(p.rows, 'replace') }), [p.rows]);
  const rows = useMemo(() => (mode ? changedRows(p.rows, mode) : []), [p.rows, mode]);
  const notes = previewNotes(p);
  const dup = mode === 'add' && p.already_imported_at != null;
  const pledgedLow = belowPledged(p.rows);
  const blocked = mode === 'replace' && pledgedLow > 0;
  const effect = mode ? effects[mode] : null;
  const title = readTitle(body.scope, body.id ?? null, body.name ?? null);

  return (
    <section aria-label={title} className="flex min-h-0 flex-1 flex-col overflow-y-auto @container">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b-2 border-rule-strong pb-1">
        <h3 className="text-lg voice-condensed font-bold uppercase">{title}</h3>
        <span className="text-sm tabular text-ink-muted">{fmtInt(p.rows.length)} {p.rows.length === 1 ? 'printing' : 'printings'}</span>
        <button type="button" onClick={onBack}
          className="inline-flex cursor-pointer items-center gap-0.5 self-center rounded-sm px-1 text-sm voice-semi font-medium text-accent-ink underline decoration-1 underline-offset-2 hover:decoration-2">
          <Chevron dir="left" className="size-3.5" />
          Read something else
        </button>
      </div>

      <fieldset className="flex flex-col py-1" disabled={busy}>
        <legend className="sr-only">How to import</legend>
        {MODES.map((m) => (
          <label key={m.mode} className="ruled flex cursor-pointer items-start gap-3 px-1 py-2">
            <input type="radio" name="mx-mode" checked={mode === m.mode} onChange={() => onMode(m.mode)} className="mt-1 accent-accent" />
            <span className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="flex flex-wrap items-baseline justify-between gap-x-4">
                <span className="text-md voice-semi font-medium text-ink">{m.title}</span>
                <span className="text-sm tabular text-ink">{effectLine(effects[m.mode])}</span>
              </span>
              <span className="max-w-[62ch] text-xs leading-snug text-ink-muted">{m.note}</span>
            </span>
          </label>
        ))}
      </fieldset>

      {pledgedLow > 0 && (
        <p className={`border-b border-rule py-1.5 text-sm ${mode === 'replace' ? 'text-danger' : 'text-ink-muted'}`}>
          {fmtInt(pledgedLow)} {pledgedLow === 1 ? 'printing has' : 'printings have'} more copies in built decks than this read lists, so setting your counts would go below them. Break those decks down first, or add instead.
        </p>
      )}
      {notes.length > 0 && (
        <ul className="flex flex-col gap-0.5 border-b border-rule py-1.5 text-sm text-ink-muted">
          {notes.map((n) => <li key={n}>{n}</li>)}
        </ul>
      )}
      {p.not_found.length > 0 && (
        <details className="border-b border-rule py-1.5 text-sm text-ink-muted">
          <summary className="cursor-pointer">Lines that didn’t match a printing</summary>
          <ul className="mt-1 flex max-h-32 flex-col gap-0.5 overflow-y-auto text-xs">
            {p.not_found.map((n, i) => <li key={i}>{n.qty} {n.name ?? '—'} {n.set ? `(${n.set.toUpperCase()} ${n.collector_number ?? ''})` : ''} {n.finish}</li>)}
          </ul>
        </details>
      )}

      {mode ? (
        rows.length ? <ChangeTable rows={rows} /> : <p className="py-4 text-sm text-ink-muted">Your collection already matches this read — nothing would change.</p>
      ) : (
        <p className="py-4 text-sm text-ink-muted">Choose how to import to see every card that would change.</p>
      )}

      <footer className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-rule pt-3">
        {dup && (
          <label className="inline-flex cursor-pointer items-center gap-1.5 text-sm text-ink">
            <input type="checkbox" checked={again} onChange={(e) => onAgain(e.target.checked)} className="accent-[var(--theme-accent)]" />
            You imported this exact read on {p.already_imported_at!.slice(0, 10)} — add it again anyway
          </label>
        )}
        {error != null && <FailureNote error={error} />}
        <Button tone="paper" emphasis="primary" className="ml-auto" onClick={onImport}
          disabled={busy || !mode || !effect?.printings || (dup && !again) || blocked}>
          {busy ? 'Importing…' : effect?.printings ? `Import · ${effectLine(effect)}` : 'Import'}
        </Button>
      </footer>
    </section>
  );
}

const ROW_H = 36;

/** Every printing whose count changes — virtualized (a first import can be thousands of rows). */
function ChangeTable({ rows }: { rows: ReturnType<typeof changedRows> }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const id = useId();
  const v = useVirtualizer({ count: rows.length, getScrollElement: () => ref.current, estimateSize: () => ROW_H, overscan: 12 });
  const cols = 'grid grid-cols-[minmax(0,1fr)_2.5rem_2.5rem_3.25rem] @[40rem]:grid-cols-[minmax(0,1fr)_7rem_4.5rem_4.5rem_4.5rem_5.5rem] items-center gap-x-3 px-1';
  return (
    <div role="table" aria-labelledby={`${id}-cap`} aria-rowcount={rows.length + 1} className="flex min-h-[18rem] flex-1 flex-col">
      <span id={`${id}-cap`} className="sr-only">Cards that would change</span>
      <div role="row" className={`${cols} border-b border-rule-strong py-1 text-xs voice-semi uppercase text-ink-muted`}>
        <span role="columnheader">Card</span>
        <span role="columnheader" className="hidden @[40rem]:block">Set · #</span>
        <span role="columnheader" className="hidden @[40rem]:block">Finish</span>
        <span role="columnheader" className="text-right">Now</span>
        <span role="columnheader" className="text-right">After</span>
        <span role="columnheader" className="text-right">Change</span>
      </div>
      <div ref={ref} className="min-h-0 flex-1 overflow-y-auto pr-3 [scrollbar-gutter:stable]">
        <div role="rowgroup" style={{ height: v.getTotalSize(), position: 'relative' }}>
          {v.getVirtualItems().map((it) => {
            const r = rows[it.index];
            return (
              <div key={`${r.scryfall_id}-${r.finish}`} role="row" aria-rowindex={it.index + 2}
                className={`${cols} ruled absolute inset-x-0 text-sm`} style={{ height: ROW_H, transform: `translateY(${it.start}px)` }}>
                <span role="cell" className="truncate text-ink">
                  {r.name ?? r.scryfall_id}
                  <span className="text-ink-muted @[40rem]:hidden"> · {(r.set ?? '').toUpperCase()} {r.collector_number}{r.finish === 'foil' ? ' · foil' : ''}</span>
                </span>
                <span role="cell" className="hidden truncate tabular text-ink-muted @[40rem]:block">{(r.set ?? '').toUpperCase()} · {r.collector_number}</span>
                <span role="cell" className="hidden text-ink-muted @[40rem]:block">{r.finish}</span>
                <span role="cell" className="text-right tabular text-ink-muted">{fmtInt(r.current)}</span>
                <span role="cell" className="text-right tabular text-ink">{fmtInt(r.after)}</span>
                <span role="cell" className={`text-right tabular voice-semi font-medium ${r.delta > 0 ? 'text-accent-ink' : 'text-danger'}`}>
                  {r.delta > 0 ? `+${fmtInt(r.delta)}` : `−${fmtInt(-r.delta)}`}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

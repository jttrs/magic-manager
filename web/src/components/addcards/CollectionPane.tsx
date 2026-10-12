import { useIsMutating, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useId, useMemo, useRef, useState, type DragEvent, type ReactNode } from 'react';
import { unwrap } from '../../app/queries';
import { useDownScrapers } from '../../app/scraperHealth';
import { useCompanion } from '../../app/useCompanion';
import {
  collectionImportApply, collectionImportFileApply, collectionImportFilePreview, collectionImportFormats, collectionImportPreview,
  type CollectionApplyOut, type CollectionPreviewOut, type CollectionReadIn,
} from '../../core/api';
import {
  MAX_FILE_BYTES, belowPledged, changedRows, effectLine, effectOf, fileTitle, previewNotes, readTitle, shareLinkKind,
  type ImportMode,
} from '../../core/collectionImport';
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
/** Every source's read shares this key, so only one read runs at a time across sources. */
const READ_KEY = ['collection-import-read'] as const;

const useReading = () => useIsMutating({ mutationKey: READ_KEY }) > 0;

/** One read, whatever its source: what it is, what it would change, and how to import it. */
type Read = { title: string; preview: CollectionPreviewOut; apply: (mode: ImportMode, force: boolean) => Promise<CollectionApplyOut> };

/** Add cards → Import a collection: cards you keep in another app — another
 *  app's exported file, or (with the browser companion) your Moxfield
 *  collection, a binder or a shared link read live. Every source is one
 *  button that reads; every read lands in the same diff review and imports as
 *  ONE ingest event, adding to or setting your counts, chosen per import. */
export function CollectionPane({ companion }: { companion: boolean }) {
  const qc = useQueryClient();
  const [read, setRead] = useState<Read | null>(null);
  const [mode, setMode] = useState<ImportMode | null>(null);
  const [again, setAgain] = useState(false);
  const [done, setDone] = useState<{ out: CollectionApplyOut; title: string } | null>(null);

  const onRead = (r: Read) => { setRead(r); setMode(null); setAgain(false); setDone(null); };

  const apply = useMutation({
    mutationFn: async () => ({ out: await read!.apply(mode!, again), title: read!.title }),
    onSuccess: async (r) => {
      setDone(r);
      setRead(null);
      await qc.invalidateQueries({ queryKey: ['collection'] });
      await qc.invalidateQueries({ queryKey: ['holdings'] });
      await qc.invalidateQueries({ queryKey: ['history'] });
    },
  });

  // The sources stay mounted (hidden) during review, so a listed binder or a pasted link survives *Read something else*.
  return (
    <>
    {read && (
      <Review read={read} mode={mode} onMode={setMode} again={again} onAgain={setAgain} onBack={() => { setRead(null); apply.reset(); }}
        onImport={() => apply.mutate()} busy={apply.isPending} error={apply.error} />
    )}
    <div hidden={read != null} className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto pr-3 [scrollbar-gutter:stable]">
      {done && (
        <p role="status" className="flex flex-wrap items-baseline gap-3 rounded-sm bg-paper-sunk px-3 py-2 text-md">
          <span className="highlighter px-1 voice-semi font-medium">
            Imported: {fmtInt(done.out.added)} new {done.out.added === 1 ? 'printing' : 'printings'}, {fmtInt(done.out.updated)} changed
          </span>
          <span className="text-sm text-ink-muted">One entry in Purchase history · {done.title}</span>
        </p>
      )}
      <p className="max-w-[62ch] text-md leading-relaxed text-ink-muted">
        Bring in the cards you track in another app. You’ll see every card that would change before anything is saved.
      </p>
      <FileSource onRead={onRead} />
      {companion && <MoxfieldSource onRead={onRead} />}
    </div>
    </>
  );
}

/** An exported collection file: drop it or choose it — choosing reads it. The app is detected from the header. */
function FileSource({ onRead }: { onRead: (r: Read) => void }) {
  const formats = useQuery({ queryKey: ['collection-import-formats'], queryFn: async () => unwrap(await collectionImportFormats()), staleTime: Infinity });
  const input = useRef<HTMLInputElement | null>(null);
  const [drag, setDrag] = useState(false);
  const hintId = useId();
  const reading = useReading();
  const readFile = useMutation({
    mutationKey: READ_KEY,
    mutationFn: async (f: File): Promise<Read> => {
      if (f.size > MAX_FILE_BYTES) throw new Error(`${f.name} is too big to import here (over 25 MB). Export a smaller part of your collection.`);
      const body = { filename: f.name, text: await f.text() };
      const p = unwrap(await collectionImportFilePreview({ body }));
      return {
        title: fileTitle(p.format_name, f.name), preview: p,
        apply: async (mode, force) => unwrap(await collectionImportFileApply({ body: { ...body, format: p.format, mode, force } })),
      };
    },
    onSuccess: onRead,
  });
  const pick = (f: File | undefined) => { if (f && !reading) readFile.mutate(f); };
  const onDrop = (e: DragEvent) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); };
  const names = formats.data?.map((f) => f.name) ?? [];

  return (
    <section aria-labelledby="ci-file" className="flex flex-col gap-2">
      <h3 id="ci-file" className={H3}>From an exported file</h3>
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        className={`flex flex-wrap items-center gap-x-4 gap-y-2 rounded-sm border border-dashed px-4 py-4 transition-colors ease-guide ${drag ? 'border-accent bg-paper-sunk' : 'border-rule-strong'}`}
      >
        <input ref={input} type="file" accept=".csv,.txt,text/csv,text/plain" className="sr-only" tabIndex={-1} aria-hidden
          onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ''; }} />
        <Button tone="paper" emphasis="primary" aria-describedby={hintId} disabled={reading} onClick={() => input.current?.click()}>
          {readFile.isPending ? `Reading ${readFile.variables?.name ?? 'file'}…` : 'Choose a file to read'}
        </Button>
        <p id={hintId} className="min-w-0 flex-1 basis-[22rem] text-md leading-relaxed text-ink">
          or drop it here. A CSV exported from {names.length ? listWords(names) : 'your collection app'} — we tell which app wrote it.
        </p>
      </div>
      {formats.data?.some((f) => f.how) && (
        <details className="text-sm text-ink-muted">
          <summary className="cursor-pointer py-1 voice-semi text-ink">Where each app keeps its export</summary>
          <dl className="mt-1 flex max-w-[62ch] flex-col @container">
            {formats.data.filter((f) => f.how).map((f) => (
              <div key={f.id} className="ruled grid gap-x-4 py-1.5 @[24rem]:grid-cols-[8rem_minmax(0,1fr)]">
                <dt className="voice-semi font-medium text-ink">{f.name}</dt>
                <dd className="leading-snug">{f.how}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
      {readFile.error && <FailureNote error={readFile.error} />}
    </section>
  );
}

const listWords = (xs: string[]) => (xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} or ${xs[xs.length - 1]}`);

type MxRead = { what: 'collection' } | { what: 'binder'; binder: MoxfieldBinder } | { url: string };

/** Moxfield read live in this browser by the companion: each row is one button that reads. */
function MoxfieldSource({ onRead }: { onRead: (r: Read) => void }) {
  const c = useCompanion();
  const [awaiting, setAwaiting] = useState<string | null>(null);
  const [binders, setBinders] = useState<MoxfieldBinder[] | null>(null);
  const [link, setLink] = useState('');
  const down = useDownScrapers(DOWN_KEYS);
  const ready = c.status === 'ready';
  const moxOn = Boolean(c.hello?.features.moxfield);
  const linkErr = useId();

  const reading = useReading();
  const listBinders = useMutation({
    mutationKey: READ_KEY,
    mutationFn: async () => (await c.read('moxfield_binders', {}, setAwaiting)).binders,
    onSuccess: setBinders,
    onSettled: () => setAwaiting(null),
  });

  const readMx = useMutation({
    mutationKey: READ_KEY,
    mutationFn: async (what: MxRead): Promise<Read> => {
      const params = 'url' in what ? { url: what.url } : what.what === 'binder' ? { what: 'binder' as const, binder: what.binder.id } : { what: 'collection' as const };
      const d = await c.read('moxfield_collection', params, setAwaiting, { ackTimeoutMs: READ_TIMEOUT_MS });
      setAwaiting(null);
      const x = d.collection;
      const name = x.name ?? ('binder' in what ? what.binder.name : null) ?? null;
      const body: CollectionReadIn = { source: 'moxfield', scope: x.scope, id: x.id, name, lines: x.lines };
      return {
        title: readTitle(body.scope, body.id ?? null, name), preview: unwrap(await collectionImportPreview({ body })),
        apply: async (mode, force) => unwrap(await collectionImportApply({ body: { ...body, mode, force } })),
      };
    },
    onSuccess: onRead,
    onSettled: () => setAwaiting(null),
  });

  const off = !ready || !moxOn || reading;
  const linkKind = shareLinkKind(link);
  const v = readMx.variables;
  const readingThis = (k: 'collection' | 'binder' | 'url', id?: string) =>
    readMx.isPending && v != null && ('url' in v ? k === 'url' : v.what === k && (k !== 'binder' || (v.what === 'binder' && v.binder.id === id)));
  const label = (k: Parameters<typeof readingThis>[0], idle: string, id?: string) => (readingThis(k, id) ? (awaiting != null ? 'Waiting for approval…' : 'Reading…') : idle);

  return (
    <section aria-labelledby="ci-mox" className="flex flex-col gap-1">
      <h3 id="ci-mox" className={`${H3} flex flex-wrap items-baseline gap-x-3`}>
        Live from Moxfield
        <span className="text-sm normal-case voice-semi font-normal text-ink-muted">read in this browser by the companion</span>
      </h3>
      {(!ready || !moxOn) && (
        <p className="max-w-[62ch] py-1 text-md leading-relaxed text-ink">
          {!ready
            ? c.status === 'checking' ? 'Looking for the browser companion…' : 'Set up the browser companion first — the plug icon at the top of the app.'
            : ALLOW_ACCESS_HINT}
        </p>
      )}
      <ScraperNotice down={down} />
      <ul className="flex flex-col">
        <SourceRow title="Your whole collection" note="Every card in your Moxfield collection. Sign in to Moxfield in this browser first."
          action={<Button tone="paper" disabled={off} onClick={() => readMx.mutate({ what: 'collection' })}>{label('collection', 'Read my collection')}</Button>} />
        <SourceRow title="One of your binders" note="Only that binder’s cards. Its name goes on the import’s history entry."
          action={(
            <Button tone="paper" disabled={off} onClick={() => listBinders.mutate()}>
              {listBinders.isPending ? (awaiting != null ? 'Waiting for approval…' : 'Listing…') : binders ? 'List again' : 'Choose a binder…'}
            </Button>
          )}>
          {binders && (binders.length ? (
            <ul aria-label="Your Moxfield binders" className="mt-2 flex flex-wrap gap-2">
              {binders.map((b) => (
                <li key={b.id}>
                  <Button tone="paper" disabled={off} aria-label={`Read binder ${b.name ?? b.id}`} onClick={() => readMx.mutate({ what: 'binder', binder: b })}>
                    {label('binder', b.name ?? b.id, b.id)}
                    {b.cards != null && !readingThis('binder', b.id) && <span className="tabular text-ink-muted">{fmtInt(b.cards)}</span>}
                  </Button>
                </li>
              ))}
            </ul>
          ) : <p className="mt-1 text-sm text-ink-muted">You have no binders on Moxfield.</p>)}
        </SourceRow>
        <SourceRow title="A shared link" note="A collection or binder someone shared (Public or Unlisted on Moxfield) — read without signing in.">
          <form className="mt-1 flex w-full flex-wrap items-start gap-2" onSubmit={(e) => { e.preventDefault(); if (linkKind && !off) readMx.mutate({ url: link.trim() }); }}>
            <span className="flex min-w-0 flex-1 basis-[18rem] flex-col gap-1">
              <input type="url" aria-label="Moxfield collection or binder link" value={link} onChange={(e) => setLink(e.target.value)}
                placeholder="https://moxfield.com/binders/…" aria-invalid={Boolean(link.trim() && !linkKind)} aria-describedby={link.trim() && !linkKind ? linkErr : undefined}
                className="h-9 w-full rounded-sm border border-rule-strong bg-paper-raised px-3 text-md text-ink placeholder:text-ink-muted focus-visible:border-accent aria-invalid:border-danger" />
              {link.trim() && !linkKind && <span id={linkErr} className="text-xs text-danger">Paste a moxfield.com/collection/… or moxfield.com/binders/… link.</span>}
            </span>
            <Button type="submit" tone="paper" disabled={off || !linkKind}>{label('url', 'Read link')}</Button>
          </form>
        </SourceRow>
      </ul>
      {awaiting != null && <AwaitingNote summary={awaiting} />}
      {(readMx.error ?? listBinders.error) && <FailureNote error={readMx.error ?? listBinders.error} />}
    </section>
  );
}

/** A ruled source row: what it reads on the left, its one action on the right (or below, in `children`). */
function SourceRow({ title, note, action, children }: { title: string; note: string; action?: ReactNode; children?: ReactNode }) {
  return (
    <li className="ruled flex flex-wrap items-center gap-x-4 gap-y-1 px-1 py-2.5">
      <span className="flex min-w-0 flex-1 basis-[20rem] flex-col gap-0.5">
        <span className="text-md voice-semi font-medium text-ink">{title}</span>
        <span className="max-w-[62ch] text-sm leading-snug text-ink-muted">{note}</span>
      </span>
      {action}
      {children && <div className="w-full">{children}</div>}
    </li>
  );
}

const MODES: { mode: ImportMode; title: string; note: string }[] = [
  { mode: 'add', title: 'Add to what you own', note: 'Each card’s count here is added on top of yours — for cards that are new to you, like a binder of fresh pulls.' },
  { mode: 'replace', title: 'Set your counts to match', note: 'Each listed printing gets the count from this read, which can lower it. Cards not in it stay as they are.' },
];

function Review({ read, mode, onMode, again, onAgain, onBack, onImport, busy, error }: {
  read: Read; mode: ImportMode | null; onMode: (m: ImportMode) => void; again: boolean; onAgain: (b: boolean) => void;
  onBack: () => void; onImport: () => void; busy: boolean; error: unknown;
}) {
  const { preview: p, title } = read;
  const effects = useMemo(() => ({ add: effectOf(p.rows, 'add'), replace: effectOf(p.rows, 'replace') }), [p.rows]);
  const rows = useMemo(() => (mode ? changedRows(p.rows, mode) : []), [p.rows, mode]);
  const notes = previewNotes(p);
  const dup = mode === 'add' && p.already_imported_at != null;
  const pledgedLow = belowPledged(p.rows);
  const blocked = mode === 'replace' && pledgedLow > 0;
  const effect = mode ? effects[mode] : null;

  return (
    <section aria-label={title} className="flex min-h-0 flex-1 flex-col overflow-y-auto @container">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b-2 border-rule-strong pb-1">
        <h3 className="text-lg voice-condensed font-bold uppercase">{title}</h3>
        <span className="text-sm tabular text-ink-muted">{fmtInt(p.rows.length)} {p.rows.length === 1 ? 'printing' : 'printings'}</span>
        <button type="button" onClick={onBack} disabled={busy}
          className="inline-flex cursor-pointer disabled:cursor-default disabled:opacity-50 items-center gap-0.5 self-center rounded-sm px-1 text-sm voice-semi font-medium text-accent-ink underline decoration-1 underline-offset-2 hover:decoration-2">
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
            <input type="checkbox" checked={again} onChange={(e) => onAgain(e.target.checked)} className="accent-accent" />
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

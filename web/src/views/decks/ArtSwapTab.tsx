import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useId, useMemo, useState, type ReactNode } from 'react';
import { artSwapsQuery, artTagsQuery, unwrap } from '../../app/queries';
import { useDebounced } from '../../app/useDebounced';
import { useJob } from '../../app/useJob';
import { Button } from '../../components/Button';
import { Chevron } from '../../components/Chevron';
import { ProgressRule } from '../../components/ProgressRule';
import { EmptyNote } from '../../components/States';
import { artLookup, type ArtTagRefOut, type PrintingOut } from '../../core/api';
import { artView, choiceFor, choiceNote, draftPrintingIds, swapAllFree, wasPrinting, type ArtRow } from '../../core/artSwap';
import { restorePrinting, swapPrinting, type Draft } from '../../core/deckDraft';
import { fmtCount, fmtInt } from '../../core/format';

const crop = (url: string) => url.replace('/normal/', '/art_crop/');
const QUICK = ['cat', 'moon', 'ocean', 'dragon', 'forest'];

type Edit = (fn: (d: Draft) => Draft) => void;
type Inspect = (p: PrintingOut) => void;

/** Find cards → Art: pick a Scryfall Tagger art tag and put each card in the
 *  draft on an on-theme printing — yours with free copies first, else the
 *  cheapest. Swaps only change the draft; Save writes them as usual. */
export function ArtSwapTab({ draft, onEdit, onInspect, tag, onTag }: { draft: Draft; onEdit: Edit; onInspect: Inspect; tag: ArtTagRefOut | null; onTag: (t: ArtTagRefOut | null) => void }) {
  const sids = useDebounced(draftPrintingIds(draft), 400);
  const q = useQuery(artSwapsQuery(tag?.id ?? null, sids));
  const tagsQ = useQuery(artTagsQuery(''));
  // A quick pick names the tag by slug; the answer carries its id.
  const fresh = q.data && tag && (q.data.tag.id === tag.id || q.data.tag.label === tag.label) ? q.data : undefined;
  const view = useMemo(() => artView(draft, fresh), [draft, fresh]);
  // Swap the quick pick's slug for the server's tag so the answer keeps matching.
  const answered = q.data?.tag;
  useEffect(() => {
    if (answered && fresh && tag && (answered.id !== tag.id || answered.label !== tag.label)) onTag({ id: answered.id, label: answered.label });
  }, [answered, fresh, tag, onTag]);

  if (tagsQ.data && !tagsQ.data.synced) return <SyncTags />;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <TagPicker tag={tag} onTag={onTag} />
      {!tag ? (
        <p className="mx-4 mt-4 max-w-[52ch] text-sm text-ink-muted">
          Pick an art theme and each card in the deck that has a printing with that art shows up here, on the copy you have free, else the cheapest.
        </p>
      ) : q.isError ? (
        <p role="alert" className="mx-4 mt-4 text-sm text-danger">{(q.error as Error).message}</p>
      ) : !fresh ? (
        <p role="status" className="mx-4 mt-4 text-sm text-ink-muted">Looking for {tag.label} art…</p>
      ) : (
        <Results tag={tag} sids={sids} view={view} onEdit={onEdit} onInspect={onInspect} />
      )}
    </div>
  );
}

function TagPicker({ tag, onTag }: { tag: ArtTagRefOut | null; onTag: (t: ArtTagRefOut | null) => void }) {
  const id = useId();
  const [text, setText] = useState(tag?.label ?? '');
  const needle = useDebounced(text.trim(), 200);
  const editing = needle.length > 0 && needle !== tag?.label;
  const res = useQuery({ ...artTagsQuery(needle), enabled: editing });
  const choose = (t: ArtTagRefOut) => {
    setText(t.label);
    onTag({ id: t.id, label: t.label });
  };
  const hits = editing ? res.data?.tags ?? [] : [];
  return (
    <div className="mx-4 mt-3 flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm voice-semi text-ink-muted">Art theme</label>
      <input
        id={id}
        type="search"
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          if (!e.target.value.trim()) onTag(null);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && hits[0]) choose(hits[0]);
        }}
        placeholder="cat, moon, ocean…"
        autoComplete="off"
        spellCheck={false}
        aria-describedby={`${id}-hint`}
        className="h-10 rounded-sm border border-rule-strong bg-paper-raised px-3 text-md text-ink placeholder:text-ink-muted focus-visible:border-accent"
      />
      <div id={`${id}-hint`} className={`flex flex-wrap items-center gap-1.5 ${editing || !tag ? 'min-h-8' : ''}`} aria-live="polite">
        {editing ? (
          res.isFetching && !res.data ? <span className="text-xs text-ink-muted">Looking…</span>
            : hits.length === 0 ? <span className="text-xs text-ink-muted">No art tag matches “{needle}”.</span>
              : hits.map((t) => (
                <Chip key={t.id} onClick={() => choose(t)} title={`${fmtInt(t.illustrations)} artworks tagged ${t.label}`}>
                  {t.label} <span className="tabular opacity-70">{fmtInt(t.illustrations)}</span>
                </Chip>
              ))
        ) : !tag ? (
          <>
            <span className="text-xs text-ink-muted">Try</span>
            {QUICK.map((s) => <Chip key={s} onClick={() => choose({ id: s, label: s })}>{s}</Chip>)}
          </>
        ) : null}
      </div>
    </div>
  );
}

function Chip({ children, onClick, title }: { children: ReactNode; onClick: () => void; title?: string }) {
  return (
    <button type="button" onClick={onClick} title={title} className="inline-flex min-h-7 cursor-pointer items-center gap-1 rounded-pill border border-rule px-2.5 text-sm text-ink hover:border-rule-strong hover:bg-paper-sunk focus-visible:border-accent">
      {children}
    </button>
  );
}

function Results({ tag, sids, view, onEdit, onInspect }: { tag: ArtTagRefOut; sids: string[]; view: ReturnType<typeof artView>; onEdit: Edit; onInspect: Inspect }) {
  const total = view.swap.length + view.onTheme.length + view.none.length;
  return (
    <>
      <div className="mx-4 mt-1 flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-rule pb-2">
        <p className="min-w-0 flex-1 text-sm text-ink-muted" aria-live="polite">
          <b className="voice-semi font-medium text-ink">{fmtInt(view.onTheme.length)}</b> of {fmtCount(total, 'card')} on theme
          {view.swap.length > 0 && <> · <b className="voice-semi font-medium text-ink">{fmtInt(view.swap.length)}</b> can swap</>}
        </p>
        <Button tone="paper" disabled={view.freeSwaps === 0} onClick={() => onEdit((d) => swapAllFree(d, view))} title="Swap every card whose on-theme printing you have free">
          Swap all free · {fmtInt(view.freeSwaps)}
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-8 [scrollbar-gutter:stable]">
        {total > 0 && view.swap.length === 0 && view.onTheme.length === 0 && (
          <p className="mt-4 text-sm text-ink-muted">No card in this deck has a {tag.label} printing in your catalog yet.</p>
        )}
        <Group title="Can swap" count={view.swap.length}>
          {view.swap.map((r) => <ArtLine key={r.row.key} r={r} onEdit={onEdit} onInspect={onInspect} />)}
        </Group>
        <Group title="On theme" count={view.onTheme.length}>
          {view.onTheme.map((r) => <ArtLine key={r.row.key} r={r} onEdit={onEdit} onInspect={onInspect} />)}
        </Group>
        <Lookup key={tag.id} tag={tag} sids={sids} without={view.none.length} />
      </div>
    </>
  );
}

function Group({ title, count, children }: { title: string; count: number; children: ReactNode }) {
  const id = useId();
  if (!count) return null;
  return (
    <section aria-labelledby={id}>
      <h3 id={id} className="sticky top-0 z-10 flex items-baseline gap-2 border-b border-rule bg-paper pb-1 pt-3 text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">
        {title}<span className="ml-auto tabular">{count}</span>
      </h3>
      <ul>{children}</ul>
    </section>
  );
}

function Thumb({ p, size }: { p: PrintingOut; size: 'sm' | 'md' }) {
  const box = size === 'md' ? 'h-11 w-16' : 'h-8 w-11 opacity-70';
  return p.image_uri
    ? <img src={crop(p.image_uri)} alt="" loading="lazy" decoding="async" className={`${box} shrink-0 rounded-xs object-cover`} />
    : <span aria-hidden="true" className={`${box} shrink-0 rounded-xs border border-rule bg-paper-sunk`} />;
}

const where = (p: PrintingOut) => `${p.set_code.toUpperCase()} #${p.collector_number}`;

function ArtLine({ r, onEdit, onInspect }: { r: ArtRow; onEdit: Edit; onInspect: Inspect }) {
  const [open, setOpen] = useState(false);
  const cur = r.row.printing;
  const target = r.status === 'swap' ? r.pick : cur;
  const others = r.candidates.filter((c) => c.scryfall_id !== target?.scryfall_id);
  const listId = useId();
  if (!target) return null;
  const swapTo = (p: PrintingOut) => onEdit((d) => swapPrinting(d, r.row.key, p, choiceFor(r, p).finish));
  const note = (p: PrintingOut) => {
    const c = choiceFor(r, p);
    return { text: choiceNote(p, c.covered ? c.free : 0), free: c.covered };
  };
  const was = wasPrinting(r.row);
  return (
    <li className="ruled py-1.5">
      <div className="flex items-center gap-2">
        {r.status === 'swap' && (
          <>
            <Thumb p={cur} size="sm" />
            <Chevron dir="right" className="size-3.5 shrink-0 text-ink-muted" />
          </>
        )}
        <button type="button" onClick={() => onInspect(target)} className="shrink-0 cursor-pointer rounded-xs" aria-label={`Inspect ${target.name}, ${where(target)}`}>
          <Thumb p={target} size="md" />
        </button>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-md voice-semi font-medium text-ink">{cur.name}{r.row.count > 1 && <span className="tabular text-ink-muted"> ×{r.row.count}</span>}</span>
          <span className="truncate text-xs tabular text-ink-muted">
            {where(target)} · <span className={note(target).free ? 'text-accent-ink' : ''}>{note(target).text}</span>
            {r.status === 'swapped' && was && <> · <span className="voice-semi text-accent-ink">was {where(was)}</span></>}
          </span>
          {others.length > 0 && (
            <button type="button" aria-expanded={open} aria-controls={listId} onClick={() => setOpen((o) => !o)} className="-ml-1 inline-flex cursor-pointer items-center gap-0.5 self-start rounded-xs px-1 text-xs voice-semi text-ink-muted hover:bg-paper-sunk hover:text-ink">
              {others.length} other {others.length === 1 ? 'printing' : 'printings'} <Chevron dir={open ? 'up' : 'down'} className="size-3" />
            </button>
          )}
        </span>
        {r.status === 'swap' && (
          <button type="button" onClick={() => swapTo(target)} aria-label={`Swap ${cur.name} to ${where(target)}`} className="shrink-0 cursor-pointer rounded-sm px-2 py-1 text-sm voice-semi text-accent-ink hover:bg-paper-sunk">Swap</button>
        )}
        {r.status === 'swapped' && (
          <button type="button" onClick={() => onEdit((d) => restorePrinting(d, r.row.key))} aria-label={`Undo swap of ${cur.name}`} className="shrink-0 cursor-pointer rounded-sm px-2 py-1 text-sm voice-semi text-ink-muted hover:bg-paper-sunk hover:text-ink">Undo</button>
        )}
      </div>
      {open && (
        <ul id={listId} aria-label={`Other ${cur.name} printings with this art`} className="mt-1.5 flex gap-2 overflow-x-auto pb-1 pl-[calc(2.75rem+1.375rem)]">
          {others.map((p) => (
            <li key={p.scryfall_id} className="shrink-0">
              <button type="button" onClick={() => { swapTo(p); setOpen(false); }} aria-label={`Use ${where(p)}, ${note(p).text}`} className="flex w-24 cursor-pointer flex-col gap-0.5 rounded-sm p-1 text-left hover:bg-paper-sunk focus-visible:bg-paper-sunk">
                {p.image_uri ? <img src={crop(p.image_uri)} alt="" loading="lazy" decoding="async" className="h-16 w-full rounded-xs object-cover" /> : <span aria-hidden="true" className="h-16 w-full rounded-xs border border-rule bg-paper-sunk" />}
                <span className="truncate text-xs tabular text-ink">{where(p)}</span>
                <span className={`truncate text-xs tabular ${note(p).free ? 'text-accent-ink' : 'text-ink-muted'}`}>{note(p).text}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

/** Cards without a local on-theme printing, and the way to ask Scryfall for more. */
function Lookup({ tag, sids, without }: { tag: ArtTagRefOut; sids: string[]; without: number }) {
  const qc = useQueryClient();
  const [state, setState] = useState<{ busy: boolean; msg: string | null; error: boolean }>({ busy: false, msg: null, error: false });
  const run = async () => {
    setState({ busy: true, msg: null, error: false });
    try {
      const r = unwrap(await artLookup({ body: { tag: tag.id, cards: sids.map((scryfall_id) => ({ scryfall_id, board: 'main', finish: 'either', count: 1 })) } }));
      await qc.invalidateQueries({ queryKey: ['art', 'swaps'] });
      setState({ busy: false, error: false, msg: r.added ? `Found ${fmtCount(r.added, 'more printing')}.` : 'Scryfall has nothing new for these cards.' });
    } catch (e) {
      setState({ busy: false, error: true, msg: `Couldn’t reach Scryfall: ${(e as Error).message}` });
    }
  };
  return (
    <div className="mt-4 flex flex-col gap-2 border-t border-rule pt-3 text-sm text-ink-muted">
      {without > 0 && <p>{fmtCount(without, 'card')} {without === 1 ? 'has' : 'have'} no {tag.label} printing in your catalog.</p>}
      <div className="flex flex-wrap items-center gap-3">
        <Button tone="paper" disabled={state.busy} onClick={run}>{state.busy ? 'Asking Scryfall…' : 'Look on Scryfall for more'}</Button>
        {state.msg && <span role={state.error ? 'alert' : 'status'} className={state.error ? 'text-danger' : ''}>{state.msg}</span>}
      </div>
    </div>
  );
}

/** Art tags aren't loaded yet: one click runs the tag sync job. */
function SyncTags() {
  const qc = useQueryClient();
  const { live, start } = useJob();
  const [err, setErr] = useState<string | null>(null);
  const running = Boolean(live && live.status !== 'succeeded' && live.status !== 'failed');
  useEffect(() => {
    if (live?.status === 'succeeded') void qc.invalidateQueries({ queryKey: ['art'] });
  }, [live?.status, qc]);
  return (
    <EmptyNote title="Art themes aren’t loaded yet">
      <span className="flex flex-col items-start gap-3">
        <span>Art themes come from Scryfall’s tags. Load them once (a few minutes) to find on-theme printings.</span>
        <Button tone="paper" emphasis="primary" disabled={running} onClick={async () => setErr(await start('scryfall.sync_tags', { refresh: false }))}>
          {running ? 'Loading art themes…' : 'Load art themes'}
        </Button>
        {live && running && <ProgressRule label="Loading Scryfall tags" done={live.done} total={live.total} message={live.log.at(-1)?.msg} verb="Loading" />}
        {(err || live?.error) && <span role="alert" className="text-danger">{err ?? live?.error}</span>}
      </span>
    </EmptyNote>
  );
}

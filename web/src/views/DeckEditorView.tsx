import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getRouteApi, Link, useBlocker, useNavigate } from '@tanstack/react-router';
import { DropdownMenu, Popover, Tabs } from 'radix-ui';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Group, Panel, Separator, useDefaultLayout } from 'react-resizable-panels';
import { deckCheckQuery, deckQuery, printingSearchQuery, suggestionsQuery, unwrap } from '../app/queries';
import { useMediaQuery } from '../app/useMediaQuery';
import { Button } from '../components/Button';
import { CardInspector } from '../components/CardInspector';
import { Chevron } from '../components/Chevron';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { EmptyNote, ErrorNote, GridSkeleton } from '../components/States';
import { deckPreview, deckSave, type CheckOut, type DeckDetailOut, type PreviewOut, type PrintingOut, type SuggestionOut, type SwapLineOut } from '../core/api';
import {
  addCard, canCommand, collectionFirst, commanderName, draftCards, draftFromDeck, draftOracles, draftSections, draftStats,
  moveCard, setCount, setFinish, type Board, type Draft, type DraftFinish, type DraftRow,
} from '../core/deckDraft';
import { fmtInt, fmtUsd } from '../core/format';
import { fromPrinting, type GuideCard } from '../core/guideCard';

const route = getRouteApi('/decks/$slug/edit');
const crop = (url: string) => url.replace('/normal/', '/art_crop/');

/** Deck editor: the draft decklist on the left, "Find cards" on the right.
 *  Edits stay a draft until Save cuts a new version; a built deck first shows
 *  the physical swap (pull · sleeve · missing). */
export function DeckEditorView() {
  const { slug } = route.useParams();
  const q = useQuery(deckQuery(slug));
  if (q.isPending) return <Frame><GridSkeleton label="Loading deck…" /></Frame>;
  if (q.isError) return <Frame><ErrorNote error={q.error} onRetry={() => q.refetch()} /></Frame>;
  if (!q.data.editable) {
    return (
      <Frame>
        <EmptyNote title="This decklist is read-only">
          Precon decklists stay as released. <Link to="/decks" search={(s) => ({ ...s, deck: slug })} className="text-accent-ink underline">Back to the deck</Link> and use Copy to edit.
        </EmptyNote>
      </Frame>
    );
  }
  return <Editor key={`${slug}:${q.data.version_id}`} slug={slug} detail={q.data} />;
}

function Frame({ children }: { children: ReactNode }) {
  return <main id="main" tabIndex={-1} className="min-h-0 min-w-0 p-2 sm:p-3 lg:h-[calc(100dvh-var(--size-topbar))] lg:p-4"><div className="paper-grain h-full rounded-sm bg-paper text-ink">{children}</div></main>;
}

function Editor({ slug, detail }: { slug: string; detail: DeckDetailOut }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const narrow = useMediaQuery('(max-width: 63.99rem)');
  const [draft, setDraft] = useState<Draft>(() => draftFromDeck(detail.cards));
  const [name, setName] = useState(detail.deck.name);
  const [pane, setPane] = useState<'deck' | 'find'>('deck');
  const [review, setReview] = useState<PreviewOut | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [inspecting, setInspecting] = useState<GuideCard | null>(null);
  const inspect = (p: PrintingOut) => setInspecting(fromPrinting(p));
  const stats = draftStats(draft, detail.deck.format);
  const renamed = name.trim() !== detail.deck.name && name.trim().length > 0;
  const dirty = stats.dirty || renamed;

  const blocker = useBlocker({ shouldBlockFn: () => dirty && !saving, enableBeforeUnload: () => dirty, withResolver: true });

  const commit = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      unwrap(await deckSave({ path: { slug }, body: { cards: draftCards(draft), expected_version_id: detail.version_id, name: renamed ? name.trim() : null } }));
      await Promise.all(['decks', 'collection', 'holdings'].map((k) => qc.invalidateQueries({ queryKey: [k] })));
      navigate({ to: '/decks', search: (s) => ({ ...s, deck: slug }) });
    } catch (e) {
      setSaving(false);
      throw e;
    }
  };
  const onSave = async () => {
    setSaveError(null);
    try {
      if (stats.dirty && detail.deck.built > 0) {
        const pv = unwrap(await deckPreview({ path: { slug }, body: { cards: draftCards(draft) } }));
        if (pv.swap && (pv.swap.pull.length || pv.swap.sleeve.length || pv.swap.short.length)) {
          setReview(pv);
          return;
        }
      }
      await commit();
    } catch (e) {
      setSaveError((e as Error).message);
    }
  };

  const edit = (fn: (d: Draft) => Draft) => setDraft((d) => fn(d));
  const deckPane = <DraftList draft={draft} onEdit={edit} onInspect={inspect} />;
  const findPane = <FindCards draft={draft} format={detail.deck.format} onAdd={(p, board) => edit((d) => addCard(d, p, board))} onInspect={inspect} />;

  return (
    <main id="main" tabIndex={-1} className="min-h-0 min-w-0 p-2 sm:p-3 lg:h-[calc(100dvh-var(--size-topbar))] lg:p-4">
      <div className="paper-grain flex h-full min-h-[70dvh] flex-col rounded-sm bg-paper text-ink shadow-[0_1px_0_var(--theme-chrome-line),0_18px_40px_-28px_var(--theme-scrim)]">
        <header className="flex flex-wrap items-end gap-x-5 gap-y-2 border-b-2 border-rule-strong px-5 pb-2 pt-3">
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <Link to="/decks" search={(s) => ({ ...s, deck: slug })} className="inline-flex items-center gap-0.5 self-start text-sm voice-semi text-accent-ink">
              <Chevron dir="left" className="size-3.5" /> Back to deck
            </Link>
            <label className="sr-only" htmlFor="deck-name">Deck name</label>
            <input
              id="deck-name"
              value={name}
              maxLength={120}
              onChange={(e) => setName(e.target.value)}
              className="-mx-1 min-w-0 rounded-sm border border-transparent bg-transparent px-1 text-3xl voice-condensed font-bold leading-tight text-ink hover:border-rule focus-visible:border-accent"
            />
          </div>
          <dl className="flex items-baseline gap-4 text-sm tabular">
            <div className="flex flex-col items-end">
              <dt className="text-ink-muted">Cards</dt>
              <dd className={`text-xl voice-condensed font-bold ${stats.target && stats.size !== stats.target ? 'text-accent-ink' : 'text-ink'}`}>
                {fmtInt(stats.size)}{stats.target && <span className="text-md font-regular text-ink-muted"> / {stats.target}</span>}
              </dd>
            </div>
            <DeckChecks slug={slug} draft={draft} />
            <div className="flex flex-col items-end">
              <dt className="text-ink-muted">Changes</dt>
              <dd className="text-xl voice-condensed font-bold" aria-live="polite">
                {stats.dirty ? <>{stats.added > 0 && <span className="text-accent-ink">+{stats.added}</span>} {stats.removed > 0 && <span className="text-danger">−{stats.removed}</span>}</> : <span className="text-ink-muted">none</span>}
              </dd>
            </div>
          </dl>
          <div className="flex items-center gap-2">
            <Button tone="paper" disabled={!dirty} onClick={() => { setDraft(draftFromDeck(detail.cards)); setName(detail.deck.name); }}>Discard changes</Button>
            <Button emphasis="primary" disabled={!dirty || saving} onClick={onSave}>{saving ? 'Saving…' : 'Save deck'}</Button>
          </div>
          {saveError && <p role="alert" className="w-full text-sm text-danger">{saveError}</p>}
        </header>

        {narrow ? (
          <Tabs.Root value={pane} onValueChange={(v) => setPane(v as 'deck' | 'find')} className="flex min-h-0 flex-1 flex-col">
            <Tabs.List aria-label="Editor panes" className="mx-4 mt-2 flex gap-px overflow-hidden rounded-sm border border-rule-strong bg-rule">
              <PaneTab value="deck">Deck · {fmtInt(stats.size)}</PaneTab>
              <PaneTab value="find">Find cards</PaneTab>
            </Tabs.List>
            <Tabs.Content value="deck" className="min-h-0 flex-1">{deckPane}</Tabs.Content>
            <Tabs.Content value="find" className="min-h-0 flex-1">{findPane}</Tabs.Content>
          </Tabs.Root>
        ) : (
          <EditorSplit left={deckPane} right={findPane} />
        )}
      </div>

      <CardInspector card={inspecting} onClose={() => setInspecting(null)} />
      <ConfirmDialog
        open={review != null}
        onOpenChange={(o) => !o && setReview(null)}
        title="Update your built deck"
        confirmLabel="Save and update"
        onConfirm={commit}
      >
        {review?.swap && <SwapList swap={review.swap} />}
      </ConfirmDialog>
      <ConfirmDialog
        open={blocker.status === 'blocked'}
        onOpenChange={(o) => !o && blocker.reset?.()}
        title="Leave without saving?"
        confirmLabel="Discard changes"
        onConfirm={async () => blocker.proceed?.()}
      >
        <p>Your edits to {detail.deck.name} haven’t been saved.</p>
      </ConfirmDialog>
    </main>
  );
}

function PaneTab({ value, children }: { value: string; children: ReactNode }) {
  return (
    <Tabs.Trigger value={value} className="min-h-9 flex-1 cursor-pointer bg-paper-raised px-3 text-sm voice-semi text-ink data-[state=active]:bg-accent data-[state=active]:text-on-accent">
      {children}
    </Tabs.Trigger>
  );
}

function EditorSplit({ left, right }: { left: ReactNode; right: ReactNode }) {
  const layout = useDefaultLayout({ id: 'mm.deck-editor.split', panelIds: ['draft', 'find'], storage: localStorage });
  return (
    <Group orientation="horizontal" className="min-h-0 flex-1" defaultLayout={layout.defaultLayout ?? { draft: 56, find: 44 }} onLayoutChanged={layout.onLayoutChanged}>
      <Panel id="draft" minSize="34" className="flex min-w-0 flex-col">{left}</Panel>
      <Separator aria-label="Resize editor panes" className="group relative w-4 shrink-0 cursor-col-resize outline-none">
        <span className="absolute inset-y-2 left-1/2 w-px -translate-x-1/2 bg-rule-strong/40 transition-colors ease-guide group-hover:bg-rule-strong group-focus-visible:bg-focus group-data-[separator=active]:bg-focus" />
      </Separator>
      <Panel id="find" minSize="28" className="flex min-w-0 flex-col">{right}</Panel>
    </Group>
  );
}

// ---------- left: the draft decklist ----------

const BOARD_LABEL: Record<Board, string> = { commander: 'Commander', main: 'Main deck', companion: 'Companion', side: 'Sideboard', maybe: 'Maybe', token: 'Tokens' };
const FINISH_LABEL: Record<DraftFinish, string> = { either: 'Any finish', nonfoil: 'Nonfoil', foil: 'Foil' };

type Inspect = (p: PrintingOut) => void;

function DraftList({ draft, onEdit, onInspect }: { draft: Draft; onEdit: (fn: (d: Draft) => Draft) => void; onInspect: Inspect }) {
  const sections = useMemo(() => draftSections(draft), [draft]);
  if (!sections.length) {
    return <EmptyNote title="An empty deck">Search for cards on the right{'\u00a0'}— add a commander first to get EDHREC suggestions.</EmptyNote>;
  }
  return (
    <div className="h-full min-h-0 overflow-y-auto overscroll-contain px-4 pb-8 [scrollbar-gutter:stable]">
      {sections.map((s) => (
        <section key={s.key} aria-labelledby={`ds-${s.key}`}>
          <h2 id={`ds-${s.key}`} className="sticky top-0 z-10 flex items-baseline gap-2 border-b border-rule bg-paper pb-1 pt-3 text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">
            {s.label}<span className="ml-auto tabular">{s.count}</span>
          </h2>
          <ul>
            {s.rows.map((r) => <DraftLine key={r.key} row={r} onEdit={onEdit} onInspect={onInspect} />)}
          </ul>
        </section>
      ))}
    </div>
  );
}

function DraftLine({ row, onEdit, onInspect }: { row: DraftRow; onEdit: (fn: (d: Draft) => Draft) => void; onInspect: Inspect }) {
  const p = row.printing;
  const removed = row.count === 0;
  const delta = row.count - row.saved;
  const free = p.free ?? 0;
  return (
    <li className={`ruled flex items-center gap-2 py-1 ${removed ? 'opacity-55' : ''}`}>
      <span className="flex shrink-0 items-center rounded-sm border border-rule" role="group" aria-label={`${p.name} count`}>
        <StepButton label={`One fewer ${p.name}`} onClick={() => onEdit((d) => setCount(d, row.key, row.count - 1))} disabled={removed}>−</StepButton>
        <span className="w-7 text-center text-sm tabular" aria-live="polite">{row.count}</span>
        <StepButton label={`One more ${p.name}`} onClick={() => onEdit((d) => setCount(d, row.key, row.count + 1))}>+</StepButton>
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <CardName p={p} onInspect={onInspect} struck={removed} />
        <span className="truncate text-xs tabular text-ink-muted">
          {[p.set_code.toUpperCase(), `#${p.collector_number}`, row.finish !== 'either' && FINISH_LABEL[row.finish], free > 0 ? `${free} free` : Object.values(p.owned ?? {}).some(Boolean) ? 'owned, all pledged' : 'not owned'].filter(Boolean).join(' · ')}
        </span>
      </span>
      {delta !== 0 && (
        <span className={`shrink-0 text-xs voice-condensed font-bold uppercase tracking-[0.06em] ${delta > 0 ? 'text-accent-ink' : 'text-danger'}`}>
          {row.saved === 0 ? 'New' : removed ? 'Removed' : delta > 0 ? `+${delta}` : `−${-delta}`}
        </span>
      )}
      <span className="w-14 shrink-0 text-right text-xs tabular text-ink-muted">{fmtUsd((row.finish === 'foil' ? p.price_usd_foil : p.price_usd) ?? p.price_usd_foil)}</span>
      <RowMenu row={row} onEdit={onEdit} />
    </li>
  );
}

function StepButton({ label, onClick, disabled, children }: { label: string; onClick: () => void; disabled?: boolean; children: ReactNode }) {
  return (
    <button type="button" aria-label={label} onClick={onClick} disabled={disabled} className="touch-hit grid size-7 cursor-pointer place-items-center text-md text-accent-ink hover:bg-paper-sunk disabled:cursor-not-allowed disabled:text-ink-muted disabled:hover:bg-transparent">
      {children}
    </button>
  );
}

const MOVE_TO: Board[] = ['main', 'commander', 'companion', 'side', 'maybe'];

function RowMenu({ row, onEdit }: { row: DraftRow; onEdit: (fn: (d: Draft) => Draft) => void }) {
  const item = 'flex min-h-8 cursor-pointer select-none items-center gap-2 rounded-xs px-2 text-sm text-on-chrome outline-none data-[highlighted]:bg-chrome data-[disabled]:cursor-default data-[disabled]:text-on-chrome-muted';
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger aria-label={`More for ${row.printing.name}`} className="touch-hit grid size-8 shrink-0 cursor-pointer place-items-center rounded-sm text-ink-muted hover:bg-paper-sunk hover:text-ink data-[state=open]:bg-paper-sunk">
        <span aria-hidden="true" className="text-lg leading-none">⋯</span>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={4} collisionPadding={12} className="z-50 min-w-[12rem] rounded-sm border border-chrome-line bg-chrome-raised p-1 shadow-[0_12px_28px_-12px_var(--theme-scrim)]">
          <DropdownMenu.Label className="px-2 pb-1 pt-1.5 text-xs voice-semi text-on-chrome-muted">Move to</DropdownMenu.Label>
          {MOVE_TO.map((b) => (
            <DropdownMenu.Item key={b} disabled={b === row.board} className={item} onSelect={() => onEdit((d) => moveCard(d, row.key, b))}>
              {BOARD_LABEL[b]}{b === row.board && <span className="ml-auto text-xs">current</span>}
            </DropdownMenu.Item>
          ))}
          <DropdownMenu.Separator className="my-1 h-px bg-chrome-line" />
          <DropdownMenu.Label className="px-2 pb-1 pt-1.5 text-xs voice-semi text-on-chrome-muted">Finish when building</DropdownMenu.Label>
          {(['either', 'nonfoil', 'foil'] as DraftFinish[]).filter((f) => f === 'either' || row.printing.finishes.includes(f as 'nonfoil' | 'foil')).map((f) => (
            <DropdownMenu.Item key={f} disabled={f === row.finish} className={item} onSelect={() => onEdit((d) => setFinish(d, row.key, f))}>
              {FINISH_LABEL[f]}{f === row.finish && <span className="ml-auto text-xs">current</span>}
            </DropdownMenu.Item>
          ))}
          <DropdownMenu.Separator className="my-1 h-px bg-chrome-line" />
          {row.count > 0 ? (
            <DropdownMenu.Item className={item} onSelect={() => onEdit((d) => setCount(d, row.key, 0))}>Remove from deck</DropdownMenu.Item>
          ) : (
            <DropdownMenu.Item className={item} onSelect={() => onEdit((d) => setCount(d, row.key, row.saved))}>Undo remove</DropdownMenu.Item>
          )}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

// ---------- right: find cards ----------

function FindCards({ draft, format, onAdd, onInspect }: { draft: Draft; format: string | null; onAdd: (p: PrintingOut, board: Board) => void; onInspect: Inspect }) {
  const commander = commanderName(draft);
  const [tab, setTab] = useState<'search' | 'suggest'>(commander ? 'suggest' : 'search');
  const inDeck = useMemo(() => draftOracles(draft), [draft]);
  const wantsCommander = !commander && ['commander', 'brawl', 'paupercommander', 'oathbreaker', 'edh'].includes((format ?? '').toLowerCase());
  return (
    <Tabs.Root value={tab} onValueChange={(v) => setTab(v as 'search' | 'suggest')} className="flex h-full min-h-0 flex-col">
      <Tabs.List aria-label="Find cards" className="mx-4 mt-3 flex gap-px self-start overflow-hidden rounded-sm border border-rule-strong bg-rule">
        <PaneTab value="search">Search</PaneTab>
        <PaneTab value="suggest">Suggestions</PaneTab>
      </Tabs.List>
      <Tabs.Content value="search" className="flex min-h-0 flex-1 flex-col">
        <SearchTab inDeck={inDeck} wantsCommander={wantsCommander} onAdd={onAdd} onInspect={onInspect} />
      </Tabs.Content>
      <Tabs.Content value="suggest" className="flex min-h-0 flex-1 flex-col">
        <SuggestTab commander={commander} inDeck={inDeck} onAdd={onAdd} onInspect={onInspect} />
      </Tabs.Content>
    </Tabs.Root>
  );
}

function SearchTab({ inDeck, wantsCommander, onAdd, onInspect }: { inDeck: Set<string>; wantsCommander: boolean; onAdd: (p: PrintingOut, board: Board) => void; onInspect: Inspect }) {
  const [text, setText] = useState('');
  const [q, setQ] = useState('');
  useEffect(() => {
    const t = setTimeout(() => setQ(text), 220);
    return () => clearTimeout(t);
  }, [text]);
  const res = useQuery(printingSearchQuery(q));
  const hits = useMemo(() => collectionFirst(res.data?.printings ?? []), [res.data]);
  return (
    <>
      <label className="mx-4 mt-3 flex flex-col gap-1.5 text-sm voice-semi text-ink-muted">
        {wantsCommander ? 'Search all cards — start with your commander' : 'Search all cards'}
        <input
          type="search"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Sol Ring, Tifa…"
          autoComplete="off"
          spellCheck={false}
          className="h-10 rounded-sm border border-rule-strong bg-paper-raised px-3 text-md text-ink placeholder:text-ink-muted focus-visible:border-accent"
        />
      </label>
      <p className="mx-4 mt-1 text-xs text-ink-muted">Cards you own and have free are listed first.</p>
      <ResultList
        empty={q.trim().length < 2 ? 'Type at least two letters.' : res.isPending ? null : 'No cards match.'}
        loading={q.trim().length >= 2 && res.isFetching && !res.data}
        error={res.isError ? (res.error as Error).message : null}
      >
        {hits.map((p) => (
          <ResultLine key={p.scryfall_id} p={p} inDeck={!!p.oracle_id && inDeck.has(p.oracle_id)} note={freeNote(p.free ?? 0, owned(p))} onAdd={onAdd} onInspect={onInspect} offerCommander={wantsCommander && canCommand(p)} />
        ))}
      </ResultList>
    </>
  );
}

const owned = (p: PrintingOut) => Object.values(p.owned ?? {}).reduce((s, n) => s + n, 0);
const freeNote = (free: number, own: number) => (free > 0 ? `${free} free` : own > 0 ? 'owned, all pledged' : null);

function SuggestTab({ commander, inDeck, onAdd, onInspect }: { commander: string | null; inDeck: Set<string>; onAdd: (p: PrintingOut, board: Board) => void; onInspect: Inspect }) {
  const [freeOnly, setFreeOnly] = useState(false);
  const [hideInDeck, setHideInDeck] = useState(true);
  const res = useQuery(suggestionsQuery(commander));
  const cards = useMemo(
    () => (res.data?.cards ?? []).filter((c: SuggestionOut) => (!freeOnly || c.free > 0) && (!hideInDeck || !c.printing.oracle_id || !inDeck.has(c.printing.oracle_id))),
    [res.data, freeOnly, hideInDeck, inDeck],
  );
  if (!commander) return <EmptyNote title="No commander yet">Add a commander from Search to see what EDHREC players run with it.</EmptyNote>;
  return (
    <>
      <div className="mx-4 mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <span className="min-w-0 truncate text-ink-muted">EDHREC picks for <b className="text-ink">{res.data?.commander ?? commander}</b></span>
        <label className="ml-auto inline-flex cursor-pointer items-center gap-1.5"><input type="checkbox" checked={freeOnly} onChange={(e) => setFreeOnly(e.target.checked)} className="accent-[var(--theme-accent)]" /> Free in my collection</label>
        <label className="inline-flex cursor-pointer items-center gap-1.5"><input type="checkbox" checked={hideInDeck} onChange={(e) => setHideInDeck(e.target.checked)} className="accent-[var(--theme-accent)]" /> Hide cards in deck</label>
      </div>
      <ResultList empty={res.isPending ? null : 'No suggestions match.'} loading={res.isPending} error={res.isError ? (res.error as Error).message : null}>
        {cards.map((c) => (
          <ResultLine
            key={c.printing.scryfall_id}
            p={c.printing}
            inDeck={!!c.printing.oracle_id && inDeck.has(c.printing.oracle_id)}
            lead={c.inclusion_pct != null ? `${Math.round(c.inclusion_pct)}%` : '—'}
            note={freeNote(c.free, c.owned)}
            onAdd={onAdd}
            onInspect={onInspect}
          />
        ))}
      </ResultList>
    </>
  );
}

function ResultList({ children, empty, loading, error }: { children: ReactNode[]; empty: string | null; loading: boolean; error: string | null }) {
  if (error) return <p role="alert" className="mx-4 mt-4 text-sm text-danger">{error}</p>;
  if (loading) return <p role="status" className="mx-4 mt-4 text-sm text-ink-muted">Looking…</p>;
  if (!children.length) return empty ? <p className="mx-4 mt-4 text-sm text-ink-muted">{empty}</p> : null;
  return <ul className="mt-2 min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-8 [scrollbar-gutter:stable]">{children}</ul>;
}

function ResultLine({ p, inDeck, lead, note, onAdd, onInspect, offerCommander = false }: { p: PrintingOut; inDeck: boolean; lead?: string; note: string | null; onAdd: (p: PrintingOut, board: Board) => void; onInspect: Inspect; offerCommander?: boolean }) {
  return (
    <li className="ruled flex items-center gap-3 py-1.5">
      {p.image_uri ? <img src={crop(p.image_uri)} alt="" loading="lazy" decoding="async" className="size-10 shrink-0 rounded-xs object-cover" /> : <span aria-hidden="true" className="size-10 shrink-0 rounded-xs border border-rule bg-paper-sunk" />}
      {lead && <span className="w-10 shrink-0 text-right text-sm voice-condensed font-bold tabular text-ink">{lead}</span>}
      <span className="flex min-w-0 flex-1 flex-col">
        <CardName p={p} onInspect={onInspect} />
        <span className="truncate text-xs tabular text-ink-muted">
          {[p.type_line?.split(' — ')[0], `${p.set_code.toUpperCase()} #${p.collector_number}`].filter(Boolean).join(' · ')}
          {note && <> · <span className={note.endsWith('free') ? 'text-accent-ink' : ''}>{note}</span></>}
          {inDeck && <> · <span className="voice-semi text-ink">in deck</span></>}
        </span>
      </span>
      {offerCommander && (
        <button type="button" onClick={() => onAdd(p, 'commander')} className="shrink-0 cursor-pointer rounded-sm px-2 py-1 text-sm voice-semi text-accent-ink hover:bg-paper-sunk">
          As commander
        </button>
      )}
      <button type="button" aria-label={`Add ${p.name}`} onClick={() => onAdd(p, 'main')} className="touch-hit grid size-9 shrink-0 cursor-pointer place-items-center rounded-sm text-xl text-accent-ink hover:bg-paper-sunk">+</button>
    </li>
  );
}

// ---------- save review: the physical swap ----------

function SwapList({ swap }: { swap: NonNullable<PreviewOut['swap']> }) {
  const n = (ls: SwapLineOut[]) => ls.reduce((t, l) => t + l.qty, 0);
  return (
    <>
      <p>This deck is built, so saving moves cards in and out of it to match the new list.</p>
      <SwapGroup title={`Take out · ${n(swap.pull)}`} lines={swap.pull} note="These go back to your collection as free copies." />
      <SwapGroup title={`Put in · ${n(swap.sleeve)}`} lines={swap.sleeve} note="Free copies from your collection." />
      <SwapGroup title={`Missing · ${n(swap.short)}`} lines={swap.short} note="Not free in your collection — get these to finish the deck." tone="danger" />
    </>
  );
}

function SwapGroup({ title, lines, note, tone }: { title: string; lines: SwapLineOut[]; note: string; tone?: 'danger' }) {
  if (!lines.length) return null;
  return (
    <section className="flex flex-col gap-1">
      <h3 className={`border-b border-rule pb-0.5 text-sm voice-semi font-medium ${tone === 'danger' ? 'text-danger' : 'text-ink'}`}>{title}</h3>
      <p className="text-xs text-ink-muted">{note}</p>
      <ul className="max-h-36 overflow-y-auto text-sm">
        {lines.map((l) => (
          <li key={`${l.printing.scryfall_id}|${l.finish}`} className="flex gap-2 py-0.5">
            <span className="min-w-0 flex-1 truncate">{l.printing.name}</span>
            <span className="tabular text-ink-muted">{l.printing.set_code.toUpperCase()} · ×{l.qty}{l.finish === 'foil' ? ' ✦' : ''}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** The card name opens the inspector (bigger art, facts, your copies). */
function CardName({ p, onInspect, struck = false }: { p: PrintingOut; onInspect: Inspect; struck?: boolean }) {
  return (
    <button
      type="button"
      onClick={() => onInspect(p)}
      className={`min-w-0 cursor-pointer self-start truncate text-left text-md voice-semi font-medium text-ink underline-offset-4 decoration-rule-strong hover:underline focus-visible:underline ${struck ? 'line-through' : ''}`}
    >
      {p.name}
    </button>
  );
}

// ---------- checks: format legality + bracket floor ----------

const FORMAT_NAME: Record<string, string> = { commander: 'Commander', brawl: 'Brawl', paupercommander: 'Pauper Commander', oathbreaker: 'Oathbreaker' };
const formatName = (f: string) => FORMAT_NAME[f] ?? f.charAt(0).toUpperCase() + f.slice(1);

const BRACKET_NAME: Record<number, string> = { 1: 'Exhibition', 2: 'Core', 3: 'Upgraded', 4: 'Optimized' };

/** Legality (Scryfall's per-format legality) and, for Commander, the bracket
 *  FLOOR from Wizards' published criteria. Advisory — never blocks saving. */
function DeckChecks({ slug, draft }: { slug: string; draft: Draft }) {
  const [combos, setCombos] = useState(false);
  const cards = useDebounced(draftCards(draft), 450);
  const q = useQuery(deckCheckQuery(slug, cards, combos));
  const r: CheckOut | undefined = q.data;
  const errors = r?.legality.violations.filter((v) => v.severity === 'error') ?? [];
  const b = r?.bracket;
  return (
    <div className="flex flex-col items-end">
      <dt className="text-ink-muted">Checks</dt>
      <dd>
        <Popover.Root>
          <Popover.Trigger className="cursor-pointer rounded-sm px-1 text-xl voice-condensed font-bold hover:bg-paper-sunk data-[state=open]:bg-paper-sunk" aria-label="Deck checks">
            {!r ? <span className="text-ink-muted">…</span> : (
              <>
                <span className={errors.length ? 'text-danger' : 'text-ink'}>{errors.length ? `${errors.length} issue${errors.length > 1 ? 's' : ''}` : 'Legal'}</span>
                {b?.suggested_bracket != null && <span className="text-ink"> · B{b.suggested_bracket}+</span>}
              </>
            )}
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Content align="end" sideOffset={6} collisionPadding={12} className="z-50 flex max-h-[70dvh] w-[min(24rem,calc(100vw-1.5rem))] flex-col gap-3 overflow-y-auto rounded-sm border border-chrome-line bg-chrome-raised p-3 text-sm text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]">
              {!r ? <p className="text-on-chrome-muted">Checking…</p> : (
                <>
                  <section className="flex flex-col gap-1">
                    <h3 className="voice-semi font-medium">{errors.length ? 'Not legal' : 'Legal'} in {formatName(r.format)}</h3>
                    {r.legality.violations.length === 0 && <p className="text-on-chrome-muted">No problems found.</p>}
                    <ul className="flex flex-col gap-1">
                      {r.legality.violations.map((v, i) => (
                        <li key={`${v.code}-${i}`} className={v.severity === 'error' ? 'text-danger' : 'text-on-chrome-muted'}>{v.message}</li>
                      ))}
                    </ul>
                  </section>
                  {b && (
                    <section className="flex flex-col gap-1 border-t border-chrome-line pt-2">
                      <h3 className="voice-semi font-medium">
                        {b.suggested_bracket != null ? `Bracket ${b.suggested_bracket} or higher · ${BRACKET_NAME[b.suggested_bracket]}` : 'Bracket needs a commander'}
                      </h3>
                      <p className="text-on-chrome-muted">
                        Wizards’ Commander Brackets are guidelines for talking about power, not rules. This is the lowest bracket the list allows by their published criteria; how strong it plays is still your call.
                      </p>
                      {b.game_changers.length > 0 && <p>Game Changers: {b.game_changers.join(', ')}</p>}
                      {b.mass_land_denial.length > 0 && <p>Mass land denial: {b.mass_land_denial.join(', ')}</p>}
                      {b.extra_turns.length > 0 && <p>Extra turns: {b.extra_turns.join(', ')}</p>}
                      {combos
                        ? <p className="text-on-chrome-muted">{b.spellbook_available ? `Two-card combos: ${b.two_card_combos}` : 'Commander Spellbook didn’t answer; combos not counted.'}</p>
                        : <button type="button" onClick={() => setCombos(true)} className="self-start cursor-pointer text-accent underline-offset-4 hover:underline">Also check two-card combos</button>}
                    </section>
                  )}
                </>
              )}
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
      </dd>
    </div>
  );
}

function useDebounced<T>(value: T, ms: number): T {
  const key = JSON.stringify(value);
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(JSON.parse(key) as T), ms);
    return () => clearTimeout(t);
  }, [key, ms]);
  return v;
}

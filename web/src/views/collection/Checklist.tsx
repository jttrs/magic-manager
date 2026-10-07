import { useVirtualizer } from '@tanstack/react-virtual';
import { memo, useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { Button } from '../../components/Button';
import { CardArt } from '../../components/CardFace';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import type { GuideSection } from '../../components/VirtualGuide';
import type { CollectionCardOut } from '../../core/api';
import { cellKey, cellValue, countFinishes, nextCell, ownedOf, parseCount, pledgedOf, type Draft, type Finish } from '../../core/checklist';
import { fmtInt } from '../../core/format';
import { rarityLetter, type GuideCard } from '../../core/guideCard';
import type { Checklist } from './useChecklist';

type Line = { kind: 'line'; key: string; card: GuideCard; data: CollectionCardOut; family: string; finishes: Finish[]; n: number };
type Row = { kind: 'head'; key: string; label: string; level: 1 | 2; meta?: string } | Line;
/** The cell keyboard navigation goes to — keyed by card, so filtering never moves it onto another card. */
type Target = { id: string; finish: Finish };

const LINE_H = 40;

/** Checklist mode's sheet body: one ruled line per printing with a count cell
 *  per finish. Enter/Tab walk down the finish column (Shift goes up), ←/→ switch
 *  finish, Esc puts the cell back. Virtualized for whole set families. */
export function ChecklistTable({ sections, byId, familyNames, checklist }: {
  sections: GuideSection[];
  byId: ReadonlyMap<string, CollectionCardOut>;
  familyNames: ReadonlyMap<string, string>;
  checklist: Checklist;
}) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [target, setTarget] = useState<Target | null>(null);
  // Set by keyboard navigation and consumed by the cell that takes focus, so a
  // row remounting (scroll, refetch, filter) never steals focus on its own.
  const pendingFocus = useRef(false);
  const grabFocus = useCallback(() => {
    const take = pendingFocus.current;
    pendingFocus.current = false;
    return take;
  }, []);

  const { rows, lines } = useMemo(() => {
    const rows: Row[] = [];
    const lines: Line[] = [];
    for (const s of sections) {
      rows.push({ kind: 'head', key: `h:${s.key}`, label: s.label, level: s.level ?? 2, meta: s.level === 1 ? undefined : `${fmtInt(s.items.length)}` });
      for (const card of s.items) {
        const data = byId.get(card.key);
        if (!data) continue;
        const line: Line = { kind: 'line', key: `${s.key}:${card.key}`, card, data, family: familyNames.get(data.family) ?? data.family.toUpperCase(), finishes: countFinishes(data), n: lines.length };
        rows.push(line);
        lines.push(line);
      }
    }
    return { rows, lines };
  }, [sections, byId, familyNames]);

  const rowOf = useMemo(() => {
    const m = new Map<number, number>();
    rows.forEach((r, i) => r.kind === 'line' && m.set(r.n, i));
    return m;
  }, [rows]);

  const virt = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: (i) => (rows[i].kind === 'line' ? LINE_H : (rows[i] as { level: number }).level === 1 ? 52 : 34),
    getItemKey: (i) => rows[i].key,
    overscan: 20,
  });

  const go = (to: { row: number; finish: Finish } | null) => {
    const line = to ? lines[to.row] : undefined;
    if (!to || !line) return false;
    pendingFocus.current = true;
    setTarget({ id: line.data.scryfall_id, finish: to.finish });
    const r = rowOf.get(to.row);
    if (r != null) virt.scrollToIndex(r, { align: 'auto' });
    return true;
  };

  const onKey = (line: Line, finish: Finish) => (e: KeyboardEvent<HTMLInputElement>) => {
    const move =
      e.key === 'Enter' || e.key === 'Tab' ? (e.shiftKey ? 'up' : 'down')
      : e.key === 'ArrowDown' ? 'down'
      : e.key === 'ArrowUp' ? 'up'
      : e.key === 'ArrowLeft' ? 'left'
      : e.key === 'ArrowRight' ? 'right'
      : null;
    if (e.key === 'Escape') {
      e.preventDefault();
      checklist.set(line.data, finish, null, line.family);
      return;
    }
    if (!move) return;
    // Enter/Tab on a flagged cell keeps your count.
    if (e.key === 'Enter' || e.key === 'Tab') checklist.confirm(line.data, finish);
    if (go(nextCell(lines, line.n, finish, move))) e.preventDefault();
    else if (e.key === 'Enter') e.preventDefault();
  };

  return (
    <div className="@container flex h-full min-h-0 flex-col">
      <div aria-hidden className="mx-4 grid grid-cols-[minmax(0,1fr)_repeat(2,5.25rem)] items-end gap-2 border-b-2 border-rule-strong pb-1 text-xs voice-semi font-medium uppercase tracking-[0.08em] text-ink-muted @[26rem]:grid-cols-[var(--size-thumb)_minmax(0,1fr)_repeat(2,6rem)]">
        <span className="@[26rem]:col-span-2">Printing</span>
        <span className="text-right">Nonfoil</span>
        <span className="text-right">Foil ✦</span>
      </div>
      <div ref={scrollRef} role="region" aria-label="Count your copies" className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-6">
        <div className="relative w-full" style={{ height: virt.getTotalSize() }}>
          {virt.getVirtualItems().map((vi) => {
            const row = rows[vi.index];
            return (
              <div key={vi.key} data-index={vi.index} ref={virt.measureElement} className="absolute left-0 top-0 w-full" style={{ transform: `translateY(${vi.start}px)` }}>
                {row.kind === 'head' ? (
                  <div className={row.level === 1 ? 'flex items-end border-b-2 border-rule-strong pb-1.5 pt-5 text-ink' : 'flex items-center border-b border-rule pb-1 pt-3 text-ink-muted'}>
                    <span className={row.level === 1 ? 'text-2xl voice-condensed font-bold uppercase leading-none' : 'text-sm voice-condensed font-medium uppercase tracking-[0.06em]'}>{row.label}</span>
                    {row.meta && <span className="ml-auto text-sm tabular">{row.meta}</span>}
                  </div>
                ) : (
                  <CountLine
                    line={row}
                    draft={checklist.draft}
                    focus={target?.id === row.data.scryfall_id ? target.finish : null}
                    grabFocus={grabFocus}
                    onFocusCell={(finish) => setTarget({ id: row.data.scryfall_id, finish })}
                    onSet={(finish, qty) => checklist.set(row.data, finish, qty, row.family)}
                    onKey={(finish) => onKey(row, finish)}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

type LineProps = {
  line: Line;
  draft: Draft;
  focus: Finish | null;
  grabFocus: () => boolean;
  onFocusCell: (f: Finish) => void;
  onSet: (f: Finish, qty: number | null) => void;
  onKey: (f: Finish) => (e: KeyboardEvent<HTMLInputElement>) => void;
};

const CountLine = memo(function CountLine({ line, draft, focus, grabFocus, onFocusCell, onSet, onKey }: LineProps) {
  const { card, data } = line;
  const edited = line.finishes.some((f) => draft[cellKey(data.scryfall_id, f)]);
  return (
    <div className={`grid min-h-10 grid-cols-[minmax(0,1fr)_repeat(2,5.25rem)] items-center gap-2 ruled @[26rem]:grid-cols-[var(--size-thumb)_minmax(0,1fr)_repeat(2,6rem)] ${edited ? 'highlighter' : ''}`}>
      <span className="hidden h-[var(--size-thumb)] w-[var(--size-thumb)] overflow-hidden rounded-xs @[26rem]:block">
        <CardArt card={card} crop />
      </span>
      <span className="flex min-w-0 flex-col leading-tight">
        <span className="truncate text-sm voice-semi text-ink">{card.name}</span>
        <span className="truncate text-2xs tabular text-ink-muted" translate="no">
          {[card.setCode, card.cn, rarityLetter(card.rarity)].filter(Boolean).join(' · ')}
          {card.tags.length > 0 && ` · ${card.tags.join(' · ')}`}
        </span>
      </span>
      {(['nonfoil', 'foil'] as const).map((f) =>
        line.finishes.includes(f) ? (
          <CountCell
            key={f}
            label={`${card.name} ${card.setCode ?? ''} ${card.cn ?? ''} ${f}`}
            was={draft[cellKey(data.scryfall_id, f)]?.was ?? ownedOf(data, f)}
            value={cellValue(draft, data, f)}
            pledged={pledgedOf(data, f)}
            moved={!!draft[cellKey(data.scryfall_id, f)]?.moved}
            focused={focus === f}
            grabFocus={grabFocus}
            onFocus={() => onFocusCell(f)}
            onSet={(q) => onSet(f, q)}
            onKeyDown={onKey(f)}
          />
        ) : (
          <span key={f} className="text-right text-sm text-ink-muted" title={`No ${f} printing`}>—</span>
        ),
      )}
    </div>
  );
});

function CountCell({ label, was, value, pledged, moved, focused, grabFocus, onFocus, onSet, onKeyDown }: {
  label: string;
  was: number;
  value: number;
  pledged: number;
  /** The collection changed under this cell: recheck it (Enter keeps your count). */
  moved: boolean;
  focused: boolean;
  grabFocus: () => boolean;
  onFocus: () => void;
  onSet: (qty: number | null) => void;
  onKeyDown: (e: KeyboardEvent<HTMLInputElement>) => void;
}) {
  const ref = useRef<HTMLInputElement | null>(null);
  const [text, setText] = useState(String(value));
  const [bad, setBad] = useState(false);
  const active = useRef(false);

  // Follow the draft (discard, save, Esc) unless you're mid-typing.
  useEffect(() => {
    if (!active.current) setText(String(value));
  }, [value]);
  useEffect(() => {
    // Only keyboard navigation moves focus here; a remount never steals it.
    if (focused && document.activeElement !== ref.current && grabFocus()) {
      ref.current?.focus({ preventScroll: true });
      ref.current?.select();
    }
  }, [focused, grabFocus]);

  const delta = value - was;
  const low = value < pledged;
  return (
    <span className="flex items-center justify-end gap-1.5">
      <span className={`min-w-6 whitespace-nowrap text-right text-2xs tabular voice-semi ${moved || delta > 0 ? 'text-accent-ink' : 'text-danger'}`} aria-hidden={delta === 0 && !moved}>
        {moved ? `now ${was}` : delta > 0 ? `+${delta}` : delta < 0 ? `−${-delta}` : ''}
      </span>
      <input
        ref={ref}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        aria-label={label}
        aria-invalid={bad || low || undefined}
        aria-description={moved ? `Changed to ${was} since you started counting` : undefined}
        title={moved ? `Your collection now has ${was} — retype the count, or press Enter to keep ${value}` : pledged ? `${pledged} in built decks — break those down to count fewer` : undefined}
        value={text}
        onFocus={(e) => {
          active.current = true;
          e.currentTarget.select();
          onFocus();
        }}
        onBlur={() => {
          active.current = false;
          setBad(false);
          setText(String(value));
        }}
        onChange={(e) => {
          const t = e.target.value;
          setText(t);
          const n = parseCount(t);
          setBad(n === 'invalid');
          if (n !== 'invalid') onSet(n);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Escape') setText(String(was));
          onKeyDown(e);
        }}
        className={`h-7 w-11 rounded-xs border bg-paper-raised px-1.5 text-right text-sm tabular text-ink outline-none transition-[border-color,background-color] duration-150 ease-guide focus:border-accent focus:bg-paper ${bad || low ? 'border-danger' : moved ? 'border-accent ring-2 ring-accent' : 'border-rule'} ${delta !== 0 ? 'font-semibold' : ''}`}
      />
    </span>
  );
}

/** Discard (confirmed) + the one commit, Save. */
export function ChecklistActions({ checklist: c }: { checklist: Checklist }) {
  const [confirm, setConfirm] = useState(false);
  const low = c.summary.belowPledged;
  const n = c.summary.cells;
  return (
    <>
      <Button tone="paper" disabled={!c.dirty || c.saving} onClick={() => setConfirm(true)}>Discard</Button>
      <Button
        emphasis="primary"
        disabled={!c.dirty || c.saving || low.length > 0 || c.summary.moved > 0}
        title={c.summary.moved ? 'Recheck the flagged counts first' : low.length ? `${low[0].name} can’t go below the ${low[0].min} in built decks` : undefined}
        onClick={() => void c.save()}
      >
        {c.saving ? 'Saving…' : n ? `Save ${fmtInt(n)} ${n === 1 ? 'change' : 'changes'}` : 'Save'}
      </Button>
      <ConfirmDialog open={confirm} onOpenChange={setConfirm} title={`Discard ${fmtInt(n)} ${n === 1 ? 'count' : 'counts'}?`} confirmLabel="Discard counts" onConfirm={async () => c.discard()}>
        <p>Your collection stays as it was. The counts you typed are thrown away.</p>
      </ConfirmDialog>
    </>
  );
}

/** Save errors (stale counts, pledged copies) and the below-pledged hint, above the table. */
export function ChecklistNotes({ checklist: c }: { checklist: Checklist }) {
  const low = c.summary.belowPledged;
  const moved = c.summary.moved;
  if (!c.error && !low.length && !moved) return null;
  return (
    <div className="mx-4 mb-2 flex flex-col gap-1 text-sm">
      {c.error && <p role="alert" className="text-danger">Couldn’t save: {c.error}</p>}
      {moved > 0 && (
        <p role="status" className="flex flex-wrap items-center gap-x-3 gap-y-1 text-ink">
          <span>
            {fmtInt(moved)} {moved === 1 ? 'count changed' : 'counts changed'} in your collection since you started counting. Each flagged cell shows the new number — retype it, or press Enter to keep yours.
          </span>
          <button type="button" onClick={() => c.confirm()} className="cursor-pointer text-accent-ink underline hover:text-ink">Keep all my counts</button>
        </p>
      )}
      {low.length > 0 && (
        <p className="text-danger">
          {low[0].name} has {low[0].min} {low[0].min === 1 ? 'copy' : 'copies'} in built decks — break {low[0].min === 1 ? 'it' : 'them'} down before counting fewer{low.length > 1 ? ` (and ${low.length - 1} more)` : ''}.
        </p>
      )}
    </div>
  );
}

/** Asks before leaving Collection with unsaved counts (they stay in this browser either way). */
export function ChecklistLeaveGuard({ checklist: c }: { checklist: Checklist }) {
  const b = c.blocker;
  return (
    <ConfirmDialog
      open={b.status === 'blocked'}
      onOpenChange={(o) => !o && b.reset?.()}
      title="Leave with unsaved counts?"
      confirmLabel="Leave"
      onConfirm={async () => b.proceed?.()}
    >
      <p>{fmtInt(c.summary.cells)} {c.summary.cells === 1 ? 'count isn’t' : 'counts aren’t'} saved yet. They stay in this browser — come back to Collection to save or discard them.</p>
    </ConfirmDialog>
  );
}

import { useVirtualizer } from '@tanstack/react-virtual';
import { memo, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
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
type Target = { row: number; finish: Finish };

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

  const go = (to: Target | null) => {
    if (!to) return false;
    setTarget(to);
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
    if (go(nextCell(lines, line.n, finish, move))) e.preventDefault();
    else if (e.key === 'Enter') e.preventDefault();
  };

  return (
    <div className="@container flex h-full min-h-0 flex-col">
      <div aria-hidden className="mx-4 grid grid-cols-[minmax(0,1fr)_repeat(2,4.75rem)] items-end gap-2 border-b-2 border-rule-strong pb-1 text-xs voice-semi font-medium uppercase tracking-[0.08em] text-ink-muted @[26rem]:grid-cols-[var(--size-thumb)_minmax(0,1fr)_repeat(2,5.5rem)]">
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
                    focus={target?.row === row.n ? target.finish : null}
                    onFocusCell={(finish) => setTarget({ row: row.n, finish })}
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
  onFocusCell: (f: Finish) => void;
  onSet: (f: Finish, qty: number | null) => void;
  onKey: (f: Finish) => (e: KeyboardEvent<HTMLInputElement>) => void;
};

const CountLine = memo(function CountLine({ line, draft, focus, onFocusCell, onSet, onKey }: LineProps) {
  const { card, data } = line;
  const edited = line.finishes.some((f) => draft[cellKey(data.scryfall_id, f)]);
  return (
    <div className={`grid min-h-10 grid-cols-[minmax(0,1fr)_repeat(2,4.75rem)] items-center gap-2 ruled @[26rem]:grid-cols-[var(--size-thumb)_minmax(0,1fr)_repeat(2,5.5rem)] ${edited ? 'highlighter' : ''}`}>
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
            focused={focus === f}
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

function CountCell({ label, was, value, pledged, focused, onFocus, onSet, onKeyDown }: {
  label: string;
  was: number;
  value: number;
  pledged: number;
  focused: boolean;
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
    if (focused && document.activeElement !== ref.current) {
      ref.current?.focus({ preventScroll: true });
      ref.current?.select();
    }
  }, [focused]);

  const delta = value - was;
  const low = value < pledged;
  return (
    <span className="flex items-center justify-end gap-1.5">
      <span className={`w-6 text-right text-2xs tabular voice-semi ${delta > 0 ? 'text-accent-ink' : 'text-danger'}`} aria-hidden={delta === 0}>
        {delta > 0 ? `+${delta}` : delta < 0 ? `−${-delta}` : ''}
      </span>
      <input
        ref={ref}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        aria-label={label}
        aria-invalid={bad || low || undefined}
        title={pledged ? `${pledged} in built decks — break those down to count fewer` : undefined}
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
        className={`h-7 w-11 rounded-xs border bg-paper-raised px-1.5 text-right text-sm tabular text-ink outline-none transition-[border-color,background-color] duration-150 ease-guide focus:border-accent focus:bg-paper ${bad || low ? 'border-danger' : 'border-rule'} ${delta !== 0 ? 'font-semibold' : ''}`}
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
        disabled={!c.dirty || c.saving || low.length > 0}
        title={low.length ? `${low[0].name} can’t go below the ${low[0].min} in built decks` : undefined}
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
  if (!c.error && !low.length) return null;
  return (
    <div className="mx-4 mb-2 flex flex-col gap-1 text-sm">
      {c.error && <p role="alert" className="text-danger">Couldn’t save: {c.error}</p>}
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

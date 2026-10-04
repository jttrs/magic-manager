import { useVirtualizer } from '@tanstack/react-virtual';
import { useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Chevron } from './Chevron';
import type { GuideCard, GuideGroup } from '../core/guideCard';
import { CardRow } from './CardRow';
import { CardTile } from './CardTile';

type Density = 'grid' | 'list';

export type GuideSection = GuideGroup & {
  level?: 1 | 2;
  /** Shown right after the label (e.g. a progress meter or a set name). */
  detail?: ReactNode;
  /** Right-aligned facts; defaults to the card count. */
  meta?: ReactNode;
  /** Plain-text noun for jump buttons, e.g. "set family" (default "section"). */
  noun?: string;
};

type Head = { kind: 'head'; key: string; section: GuideSection; level: 1 | 2; collapsed: boolean };
type VRow = Head | { kind: 'cards'; key: string; items: GuideCard[] };

type Props = {
  sections: GuideSection[];
  density: Density;
  selected: ReadonlySet<string>;
  onToggle: (key: string) => void;
  barLabels?: [string, string];
  /** Accessible name for the scroll region. */
  label: string;
  minCardWidth?: number;
};

const GAP = 12;

/** One virtualized scroll region for any grouped card list, in grid or list view. */
export function VirtualGuide({ sections, density, selected, onToggle, barLabels, label, minCardWidth = 120 }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const columns = density === 'list' ? 1 : Math.max(1, Math.floor((width + GAP) / (minCardWidth + GAP)));
  const [collapsed, setCollapsed] = useState<ReadonlySet<string>>(() => new Set());
  const toggleSection = (key: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (!next.delete(key)) next.add(key);
      return next;
    });

  // A collapsed level-1 section hides every level-2 section under it.
  const rows = useMemo<VRow[]>(() => {
    const out: VRow[] = [];
    let parentClosed = false;
    for (const s of sections) {
      const level = s.level ?? 2;
      if (level === 1) parentClosed = false;
      else if (parentClosed) continue;
      const closed = collapsed.has(s.key);
      out.push({ kind: 'head', key: `h:${s.key}`, section: s, level, collapsed: closed });
      if (level === 1) parentClosed = closed;
      if (closed) continue;
      for (let i = 0; i < s.items.length; i += columns) {
        out.push({ kind: 'cards', key: `c:${s.key}:${i}`, items: s.items.slice(i, i + columns) });
      }
    }
    return out;
  }, [sections, columns, collapsed]);

  const cardH = width ? ((width - GAP * (columns - 1)) / columns) * (680 / 488) + 52 : 220;
  const virt = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: (i) => {
      const r = rows[i];
      return r.kind === 'head' ? (r.level === 1 ? 72 : 38) : density === 'list' ? 33 : cardH + GAP;
    },
    getItemKey: (i) => rows[i].key,
    // Keep ~a screen of rows mounted either side so short scroll-backs never remount.
    overscan: density === 'list' ? 24 : 6,
  });

  /** Scroll to the previous/next head of the same level, then focus its toggle. */
  const jump = (from: number, dir: 1 | -1) => {
    const level = (rows[from] as Head).level;
    for (let i = from + dir; i >= 0 && i < rows.length; i += dir) {
      const r = rows[i];
      if (r.kind === 'head' && r.level === level) {
        virt.scrollToIndex(i, { align: 'start' });
        window.setTimeout(() => scrollRef.current?.querySelector<HTMLButtonElement>(`[data-head="${CSS.escape(r.key)}"] button[aria-expanded]`)?.focus({ preventScroll: true }), 80);
        return;
      }
    }
  };
  const neighbor = (from: number, dir: 1 | -1) => {
    const level = (rows[from] as Head).level;
    for (let i = from + dir; i >= 0 && i < rows.length; i += dir) {
      const r = rows[i];
      if (r.kind === 'head' && r.level === level) return true;
    }
    return false;
  };

  return (
    <div ref={scrollRef} role="region" aria-label={label} tabIndex={0} className="@container h-full min-h-0 overflow-y-auto overscroll-contain px-4 pb-6 focus-visible:outline-offset-[-2px]">
      <div className="relative w-full" style={{ height: virt.getTotalSize() }}>
        {virt.getVirtualItems().map((vi) => {
          const row = rows[vi.index];
          return (
            <div
              key={vi.key}
              data-index={vi.index}
              ref={virt.measureElement}
              className="absolute left-0 top-0 w-full"
              style={{ transform: `translateY(${vi.start}px)` }}
            >
              {row.kind === 'head' ? (
                <SectionHead
                  row={row}
                  onToggle={() => toggleSection(row.section.key)}
                  onPrev={neighbor(vi.index, -1) ? () => jump(vi.index, -1) : undefined}
                  onNext={neighbor(vi.index, 1) ? () => jump(vi.index, 1) : undefined}
                />
              ) : density === 'list' ? (
                row.items.map((c) => <CardRow key={c.key} card={c} selected={selected.has(c.key)} onToggle={onToggle} barLabels={barLabels} />)
              ) : (
                <div className="grid pb-3" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`, columnGap: GAP }}>
                  {row.items.map((c) => (
                    <CardTile key={c.key} card={c} selected={selected.has(c.key)} onToggle={onToggle} barLabels={barLabels} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SectionHead({ row, onToggle, onPrev, onNext }: { row: Head; onToggle: () => void; onPrev?: () => void; onNext?: () => void }) {
  const { section: s, level, collapsed } = row;
  const top = level === 1;
  const H = top ? 'h2' : 'h3';
  const noun = s.noun ?? 'section';
  return (
    <div
      data-head={row.key}
      className={
        top
          ? 'flex flex-wrap items-end gap-x-4 gap-y-1 border-b-2 border-rule-strong pb-1.5 pt-6 text-ink'
          : 'flex items-center gap-x-3 border-b border-rule pb-1 pt-3 text-ink-muted'
      }
    >
      <div className="min-w-0">
        <H className="m-0">
          <button
            type="button"
            aria-expanded={!collapsed}
            onClick={onToggle}
            className={`group flex cursor-pointer items-center gap-1.5 text-left ${top ? 'text-2xl voice-condensed font-bold uppercase leading-none text-ink' : 'text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted hover:text-ink'}`}
          >
            <Chevron dir={collapsed ? 'right' : 'down'} className={`shrink-0 text-ink-muted transition-transform group-hover:text-ink ${top ? 'size-5' : 'size-4'}`} />
            {s.label}
          </button>
        </H>
      </div>
      {s.detail}
      <span className={`ml-auto tabular ${top ? 'text-sm text-ink-muted' : 'text-sm'}`}>{s.meta ?? s.items.length}</span>
      <span className="flex shrink-0 items-center">
        <JumpButton dir="up" label={`Previous ${noun}`} onClick={onPrev} />
        <JumpButton dir="down" label={`Next ${noun}`} onClick={onNext} />
      </span>
    </div>
  );
}

function JumpButton({ dir, label, onClick }: { dir: 'up' | 'down'; label: string; onClick?: () => void }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={!onClick}
      onClick={onClick}
      className="grid size-7 cursor-pointer place-items-center rounded-sm text-ink-muted hover:bg-paper-sunk hover:text-ink disabled:cursor-default disabled:opacity-30 disabled:hover:bg-transparent"
    >
      <Chevron dir={dir} className="size-4" />
    </button>
  );
}

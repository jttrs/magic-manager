import { useVirtualizer } from '@tanstack/react-virtual';
import { useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { GuideCard, GuideGroup } from '../core/guideCard';
import { CardRow } from './CardRow';
import { CardTile } from './CardTile';

type Density = 'grid' | 'rows';

export type GuideSection = GuideGroup & { level?: 1 | 2; head?: ReactNode };

type VRow =
  | { kind: 'head'; key: string; level: 1 | 2; label: string; count: number; head?: ReactNode }
  | { kind: 'cards'; key: string; items: GuideCard[] };

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

/** One virtualized scroll region for any grouped card list, in grid or rows density. */
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

  const columns = density === 'rows' ? 1 : Math.max(1, Math.floor((width + GAP) / (minCardWidth + GAP)));

  const rows = useMemo<VRow[]>(() => {
    const out: VRow[] = [];
    for (const s of sections) {
      out.push({ kind: 'head', key: `h:${s.key}`, level: s.level ?? 2, label: s.label, count: s.items.length, head: s.head });
      for (let i = 0; i < s.items.length; i += columns) {
        out.push({ kind: 'cards', key: `c:${s.key}:${i}`, items: s.items.slice(i, i + columns) });
      }
    }
    return out;
  }, [sections, columns]);

  const cardH = width ? ((width - GAP * (columns - 1)) / columns) * (680 / 488) + 52 : 220;
  const virt = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: (i) => (rows[i].kind === 'head' ? (rows[i] as { level: number }).level === 1 ? 52 : 34 : density === 'rows' ? 33 : cardH + GAP),
    getItemKey: (i) => rows[i].key,
    overscan: density === 'rows' ? 12 : 3,
  });

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
                row.head ?? <SubHead label={row.label} count={row.count} level={row.level} />
              ) : density === 'rows' ? (
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

function SubHead({ label, count, level }: { label: string; count: number; level: 1 | 2 }) {
  return level === 1 ? (
    <h3 className="flex items-baseline gap-3 border-b-2 border-rule-strong pb-1 pt-4 text-2xl voice-condensed font-bold uppercase text-ink">
      {label}
      <span className="ml-auto text-sm voice-semi font-regular normal-case tabular text-ink-muted">{count}</span>
    </h3>
  ) : (
    <h4 className="flex items-baseline gap-2 border-b border-rule pb-1 pt-3 text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">
      {label}
      <span className="ml-auto tabular">{count}</span>
    </h4>
  );
}

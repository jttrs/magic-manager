import { combine } from '@atlaskit/pragmatic-drag-and-drop/combine';
import { draggable, dropTargetForElements } from '@atlaskit/pragmatic-drag-and-drop/element/adapter';
import { attachClosestEdge, extractClosestEdge, type Edge } from '@atlaskit/pragmatic-drag-and-drop-hitbox/closest-edge';
import { reorderWithEdge } from '@atlaskit/pragmatic-drag-and-drop-hitbox/util/reorder-with-edge';
import { Popover } from 'radix-ui';
import { useEffect, useId, useRef, useState } from 'react';
import type { SortDir, SortPreset, SortRule } from '../core/sort';

type KeyMeta = { label: string; defaultDir: SortDir };

type Props<K extends string> = {
  keys: Record<K, KeyMeta>;
  rules: SortRule<K>[];
  presets: SortPreset<K>[];
  onChange: (rules: SortRule<K>[]) => void;
};

const DIR_LABEL: Record<SortDir, string> = { asc: 'A→Z / low→high', desc: 'Z→A / high→low' };

/**
 * Hierarchical sort editor. The sidebar shows the current hierarchy as one line
 * ("Set › Rarity › #"); the popover edits it: add/remove levels, flip direction,
 * reorder by drag (Pragmatic drag-and-drop) or by the ↑/↓ buttons, or start
 * from a preset. The first level also sets the guide's section heads.
 */
export function SortBuilder<K extends string>({ keys, rules, presets, onChange }: Props<K>) {
  const id = useId();
  const [live, setLive] = useState('');
  const unused = (Object.keys(keys) as K[]).filter((k) => !rules.some((r) => r.key === k));
  const summary = rules.length ? rules.map((r) => `${keys[r.key].label}${r.dir !== keys[r.key].defaultDir ? (r.dir === 'asc' ? ' ↑' : ' ↓') : ''}`).join(' › ') : 'Unsorted';

  const move = (from: number, to: number) => {
    if (to < 0 || to >= rules.length) return;
    const next = [...rules];
    const [r] = next.splice(from, 1);
    next.splice(to, 0, r);
    onChange(next);
    setLive(`${keys[r.key].label} moved to level ${to + 1} of ${next.length}`);
  };

  return (
    <div className="flex flex-col gap-1.5">
      <span id={`${id}-l`} className="text-sm voice-semi text-on-chrome-muted">Sort</span>
      <Popover.Root>
        <Popover.Trigger
          aria-labelledby={`${id}-l ${id}-s`}
          className="flex min-h-9 w-full cursor-pointer items-center gap-2 rounded-sm border border-chrome-line bg-chrome-raised px-2.5 text-left text-md text-on-chrome transition-colors ease-guide hover:border-on-chrome-muted data-[state=open]:border-accent"
        >
          <span id={`${id}-s`} className="min-w-0 flex-1 truncate voice-semi">{summary}</span>
          <span aria-hidden="true" className="text-on-chrome-muted">▾</span>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="start"
            sideOffset={4}
            collisionPadding={12}
            aria-label="Sort hierarchy"
            tabIndex={-1}
            onOpenAutoFocus={(e) => {
              e.preventDefault();
              (e.currentTarget as HTMLElement).focus({ preventScroll: true });
            }}
            className="z-50 flex focus:outline-none w-[22rem] max-w-[calc(100vw-1.5rem)] flex-col gap-3 rounded-sm border border-chrome-line bg-chrome-raised p-3 text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]"
          >
            <div className="flex items-baseline justify-between">
              <h2 className="text-sm voice-condensed uppercase tracking-[0.06em] text-on-chrome-muted">Sort by, in order</h2>
              {rules.length > 0 && (
                <button type="button" onClick={() => onChange([])} className="cursor-pointer text-xs text-on-chrome-muted underline hover:text-on-chrome">Clear</button>
              )}
            </div>
            <ol className="flex flex-col gap-1" aria-label="Sort levels">
              {rules.map((r, i) => (
                <RuleRow
                  key={r.key}
                  index={i}
                  count={rules.length}
                  label={keys[r.key].label}
                  dir={r.dir}
                  onDir={(dir) => onChange(rules.map((x, j) => (j === i ? { ...x, dir } : x)))}
                  onRemove={() => onChange(rules.filter((_, j) => j !== i))}
                  onMove={move}
                  onDropAt={(from, edge) => {
                    const next = reorderWithEdge({ list: rules, startIndex: from, indexOfTarget: i, closestEdgeOfTarget: edge, axis: 'vertical' });
                    onChange(next);
                    setLive(`${keys[rules[from].key].label} moved to level ${next.findIndex((x) => x.key === rules[from].key) + 1}`);
                  }}
                />
              ))}
            </ol>
            {rules.length === 0 && <p className="text-sm text-on-chrome-muted">No sort levels. Add one below or pick a preset.</p>}
            {unused.length > 0 && (
              <label className="flex items-center gap-2 text-sm text-on-chrome-muted">
                Then by
                <select
                  value=""
                  onChange={(e) => {
                    const k = e.target.value as K;
                    if (k) onChange([...rules, { key: k, dir: keys[k].defaultDir }]);
                  }}
                  className="min-h-8 flex-1 cursor-pointer rounded-sm border border-chrome-line bg-chrome px-2 text-sm text-on-chrome"
                >
                  <option value="">Add a level…</option>
                  {unused.map((k) => <option key={k} value={k}>{keys[k].label}</option>)}
                </select>
              </label>
            )}
            <div className="flex flex-col gap-1.5 border-t border-chrome-line pt-2">
              <span className="text-xs voice-condensed uppercase tracking-[0.06em] text-on-chrome-muted">Presets</span>
              <div className="flex flex-wrap gap-1.5">
                {presets.map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    onClick={() => onChange(p.rules)}
                    className="min-h-7 cursor-pointer rounded-pill border border-chrome-line px-2.5 text-xs voice-semi text-on-chrome-muted transition-colors ease-guide hover:border-on-chrome-muted hover:text-on-chrome"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            <p aria-live="polite" className="sr-only">{live}</p>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </div>
  );
}

type RowProps = {
  index: number;
  count: number;
  label: string;
  dir: SortDir;
  onDir: (d: SortDir) => void;
  onRemove: () => void;
  onMove: (from: number, to: number) => void;
  onDropAt: (from: number, edge: Edge | null) => void;
};

const SORT_ITEM = 'mm-sort-rule';

function RuleRow({ index, count, label, dir, onDir, onRemove, onMove, onDropAt }: RowProps) {
  const ref = useRef<HTMLLIElement>(null);
  const handle = useRef<HTMLSpanElement>(null);
  const [edge, setEdge] = useState<Edge | null>(null);
  const [dragging, setDragging] = useState(false);
  const dropRef = useRef(onDropAt);
  useEffect(() => {
    dropRef.current = onDropAt;
  }, [onDropAt]);

  useEffect(() => {
    const el = ref.current;
    const h = handle.current;
    if (!el || !h) return;
    return combine(
      draggable({
        element: el,
        dragHandle: h,
        getInitialData: () => ({ type: SORT_ITEM, index }),
        onDragStart: () => setDragging(true),
        onDrop: () => setDragging(false),
      }),
      dropTargetForElements({
        element: el,
        canDrop: ({ source }) => source.data.type === SORT_ITEM && source.data.index !== index,
        getData: ({ input, element }) => attachClosestEdge({ index }, { element, input, allowedEdges: ['top', 'bottom'] }),
        onDrag: ({ self }) => setEdge(extractClosestEdge(self.data)),
        onDragLeave: () => setEdge(null),
        onDrop: ({ source, self }) => {
          setEdge(null);
          dropRef.current(source.data.index as number, extractClosestEdge(self.data));
        },
      }),
    );
  }, [index]);

  const btn = 'grid h-7 w-7 shrink-0 cursor-pointer place-items-center rounded-xs text-on-chrome-muted transition-colors ease-guide hover:bg-chrome-line hover:text-on-chrome disabled:cursor-not-allowed disabled:opacity-30';
  return (
    <li
      ref={ref}
      className={`relative flex items-center gap-1 rounded-xs border border-chrome-line bg-chrome px-1 py-0.5 ${dragging ? 'opacity-40' : ''}`}
    >
      {edge && (
        <span aria-hidden="true" className={`pointer-events-none absolute inset-x-0 h-0.5 rounded-pill bg-accent ${edge === 'top' ? '-top-[3px]' : '-bottom-[3px]'}`} />
      )}
      <span ref={handle} aria-hidden="true" className="cursor-grab select-none px-1 text-on-chrome-muted active:cursor-grabbing" title="Drag to reorder">⋮⋮</span>
      <span className="w-4 shrink-0 tabular text-xs text-on-chrome-muted">{index + 1}</span>
      <span className="min-w-0 flex-1 truncate text-sm voice-semi">{label}</span>
      <button type="button" className={`${btn} w-auto px-1.5 text-xs`} onClick={() => onDir(dir === 'asc' ? 'desc' : 'asc')} aria-label={`${label}: ${DIR_LABEL[dir]}. Reverse`} title={DIR_LABEL[dir]}>
        {dir === 'asc' ? '↑ Asc' : '↓ Desc'}
      </button>
      <button type="button" className={btn} onClick={() => onMove(index, index - 1)} disabled={index === 0} aria-label={`Move ${label} up`}>▲</button>
      <button type="button" className={btn} onClick={() => onMove(index, index + 1)} disabled={index === count - 1} aria-label={`Move ${label} down`}>▼</button>
      <button type="button" className={btn} onClick={onRemove} aria-label={`Remove ${label}`}>×</button>
    </li>
  );
}

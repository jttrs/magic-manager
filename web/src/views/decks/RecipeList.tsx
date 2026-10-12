import { defaultRangeExtractor, useVirtualizer, type Range } from '@tanstack/react-virtual';
import { useCallback, useMemo, useRef } from 'react';
import { useRovingFocus } from '../../app/useRovingFocus';
import { EmptyNote } from '../../components/States';
import type { RecipeOut } from '../../core/api';
import { coverage, KIND_LABEL, ownershipLabel, type DeckGroup } from '../../core/decks';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';

const crop = (url: string) => url.replace('/normal/', '/art_crop/');

type Item = { type: 'head'; g: DeckGroup } | { type: 'row'; r: RecipeOut };

/** Every recipe as ruled rows under group heads — virtualized (the catalog runs to ~1,300 rows),
 *  the current group head pinned. One tab stop for the list (↑/↓, Home/End, Enter opens). */
export function RecipeList({ groups, total, active, onPick }: { groups: DeckGroup[]; total: number; active?: string; onPick: (key: string) => void }) {
  const items = useMemo<Item[]>(() => groups.flatMap((g) => [{ type: 'head', g } as Item, ...g.decks.map((r) => ({ type: 'row', r }) as Item)]), [groups]);
  const heads = useMemo(() => items.flatMap((it, i) => (it.type === 'head' ? [i] : [])), [items]);
  const keys = useMemo(() => items.flatMap((it) => (it.type === 'row' ? [it.r.key] : [])), [items]);
  const index = useMemo(() => new Map(items.flatMap((it, i) => (it.type === 'row' ? [[it.r.key, i] as const] : []))), [items]);
  const activeKey = active && index.has(active) ? active : groups.flatMap((g) => g.decks).find((r) => active && r.slugs.includes(active))?.key;

  const scrollRef = useRef<HTMLElement | null>(null);
  const stickyRef = useRef(0);
  const rangeExtractor = useCallback(
    (range: Range) => {
      stickyRef.current = [...heads].reverse().find((i) => range.startIndex >= i) ?? 0;
      return [...new Set([stickyRef.current, ...defaultRangeExtractor(range)])].sort((a, b) => a - b);
    },
    [heads],
  );
  const virt = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: (i) => (items[i]?.type === 'head' ? 36 : 57),
    overscan: 12,
    rangeExtractor,
    getItemKey: (i) => (items[i].type === 'head' ? `h:${(items[i] as { g: DeckGroup }).g.key}` : (items[i] as { r: RecipeOut }).r.key),
  });
  const reveal = useCallback((key: string) => {
    const i = index.get(key);
    if (i != null) virt.scrollToIndex(i, { align: 'auto' });
  }, [index, virt]);
  const { navRef, tabKey, setFocusKey, onKeyDown } = useRovingFocus(keys, activeKey, 'data-recipe', reveal);
  const setRefs = useCallback((el: HTMLElement | null) => {
    scrollRef.current = el;
    (navRef as { current: HTMLElement | null }).current = el;
  }, [navRef]);

  if (!total) return <EmptyNote title="No recipes match">Clear the search, show more of what you own, or pick more kinds, deck types or sets.</EmptyNote>;
  return (
    <nav ref={setRefs} aria-label="Deck recipes" onKeyDown={onKeyDown} className="h-full min-h-0 overflow-y-auto overscroll-contain px-4 pb-6 [scrollbar-gutter:stable]">
      <div className="relative w-full" style={{ height: virt.getTotalSize() }}>
        {virt.getVirtualItems().map((vi) => {
          const it = items[vi.index];
          const sticky = it.type === 'head' && stickyRef.current === vi.index;
          return (
            <div
              key={vi.key}
              data-index={vi.index}
              ref={virt.measureElement}
              className={sticky ? 'sticky top-0 z-10' : 'absolute inset-x-0 top-0'}
              style={sticky ? undefined : { transform: `translateY(${vi.start}px)` }}
            >
              {it.type === 'head' ? (
                <h2 className="flex items-baseline gap-2 border-b border-rule bg-paper pb-1 pt-3 text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">
                  <span className="min-w-0 truncate">{it.g.label}</span>
                  <span className="ml-auto tabular normal-case tracking-normal">{fmtCount(it.g.decks.length, 'recipe')}{it.g.ready ? ` · ${fmtInt(it.g.ready)} ready` : ''}</span>
                </h2>
              ) : (
                <RecipeRow r={it.r} active={it.r.key === activeKey} tabbable={it.r.key === tabKey} onFocus={() => setFocusKey(it.r.key)} onPick={() => onPick(it.r.key)} />
              )}
            </div>
          );
        })}
      </div>
    </nav>
  );
}

/** The kind of recipe, printed like a guide's product code: hairline, no fill, never amber. */
export function KindMark({ kind }: { kind: RecipeOut['kind'] }) {
  return (
    <span className="shrink-0 rounded-xs border border-rule px-1 text-2xs leading-[1.15rem] voice-condensed font-medium uppercase tracking-[0.08em] text-ink-muted">
      {KIND_LABEL[kind]}
    </span>
  );
}

/** What you own of it: built copies in accent ink, loose / not built in ink, not owned muted. */
function OwnMark({ r }: { r: Pick<RecipeOut, 'ownership' | 'built' | 'loose' | 'kind'> }) {
  const tone = r.ownership === 'built' ? 'text-accent-ink' : r.ownership === 'loose' ? 'text-ink' : 'text-ink-muted';
  return <span className={`shrink-0 text-xs voice-condensed uppercase tracking-[0.06em] ${tone}`}>{ownershipLabel(r)}</span>;
}

function RecipeRow({ r, active, tabbable, onFocus, onPick }: { r: RecipeOut; active: boolean; tabbable: boolean; onFocus: () => void; onPick: () => void }) {
  const cover = coverage(r);
  const unowned = r.ownership === 'none';
  return (
    <button
      type="button"
      data-recipe={r.key}
      tabIndex={tabbable ? 0 : -1}
      onFocus={onFocus}
      onClick={onPick}
      aria-current={active ? 'true' : undefined}
      className={`ruled flex w-full cursor-pointer items-center gap-3 px-1 py-2 text-left transition-colors ease-guide hover:bg-paper-sunk ${active ? 'highlighter' : ''}`}
    >
      {r.image_uri ? (
        <img src={crop(r.image_uri)} alt="" loading="lazy" decoding="async" className={`size-10 shrink-0 rounded-xs object-cover ${unowned ? 'opacity-55 grayscale' : ''}`} />
      ) : (
        <span aria-hidden className="size-10 shrink-0 rounded-xs border border-rule bg-paper-sunk" />
      )}
      <span className="flex min-w-0 flex-1 flex-col">
        <span className={`truncate text-md voice-semi font-medium ${unowned ? 'text-ink-muted' : 'text-ink'}`}>{r.name}</span>
        <span className="flex min-w-0 items-baseline gap-1.5">
          <KindMark kind={r.kind} />
          <OwnMark r={r} />
          <span className="truncate text-xs tabular text-ink-muted">
            {[r.kind !== 'jumpstart' && r.deck_type, r.set_code?.toUpperCase(), r.released?.slice(0, 4)].filter(Boolean).join(' · ')}
          </span>
        </span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-0.5 text-xs tabular">
        {r.read ? <span className="text-ink">{fmtUsd(r.value_usd)}</span> : <span className="text-ink-muted" title="Open it to read its card list">not read</span>}
        {cover && <span className={r.status === 'far' ? 'text-ink-muted' : 'voice-semi text-accent-ink'}>{cover}</span>}
      </span>
    </button>
  );
}

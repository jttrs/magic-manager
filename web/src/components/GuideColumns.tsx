import { Group, Panel, Separator, useDefaultLayout } from 'react-resizable-panels';
import { useState, type ReactNode } from 'react';
import { useMediaQuery } from '../app/useMediaQuery';

export type Column = { id: string; title: string; count: number; body: ReactNode; legend?: ReactNode };

/**
 * The guide sheet split into horizontal, resizable columns. Only `visible` ids
 * render; widths persist per visible-set. Dividers are keyboard-operable
 * separators (WAI-ARIA window splitter, via react-resizable-panels).
 */
export function GuideColumns({ columns, visible, onHide, storageKey }: { columns: Column[]; visible: string[]; onHide: (id: string) => void; storageKey: string }) {
  const narrow = useMediaQuery('(max-width: 47.99rem)');
  const [tab, setTab] = useState<string | null>(null);
  const visibleSet = new Set(visible);
  const shown = columns.filter((c) => visibleSet.has(c.id));
  const ids = shown.map((c) => c.id);
  const layout = useDefaultLayout({ id: `${storageKey}:${ids.join('+')}`, panelIds: ids, storage: localStorage });

  if (narrow && shown.length) {
    // Phones: one column at a time, chosen from a tab strip of the visible columns.
    const active = shown.find((c) => c.id === tab) ?? shown[0];
    return (
      <div className="flex h-[calc(100dvh-10rem)] min-h-0 flex-col">
        <div role="tablist" aria-label="Columns" className="mx-3 flex gap-1 border-b-2 border-rule-strong">
          {shown.map((c) => (
            <button
              key={c.id}
              role="tab"
              type="button"
              aria-selected={c.id === active.id}
              aria-controls={`tabpanel-${c.id}`}
              onClick={() => setTab(c.id)}
              className="min-w-0 flex-1 cursor-pointer truncate rounded-t-sm px-2 pb-1 pt-1.5 text-md voice-condensed font-bold uppercase text-ink-muted aria-selected:bg-paper-sunk aria-selected:text-ink"
            >
              {c.title} <span className="font-regular tabular">{c.count}</span>
            </button>
          ))}
        </div>
        <div role="tabpanel" id={`tabpanel-${active.id}`} aria-label={active.title} className="flex min-h-0 flex-1 flex-col">
          {active.legend && <div className="mx-4 pt-1.5">{active.legend}</div>}
          <div className="min-h-0 flex-1">{active.body}</div>
        </div>
      </div>
    );
  }

  if (!shown.length) {
    return <p className="p-6 text-md text-ink-muted">All columns are hidden. Turn one back on in the sidebar.</p>;
  }
  return (
    <Group orientation="horizontal" className="h-full min-h-0" defaultLayout={layout.defaultLayout} onLayoutChanged={layout.onLayoutChanged}>
      {shown.map((c, i) => (
        <PanelFrag key={c.id} col={c} first={i === 0} onHide={onHide} canHide={shown.length > 1} />
      ))}
    </Group>
  );
}

function PanelFrag({ col, first, onHide, canHide }: { col: Column; first: boolean; onHide: (id: string) => void; canHide: boolean }) {
  return (
    <>
      {!first && (
        <Separator aria-label="Resize columns" className="group relative w-4 shrink-0 cursor-col-resize outline-none">
          <span className="absolute inset-y-2 left-1/2 w-px -translate-x-1/2 bg-rule-strong/40 transition-colors ease-guide group-hover:bg-rule-strong group-focus-visible:bg-focus group-data-[separator=active]:bg-focus" />
          <span
            aria-hidden="true"
            className="absolute left-1/2 top-1/2 grid h-12 w-3 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-pill border border-rule-strong bg-paper text-2xs leading-none text-ink-muted transition-colors ease-guide group-hover:border-accent group-hover:bg-highlight-solid group-hover:text-on-accent group-focus-visible:border-focus group-focus-visible:bg-highlight-solid group-focus-visible:text-on-accent group-data-[separator=active]:bg-highlight-solid"
          >
            ⋮
          </span>
        </Separator>
      )}
      <Panel id={col.id} minSize="18" className="flex min-w-0 flex-col">
        <section aria-labelledby={`col-${col.id}`} className="flex h-full min-h-0 flex-col">
          <header className="mx-4 flex items-baseline gap-3 border-b-2 border-rule-strong pb-1 pt-2">
            <h2 id={`col-${col.id}`} className="min-w-0 truncate text-2xl voice-condensed font-bold uppercase leading-none text-ink">
              {col.title}
              <span className="font-regular text-ink-muted"> · <span className="tabular">{col.count}</span></span>
            </h2>
            {canHide && (
              <button
                type="button"
                onClick={() => onHide(col.id)}
                aria-label={`Hide ${col.title} column`}
                className="ml-auto grid h-7 w-7 shrink-0 cursor-pointer place-items-center rounded-sm text-lg leading-none text-ink-muted transition-colors ease-guide hover:bg-paper-sunk hover:text-ink"
              >
                ×
              </button>
            )}
          </header>
          {col.legend && <div className="mx-4 pt-1.5">{col.legend}</div>}
          <div className="min-h-0 flex-1">{col.body}</div>
        </section>
      </Panel>
    </>
  );
}

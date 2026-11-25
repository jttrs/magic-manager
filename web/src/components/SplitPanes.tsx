import type { ReactNode } from 'react';
import { Group, Panel, Separator, useDefaultLayout } from 'react-resizable-panels';

/** List | inspector, divider-resizable; the split is remembered per `id`. */
export function SplitPanes({ id, list, inspector, label, defaults = [34, 66], detailId = 'detail' }: { id: string; list: ReactNode; inspector: ReactNode; label: string; defaults?: [number, number]; detailId?: string }) {
  const layout = useDefaultLayout({ id, panelIds: ['list', detailId], storage: localStorage });
  return (
    <Group orientation="horizontal" className="h-full min-h-0" defaultLayout={layout.defaultLayout ?? { list: defaults[0], [detailId]: defaults[1] }} onLayoutChanged={layout.onLayoutChanged}>
      <Panel id="list" minSize="22" className="flex min-w-0 flex-col">{list}</Panel>
      <Separator aria-label={label} className="group relative w-4 shrink-0 cursor-col-resize outline-none">
        <span className="absolute inset-y-2 left-1/2 w-px -translate-x-1/2 bg-rule-strong/40 transition-colors ease-guide group-hover:bg-rule-strong group-focus-visible:bg-focus group-data-[separator=active]:bg-focus" />
        <span aria-hidden="true" className="absolute left-1/2 top-1/2 grid h-3 w-5 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-sm border border-accent bg-paper text-accent-ink opacity-0 transition-opacity ease-guide group-hover:opacity-100 group-focus-visible:opacity-100 group-data-[separator=active]:opacity-100">
          <svg viewBox="0 0 16 8" className="h-2 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 1 2 4l3 3M11 1l3 3-3 3" />
          </svg>
        </span>
      </Separator>
      <Panel id={detailId} minSize="40" className="flex min-w-0 flex-col">{inspector}</Panel>
    </Group>
  );
}

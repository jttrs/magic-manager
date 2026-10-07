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
        <span aria-hidden="true" className="absolute left-1/2 top-1/2 grid h-12 w-3 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-pill border border-rule-strong bg-paper text-2xs leading-none text-ink-muted transition-colors ease-guide group-hover:border-accent group-hover:bg-highlight-solid group-hover:text-on-accent group-focus-visible:bg-highlight-solid group-focus-visible:text-on-accent">⋮</span>
      </Separator>
      <Panel id={detailId} minSize="40" className="flex min-w-0 flex-col">{inspector}</Panel>
    </Group>
  );
}

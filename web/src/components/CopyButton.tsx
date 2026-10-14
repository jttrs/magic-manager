import { type ComponentType, type ReactNode, type SVGProps } from 'react';
import { Button } from './Button';
import { useCopy, type GetText } from './useCopy';

/** The copy result. Always mounted (a live region must exist before it
 *  changes) but takes no space while empty, so buttons sit close together. */
const Status = ({ text, className = 'text-xs text-on-chrome-muted' }: { text: string; className?: string }) => (
  <span aria-live="polite" className={text ? className : 'sr-only'}>{text}</span>
);

/** Copies text to the clipboard and announces the result politely. */
export function CopyButton({ label, getText, emphasis = 'quiet', tone = 'chrome' }: { label: string; getText: GetText; emphasis?: 'primary' | 'quiet'; tone?: 'chrome' | 'paper' }) {
  const { status, busy, copy } = useCopy();
  return (
    <div className="flex flex-col gap-1">
      <Button tone={tone} emphasis={emphasis} onClick={() => copy(label, getText)} disabled={busy != null} className="w-full">{busy ? 'Building list…' : label}</Button>
      <Status text={status} />
    </div>
  );
}

export type CopyTarget = { id: string; name: string; Mark: ComponentType<SVGProps<SVGSVGElement>>; getText: GetText; note?: string };

/** A label line (what will be copied) over a compact row of icon-only store
 *  marks; each copies that store's list and shows a check when done. The
 *  copy result briefly takes the label line's place, so nothing below moves. */
export function CopyTargets({ targets, lead }: { targets: readonly CopyTarget[]; lead?: ReactNode }) {
  const { status, busy, done, copy } = useCopy();
  return (
    <div className="flex flex-col gap-1.5">
      {lead != null && (
        <>
          {!status && <span className="text-sm voice-semi tabular text-on-chrome-muted">{lead}</span>}
          <Status text={status} className="text-sm voice-semi text-on-chrome" />
        </>
      )}
      {/* Names ride beside the marks only when the strip is wide enough for all of them. */}
      <div className="@container">
        <div className="flex w-full divide-x divide-chrome-line overflow-hidden rounded-sm border border-chrome-line">
          {targets.map(({ id, name, Mark, getText, note }) => {
            const state = busy === id ? 'busy' : done === id ? 'done' : 'idle';
            return (
              <button
                key={id}
                type="button"
                onClick={() => copy(id, getText, note)}
                disabled={busy != null}
                aria-label={`Copy ${name} list`}
                title={`Copy ${name} list`}
                data-state={state}
                className="group relative flex h-8 min-w-0 flex-auto cursor-pointer items-center justify-center gap-1.5 px-2 text-accent transition-colors duration-200 ease-guide hover:bg-chrome focus-visible:z-10 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus disabled:cursor-wait"
              >
                {state === 'done' ? (
                  <svg viewBox="0 0 16 16" aria-hidden="true" className="size-4">
                    <path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <Mark className="size-[1.125rem] shrink-0 group-data-[state=busy]:animate-pulse group-disabled:group-data-[state=idle]:opacity-45" />
                )}
                <span className="hidden truncate text-xs voice-condensed font-medium uppercase tracking-[0.06em] text-on-chrome @[21.5rem]:inline">{name}</span>
              </button>
            );
          })}
        </div>
      </div>
      {lead == null && <Status text={status} />}
    </div>
  );
}

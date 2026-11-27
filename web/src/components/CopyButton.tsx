import { Popover } from 'radix-ui';
import { useState, type ComponentType, type SVGProps } from 'react';
import { Button } from './Button';
import { CheckMark } from './icons/marks';
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

/** A compact row of icon-only store marks; each copies that store's list and
 *  shows a check when done. The result appears in a small bubble anchored on
 *  the clicked mark (and is announced politely); `describe` says what was
 *  copied ("14,254 cards · ≈ $185,299 at market"), read when the copy starts. */
export function CopyTargets({ targets, describe }: { targets: readonly CopyTarget[]; describe?: () => string }) {
  const { status, failed, busy, done, copy } = useCopy();
  const [last, setLast] = useState<{ id: string; what: string } | null>(null);
  const click = (id: string, name: string, getText: GetText, note?: string) => {
    // Keep the target's note (e.g. what Card Kingdom's list can't carry) beside the description.
    setLast({ id, what: describe ? `Copied ${describe()} for ${name}${note ? `. ${note}` : ''}` : '' });
    void copy(id, getText, note);
  };
  return (
    <div className="flex flex-col gap-1.5">
      {/* Names ride beside the marks only when the strip is wide enough for all of them. */}
      <div className="@container">
        <div className="flex w-full divide-x divide-chrome-line overflow-hidden rounded-sm border border-chrome-line">
          {targets.map(({ id, name, Mark, getText, note }) => {
            const state = busy === id ? 'busy' : done === id ? 'done' : 'idle';
            const open = last?.id === id && !!status && busy == null;
            const text = !failed && last?.what ? last.what : status;
            return (
              <Popover.Root key={id} open={open} onOpenChange={(o) => !o && setLast(null)}>
                <Popover.Anchor asChild>
                  <button
                    type="button"
                    onClick={() => click(id, name, getText, note)}
                    disabled={busy != null}
                    aria-label={`Copy ${name} list`}
                    title={`Copy ${name} list`}
                    data-state={state}
                    className="group relative flex h-8 min-w-0 flex-auto cursor-pointer items-center justify-center gap-1.5 px-2 text-accent transition-colors duration-200 ease-guide hover:bg-chrome focus-visible:z-10 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus disabled:cursor-wait"
                  >
                    {state === 'done' ? (
                      <CheckMark className="size-icon-sm" />
                    ) : (
                      <Mark className="size-icon-md shrink-0 group-data-[state=busy]:animate-pulse group-disabled:group-data-[state=idle]:opacity-45" />
                    )}
                    <span className="hidden truncate text-xs voice-condensed font-medium uppercase tracking-caps text-on-chrome @[21.5rem]:inline">{name}</span>
                  </button>
                </Popover.Anchor>
                <Popover.Portal>
                  <Popover.Content
                    side="top"
                    sideOffset={6}
                    collisionPadding={12}
                    onOpenAutoFocus={(e) => e.preventDefault()}
                    onCloseAutoFocus={(e) => e.preventDefault()}
                    className={`z-50 max-w-[16rem] rounded-sm border bg-chrome-raised px-2.5 py-1.5 text-sm leading-snug text-on-chrome shadow-popover focus:outline-none ${failed ? 'border-danger' : 'border-chrome-line'}`}
                  >
                    {text}
                  </Popover.Content>
                </Popover.Portal>
              </Popover.Root>
            );
          })}
        </div>
      </div>
      <Status text={status} className="sr-only" />
    </div>
  );
}

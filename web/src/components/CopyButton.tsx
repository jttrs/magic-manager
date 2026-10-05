import { useState, type ComponentType, type ReactNode, type SVGProps } from 'react';
import { Button } from './Button';

type GetText = () => string | Promise<string>;

/** Clipboard copy with a polite status line shared by one or more buttons. */
function useCopy() {
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  async function copy(id: string, getText: GetText, note?: string) {
    setBusy(id);
    let text = '';
    try {
      text = await getText();
    } catch {
      setStatus('Couldn’t build the list. Check that `uv run mm serve` is running, then try again.');
      return;
    } finally {
      setBusy(null);
    }
    if (!text) {
      setStatus('Nothing to copy');
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      const n = text.trimEnd().split('\n').length;
      setStatus(`Copied ${n} line${n === 1 ? '' : 's'}${note ? ` — ${note}` : ''}`);
      setDone(id);
      window.setTimeout(() => setDone((d) => (d === id ? null : d)), 1600);
    } catch {
      setStatus('Clipboard blocked — allow clipboard access and try again');
    }
    window.setTimeout(() => setStatus(''), note ? 6000 : 2400);
  }
  return { status, busy, done, copy };
}

const Status = ({ text }: { text: string }) => <span aria-live="polite" className="min-h-4 text-xs text-on-chrome-muted">{text}</span>;

/** Copies text to the clipboard and announces the result politely. */
export function CopyButton({ label, getText, emphasis = 'quiet' }: { label: string; getText: GetText; emphasis?: 'primary' | 'quiet' }) {
  const { status, busy, copy } = useCopy();
  return (
    <div className="flex flex-col gap-1">
      <Button emphasis={emphasis} onClick={() => copy(label, getText)} disabled={busy != null} className="w-full">{busy ? 'Building list…' : label}</Button>
      <Status text={status} />
    </div>
  );
}

export type CopyTarget = { id: string; name: string; Mark: ComponentType<SVGProps<SVGSVGElement>>; getText: GetText; note?: string };

/** A label line (what will be copied) over a compact row of icon-only store
 *  marks; each copies that store's list and shows a check when done. */
export function CopyTargets({ targets, lead }: { targets: readonly CopyTarget[]; lead?: ReactNode }) {
  const { status, busy, done, copy } = useCopy();
  return (
    <div className="flex flex-col gap-1.5">
      {lead && <span className="text-sm voice-semi tabular text-on-chrome-muted">{lead}</span>}
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
      <Status text={status} />
    </div>
  );
}

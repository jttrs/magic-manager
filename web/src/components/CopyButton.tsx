import { useState } from 'react';
import { Button } from './Button';

type GetText = () => string | Promise<string>;

/** Clipboard copy with a polite status line shared by one or more buttons. */
function useCopy() {
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
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
    } catch {
      setStatus('Clipboard blocked — allow clipboard access and try again');
    }
    window.setTimeout(() => setStatus(''), note ? 6000 : 2400);
  }
  return { status, busy, copy };
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

export type CopyTarget = { id: string; name: string; icon: string; getText: GetText; note?: string };

/** One row of store marks; each copies that store's paste-ready list. */
export function CopyTargets({ targets }: { targets: readonly CopyTarget[] }) {
  const { status, busy, copy } = useCopy();
  return (
    <div className="flex flex-col gap-1">
      <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${targets.length}, minmax(0, 1fr))` }}>
        {targets.map((t) => (
          <Button
            key={t.id}
            onClick={() => copy(t.id, t.getText, t.note)}
            disabled={busy != null}
            aria-label={`Copy ${t.name} list`}
            title={`Copy ${t.name} list`}
            className="flex-col !gap-1 px-1 py-2"
          >
            <img src={t.icon} alt="" width={20} height={20} className="size-5 rounded-xs" />
            <span className="text-xs leading-tight">{busy === t.id ? 'Building…' : t.name}</span>
          </Button>
        ))}
      </div>
      <Status text={status} />
    </div>
  );
}

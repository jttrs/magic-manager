import { useState } from 'react';
import { Button } from './Button';

/** Copies text to the clipboard and announces the result politely. */
export function CopyButton({ label, getText, emphasis = 'quiet' }: { label: string; getText: () => string | Promise<string>; emphasis?: 'primary' | 'quiet' }) {
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  async function copy() {
    setBusy(true);
    let text = '';
    try {
      text = await getText();
    } catch {
      setStatus('Couldn’t build the list. Check that `uv run mm serve` is running, then try again.');
      return;
    } finally {
      setBusy(false);
    }
    if (!text) {
      setStatus('Nothing to copy');
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      const n = text.split('\n').length;
      setStatus(`Copied ${n} line${n === 1 ? '' : 's'}`);
    } catch {
      setStatus('Clipboard blocked — allow clipboard access and try again');
    }
    window.setTimeout(() => setStatus(''), 2400);
  }
  return (
    <div className="flex flex-col gap-1">
      <Button emphasis={emphasis} onClick={copy} disabled={busy} className="w-full">{busy ? 'Building list…' : label}</Button>
      <span aria-live="polite" className="min-h-4 text-xs text-on-chrome-muted">{status}</span>
    </div>
  );
}

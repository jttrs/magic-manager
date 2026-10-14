import { useState } from 'react';

export type GetText = () => string | Promise<string>;

/** Clipboard copy with a polite status line shared by one or more buttons. */
export function useCopy() {
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


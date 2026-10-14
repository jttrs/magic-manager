import { useEffect, useRef, useState } from 'react';

export type GetText = () => string | Promise<string>;

/** Clipboard copy with a polite status line shared by one or more buttons.
 *  `failed` is true while the status line reports a failure; every outcome's
 *  status clears itself (one timer, so a newer copy cancels an older clear). */
export function useCopy() {
  const [status, setStatus] = useState('');
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const clear = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(clear.current), []);
  function report(text: string, isFailure: boolean, ms: number) {
    setStatus(text);
    setFailed(isFailure);
    window.clearTimeout(clear.current);
    clear.current = window.setTimeout(() => {
      setStatus('');
      setFailed(false);
    }, ms);
  }
  async function copy(id: string, getText: GetText, note?: string) {
    setBusy(id);
    let text = '';
    try {
      text = await getText();
    } catch {
      report('Couldn’t build the list. Check that `uv run mm serve` is running, then try again.', true, 6000);
      return;
    } finally {
      setBusy(null);
    }
    if (!text) {
      report('Nothing to copy', true, 2400);
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      const n = text.trimEnd().split('\n').length;
      report(`Copied ${n} line${n === 1 ? '' : 's'}${note ? ` — ${note}` : ''}`, false, note ? 6000 : 2400);
      setDone(id);
      window.setTimeout(() => setDone((d) => (d === id ? null : d)), 1600);
    } catch {
      report('Clipboard blocked — allow clipboard access and try again', true, 2400);
    }
  }
  return { status, failed, busy, done, copy };
}

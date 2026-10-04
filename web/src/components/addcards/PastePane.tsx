import { useState } from 'react';
import { unwrap } from '../../app/queries';
import { ingestResolve, type ResolveOut } from '../../core/api';
import { Button } from '../Button';

const FORMATS = [
  { value: 'auto', label: 'Detect' },
  { value: 'moxfield', label: 'Moxfield / ManaPool / Arena' },
  { value: 'tcgplayer', label: 'TCGplayer' },
  { value: 'names', label: 'Names only' },
] as const;

const EXAMPLE = '4 Lightning Bolt (M10) 146\n1 Sol Ring [CMM] 410\n2 Cloud, Ex-SOLDIER *F*\n1 Counterspell';

/** Paste any list; the server reads every line and resolves it to printings. */
export function PastePane({ text, onText, onResolved }: { text: string; onText: (t: string) => void; onResolved: (r: ResolveOut) => void }) {
  const [format, setFormat] = useState<(typeof FORMATS)[number]['value']>('auto');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function read() {
    if (!text.trim()) {
      setError('Paste at least one line, like “4 Lightning Bolt”.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      onResolved(unwrap(await ingestResolve({ body: { text, format } })));
    } catch (e) {
      setError(`Couldn’t read the list: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <label className="flex min-h-0 flex-1 flex-col gap-1.5 text-sm voice-semi text-ink-muted">
        Card list
        <textarea
          autoFocus
          value={text}
          onChange={(e) => onText(e.target.value)}
          placeholder={EXAMPLE}
          spellCheck={false}
          className="min-h-56 flex-1 resize-none rounded-sm border border-rule-strong bg-paper-raised p-3 text-sm tabular leading-relaxed text-ink placeholder:text-ink-muted focus-visible:border-accent"
        />
      </label>
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1.5 text-sm voice-semi text-ink-muted">
          Format
          <select value={format} onChange={(e) => setFormat(e.target.value as typeof format)} className="h-9 cursor-pointer rounded-sm border border-rule bg-paper-raised px-2 text-sm text-ink focus-visible:border-accent">
            {FORMATS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
        </label>
        <Button tone="paper" emphasis="primary" onClick={read} disabled={busy} className="ml-auto">{busy ? 'Reading…' : 'Read list'}</Button>
      </div>
      <p role="alert" className="min-h-4 text-sm text-danger">{error}</p>
    </div>
  );
}

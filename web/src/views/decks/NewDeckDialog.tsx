import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Dialog, ToggleGroup } from 'radix-ui';
import { useState, type FormEvent, type ReactNode } from 'react';
import { unwrap } from '../../app/queries';
import { Button } from '../../components/Button';
import { deckCreate } from '../../core/api';

const FORMATS = [
  { value: 'commander', label: 'Commander' },
  { value: 'brawl', label: 'Brawl' },
  { value: 'standard', label: 'Standard' },
  { value: 'modern', label: 'Modern' },
  { value: 'pauper', label: 'Pauper' },
] as const;

/** Start an empty deck: name + format, then straight into the editor. */
export function NewDeckDialog({ trigger }: { trigger: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [format, setFormat] = useState<string>('commander');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const qc = useQueryClient();
  const navigate = useNavigate();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = unwrap(await deckCreate({ body: { name: name.trim(), format } }));
      await qc.invalidateQueries({ queryKey: ['decks'] });
      setOpen(false);
      setName('');
      navigate({ to: '/decks/$slug/edit', params: { slug: r.slug } });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !busy && setOpen(o)}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        <Dialog.Content className="paper-grain fixed left-1/2 top-1/2 z-50 w-[min(28rem,calc(100vw-1.5rem))] -translate-x-1/2 -translate-y-1/2 rounded-sm bg-paper p-5 text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none">
          <form onSubmit={submit} className="flex flex-col gap-4">
            <Dialog.Title className="border-b-2 border-rule-strong pb-2 text-2xl voice-condensed font-bold leading-none">New deck</Dialog.Title>
            <Dialog.Description className="sr-only">Name your deck and pick its format; you’ll add cards in the editor.</Dialog.Description>
            <label className="flex flex-col gap-1.5 text-sm voice-semi text-ink-muted">
              Deck name
              <input
                autoFocus
                required
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Tifa’s Monk Combo"
                autoComplete="off"
                className="h-10 rounded-sm border border-rule-strong bg-paper-raised px-3 text-md text-ink placeholder:text-ink-muted focus-visible:border-accent"
              />
            </label>
            <div className="flex flex-col gap-1.5">
              <span id="new-deck-format" className="text-sm voice-semi text-ink-muted">Format</span>
              <ToggleGroup.Root
                type="single"
                aria-labelledby="new-deck-format"
                value={format}
                onValueChange={(v) => v && setFormat(v)}
                className="flex flex-wrap gap-px overflow-hidden rounded-sm border border-rule-strong bg-rule"
              >
                {FORMATS.map((f) => (
                  <ToggleGroup.Item
                    key={f.value}
                    value={f.value}
                    className="min-h-9 flex-1 cursor-pointer bg-paper-raised px-2.5 text-sm voice-semi text-ink transition-colors ease-guide hover:bg-paper-sunk data-[state=on]:bg-accent data-[state=on]:text-on-accent"
                  >
                    {f.label}
                  </ToggleGroup.Item>
                ))}
              </ToggleGroup.Root>
            </div>
            {error && <p role="alert" className="text-sm text-danger">{error}</p>}
            <div className="flex justify-end gap-2">
              <Dialog.Close asChild>
                <Button tone="paper" disabled={busy}>Cancel</Button>
              </Dialog.Close>
              <Button type="submit" emphasis="primary" disabled={busy || !name.trim()}>{busy ? 'Creating…' : 'Create and edit'}</Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

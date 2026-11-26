import { AlertDialog } from 'radix-ui';
import { dialogContentClass, dialogOverlayClass, dialogTitleClass } from './controls/surfaces';
import { useState, type ReactNode } from 'react';
import { Button } from './Button';

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
  /** Names the action, e.g. "Build deck". */
  confirmLabel: string;
  onConfirm: () => Promise<void>;
  /** An optional second commit (e.g. "Build with 3 missing"). */
  alternate?: { label: string; onConfirm: () => Promise<void> };
  /** Confirm can't succeed (the body says why). */
  confirmDisabled?: boolean;
};

/** Confirms a physical-collection change (pledges move). The commit is the one
 *  filled amber button; failures stay in the dialog with the engine's message. */
export function ConfirmDialog({ open, onOpenChange, title, children, confirmLabel, onConfirm, alternate, confirmDisabled }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = (fn: () => Promise<void>) => async () => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onOpenChange(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <AlertDialog.Root open={open} onOpenChange={(o) => { if (!busy) { setError(null); onOpenChange(o); } }}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className={dialogOverlayClass} />
        <AlertDialog.Content className={dialogContentClass('sm')}>
          <AlertDialog.Title className={dialogTitleClass}>{title}</AlertDialog.Title>
          <AlertDialog.Description asChild>
            <div className="flex flex-col gap-3 text-md leading-relaxed">{children}</div>
          </AlertDialog.Description>
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
            <AlertDialog.Cancel asChild>
              <Button tone="paper" disabled={busy}>Cancel</Button>
            </AlertDialog.Cancel>
            {alternate && <Button tone="paper" disabled={busy} onClick={run(alternate.onConfirm)}>{alternate.label}</Button>}
            <Button emphasis="primary" disabled={busy || confirmDisabled} onClick={run(onConfirm)}>{busy ? 'Working…' : confirmLabel}</Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}

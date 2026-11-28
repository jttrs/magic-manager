import { Popover } from 'radix-ui';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { fmtUsd } from '../core/format';
import { parseCount } from '../core/checklist';
import { Button } from './Button';
import { IconAction } from './IconAction';
import { CountInput } from './controls/Inputs';
import { menuLabelClass, menuPanelClass } from './controls/surfaces';
import { MinusMark, PlusMark } from './icons/marks';

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The element the popover hangs from (the tally button). */
  anchor: ReactNode;
  finish: 'nonfoil' | 'foil';
  cardName: string;
  owned: number;
  /** Copies already waiting in the draft. */
  pending: number;
  /** Market price of one copy, when known. */
  unitUsd?: number | null;
  /** The absolute amount to add (0 removes it from the draft). */
  onApply: (n: number) => void;
};

const QUICK = [1, 2, 3, 4];

/** How many copies to add of one finish: type, step, or pick 1–4. Enter applies, Esc leaves it as it was. */
export function AmountPicker({ open, onOpenChange, anchor, finish, cardName, owned, pending, unitUsd, onApply }: Props) {
  const [text, setText] = useState('');
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (open) setText(String(pending > 0 ? pending : 1));
  }, [open, pending]);

  const parsed = parseCount(text);
  const n = typeof parsed === 'number' ? parsed : 0;
  const valid = typeof parsed === 'number';
  const apply = (v: number) => {
    onApply(v);
    onOpenChange(false);
  };
  return (
    <Popover.Root open={open} onOpenChange={onOpenChange}>
      <Popover.Anchor asChild>{anchor}</Popover.Anchor>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={4}
          className={`${menuPanelClass} flex w-64 flex-col gap-3 p-3`}
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            ref.current?.focus();
            ref.current?.select();
          }}
        >
          <p className={`${menuLabelClass} truncate !p-0`} title={cardName}>
            {finish === 'foil' ? 'Foil ✦' : 'Nonfoil'} · {cardName}
          </p>
          <div className="flex items-center gap-2">
            <span className="text-sm voice-semi">Add</span>
            <IconAction tone="chrome" label="One fewer" Icon={MinusMark} disabled={n <= 0} onClick={() => setText(String(Math.max(0, n - 1)))} />
            <CountInput
              ref={ref}
              value={text}
              state={valid ? 'ok' : 'invalid'}
              aria-label="Copies to add"
              onChange={(e) => setText(e.target.value)}
              onFocus={(e) => e.currentTarget.select()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && valid && n !== pending) {
                  e.preventDefault();
                  apply(n);
                }
              }}
            />
            <IconAction tone="chrome" label="One more" Icon={PlusMark} onClick={() => setText(String(Math.min(9999, n + 1)))} />
          </div>
          <div className="flex gap-1.5">
            {QUICK.map((q) => (
              <Button key={q} tone="paper" emphasis="quiet" className="flex-1" onClick={() => setText(String(q))}>
                {q}
              </Button>
            ))}
          </div>
          <p className="text-xs tabular text-on-chrome-muted">
            {owned} owned → {owned + n}
            {unitUsd != null && n > 0 ? ` · ${fmtUsd(unitUsd * n)} at market` : ''}
          </p>
          <div className="flex items-center justify-between gap-2">
            {pending > 0 ? (
              <Button tone="chrome" emphasis="link" onClick={() => apply(0)}>
                Remove from draft
              </Button>
            ) : (
              <span />
            )}
            <Button emphasis="primary" disabled={!valid || n === pending} onClick={() => apply(n)}>
              Add {n}
            </Button>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

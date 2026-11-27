import { DropdownMenu, Popover } from 'radix-ui';
import { useState } from 'react';
import type { CopyTarget } from './CopyButton';
import { IconTooltip } from './IconTooltip';
import { iconActionClass } from './iconActionClass';
import { menuItemClass, menuLabelClass, menuPanelClass } from './controls/surfaces';
import { markBadge } from '../core/marks';
import { BuyListMark, CheckMark, CloseMark } from './icons/marks';
import { useCopy } from './useCopy';

/** A choice that changes WHAT gets copied (e.g. Cheapest vs Deck's printings). */
export type CopyListOption<T extends string> = { label: string; value: T; options: readonly { value: T; label: string }[]; onChange: (v: T) => void };

/** ONE icon in the strip's Buy group that copies a bulk list for a store: a menu
 *  headed by what will be copied (`describe`, e.g. "12 marked cards" or "140 missing
 *  cards · ≈ $212"), an optional choice of WHICH list, then one item per destination
 *  — each in that store's own format (`buyListTargets`). The result shows in a small
 *  bubble on the icon and is announced politely. */
export function CopyListMenu<T extends string>({ targets, describe, option, disabledReason, marked }: {
  targets: readonly CopyTarget[];
  describe: () => string;
  option?: CopyListOption<T>;
  /** Why nothing can be copied right now (shown instead of opening the menu). */
  disabledReason?: string;
  /** Cards marked in the view: their count rides the icon, and the menu can clear them. */
  marked?: { count: number; onClear: () => void };
}) {
  const { status, failed, busy, copy } = useCopy();
  const [bubble, setBubble] = useState<string | null>(null);
  const label = 'Copy a list for a store';
  const pick = (t: CopyTarget) => {
    const what = describe();
    setBubble(`Copied ${what} for ${t.name}${t.note ? `. ${t.note}` : ''}`);
    void copy(t.id, t.getText, t.note);
  };
  const text = !failed && bubble ? bubble : status;
  return (
    <Popover.Root open={!!status && busy == null} onOpenChange={(o) => !o && setBubble(null)}>
      <DropdownMenu.Root>
        <Popover.Anchor asChild>
          <span className="inline-flex">
            <IconTooltip label={disabledReason ?? (busy ? 'Building the list…' : label)}>
              <DropdownMenu.Trigger aria-label={label} aria-disabled={disabledReason ? true : undefined} disabled={!!disabledReason || busy != null} className={iconActionClass('paper')}>
                {status && !failed ? <CheckMark className="size-icon-md" /> : <BuyListMark className={`size-icon-md ${busy ? 'animate-pulse' : ''}`} />}
                {marked && marked.count > 0 && (
                  <span aria-hidden="true" className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-pill bg-accent px-1 text-2xs font-bold leading-none tabular text-on-accent">{markBadge(marked.count)}</span>
                )}
              </DropdownMenu.Trigger>
            </IconTooltip>
          </span>
        </Popover.Anchor>
        <DropdownMenu.Portal>
          <DropdownMenu.Content align="end" sideOffset={4} collisionPadding={12} className={`${menuPanelClass} w-[min(20rem,calc(100vw-1.5rem))] py-1`}>
            <DropdownMenu.Label className={menuLabelClass}>Copy {describe()}</DropdownMenu.Label>
            {option && (
              <>
                <DropdownMenu.Separator className="my-1 h-px bg-chrome-line" />
                <DropdownMenu.Label className={menuLabelClass}>{option.label}</DropdownMenu.Label>
                <DropdownMenu.RadioGroup value={option.value} onValueChange={(v) => option.onChange(v as T)}>
                  {option.options.map((o) => (
                    <DropdownMenu.RadioItem key={o.value} value={o.value} onSelect={(e) => e.preventDefault()} className={menuItemClass}>
                      <span aria-hidden="true" className="w-3 text-accent"><DropdownMenu.ItemIndicator><CheckMark className="size-icon-xs" /></DropdownMenu.ItemIndicator></span>
                      {o.label}
                    </DropdownMenu.RadioItem>
                  ))}
                </DropdownMenu.RadioGroup>
              </>
            )}
            <DropdownMenu.Separator className="my-1 h-px bg-chrome-line" />
            <DropdownMenu.Label className={menuLabelClass}>Copy for</DropdownMenu.Label>
            {targets.map((t) => (
              <DropdownMenu.Item key={t.id} onSelect={() => pick(t)} className={menuItemClass}>
                <t.Mark className="size-icon-sm shrink-0 text-accent" />
                <span className="flex min-w-0 flex-col">
                  <span>{t.name}</span>
                  {t.format && <span className="text-xs text-on-chrome-muted">{t.format}</span>}
                </span>
              </DropdownMenu.Item>
            ))}
            {marked && marked.count > 0 && (
              <>
                <DropdownMenu.Separator className="my-1 h-px bg-chrome-line" />
                <DropdownMenu.Item onSelect={marked.onClear} className={menuItemClass}>
                  <CloseMark className="size-icon-sm shrink-0 text-on-chrome-muted" />
                  Clear {marked.count === 1 ? 'the mark' : `all ${marked.count} marks`}
                </DropdownMenu.Item>
              </>
            )}
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
      <Popover.Portal>
        <Popover.Content
          side="bottom"
          align="end"
          sideOffset={6}
          collisionPadding={12}
          onOpenAutoFocus={(e) => e.preventDefault()}
          onCloseAutoFocus={(e) => e.preventDefault()}
          className={`${menuPanelClass} max-w-[16rem] px-2.5 py-1.5 text-sm leading-snug focus:outline-none ${failed ? 'border-danger' : ''}`}
        >
          {text}
        </Popover.Content>
      </Popover.Portal>
      <span aria-live="polite" className="sr-only">{status}</span>
    </Popover.Root>
  );
}

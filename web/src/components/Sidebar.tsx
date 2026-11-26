import { DropdownMenu, ToggleGroup } from 'radix-ui';
import { useId, type ReactNode } from 'react';
import { RailField } from './controls/RailField';
import { TextInput } from './controls/TextField';
import { triggerClass } from './controls/fieldClass';
import { menuItemClass, menuPanelClass } from './controls/surfaces';
import { CaretMark, CheckMark } from './icons/marks';

/** A rail section. Sections add no spacing of their own: the rail (`#view-controls`)
 *  sets ONE gap between every control, and a printed heading adds one fixed space above
 *  it — so the rhythm is the same in every rail. `quiet` keeps the heading for screen
 *  readers only: the rail's search-then-filters order explains itself, so *Find* /
 *  *Show* print no label, while sections that switch to something else do. */
export function SideSection({ title, children, id, quiet = false }: { title: string; children: ReactNode; id?: string; quiet?: boolean }) {
  const own = useId();
  const hid = id ?? own;
  return (
    <section aria-labelledby={hid} className="contents">
      <h2 id={hid} className={quiet ? 'sr-only' : 'pt-2 text-sm voice-condensed uppercase tracking-caps text-on-chrome-muted'}>{title}</h2>
      {children}
    </section>
  );
}

type Opt<T extends string> = { value: T; label: string; disabled?: boolean; title?: string };

const SEGMENTS = 'grid min-h-control pointer-coarse:min-h-control-coarse min-w-0 rounded-sm border border-chrome-line p-0.5';
const SEGMENT =
  'flex min-h-7 min-w-0 cursor-pointer items-center justify-center gap-1.5 rounded-xs px-1.5 text-sm voice-semi text-on-chrome-muted transition-colors ease-guide hover:text-on-chrome ' +
  'disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:text-on-chrome-muted data-[state=on]:bg-accent data-[state=on]:text-on-accent data-[state=on]:hover:text-on-accent';

/** Single-choice segmented control (view type, chase mode). `showLabel` prints the label above it.
 *  `wrap` lays long labels out two to a row so they stay whole in the narrow sidebar. */
export function Segmented<T extends string>({ value, options, onChange, label, showLabel = false, labelExtra, wrap = false }: { value: T; options: Opt<T>[]; onChange: (v: T) => void; label: string; showLabel?: boolean; labelExtra?: ReactNode; wrap?: boolean }) {
  const id = useId();
  const group = (
    <ToggleGroup.Root
      type="single"
      value={value}
      onValueChange={(v) => v && onChange(v as T)}
      {...(showLabel ? { 'aria-labelledby': id } : { 'aria-label': label })}
      className={`${SEGMENTS} ${wrap ? 'grid-cols-2' : 'auto-cols-fr grid-flow-col'}`}
    >
      {options.map((o) => (
        <ToggleGroup.Item key={o.value} value={o.value} disabled={o.disabled} title={o.title} className={SEGMENT}>
          <span className="truncate">{o.label}</span>
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
  return showLabel ? <RailField label={label} labelId={id} extra={labelExtra}>{group}</RailField> : group;
}

/** Segmented look, toggle behavior: each segment switches on/off independently
 *  (e.g. Show: Owned | Missing — both, either, or neither). Optional counts. */
export function SegmentedToggles<T extends string>({ value, options, onChange, label, showLabel = false, labelExtra }: { value: T[]; options: (Opt<T> & { count?: number })[]; onChange: (v: T[]) => void; label: string; showLabel?: boolean; labelExtra?: ReactNode }) {
  const id = useId();
  const group = (
    <ToggleGroup.Root
      type="multiple"
      value={value}
      onValueChange={(v) => onChange(v as T[])}
      {...(showLabel ? { 'aria-labelledby': id } : { 'aria-label': label })}
      className={`${SEGMENTS} auto-cols-fr grid-flow-col gap-0.5`}
    >
      {options.map((o) => (
        <ToggleGroup.Item key={o.value} value={o.value} className={SEGMENT}>
          <span className="truncate">{o.label}</span>
          {o.count != null && <span className="tabular text-xs opacity-75">{o.count}</span>}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
  return showLabel ? <RailField label={label} labelId={id} extra={labelExtra}>{group}</RailField> : group;
}

/** Multi-select chips; "on" chips carry the accent. `showLabel` prints the label above. */
export function ChipToggles<T extends string>({ value, options, onChange, label, showLabel = false }: { value: T[]; options: (Opt<T> & { count?: number })[]; onChange: (v: T[]) => void; label: string; showLabel?: boolean }) {
  const id = useId();
  const group = (
    <ToggleGroup.Root type="multiple" value={value} onValueChange={(v) => onChange(v as T[])} {...(showLabel ? { 'aria-labelledby': id } : { 'aria-label': label })} className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <ToggleGroup.Item
          key={o.value}
          value={o.value}
          className="inline-flex min-h-7 pointer-coarse:min-h-control-coarse cursor-pointer items-center gap-1.5 rounded-pill border border-chrome-line px-2.5 text-xs voice-semi text-on-chrome-muted
                     transition-[color,background-color,border-color] ease-guide hover:border-on-chrome-muted hover:text-on-chrome
                     data-[state=on]:border-accent data-[state=on]:bg-accent data-[state=on]:text-on-accent"
        >
          {o.label}
          {o.count != null && <span className="tabular opacity-75">{o.count}</span>}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
  return showLabel ? <RailField label={label} labelId={id}>{group}</RailField> : group;
}

/** A labelled search box for a rail. */
export function TextField({ label, value, onChange, placeholder, name, labelExtra }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; name: string; labelExtra?: ReactNode }) {
  const id = useId();
  return (
    <RailField label={label} htmlFor={id} extra={labelExtra}>
      <TextInput id={id} name={name} type="search" autoComplete="off" spellCheck={false} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
    </RailField>
  );
}

/** Single choice from a short list: a trigger matching MultiSelect's, opening a
 *  radio menu (Radix DropdownMenu — arrow keys, type-ahead, Escape). Optional counts. */
export function SelectField<T extends string>({ label, value, options, onChange, labelExtra }: { label: string; value: T; options: (Opt<T> & { count?: number })[]; onChange: (v: T) => void; labelExtra?: ReactNode }) {
  const id = useId();
  const current = options.find((o) => o.value === value);
  return (
    <RailField label={label} labelId={`${id}-l`} extra={labelExtra}>
      <DropdownMenu.Root>
        <DropdownMenu.Trigger aria-labelledby={`${id}-l ${id}-s`} className={triggerClass('chrome')}>
          <span id={`${id}-s`} className="min-w-0 flex-1 truncate">{current?.label ?? value}</span>
          <CaretMark className="size-icon-sm shrink-0 text-on-chrome-muted" />
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content align="start" sideOffset={4} collisionPadding={12} className={`${menuPanelClass} w-[max(var(--radix-dropdown-menu-trigger-width),12rem)] py-1`}>
            <DropdownMenu.RadioGroup value={value} onValueChange={(v) => onChange(v as T)}>
              {options.map((o) => (
                <DropdownMenu.RadioItem key={o.value} value={o.value} className={menuItemClass}>
                  <span aria-hidden="true" className="w-3 text-accent">
                    <DropdownMenu.ItemIndicator><CheckMark className="size-icon-xs" /></DropdownMenu.ItemIndicator>
                  </span>
                  <span className="min-w-0 flex-1 truncate">{o.label}</span>
                  {o.count != null && <span className="tabular text-xs text-on-chrome-muted">{o.count}</span>}
                </DropdownMenu.RadioItem>
              ))}
            </DropdownMenu.RadioGroup>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </RailField>
  );
}

/** A calendar day (YYYY-MM-DD), cleared with the field's own clear control. */
export function DateField({ label, value, onChange, name, min, max }: { label: string; value: string | undefined; onChange: (v: string | undefined) => void; name: string; min?: string; max?: string }) {
  const id = useId();
  return (
    <RailField label={label} htmlFor={id}>
      <TextInput id={id} name={name} type="date" value={value ?? ''} min={min} max={max} onChange={(e) => onChange(e.target.value || undefined)} />
    </RailField>
  );
}

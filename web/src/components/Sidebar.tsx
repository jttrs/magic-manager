import { ToggleGroup } from 'radix-ui';
import { useId, type ReactNode } from 'react';

export function SideSection({ title, children, id }: { title: string; children: ReactNode; id?: string }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-2">
      <h2 id={id} className="text-sm voice-condensed uppercase tracking-[0.06em] text-on-chrome-muted">{title}</h2>
      {children}
    </section>
  );
}

type Opt<T extends string> = { value: T; label: string };

/** Single-choice segmented control (view type, chase mode). `showLabel` prints the label above it. */
export function Segmented<T extends string>({ value, options, onChange, label, showLabel = false, labelExtra }: { value: T; options: Opt<T>[]; onChange: (v: T) => void; label: string; showLabel?: boolean; labelExtra?: ReactNode }) {
  const id = useId();
  const group = (
    <ToggleGroup.Root
      type="single"
      value={value}
      onValueChange={(v) => v && onChange(v as T)}
      {...(showLabel ? { 'aria-labelledby': id } : { 'aria-label': label })}
      className="grid min-w-0 auto-cols-fr grid-flow-col rounded-sm border border-chrome-line p-0.5"
    >
      {options.map((o) => (
        <ToggleGroup.Item
          key={o.value}
          value={o.value}
          className="min-h-8 min-w-0 truncate px-1.5 text-sm voice-semi text-on-chrome-muted rounded-xs cursor-pointer transition-colors ease-guide hover:text-on-chrome data-[state=on]:bg-accent data-[state=on]:text-on-accent data-[state=on]:hover:text-on-accent"
        >
          {o.label}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
  if (!showLabel) return group;
  return (
    <div className="flex flex-col gap-1.5">
      <span className="flex items-center gap-1.5">
        <span id={id} className="text-sm voice-semi text-on-chrome-muted">{label}</span>
        {labelExtra}
      </span>
      {group}
    </div>
  );
}

/** Segmented look, toggle behavior: each segment switches on/off independently
 *  (e.g. Show: Owned | Missing — both, either, or neither). Optional counts. */
export function SegmentedToggles<T extends string>({ value, options, onChange, label, showLabel = false }: { value: T[]; options: (Opt<T> & { count?: number })[]; onChange: (v: T[]) => void; label: string; showLabel?: boolean }) {
  const id = useId();
  const group = (
    <ToggleGroup.Root
      type="multiple"
      value={value}
      onValueChange={(v) => onChange(v as T[])}
      {...(showLabel ? { 'aria-labelledby': id } : { 'aria-label': label })}
      className="grid min-w-0 auto-cols-fr grid-flow-col gap-0.5 rounded-sm border border-chrome-line p-0.5"
    >
      {options.map((o) => (
        <ToggleGroup.Item
          key={o.value}
          value={o.value}
          className="flex min-h-8 min-w-0 cursor-pointer items-center justify-center gap-1.5 rounded-xs px-1.5 text-sm voice-semi text-on-chrome-muted transition-colors ease-guide hover:text-on-chrome data-[state=on]:bg-accent data-[state=on]:text-on-accent data-[state=on]:hover:text-on-accent"
        >
          <span className="truncate">{o.label}</span>
          {o.count != null && <span className="tabular text-xs opacity-75">{o.count}</span>}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
  if (!showLabel) return group;
  return (
    <div className="flex flex-col gap-1.5">
      <span id={id} className="text-sm voice-semi text-on-chrome-muted">{label}</span>
      {group}
    </div>
  );
}

/** Multi-select chips; "on" chips carry the highlighter. `showLabel` prints the label above. */
export function ChipToggles<T extends string>({ value, options, onChange, label, showLabel = false }: { value: T[]; options: (Opt<T> & { count?: number })[]; onChange: (v: T[]) => void; label: string; showLabel?: boolean }) {
  const id = useId();
  const group = (
    <ToggleGroup.Root type="multiple" value={value} onValueChange={(v) => onChange(v as T[])} {...(showLabel ? { 'aria-labelledby': id } : { 'aria-label': label })} className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <ToggleGroup.Item
          key={o.value}
          value={o.value}
          className="inline-flex items-center gap-1.5 min-h-7 px-2.5 rounded-pill border border-chrome-line text-xs voice-semi text-on-chrome-muted cursor-pointer
                     transition-[color,background-color,border-color] ease-guide hover:text-on-chrome hover:border-on-chrome-muted
                     data-[state=on]:bg-accent data-[state=on]:border-accent data-[state=on]:text-on-accent"
        >
          {o.label}
          {o.count != null && <span className="tabular opacity-75">{o.count}</span>}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
  if (!showLabel) return group;
  return (
    <div className="flex flex-col gap-1.5">
      <span id={id} className="text-sm voice-semi text-on-chrome-muted">{label}</span>
      {group}
    </div>
  );
}

export function TextField({ label, value, onChange, placeholder, name }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; name: string }) {
  return (
    <label className="flex flex-col gap-1.5 text-sm voice-semi text-on-chrome-muted">
      {label}
      <input
        name={name}
        type="search"
        autoComplete="off"
        spellCheck={false}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="min-h-9 rounded-sm border border-chrome-line bg-chrome-raised px-2.5 text-md text-on-chrome placeholder:text-on-chrome-muted focus-visible:border-accent"
      />
    </label>
  );
}

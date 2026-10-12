import { ToggleGroup } from 'radix-ui';
import { useId, type ReactNode } from 'react';

/** One preference in the Settings dialog: its name and a plain sentence on the
 *  left, the control on the right (stacked on phones). `control` receives the
 *  ids that label and describe it. */
export function SettingsRow({ label, description, control }: {
  label: string;
  description?: ReactNode;
  control: (ids: { labelId: string; descriptionId?: string }) => ReactNode;
}) {
  const id = useId();
  const descriptionId = description ? `${id}-d` : undefined;
  return (
    <div className="flex flex-col gap-2 border-b border-rule py-3 last:border-b-0 sm:flex-row sm:items-center sm:gap-6">
      <div className="min-w-0 flex-1">
        <p id={`${id}-l`} className="text-md font-medium leading-snug">{label}</p>
        {description && <p id={descriptionId} className="mt-0.5 text-sm leading-relaxed text-ink-muted">{description}</p>}
      </div>
      <div className="shrink-0">{control({ labelId: `${id}-l`, descriptionId })}</div>
    </div>
  );
}

type Choice<T extends string> = { value: T; label: string };

/** Single choice for a settings row: the sidebar's segmented shape in paper
 *  tokens (rule-strong border, ink-muted off, amber on). */
export function SettingsChoice<T extends string>({ value, options, onChange, labelId, descriptionId }: {
  value: T;
  options: Choice<T>[];
  onChange: (v: T) => void;
  labelId: string;
  descriptionId?: string;
}) {
  return (
    <ToggleGroup.Root
      type="single"
      value={value}
      onValueChange={(v) => v && onChange(v as T)}
      aria-labelledby={labelId}
      aria-describedby={descriptionId}
      className="grid min-w-0 auto-cols-fr grid-flow-col rounded-sm border border-rule-strong p-0.5 sm:min-w-[15rem]"
    >
      {options.map((o) => (
        <ToggleGroup.Item
          key={o.value}
          value={o.value}
          className="min-h-9 min-w-0 cursor-pointer truncate rounded-xs px-3 text-sm voice-semi text-ink-muted transition-colors ease-guide pointer-coarse:min-h-11 hover:text-ink data-[state=on]:bg-accent data-[state=on]:text-on-accent data-[state=on]:hover:text-on-accent"
        >
          {o.label}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}

/** A ruled section of the Settings dialog. */
export function SettingsGroup({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="flex flex-col">
      <h3 id={id} className="border-b-2 border-rule-strong pb-1 text-md voice-condensed font-bold uppercase tracking-[0.04em]">{title}</h3>
      {children}
    </section>
  );
}

import { Popover } from 'radix-ui';
import { useId, useMemo, useState } from 'react';

type MultiOption = { value: string; label: string; count?: number };

type Props = {
  label: string;
  options: MultiOption[];
  value: string[];
  onChange: (v: string[]) => void;
  /** Noun for the trigger summary, e.g. "families". */
  noun: string;
  placeholder?: string;
};

/**
 * Many-option picker: a compact trigger ("Final Fantasy +2 ▾") opening a
 * searchable checkbox list. DESIGN.md: chip groups stop at 5 options; anything
 * larger uses this, so long lists never take over the sidebar.
 */
export function MultiSelect({ label, options, value, onChange, noun, placeholder = 'Filter…' }: Props) {
  const [q, setQ] = useState('');
  const id = useId();
  const selected = useMemo(() => new Set(value), [value]);
  const shown = useMemo(() => {
    const ql = q.trim().toLowerCase();
    const hits = ql ? options.filter((o) => o.label.toLowerCase().includes(ql) || o.value.toLowerCase().includes(ql)) : options;
    // Selected first so the current scope is always visible at the top.
    return [...hits.filter((o) => selected.has(o.value)), ...hits.filter((o) => !selected.has(o.value))];
  }, [options, q, selected]);

  const first = options.find((o) => selected.has(o.value));
  const summary = !value.length ? `Choose ${noun}…` : value.length === 1 ? first?.label ?? value[0] : `${first?.label ?? value[0]} +${value.length - 1}`;

  const toggle = (v: string) => onChange(selected.has(v) ? value.filter((x) => x !== v) : [...value, v]);

  return (
    <div className="flex flex-col gap-1.5">
      <span id={`${id}-l`} className="text-sm voice-semi text-on-chrome-muted">{label}</span>
      <Popover.Root onOpenChange={(o) => !o && setQ('')}>
        <Popover.Trigger
          aria-labelledby={`${id}-l ${id}-s`}
          className="flex min-h-9 w-full cursor-pointer items-center gap-2 rounded-sm border border-chrome-line bg-chrome-raised px-2.5 text-left text-md text-on-chrome transition-colors ease-guide hover:border-on-chrome-muted data-[state=open]:border-accent"
        >
          <span id={`${id}-s`} className={`min-w-0 flex-1 truncate ${value.length ? '' : 'text-on-chrome-muted'}`}>{summary}</span>
          {value.length > 1 && <span className="tabular text-xs text-on-chrome-muted">{value.length}</span>}
          <span aria-hidden="true" className="text-on-chrome-muted">▾</span>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="start"
            sideOffset={4}
            collisionPadding={12}
            className="z-50 flex max-h-[min(28rem,70dvh)] w-[max(var(--radix-popover-trigger-width),18rem)] flex-col rounded-sm border border-chrome-line bg-chrome-raised text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]"
          >
            <div className="flex flex-col gap-2 border-b border-chrome-line p-2">
              <input
                type="search"
                aria-label={`Filter ${noun}`}
                placeholder={placeholder}
                autoComplete="off"
                spellCheck={false}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="min-h-8 rounded-sm border border-chrome-line bg-chrome px-2 text-sm text-on-chrome placeholder:text-on-chrome-muted focus-visible:border-accent"
              />
              <div className="flex gap-3 text-xs">
                {q && shown.length > 0 && (
                  <button type="button" className="cursor-pointer text-on-chrome-muted underline hover:text-on-chrome" onClick={() => onChange([...new Set([...value, ...shown.map((o) => o.value)])])}>
                    Select shown
                  </button>
                )}
                <button type="button" className="cursor-pointer text-on-chrome-muted underline hover:text-on-chrome" onClick={() => onChange(q ? value.filter((v) => !shown.some((o) => o.value === v)) : [])}>
                  Clear {q ? 'shown' : 'all'}
                </button>
                <span className="ml-auto tabular text-on-chrome-muted">{value.length} selected</span>
              </div>
            </div>
            <fieldset className="min-h-0 overflow-y-auto overscroll-contain py-1">
              <legend className="sr-only">{label}</legend>
              {shown.length === 0 && <p className="px-3 py-2 text-sm text-on-chrome-muted">No {noun} match “{q}”.</p>}
              {shown.map((o) => (
                <label key={o.value} className="flex cursor-pointer items-center gap-2.5 px-3 py-1.5 text-sm hover:bg-chrome-line">
                  <input type="checkbox" checked={selected.has(o.value)} onChange={() => toggle(o.value)} className="h-3.5 w-3.5 shrink-0 accent-[var(--theme-accent)]" />
                  <span className="min-w-0 flex-1 truncate">{o.label}</span>
                  {o.count != null && <span className="tabular text-xs text-on-chrome-muted">{o.count}</span>}
                </label>
              ))}
            </fieldset>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </div>
  );
}

import { Popover } from 'radix-ui';
import { useId, useMemo, useState, type ReactNode } from 'react';

type MultiOption = { value: string; label: string; count?: number; group?: string };

type Props = {
  label: string;
  options: MultiOption[];
  value: string[];
  onChange: (v: string[]) => void;
  /** Noun for the trigger summary, e.g. "families". */
  noun: string;
  placeholder?: string;
  /** Overrides the trigger text (e.g. "All card types"). */
  summary?: string;
  /** Hide the search box (short, grouped lists). */
  searchable?: boolean;
  /** Keep the authored option order (e.g. rarity) instead of pinning the selection first. */
  keepOrder?: boolean;
  /** Rendered after the label (e.g. an InfoTip). */
  labelExtra?: ReactNode;
};

/**
 * Many-option picker: a compact trigger ("Final Fantasy +2 ▾") opening a
 * searchable checkbox list. DESIGN.md: chip groups stop at 5 options; anything
 * larger uses this, so long lists never take over the sidebar.
 */
export function MultiSelect({ label, options, value, onChange, noun, placeholder = 'Filter…', summary: summaryText, searchable = true, keepOrder = false, labelExtra }: Props) {
  const [q, setQ] = useState('');
  const id = useId();
  const selected = useMemo(() => new Set(value), [value]);
  const shown = useMemo(() => {
    const ql = q.trim().toLowerCase();
    const hits = ql ? options.filter((o) => o.label.toLowerCase().includes(ql) || o.value.toLowerCase().includes(ql)) : options;
    // Grouped lists keep their authored order; flat lists pin the selection first.
    if (keepOrder || options.some((o) => o.group)) return hits;
    return [...hits.filter((o) => selected.has(o.value)), ...hits.filter((o) => !selected.has(o.value))];
  }, [options, q, selected, keepOrder]);
  const grouped = options.some((o) => o.group);
  const groups = useMemo(() => {
    const m = new Map<string, MultiOption[]>();
    for (const o of shown) m.set(o.group ?? '', [...(m.get(o.group ?? '') ?? []), o]);
    return [...m];
  }, [shown]);

  const first = options.find((o) => selected.has(o.value));
  const summary = summaryText ?? (!value.length ? `Choose ${noun}…` : value.length === 1 ? first?.label ?? value[0] : `${first?.label ?? value[0]} +${value.length - 1}`);

  const toggle = (v: string) => onChange(selected.has(v) ? value.filter((x) => x !== v) : [...value, v]);

  return (
    <div className="flex flex-col gap-1.5">
      <span className="flex items-center gap-1.5">
        <span id={`${id}-l`} className="text-sm voice-semi text-on-chrome-muted">{label}</span>
        {labelExtra}
      </span>
      <Popover.Root onOpenChange={(o) => !o && setQ('')}>
        <Popover.Trigger
          aria-labelledby={`${id}-l ${id}-s`}
          className="flex min-h-9 w-full cursor-pointer items-center gap-2 rounded-sm border border-chrome-line bg-chrome-raised px-2.5 text-left text-md text-on-chrome transition-colors ease-guide hover:border-on-chrome-muted data-[state=open]:border-accent"
        >
          <span id={`${id}-s`} className={`min-w-0 flex-1 truncate ${value.length ? '' : 'text-on-chrome-muted'}`}>{summary}</span>
          {!summaryText && value.length > 1 && <span className="tabular text-xs text-on-chrome-muted">{value.length}</span>}
          <span aria-hidden="true" className="text-on-chrome-muted">▾</span>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="start"
            sideOffset={4}
            collisionPadding={12}
            tabIndex={-1}
            onOpenAutoFocus={(e) => {
              // Searchable pickers land in the filter box; others on the panel itself,
              // so no stray focus ring lands on the first link-button.
              if (searchable) return;
              e.preventDefault();
              (e.currentTarget as HTMLElement).focus({ preventScroll: true });
            }}
            className={`z-50 flex focus:outline-none flex-col ${grouped ? "max-h-[min(36rem,85dvh)] w-[min(34rem,calc(100vw-1.5rem))]" : "max-h-[min(28rem,70dvh)] w-[max(var(--radix-popover-trigger-width),18rem)]"} rounded-sm border border-chrome-line bg-chrome-raised text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]`}
          >
            <div className="flex flex-col gap-2 border-b border-chrome-line p-2">
              {searchable && <input
                type="search"
                aria-label={`Filter ${noun}`}
                placeholder={placeholder}
                autoComplete="off"
                spellCheck={false}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="min-h-8 rounded-sm border border-chrome-line bg-chrome px-2 text-sm text-on-chrome placeholder:text-on-chrome-muted focus-visible:border-accent"
              />}
              {grouped ? (
                <div className="flex gap-3 text-xs">
                  <button type="button" className="cursor-pointer text-on-chrome-muted underline hover:text-on-chrome" onClick={() => onChange(options.map((o) => o.value))}>
                    Check all
                  </button>
                  <span className="ml-auto tabular text-on-chrome-muted">{options.filter((o) => !selected.has(o.value)).length} unchecked</span>
                </div>
              ) : (
              <div className="flex gap-3 text-xs">
                {q && shown.length > 0 && (
                  <button type="button" className="cursor-pointer text-on-chrome-muted underline hover:text-on-chrome" onClick={() => onChange([...new Set([...value, ...shown.map((o) => o.value)])])}>
                    Select shown
                  </button>
                )}
                {!q && value.length < options.length && (
                  <button type="button" className="cursor-pointer text-on-chrome-muted underline hover:text-on-chrome" onClick={() => onChange(options.map((o) => o.value))}>
                    Select all
                  </button>
                )}
                <button type="button" className="cursor-pointer text-on-chrome-muted underline hover:text-on-chrome" onClick={() => onChange(q ? value.filter((v) => !shown.some((o) => o.value === v)) : [])}>
                  Clear {q ? 'shown' : 'all'}
                </button>
                <span className="ml-auto tabular text-on-chrome-muted">{value.length} selected</span>
              </div>
              )}
            </div>
            <div className={`min-h-0 overflow-y-auto overscroll-contain py-1 ${grouped ? "gap-x-2 sm:columns-2" : ""}`}>
              {shown.length === 0 && <p className="px-3 py-2 text-sm text-on-chrome-muted">No {noun} match “{q}”.</p>}
              {groups.map(([group, opts]) => (
                <fieldset key={group || 'all'} className="break-inside-avoid py-0.5">
                  <legend className={group ? 'flex w-full items-baseline gap-2 px-3 pb-1 pt-2' : 'sr-only'}>
                    {group ? (
                      <>
                        <span className="text-xs voice-condensed uppercase tracking-[0.06em] text-on-chrome-muted">{group}</span>
                        <span className="ml-auto flex gap-2 text-xs">
                          <button type="button" className="cursor-pointer text-on-chrome-muted underline hover:text-on-chrome" aria-label={`Select all ${group}`} onClick={() => onChange([...new Set([...value, ...opts.map((o) => o.value)])])}>All</button>
                          <button type="button" className="cursor-pointer text-on-chrome-muted underline hover:text-on-chrome" aria-label={`Clear all ${group}`} onClick={() => onChange(value.filter((v) => !opts.some((o) => o.value === v)))}>None</button>
                        </span>
                      </>
                    ) : label}
                  </legend>
                  {opts.map((o) => (
                    <label key={o.value} className="flex cursor-pointer items-center gap-2.5 px-3 py-1.5 text-sm hover:bg-chrome-line">
                      <input type="checkbox" checked={selected.has(o.value)} onChange={() => toggle(o.value)} className="h-3.5 w-3.5 shrink-0 accent-[var(--theme-accent)]" />
                      <span className="min-w-0 flex-1 truncate">{o.label}</span>
                      {o.count != null && <span className="tabular text-xs text-on-chrome-muted">{o.count}</span>}
                    </label>
                  ))}
                </fieldset>
              ))}
            </div>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </div>
  );
}

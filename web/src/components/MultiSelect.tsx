import { Popover } from 'radix-ui';
import { useId, useMemo, useState, type ReactNode } from 'react';
import { bulkActions, pickCount, pickSummary, type PickMode } from '../core/multiSelect';
import { Button } from './Button';
import { Check } from './controls/Check';
import { RailField } from './controls/RailField';
import { TextInput } from './controls/TextField';
import { triggerClass } from './controls/fieldClass';
import { menuPanelClass } from './controls/surfaces';
import { CaretMark } from './icons/marks';

type MultiOption = { value: string; label: string; count?: number; group?: string };

type Props = {
  label: string;
  options: MultiOption[];
  value: string[];
  onChange: (v: string[]) => void;
  /** Noun for the trigger summary, e.g. "families". */
  noun: string;
  placeholder?: string;
  /** What the value means (see `core/multiSelect`): `include` (default), `scope` or `exclude`. */
  mode?: PickMode;
  /** Hide the search box (short, grouped lists). */
  searchable?: boolean;
  /** Keep the authored option order (e.g. rarity) instead of pinning the selection first. */
  keepOrder?: boolean;
  /** Rendered after the label (e.g. an InfoTip). */
  labelExtra?: ReactNode;
  /** Options are still loading: the trigger reads "Loading…" and stays shut. */
  loading?: boolean;
};

/**
 * Many-option picker: a compact trigger ("Final Fantasy +2") opening a
 * searchable checkbox list. DESIGN.md: chip groups stop at 5 options; anything
 * larger uses this, so long lists never take over the sidebar.
 */
export function MultiSelect({ label, options, value, onChange, noun, placeholder = 'Filter…', mode = 'include', searchable = true, keepOrder = false, labelExtra, loading = false }: Props) {
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

  const summary = pickSummary(mode, options, value, noun);
  const unfiltered = mode === 'exclude' ? options.every((o) => selected.has(o.value)) : !value.length;
  const bulk = bulkActions(mode, q ? shown : options, value, Boolean(q));

  const toggle = (v: string) => onChange(selected.has(v) ? value.filter((x) => x !== v) : [...value, v]);

  return (
    <RailField label={label} labelId={`${id}-l`} extra={labelExtra}>
      <Popover.Root onOpenChange={(o) => !o && setQ('')}>
        <Popover.Trigger
          aria-labelledby={`${id}-l ${id}-s`}
          aria-busy={loading || undefined}
          disabled={loading}
          className={triggerClass('chrome')}
        >
          <span id={`${id}-s`} className={`min-w-0 flex-1 truncate ${unfiltered || loading ? 'text-on-chrome-muted' : ''}`}>{loading ? 'Loading…' : summary}</span>
          <CaretMark className="size-icon-sm shrink-0 text-on-chrome-muted" />
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
            className={`flex focus:outline-none flex-col ${grouped ? "max-h-[min(36rem,85dvh)] w-[min(26rem,calc(100vw-1.5rem))]" : "max-h-[min(28rem,70dvh)] w-[max(var(--radix-popover-trigger-width),18rem)]"} ${menuPanelClass}`}
          >
            <div className="flex flex-col gap-2 border-b border-chrome-line p-2">
              {searchable && <TextInput
                type="search"
                aria-label={`Filter ${noun}`}
                placeholder={placeholder}
                autoComplete="off"
                spellCheck={false}
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />}
              <div className="flex gap-3 text-xs">
                {bulk.map((b) => (
                  <Button key={b.label} emphasis="link" onClick={() => onChange(b.next)}>
                    {b.label}
                  </Button>
                ))}
                <span className="ml-auto tabular text-on-chrome-muted">{pickCount(mode, options, value)}</span>
              </div>
            </div>
            <div className="min-h-0 overflow-y-auto overscroll-contain py-1">
              {shown.length === 0 && <p className="px-3 py-2 text-sm text-on-chrome-muted">No {noun} match “{q}”.</p>}
              {groups.map(([group, opts]) => (
                <fieldset key={group || 'all'} className="py-0.5">
                  <legend className={group ? 'flex w-full items-baseline gap-2 px-3 pb-1 pt-2' : 'sr-only'}>
                    {group ? (
                      <>
                        <span className="text-xs voice-condensed uppercase tracking-caps text-on-chrome-muted">{group}</span>
                        <span className="ml-auto flex gap-2 text-xs">
                          <Button emphasis="link" aria-label={`Select all ${group}`} onClick={() => onChange([...new Set([...value, ...opts.map((o) => o.value)])])}>All</Button>
                          <Button emphasis="link" aria-label={`Clear all ${group}`} onClick={() => onChange(value.filter((v) => !opts.some((o) => o.value === v)))}>None</Button>
                        </span>
                      </>
                    ) : label}
                  </legend>
                  {opts.map((o) => (
                    <label key={o.value} className="flex cursor-pointer items-start gap-2.5 px-3 py-1.5 text-sm hover:bg-chrome-line">
                      <Check checked={selected.has(o.value)} onChange={() => toggle(o.value)} />
                      <span className={`min-w-0 flex-1 ${grouped ? "line-clamp-2 break-words" : "truncate"}`}>{o.label}</span>
                      {o.count != null && <span className="tabular text-xs text-on-chrome-muted">{o.count}</span>}
                    </label>
                  ))}
                </fieldset>
              ))}
            </div>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </RailField>
  );
}

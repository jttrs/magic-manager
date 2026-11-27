import { Popover } from 'radix-ui';
import { CaretMark } from './icons/marks';
import { RailField } from './controls/RailField';
import { TextInput } from './controls/TextField';
import { triggerClass } from './controls/fieldClass';
import { menuPanelClass } from './controls/surfaces';
import { useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';

type Option = { value: string; label: string; hint?: string };

/** One-of-many picker for long lists: a compact trigger opening a filter box
 *  over a list; picking closes it. Arrow keys move, Enter picks. */
export function SearchSelect({ label, options, value, onChange, noun, nouns = `${noun}s`, placeholder, tone = 'chrome', hideLabel = false, labelExtra }: { label: string; options: Option[]; value: string | undefined; onChange: (v: string) => void; noun: string; nouns?: string; placeholder?: string; tone?: 'chrome' | 'paper'; hideLabel?: boolean; labelExtra?: ReactNode }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const [active, setActive] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);
  const shown = useMemo(() => {
    const ql = q.trim().toLowerCase();
    return ql ? options.filter((o) => o.label.toLowerCase().includes(ql) || o.value.toLowerCase().includes(ql)) : options;
  }, [options, q]);
  const current = options.find((o) => o.value === value);
  const paper = tone === 'paper';

  const pick = (v: string) => {
    onChange(v);
    setOpen(false);
  };
  const move = (i: number) => {
    const n = Math.max(0, Math.min(shown.length - 1, i));
    setActive(n);
    listRef.current?.children[n]?.scrollIntoView({ block: 'nearest' });
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); move(active + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); move(active - 1); }
    else if (e.key === 'Enter' && shown[active]) { e.preventDefault(); pick(shown[active].value); }
  };

  return (
    <RailField label={label} labelId={`${id}-l`} extra={labelExtra} tone={paper ? 'paper' : 'chrome'} hideLabel={hideLabel}>
      <Popover.Root open={open} onOpenChange={(o) => { setOpen(o); if (!o) setQ(''); else setActive(Math.max(0, options.findIndex((x) => x.value === value))); }}>
        <Popover.Trigger
          aria-labelledby={`${id}-l ${id}-s`}
          className={`${triggerClass(paper ? 'paper' : 'chrome')} ${paper ? 'sm:min-w-[15rem]' : ''}`}
        >
          <span id={`${id}-s`} className={`min-w-0 flex-1 truncate ${current ? '' : paper ? 'text-ink-muted' : 'text-on-chrome-muted'}`}>{current?.label ?? `Choose a ${noun}…`}</span>
          <CaretMark className={`size-icon-sm ${paper ? 'text-ink-muted' : 'text-on-chrome-muted'}`} />
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="start"
            sideOffset={4}
            collisionPadding={12}
            className={`flex max-h-[min(28rem,70dvh)] w-[max(var(--radix-popover-trigger-width),18rem)] flex-col ${menuPanelClass}`}
          >
            <div className="border-b border-chrome-line p-2">
              <TextInput
                type="search"
                role="combobox"
                aria-expanded="true"
                aria-controls={`${id}-list`}
                aria-activedescendant={shown[active] ? `${id}-o${active}` : undefined}
                aria-label={`Filter ${nouns}`}
                placeholder={placeholder ?? 'Filter…'}
                autoComplete="off"
                spellCheck={false}
                value={q}
                onChange={(e) => { setQ(e.target.value); setActive(0); }}
                onKeyDown={onKey}
              />
            </div>
            <ul ref={listRef} id={`${id}-list`} role="listbox" aria-label={label} className="min-h-0 overflow-y-auto overscroll-contain py-1">
              {shown.length === 0 && <li className="px-3 py-2 text-sm text-on-chrome-muted">No {nouns} match “{q}”.</li>}
              {shown.map((o, i) => (
                <li
                  key={o.value}
                  id={`${id}-o${i}`}
                  role="option"
                  aria-selected={o.value === value}
                  data-active={i === active || undefined}
                  onPointerMove={() => setActive(i)}
                  onClick={() => pick(o.value)}
                  className="flex cursor-pointer items-baseline gap-2.5 px-3 py-1.5 text-sm data-[active]:bg-chrome-line aria-selected:text-accent"
                >
                  <span className="min-w-0 flex-1 truncate">{o.label}</span>
                  {o.hint && <span className="shrink-0 text-xs text-on-chrome-muted">{o.hint}</span>}
                </li>
              ))}
            </ul>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </RailField>
  );
}

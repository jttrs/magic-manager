import { useQuery } from '@tanstack/react-query';
import { Popover } from 'radix-ui';
import { useId, useState, type KeyboardEvent } from 'react';
import { commanderSearchQuery } from '../app/queries';

type Props = { label: string; value?: string; onCommit: (name: string) => void; name: string };

/**
 * Commander input: an ARIA 1.2 combobox with local suggestions (commander-eligible
 * cards in your DB; EDHREC-cached first). Free text is accepted — the engine
 * resolves any card name via Scryfall.
 */
export function CommanderPicker({ label, value = '', onCommit, name }: Props) {
  // `draft` holds in-progress typing; when null the field shows the committed value.
  const [draft, setDraft] = useState<string | null>(null);
  const text = draft ?? value;
  const setText = (t: string) => setDraft(t);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const id = useId();
  const listId = `${id}-list`;

  const q = useQuery(commanderSearchQuery(text));
  const options = open ? (q.data ?? []) : [];

  function commit(v: string) {
    const t = v.trim();
    setOpen(false);
    setActive(-1);
    if (t && t !== value) onCommit(t);
    setDraft(null);
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(options.length - 1, i + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => Math.max(-1, i - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      commit(active >= 0 && options[active] ? options[active].name : text);
    } else if (e.key === 'Escape') {
      setOpen(false);
      setActive(-1);
      setDraft(null);
    }
  }

  return (
    <Popover.Root open={open && options.length > 0} onOpenChange={setOpen}>
      <label htmlFor={id} className="text-sm voice-semi text-on-chrome-muted">{label}</label>
      <Popover.Anchor asChild>
        <input
          id={id}
          name={name}
          role="combobox"
          aria-expanded={open && options.length > 0}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
          autoComplete="off"
          spellCheck={false}
          placeholder="Type a commander…"
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setOpen(true);
            setActive(-1);
          }}
          onFocus={() => text.length >= 2 && setOpen(true)}
          onBlur={() => window.setTimeout(() => commit(text), 120)}
          onKeyDown={onKey}
          className="min-h-10 w-full rounded-sm border border-chrome-line bg-chrome-raised px-2.5 text-lg voice-condensed text-on-chrome placeholder:text-on-chrome-muted focus-visible:border-accent"
        />
      </Popover.Anchor>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={4}
          onOpenAutoFocus={(e) => e.preventDefault()}
          className="z-50 max-h-80 w-[var(--radix-popover-trigger-width)] min-w-64 overflow-y-auto overscroll-contain rounded-sm border border-chrome-line bg-chrome-raised py-1 shadow-[0_12px_28px_-12px_var(--theme-scrim)]"
        >
          <ul id={listId} role="listbox" aria-label={`${label} suggestions`}>
            {options.map((o, i) => (
              <li
                key={o.oracle_id ?? o.name}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === active}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => commit(o.name)}
                onMouseEnter={() => setActive(i)}
                className="flex cursor-pointer items-baseline gap-2 px-3 py-1.5 text-md text-on-chrome aria-selected:bg-chrome-line"
              >
                <span className="min-w-0 truncate voice-semi">{o.name}</span>
                <span className="ml-auto shrink-0 text-2xs uppercase tracking-[0.06em] text-on-chrome-muted" translate="no">
                  {o.color_identity.join('') || 'C'}
                  {o.cached ? ' · cached' : ''}
                </span>
              </li>
            ))}
          </ul>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

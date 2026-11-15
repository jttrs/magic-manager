// How a sheet's cards are arranged (sort, grouping, grid/list), as compact
// controls in the sheet header (`GuideSheet arrange`), next to the content they
// rearrange. Choosing these never changes WHICH cards show; filters stay in the rail.
import { DropdownMenu, Popover } from 'radix-ui';
import type { ComponentType, ReactNode, SVGProps } from 'react';
import { sortShort, sortSummary, type SortPreset, type SortRule } from '../core/sort';
import { IconTooltip } from './IconTooltip';
import { iconActionClass } from './iconActionClass';
import { SortRulesEditor } from './SortBuilder';

type Mark = ComponentType<SVGProps<SVGSVGElement>>;
const base = { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true } as const;

/** Bars shortening downward with a down-arrow beside them (sort). */
export function SortMark(p: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...p}>
      <path d="M4 6h10M4 11h7M4 16h4" />
      <path d="M18 5v13M15 15l3 3 3-3" />
    </svg>
  );
}

/** Two ruled heads, each over its rows (group by). */
function GroupMark(p: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...p}>
      <path d="M3.5 4.5h17M6.5 8h11M6.5 11h11" />
      <path d="M3.5 14.5h17M6.5 18h11" />
    </svg>
  );
}

function GridMark(p: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...p}>
      <rect x="4" y="4" width="6.5" height="6.5" rx="1" />
      <rect x="13.5" y="4" width="6.5" height="6.5" rx="1" />
      <rect x="4" y="13.5" width="6.5" height="6.5" rx="1" />
      <rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1" />
    </svg>
  );
}

function ListMark(p: SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...p}>
      <path d="M8.5 6h11.5M8.5 12h11.5M8.5 18h11.5" />
      <path d="M4 6h.5M4 12h.5M4 18h.5" strokeWidth={2.4} />
    </svg>
  );
}

/** The header trigger: the control's mark, then its current choice (hidden on phones,
 *  where a small amber dot says "not the default" instead). */
const TRIGGER =
  'touch-hit inline-flex min-h-9 max-w-[14rem] shrink-0 cursor-pointer items-center gap-1.5 rounded-sm px-2 text-sm voice-semi text-ink transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk data-[state=open]:bg-paper-sunk';

function TriggerFace({ Icon, short, changed }: { Icon: Mark; short: string; changed: boolean }) {
  return (
    <>
      <span className="relative text-accent-ink">
        <Icon className="size-[1.2rem]" />
        {changed && <span aria-hidden="true" className="absolute -right-0.5 -top-0.5 size-1.5 rounded-pill bg-accent sm:hidden" />}
      </span>
      <span className="hidden min-w-0 truncate sm:inline">{short}</span>
      <span aria-hidden="true" className="hidden text-xs text-ink-muted sm:inline">▾</span>
    </>
  );
}

const MENU = 'z-50 rounded-sm border border-chrome-line bg-chrome-raised text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]';

/** Grid or list, as two pressed-state icon buttons. */
export function ViewToggle<V extends 'grid' | 'list'>({ value, onChange, label = 'Card view' }: { value: V; onChange: (v: V) => void; label?: string }) {
  const opts: { v: V; text: string; Icon: Mark }[] = [
    { v: 'grid' as V, text: 'Grid', Icon: GridMark },
    { v: 'list' as V, text: 'List', Icon: ListMark },
  ];
  return (
    <div role="group" aria-label={label} className="flex items-center">
      {opts.map(({ v, text, Icon }) => (
        <IconTooltip key={v} label={`${text} view`}>
          <button type="button" aria-label={`${text} view`} aria-pressed={value === v} onClick={() => onChange(v)} className={iconActionClass('paper')}>
            <Icon className="size-[1.2rem]" />
          </button>
        </IconTooltip>
      ))}
    </div>
  );
}

type Choice<T extends string> = { value: T; label: string };

/** One choice from a list, shown as mark + current choice, opening a radio menu. */
export function ArrangeMenu<T extends string>({ label, Icon, value, options, onChange, defaultValue }: {
  /** What the control arranges by: "Sort", "Group by". */
  label: string;
  Icon: Mark;
  value: T;
  options: readonly Choice<T>[];
  onChange: (v: T) => void;
  /** The view's default, so a phone can mark a changed choice. */
  defaultValue?: T;
}) {
  const current = options.find((o) => o.value === value)?.label ?? value;
  return (
    <DropdownMenu.Root>
      <IconTooltip label={`${label}: ${current}`}>
        <DropdownMenu.Trigger aria-label={`${label}: ${current}`} className={TRIGGER}>
          <TriggerFace Icon={Icon} short={current} changed={defaultValue != null && value !== defaultValue} />
        </DropdownMenu.Trigger>
      </IconTooltip>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={4} collisionPadding={12} className={`${MENU} w-[max(var(--radix-dropdown-menu-trigger-width),13rem)] py-1`}>
          <DropdownMenu.Label className="px-3 pb-1 pt-1.5 text-xs voice-condensed uppercase tracking-[0.06em] text-on-chrome-muted">{label}</DropdownMenu.Label>
          <DropdownMenu.RadioGroup value={value} onValueChange={(v) => onChange(v as T)}>
            {options.map((o) => (
              <DropdownMenu.RadioItem key={o.value} value={o.value} className="flex cursor-pointer items-center gap-2.5 px-3 py-1.5 text-sm outline-none data-[highlighted]:bg-chrome-line data-[state=checked]:text-accent">
                <span aria-hidden="true" className="w-3 text-accent">
                  <DropdownMenu.ItemIndicator><svg {...base} className="size-3"><path d="m4 12.5 5 5L20 6.5" strokeWidth={2.2} /></svg></DropdownMenu.ItemIndicator>
                </span>
                <span className="min-w-0 flex-1 truncate">{o.label}</span>
              </DropdownMenu.RadioItem>
            ))}
          </DropdownMenu.RadioGroup>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

/** Group by: two choices are a pressed-state pair you can see at a glance; more open a menu. */
export function GroupControl<T extends string>({ value, options, onChange, defaultValue }: { value: T; options: readonly Choice<T>[]; onChange: (v: T) => void; defaultValue?: T }) {
  if (options.length !== 2) return <ArrangeMenu label="Group by" Icon={GroupMark} value={value} options={options} onChange={onChange} defaultValue={defaultValue} />;
  return (
    <div role="group" aria-label="Group by" className="flex items-center gap-0.5">
      <span className="px-1 text-accent-ink" title="Group by"><GroupMark className="size-[1.2rem]" /></span>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
          className="min-h-9 cursor-pointer rounded-sm px-2 text-sm voice-semi text-ink-muted transition-colors ease-guide hover:bg-paper-sunk aria-pressed:text-ink aria-pressed:shadow-[inset_0_-2px_0_var(--theme-accent)]"
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** A hierarchical sort: mark + first level (`Set +2`), opening the sort editor. */
export function SortControl<K extends string>({ keys, rules, presets, onChange, defaultRules }: {
  keys: Record<K, { label: string; defaultDir: 'asc' | 'desc' }>;
  rules: SortRule<K>[];
  presets: SortPreset<K>[];
  onChange: (rules: SortRule<K>[]) => void;
  defaultRules?: readonly SortRule<K>[];
}): ReactNode {
  const full = sortSummary(keys, rules);
  const changed = defaultRules != null && sortSummary(keys, [...defaultRules]) !== full;
  return (
    <Popover.Root>
      <IconTooltip label={`Sort: ${full}`}>
        <Popover.Trigger aria-label={`Sort: ${full}`} className={TRIGGER}>
          <TriggerFace Icon={SortMark} short={sortShort(keys, rules)} changed={changed} />
        </Popover.Trigger>
      </IconTooltip>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={4}
          collisionPadding={12}
          aria-label="Sort hierarchy"
          tabIndex={-1}
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            (e.currentTarget as HTMLElement).focus({ preventScroll: true });
          }}
          className={`${MENU} flex w-[22rem] max-w-[calc(100vw-1.5rem)] flex-col gap-3 p-3 focus:outline-none`}
        >
          <SortRulesEditor keys={keys} rules={rules} presets={presets} onChange={onChange} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

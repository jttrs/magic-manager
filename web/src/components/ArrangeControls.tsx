// How a sheet's cards are arranged (sort, grouping, grid/list), as compact
// controls in the sheet header (`GuideSheet arrange`), next to the content they
// rearrange. Choosing these never changes WHICH cards show; filters stay in the rail.
import { DropdownMenu, Popover } from 'radix-ui';
import type { ComponentType, ReactNode, SVGProps } from 'react';
import { sortSummary, type SortPreset, type SortRule } from '../core/sort';
import { IconTooltip } from './IconTooltip';
import { iconActionClass } from './iconActionClass';
import { SortRulesEditor } from './SortBuilder';
import { IconAction } from './IconAction';
import { CheckMark, GridMark, GroupMark, ListMark, SortMark } from './icons/marks';
import { menuLabelClass, menuPanelClass } from './controls/surfaces';

type Mark = ComponentType<SVGProps<SVGSVGElement>>;

/** The header trigger: the control's mark only — the current choice lives in its
 *  tooltip and accessible name; a small amber dot says "not the default". */
const TRIGGER = `${iconActionClass('paper')} data-[state=open]:bg-paper-sunk`;

function TriggerFace({ Icon, changed }: { Icon: Mark; changed: boolean }) {
  return (
    <span className="relative">
      <Icon className="size-icon-md" />
      {changed && <span aria-hidden="true" className="absolute -right-1 -top-1 size-1.5 rounded-pill bg-accent" />}
    </span>
  );
}

const MENU = menuPanelClass;

/** Grid or list: ONE icon button showing the current view; a click switches to the
 *  other. Its tooltip / accessible name says what a click does. */
export function ViewToggle<V extends 'grid' | 'list'>({ value, onChange }: { value: V; onChange: (v: V) => void }) {
  const next = (value === 'grid' ? 'list' : 'grid') as V;
  return (
    <IconAction
      label={next === 'list' ? 'Switch to list view' : 'Switch to grid view'}
      Icon={value === 'grid' ? GridMark : ListMark}
      onClick={() => onChange(next)}
    />
  );
}

type Choice<T extends string> = { value: T; label: string };

/** One choice from a list, shown as mark + current choice, opening a radio menu. */
function ArrangeMenu<T extends string>({ label, Icon, value, options, onChange, defaultValue }: {
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
          <TriggerFace Icon={Icon} changed={defaultValue != null && value !== defaultValue} />
        </DropdownMenu.Trigger>
      </IconTooltip>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={4} collisionPadding={12} className={`${MENU} w-[max(var(--radix-dropdown-menu-trigger-width),13rem)] py-1`}>
          <DropdownMenu.Label className={menuLabelClass}>{label}</DropdownMenu.Label>
          <DropdownMenu.RadioGroup value={value} onValueChange={(v) => onChange(v as T)}>
            {options.map((o) => (
              <DropdownMenu.RadioItem key={o.value} value={o.value} className="flex cursor-pointer items-center gap-2.5 px-3 py-1.5 text-sm outline-none data-[highlighted]:bg-chrome-line data-[state=checked]:text-accent">
                <span aria-hidden="true" className="w-3 text-accent">
                  <DropdownMenu.ItemIndicator><CheckMark className="size-3" /></DropdownMenu.ItemIndicator>
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

/** A single-choice sort (a table's sort order): `ArrangeMenu` labelled Sort. */
export function SortMenu<T extends string>(props: { value: T; options: readonly Choice<T>[]; onChange: (v: T) => void; defaultValue?: T }) {
  return <ArrangeMenu label="Sort" Icon={SortMark} {...props} />;
}

/** Group by: two choices are a pressed-state pair you can see at a glance; more open a menu. */
export function GroupControl<T extends string>({ value, options, onChange, defaultValue }: { value: T; options: readonly Choice<T>[]; onChange: (v: T) => void; defaultValue?: T }) {
  if (options.length !== 2) return <ArrangeMenu label="Group by" Icon={GroupMark} value={value} options={options} onChange={onChange} defaultValue={defaultValue} />;
  return (
    <div role="group" aria-label="Group by" className="flex items-center gap-0.5">
      <span className="px-1 text-accent-ink" title="Group by"><GroupMark className="size-icon-md" /></span>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
          className="min-h-control cursor-pointer rounded-sm px-2 text-sm voice-semi text-ink-muted transition-colors ease-guide hover:bg-paper-sunk aria-pressed:text-ink aria-pressed:shadow-[inset_0_-2px_0_var(--theme-accent)]"
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
          <TriggerFace Icon={SortMark} changed={changed} />
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

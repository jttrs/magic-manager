import { ToggleGroup } from 'radix-ui';
import { chosenPrinting, type Finish, type ReviewLine } from '../../core/ingest';
import { fmtUsd } from '../../core/format';
import { PrintingPicker, PrintingThumb } from './PrintingPicker';

type Patch = Partial<Pick<ReviewLine, 'qty' | 'finish' | 'chosen' | 'include'>>;

const FINISH_LABEL: Record<Finish, string> = { nonfoil: 'Nonfoil', foil: 'Foil' };

/** The checklist every add-cards mode ends in: one ruled row per line, with the
 *  printing, finish and count editable and a checkbox to leave a line out. */
export function ReviewTable({ lines, onChange, onRemove, label }: { lines: ReviewLine[]; onChange: (key: string, patch: Patch) => void; onRemove?: (key: string) => void; label: string }) {
  return (
    <ul aria-label={label} className="flex flex-col">
      {lines.map((l) => (
        <ReviewRow key={l.key} line={l} onChange={(p) => onChange(l.key, p)} onRemove={onRemove ? () => onRemove(l.key) : undefined} />
      ))}
    </ul>
  );
}

function ReviewRow({ line: l, onChange, onRemove }: { line: ReviewLine; onChange: (p: Patch) => void; onRemove?: () => void }) {
  const p = chosenPrinting(l);
  const dead = l.status === 'unresolved';
  const unit = p ? (l.finish === 'foil' ? p.price_usd_foil : p.price_usd) : null;
  return (
    <li className={`ruled grid grid-cols-[auto_auto_minmax(0,1fr)] items-center gap-x-3 gap-y-1.5 py-2 @[44rem]:grid-cols-[auto_auto_minmax(0,1fr)_minmax(0,15rem)_auto_auto] ${!l.include ? 'opacity-55' : ''}`}>
      <label className="-m-2 grid size-9 cursor-pointer place-items-center has-disabled:cursor-default">
        <input
          type="checkbox"
          checked={l.include}
          disabled={dead}
          onChange={(e) => onChange({ include: e.target.checked })}
          aria-label={`Include ${l.name}`}
          className="size-4 cursor-pointer accent-[var(--theme-accent)] disabled:cursor-default"
        />
      </label>
      <PrintingThumb p={p} />
      <div className="min-w-0">
        <p className="flex min-w-0 items-baseline gap-2">
          <span className="truncate text-md voice-semi font-medium text-ink">{l.name}</span>
          {l.status === 'ambiguous' && <span className="shrink-0 text-2xs voice-condensed uppercase tracking-[0.06em] text-accent-ink">Best guess</span>}
          {dead && <span className="shrink-0 text-2xs voice-condensed uppercase tracking-[0.06em] text-danger">Not found</span>}
        </p>
        <p className="truncate text-xs text-ink-muted" title={l.note ?? l.raw}>{l.note ?? l.raw}</p>
      </div>
      {/* Narrow: one wrapping control line under the name. Wide: its children join the row's columns. */}
      <div className="col-span-3 flex min-w-0 flex-wrap items-center gap-2 pl-7 @[44rem]:contents">
        {dead ? (
          <span className="@[44rem]:col-span-3" />
        ) : (
          <>
            <span className="min-w-0 max-w-full"><PrintingPicker name={l.name} candidates={l.candidates} value={l.chosen} onChange={(chosen) => onChange({ chosen })} /></span>
            <FinishToggle name={l.name} finishes={(p?.finishes ?? ['nonfoil']) as Finish[]} value={l.finish} onChange={(finish) => onChange({ finish })} />
            <span className="ml-auto flex items-center gap-2 @[44rem]:justify-self-end">
              <span className="w-14 text-right text-xs tabular text-ink-muted">{fmtUsd(unit)}</span>
              <input
                type="number"
                inputMode="numeric"
                min={1}
                max={9999}
                value={l.qty}
                onChange={(e) => onChange({ qty: Number(e.target.value) })}
                aria-label={`Copies of ${l.name}`}
                className="h-8 w-14 rounded-sm border border-rule bg-paper-raised px-1.5 text-right text-sm tabular text-ink focus-visible:border-accent"
              />
              {onRemove && (
                <button type="button" onClick={onRemove} aria-label={`Remove ${l.name}`} title="Remove" className="grid size-9 cursor-pointer place-items-center rounded-sm text-lg text-ink-muted hover:bg-paper-sunk hover:text-ink">
                  ×
                </button>
              )}
            </span>
          </>
        )}
      </div>
    </li>
  );
}

function FinishToggle({ name, finishes, value, onChange }: { name: string; finishes: Finish[]; value: Finish; onChange: (f: Finish) => void }) {
  if (finishes.length < 2) return <span className="text-xs text-ink-muted">{FINISH_LABEL[finishes[0] ?? 'nonfoil']} only</span>;
  return (
    <ToggleGroup.Root
      type="single"
      value={value}
      onValueChange={(v) => v && onChange(v as Finish)}
      aria-label={`Finish of ${name}`}
      className="inline-grid grid-flow-col rounded-sm border border-rule p-0.5"
    >
      {finishes.map((f) => (
        <ToggleGroup.Item
          key={f}
          value={f}
          className="min-h-8 cursor-pointer rounded-xs px-2.5 text-xs voice-semi text-ink-muted transition-colors ease-guide hover:text-ink data-[state=on]:bg-paper-sunk data-[state=on]:text-ink"
        >
          {FINISH_LABEL[f]}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}

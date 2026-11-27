import { Slider } from 'radix-ui';
import { useEffect, useId, useMemo, useState } from 'react';
import { addDays, daysBetween, DATE_PRESETS, histogram, isoDay, presetOf, presetRange, rangeLabel, type DatePreset } from '../../core/dateRange';
import { Pressable } from './Pressable';
import { RailField } from './RailField';
import { TextInput } from './TextField';

/** One "when" control for a rail: presets (All time · Last 30 days · Last 90 days ·
 *  This year · Custom), a bar strip of the entries per week (or month) across the
 *  data's span with a two-handle slider over it that snaps to days, and — under
 *  Custom — typed From / To days for precision and keyboard use. `from`/`to` are
 *  ISO days; undefined = open end. */
const sameRange = (p: Exclude<DatePreset, 'custom'>, from: string | undefined, to: string | undefined, today: string) => {
  const r = presetRange(p, today);
  return r.from === from && r.to === to;
};

export function DateRange({ label, from, to, onChange, days, min, max, today = isoDay(Date.now()) }: {
  label: string;
  from?: string;
  to?: string;
  onChange: (from: string | undefined, to: string | undefined) => void;
  /** Every entry's day (YYYY-MM-DD), for the bars. */
  days: readonly string[];
  /** The data's first and last day (the slider's ends). */
  min: string;
  max: string;
  today?: string;
}) {
  const id = useId();
  // The preset you picked wins when two presets name the same start day (This year
  // vs Last 90 days on Mar 31); otherwise the range decides which pill is on.
  const [picked, setPicked] = useState<DatePreset | null>(null);
  const derived = presetOf(from, to, today);
  const preset: DatePreset = picked && picked !== 'custom' && sameRange(picked, from, to, today) ? picked : derived;
  const [custom, setCustom] = useState(derived === 'custom');
  // A range set from outside (Clear filters, back/forward) that is a preset turns Custom off.
  useEffect(() => {
    if (derived !== 'custom') setCustom(false);
  }, [derived]);
  const span = Math.max(1, daysBetween(min, max));
  const bins = useMemo(() => histogram(days, min, max), [days, min, max]);
  const peak = Math.max(1, ...bins.map((b) => b.count));
  // Thumbs stay on the track: a range reaching past the data clamps to its ends.
  const hi = to && to < max ? (to > min ? to : min) : max;
  const lo = from && from > min ? (from < hi ? from : hi) : min;
  const [drag, setDrag] = useState<[number, number] | null>(null);
  const value = drag ?? [daysBetween(min, lo), daysBetween(min, hi)];
  const shownFrom = drag ? addDays(min, drag[0]) : from;
  const shownTo = drag ? addDays(min, drag[1]) : to;
  const pick = (p: DatePreset) => {
    setPicked(p);
    setCustom(p === 'custom');
    if (p !== 'custom') {
      const r = presetRange(p, today);
      onChange(r.from, r.to);
    }
  };
  const commit = ([a, b]: number[]) => {
    setDrag(null);
    const nf = a > 0 ? addDays(min, a) : undefined;
    const nt = b < span ? addDays(min, b) : undefined;
    setPicked(null);
    setCustom(presetOf(nf, nt, today) === 'custom');
    onChange(nf, nt);
  };
  const W = 100, H = 24, gap = 0.4;
  const bw = W / Math.max(1, bins.length);
  return (
    <RailField label={label} labelId={`${id}-l`}>
      <div role="group" aria-labelledby={`${id}-l`} className="flex flex-col gap-2">
        <p aria-live="polite" className="text-sm tabular text-on-chrome">{rangeLabel(shownFrom, shownTo)}</p>
        <div className="flex flex-wrap gap-1.5">
          {DATE_PRESETS.map((p) => {
            const on = p.value === 'custom' ? custom : !custom && preset === p.value;
            return (
              <Pressable
                key={p.value}
                aria-pressed={on}
                onClick={() => pick(p.value)}
                className={`inline-flex min-h-7 items-center rounded-pill border px-2.5 text-xs voice-semi transition-colors ease-guide ${on ? 'border-accent bg-accent text-on-accent' : 'border-chrome-line text-on-chrome-muted hover:border-on-chrome-muted hover:text-on-chrome'}`}
              >
                {p.label}
              </Pressable>
            );
          })}
        </div>
        <div className="flex flex-col gap-1">
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true" className="h-8 w-full">
            {bins.map((b, i) => {
              const h = b.count ? Math.max(1.5, (b.count / peak) * H) : 0;
              const inRange = b.end >= (shownFrom ?? min) && b.start <= (shownTo ?? max);
              return <rect key={b.start} x={i * bw + gap / 2} y={H - h} width={Math.max(0.2, bw - gap)} height={h} className={inRange ? 'fill-accent' : 'fill-chrome-line'} />;
            })}
          </svg>
          <Slider.Root
            min={0}
            max={span}
            step={1}
            minStepsBetweenThumbs={0}
            value={value}
            onValueChange={(v) => setDrag([v[0], v[1]])}
            onValueCommit={commit}
            className="relative flex h-5 w-full touch-none select-none items-center"
          >
            <Slider.Track className="relative h-0.5 grow rounded-pill bg-chrome-line">
              <Slider.Range className="absolute h-full rounded-pill bg-accent" />
            </Slider.Track>
            <Slider.Thumb aria-label="From" className="block size-4 cursor-grab rounded-pill border-2 border-accent bg-chrome focus-visible:outline-2 focus-visible:outline-focus active:cursor-grabbing" />
            <Slider.Thumb aria-label="To" className="block size-4 cursor-grab rounded-pill border-2 border-accent bg-chrome focus-visible:outline-2 focus-visible:outline-focus active:cursor-grabbing" />
          </Slider.Root>
        </div>
        {custom && (
          <div className="grid grid-cols-2 gap-2">
            <TextInput type="date" aria-label="From" value={from ?? ''} min={min} max={to ?? max} onChange={(e) => onChange(e.target.value || undefined, to)} />
            <TextInput type="date" aria-label="To" value={to ?? ''} min={from ?? min} max={max} onChange={(e) => onChange(from, e.target.value || undefined)} />
          </div>
        )}
      </div>
    </RailField>
  );
}

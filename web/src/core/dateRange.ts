// Pure day math behind the date-range control: ISO days (YYYY-MM-DD, UTC), presets,
// and the histogram of entries per bin. Framework-free (core/).

const DAY = 86_400_000;
const toMs = (d: string) => Date.parse(`${d}T00:00:00Z`);
export const isoDay = (ms: number) => new Date(ms).toISOString().slice(0, 10);

/** Whole days from `a` to `b` (b − a). */
export const daysBetween = (a: string, b: string) => Math.round((toMs(b) - toMs(a)) / DAY);
export const addDays = (d: string, n: number) => isoDay(toMs(d) + n * DAY);

export type DatePreset = 'all' | '30d' | '90d' | 'year' | 'custom';
export const DATE_PRESETS: readonly { value: DatePreset; label: string }[] = [
  { value: 'all', label: 'All time' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: 'year', label: 'This year' },
  { value: 'custom', label: 'Custom' },
];

/** The range a preset means on `today` (`from`/`to` undefined = open end). */
export function presetRange(p: Exclude<DatePreset, 'custom'>, today: string): { from?: string; to?: string } {
  if (p === 'all') return {};
  if (p === 'year') return { from: `${today.slice(0, 4)}-01-01` };
  return { from: addDays(today, -(p === '30d' ? 29 : 89)) };
}

/** Which preset a range is, else 'custom'. */
export function presetOf(from: string | undefined, to: string | undefined, today: string): DatePreset {
  if (!from && !to) return 'all';
  if (to) return 'custom';
  for (const p of ['30d', '90d', 'year'] as const) if (presetRange(p, today).from === from) return p;
  return 'custom';
}

export type Bin = { start: string; end: string; count: number };

/** Entries per bin between `min` and `max` (inclusive): weekly bins, or monthly when
 *  the span is over a year — so the strip stays a readable ~10–60 bars. */
export function histogram(days: readonly string[], min: string, max: string): Bin[] {
  const span = Math.max(0, daysBetween(min, max));
  const bins: Bin[] = [];
  if (span > 366) {
    let y = Number(min.slice(0, 4)), m = Number(min.slice(5, 7));
    for (;;) {
      const start = `${y}-${String(m).padStart(2, '0')}-01`;
      if (start > max) break;
      const ny = m === 12 ? y + 1 : y, nm = m === 12 ? 1 : m + 1;
      bins.push({ start: start < min ? min : start, end: addDays(`${ny}-${String(nm).padStart(2, '0')}-01`, -1), count: 0 });
      y = ny; m = nm;
    }
  } else {
    for (let d = min; d <= max; d = addDays(d, 7)) bins.push({ start: d, end: addDays(d, 6), count: 0 });
  }
  for (const d of days) {
    const b = bins.find((x) => d >= x.start && d <= x.end);
    if (b) b.count += 1;
  }
  return bins;
}

const FMT = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
const fmt = (d: string) => FMT.format(new Date(toMs(d)));

/** "All time", "Since Aug 14, 2026", "Until …", "Aug 14, 2026 – Oct 31, 2026". */
export function rangeLabel(from: string | undefined, to: string | undefined): string {
  if (!from && !to) return 'All time';
  if (from && !to) return `Since ${fmt(from)}`;
  if (!from && to) return `Until ${fmt(to)}`;
  return `${fmt(from!)} – ${fmt(to!)}`;
}

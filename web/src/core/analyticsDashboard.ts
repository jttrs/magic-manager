// Analytics dashboard view-model (framework-free): labels, ages, sparkline geometry, URL state.
import { z } from 'zod';
import type { ErrorGroup, EventOut, ViewUsage } from './api';

export const PERIODS = [7, 30, 90] as const;
export type Period = (typeof PERIODS)[number];

export const analyticsSearch = z.object({
  days: z.coerce.number().pipe(z.union([z.literal(7), z.literal(30), z.literal(90)])).catch(30).default(30),
  ref: z.string().regex(/^[0-9a-f]{6,32}$/i).optional().catch(undefined),
});

/** The short request "ref" users see beside an error. */
export const shortRef = (rid: string | null | undefined): string => (rid ? rid.slice(0, 8) : '');

const VIEW_LABEL: Record<string, string> = {
  collection: 'Collection', history: 'Purchase history', jumpstart: 'Jumpstart', decks: 'Decks',
  deck_editor: 'Deck editor', explore: 'Explore', market: 'Market', jobs: 'Jobs', analytics: 'Analytics', other: 'Other',
};
const viewLabel = (v: string | undefined): string => (v ? VIEW_LABEL[v] ?? v : '—');

/** One readable line per error group: what failed, and how. */
export function errorTitle(name: string, d: Record<string, string>): { what: string; how: string } {
  switch (name) {
    case 'api.error':
      return { what: `${d.method ?? ''} ${d.route ?? ''}`.trim(), how: `${d.status ?? ''} · ${d.code ?? ''}` };
    case 'job.failed':
      return { what: `Job ${d.job ?? ''}`, how: d.code ?? '' };
    case 'client.error':
      return { what: `${viewLabel(d.view)} · ${d.kind ?? ''} error`, how: d.code ?? '' };
    case 'client.network_error':
      return { what: `${viewLabel(d.view)} · no answer`, how: d.code ?? '' };
    case 'companion.error':
      return { what: 'Browser companion', how: d.code ?? '' };
    default:
      return { what: name, how: Object.values(d).join(' · ') };
  }
}

export const groupTitle = (g: Pick<ErrorGroup, 'name' | 'dims'>) => errorTitle(g.name, g.dims);
export const eventTitle = (e: Pick<EventOut, 'name' | 'props'>) => errorTitle(e.name, e.props);

/** "today" · "yesterday" · "5 days ago" (calendar days, UTC like the store). */
export function ageLabel(day: string, today: string): string {
  const n = Math.round((Date.parse(`${today}T00:00:00Z`) - Date.parse(`${day}T00:00:00Z`)) / 86_400_000);
  if (n <= 0) return 'today';
  if (n === 1) return 'yesterday';
  return `${n} days ago`;
}

/** Views by use, with each one's share of the busiest (for ruled bars). */
export function viewRows(views: ViewUsage[]): (ViewUsage & { label: string; share: number; narrowShare: number })[] {
  const top = Math.max(1, ...views.map((v) => v.n));
  return views.map((v) => ({ ...v, label: viewLabel(v.view), share: v.n / top, narrowShare: v.n ? v.narrow / v.n : 0 }));
}

/** "850 ms" · "12.4 s" · "3.2 min". */
export function fmtDuration(ms: number | null | undefined): string {
  if (ms == null) return '—';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  return `${(ms / 60_000).toFixed(1)} min`;
}

/** "Opened Collection 12 → Exported a buy-list 3 (25%)". */
export function funnelRate(first: number, last: number): number | null {
  return first ? Math.round((last / first) * 100) : null;
}

const FEATURE_LABEL: Record<string, string> = {
  'deck.changed': 'Deck', 'buylist.exported': 'Buy-list', 'cards.added': 'Cards added',
  'checklist.saved': 'Checklist saved', 'undo.restored': 'Undo restored', 'job.started': 'Job started', 'job.succeeded': 'Job finished',
};
export const featureLabel = (name: string, dims: Record<string, string>): string => {
  const base = FEATURE_LABEL[name] ?? name;
  const detail = Object.values(dims).filter(Boolean).join(' · ').replace(/_/g, ' ');
  return detail ? `${base} · ${detail}` : base;
};

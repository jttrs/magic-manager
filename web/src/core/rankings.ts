// Explore rankings (EDHREC top commanders / top cards / salt) — URL state → the
// API request, the ownership filter, and the guide view-model. Framework-free.
import type { RankedOut, RankingOut } from './api';
import { fromFacts } from './explore';
import type { GuideCard } from './guideCard';
import type { CompareSearch, ExploreMode, RankBy, RankOwn, RankScope, RankTimeframe, Role } from './search';

export type RankingsState = Pick<CompareSearch, 'rank' | 'by' | 'color' | 'tag' | 'fam' | 'tf' | 'own' | 'rq'>;

/** What the engine's `RankingQuery` takes. */
export type RankingRequest = { scope: RankScope; timeframe: RankTimeframe; color?: string; tag?: string; set_family?: string };

/** Mode when none is chosen: a picked card wins, otherwise rankings. */
export const exploreMode = (mode: ExploreMode | undefined, a: string | undefined): ExploreMode => mode ?? (a ? 'card' : 'rankings');

export const SCOPE_LABEL: Record<RankScope, string> = { commanders: 'Top commanders', cards: 'Top cards', salt: 'Saltiest cards' };
export const BY_LABEL: Record<RankBy, string> = { any: 'Every commander', color: 'Colour identity', tag: 'Tag or creature type', set: 'Set family' };
export const TIMEFRAME_LABEL: Record<RankTimeframe, string> = { week: 'Week', month: 'Month', year: '2 years' };
export const OWN_LABEL: Record<RankOwn, string> = { all: 'All', owned: 'You own', free: 'Free' };

/** Narrowing applies only to commander rankings; one axis at a time. */
export const narrowBy = (s: Pick<RankingsState, 'rank' | 'by'>): RankBy => (s.rank === 'commanders' ? s.by : 'any');

/** EDHREC serves a timeframe for top commanders/cards and colour pages; salt, tags and sets are all-time. */
export const timeframeApplies = (s: Pick<RankingsState, 'rank' | 'by'>): boolean => s.rank !== 'salt' && ['any', 'color'].includes(narrowBy(s));

/** The API request, or null while the chosen axis still needs a value. */
export function rankingRequest(s: RankingsState): RankingRequest | null {
  const base = { scope: s.rank, timeframe: s.tf };
  const value = (v?: string) => (v?.trim() ? v.trim() : null);
  switch (narrowBy(s)) {
    case 'color': {
      const color = value(s.color);
      return color ? { ...base, color } : null;
    }
    case 'tag': {
      const tag = value(s.tag);
      return tag ? { ...base, tag } : null;
    }
    case 'set': {
      const fam = value(s.fam);
      return fam ? { ...base, set_family: fam } : null;
    }
    default:
      return base;
  }
}

/** Rows kept by the ownership filter and the name search. */
export function shownRows(rows: readonly RankedOut[], own: RankOwn, q: string): RankedOut[] {
  const ql = q.trim().toLowerCase();
  return rows.filter((r) => (own === 'owned' ? (r.facts.owned ?? 0) > 0 : own === 'free' ? (r.facts.free ?? 0) > 0 : true) && (!ql || r.name.toLowerCase().includes(ql)));
}

/** The role a ranked card opens in: commander rankings lead decks; top cards and salt are cards in the 99. */
export const roleFor = (scope: RankScope): Role => (scope === 'commanders' ? 'commander' : 'card');

/** The metric column: deck count, or salt for the salt ranking. */
export const metricLabel = (scope: RankScope): string => (scope === 'salt' ? 'Salt' : 'Decks');

const compact = new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 });
export const fmtMetric = (scope: RankScope, r: RankedOut): string =>
  scope === 'salt' ? (r.salt == null ? '—' : r.salt.toFixed(2)) : r.num_decks == null ? '—' : compact.format(r.num_decks);

/** A ranked card as the shared guide view-model (grid view + inspector). */
export function rankedCard(scope: RankScope, r: RankedOut): GuideCard {
  const c = fromFacts(r.name, r.slug, r.facts);
  const metric = scope === 'salt' ? `salt ${fmtMetric(scope, r)}` : `${fmtMetric(scope, r)} decks`;
  return { ...c, note: `#${r.rank ?? '—'} · ${metric}` };
}

/** "today" / "yesterday" / "5 days ago" / a date — when the ranking was read from EDHREC. */
export function fetchedAgo(iso: string | null | undefined, now: Date = new Date()): string | null {
  if (!iso) return null;
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return null;
  const day = (d: Date) => Date.UTC(d.getFullYear(), d.getMonth(), d.getDate());
  const days = Math.round((day(now) - day(t)) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 14) return `${days} days ago`;
  return t.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: t.getFullYear() === now.getFullYear() ? undefined : 'numeric' });
}

/** The ranking's page on EDHREC (same path as the JSON the engine reads). */
export function edhrecUrl(r: Pick<RankingOut, 'scope' | 'timeframe' | 'filter'>): string {
  const [kind, val] = r.filter.split(':');
  const tf = ['week', 'month', 'year'].includes(r.timeframe) ? `/${r.timeframe}` : '';
  let path: string;
  if (kind === 'color') path = `commanders/${val}${tf}`;
  else if (kind === 'tag') path = `tags/${val}`;
  else if (kind === 'set') path = `sets/${val}`;
  else if (r.scope === 'salt') path = 'top/salt';
  else path = r.scope === 'commanders' ? `commanders${tf}` : `top${tf}`;
  return `https://edhrec.com/${path}`;
}

/** Sheet summary: what the list shows and how much of it you own. */
export function rankingSummary(r: RankingOut, shown: readonly RankedOut[]): string {
  const owned = r.rows.filter((x) => (x.facts.owned ?? 0) > 0).length;
  const free = r.rows.filter((x) => (x.facts.free ?? 0) > 0).length;
  const lead = shown.length === r.rows.length ? `${r.rows.length} ranked` : `${shown.length} of ${r.rows.length} shown`;
  return `${lead} · you own ${owned} · ${free} with free copies`;
}

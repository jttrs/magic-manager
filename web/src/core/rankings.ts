// Explore rankings (EDHREC top commanders / top cards / salt) — URL state → the
// API request and page, and the guide view-model. Framework-free.
import type { RankedOut, RankingOut } from './api';
import { fromFacts } from './explore';
import type { GuideCard } from './guideCard';
import type { CompareSearch, ExploreMode, RankOwn, RankScope, RankTimeframe, Role } from './search';

export type RankingsState = Pick<CompareSearch, 'rank' | 'color' | 'tag' | 'fam' | 'tf' | 'own' | 'rq'>;

/** What the engine's `RankingQuery` takes (the job input): color, tag and set combine. */
export type RankingRequest = { scope: RankScope; timeframe: RankTimeframe; color?: string; tag?: string; set_family?: string };

/** A page of the ranking: the request plus name / ownership and how many rows. */
export type RankingPageRequest = RankingRequest & { q: string; own: RankOwn; offset: number; limit: number };

/** Rows shown at first, and how many more each "Load more" adds. */
export const FIRST_PAGE = 100;
const MORE_PAGE = 50;

/** The Explore tab: explicit `mode`, else a surfer link (`surf` — legacy links opened the surfer over any view), else a picked card, else rankings. */
export const exploreMode = (mode: ExploreMode | undefined, a: string | undefined, surf?: string): ExploreMode => mode ?? (surf != null ? 'surf' : a ? 'card' : 'rankings');

export const SCOPE_LABEL: Record<RankScope, string> = { commanders: 'Top commanders', cards: 'Top cards', salt: 'Saltiest cards' };
export const TIMEFRAME_LABEL: Record<RankTimeframe, string> = { week: 'Week', month: 'Month', year: '2 years' };
export const OWN_LABEL: Record<RankOwn, string> = { all: 'All', owned: 'You own', unused: 'Unused' };

/** Color, tag and set narrow commander rankings only. */
export const filtersApply = (s: Pick<RankingsState, 'rank'>): boolean => s.rank === 'commanders';

const value = (v?: string) => (v?.trim() ? v.trim() : undefined);

/** EDHREC serves a timeframe for top commanders/cards and color pages; salt, tags and sets are all-time.
 *  With a set family the set's list is read (no timeframe); a tag on its own is all-time. */
export function timeframeApplies(s: Pick<RankingsState, 'rank' | 'color' | 'tag' | 'fam'>): boolean {
  if (s.rank === 'salt') return false;
  if (!filtersApply(s)) return true;
  if (value(s.fam)) return false;
  return !(value(s.tag) && !value(s.color));
}

/** The API request (the job input): every filter set, for commander lists. */
export function rankingRequest(s: RankingsState): RankingRequest {
  const base: RankingRequest = { scope: s.rank, timeframe: s.tf };
  if (!filtersApply(s)) return base;
  const color = value(s.color);
  const tag = value(s.tag);
  const fam = value(s.fam);
  return { ...base, ...(color && { color }), ...(tag && { tag }), ...(fam && { set_family: fam }) };
}

/** The page read: the request plus the name / ownership filters and the first `limit` rows. */
export const rankingPage = (req: RankingRequest, s: Pick<RankingsState, 'own' | 'rq'>, limit: number): RankingPageRequest =>
  ({ ...req, q: s.rq.trim(), own: s.own, offset: 0, limit });

/** How many rows "Load more" adds next (never past the total). */
export const nextPage = (shown: number, total: number): number => Math.max(0, Math.min(MORE_PAGE, total - shown));

/** A failed job's message without the engine's exception name ("EdhrecError: …"). */
export const failureText = (error: string | null | undefined): string =>
  (error ?? '').replace(/^[A-Z][A-Za-z]*(Error|Exception|Refused|Failed):\s*/, '').trim() || 'EDHREC didn’t answer.';

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
export function rankingSummary(r: Pick<RankingOut, 'total' | 'pool' | 'owned' | 'unused'>): string {
  const lead = r.total === r.pool ? `${r.pool} ranked` : `${r.total} of ${r.pool} match`;
  return `${lead} · you own ${r.owned} · ${r.unused} unused`;
}

/** When EDHREC stopped answering partway through the list, the pool holds only
 *  the pages read: say so plainly, with the way out (Refresh). */
export function partialRankingNote(r: Pick<RankingOut, 'base' | 'pool_complete' | 'pool_partial_reason'>): string | null {
  if (r.pool_complete !== false) return null;
  const why = r.pool_partial_reason === 'rate_limited' ? 'EDHREC limited the read' : 'EDHREC stopped answering partway through';
  return `Showing the first ${r.base.toLocaleString('en-US')} — ${why}. Refresh to fetch the rest.`;
}

/** A calm note for a list EDHREC left empty (a set family with no commanders yet). */
export function emptyRankingNote(s: Pick<RankingsState, 'rank' | 'fam'>, famName?: string): string {
  if (filtersApply(s) && value(s.fam)) return `EDHREC lists no commanders from ${famName ?? s.fam?.toUpperCase()} yet.`;
  return 'EDHREC lists nothing here yet.';
}

const front = (typeLine: string | null | undefined) => (typeLine ?? '').split(' // ')[0];

/** The card type without its subtypes: "Legendary Creature — Elf" → "Creature"
 *  for commanders (they're all legendary), "Legendary Creature" otherwise. */
export function cardType(typeLine: string | null | undefined, scope: RankScope): string | null {
  let t = front(typeLine).split(' — ')[0].trim();
  if (scope === 'commanders') t = t.replace(/\bLegendary\s+/, '');
  return t || null;
}

/** The subtypes after the dash: "Legendary Creature — Elf Druid" → "Elf Druid". */
export function creatureType(typeLine: string | null | undefined): string | null {
  return front(typeLine).split(' — ')[1]?.trim() || null;
}

/** A ranked row's type columns; a partner pairing shows both cards' (once when they agree). */
export function rankedTypes(scope: RankScope, r: RankedOut): { card: string | null; sub: string | null } {
  const lines = [r.facts.type_line, r.facts.partner?.type_line];
  const join = (xs: (string | null)[]) => [...new Set(xs.filter((x): x is string => Boolean(x)))].join(' / ') || null;
  return {
    card: join(lines.map((l) => cardType(l, scope))),
    sub: join(lines.map(creatureType)),
  };
}

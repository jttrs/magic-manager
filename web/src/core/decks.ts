// Deck Manager derivations: the recipe list (every precon / Jumpstart pack in the
// catalog plus your own decks) — filters, groups, source + status markers and
// unused-card coverage copy — a deck's cards as guide sections (Commander ·
// Creatures · … · Sideboard · Tokens), and the add-cards review lines for "add
// this deck / these cards to my collection". Framework-free; every number comes
// from the engine (magic_manager.recipes).
import type { DeckCardOut, RecipeOut, ResolvedLineOut } from './api';
import { TYPE_GROUPS, typeGroup } from './cardFacts';
import { facetCounts, passes, type Facets } from './facets';
import { fmtInt } from './format';
import { treatmentLabels, type GuideCard, type GuideGroup } from './guideCard';
import { DECK_STATUS, RECIPE_ORIGINS, type DeckStatus, type DecksSearch } from './search';

export const DECK_GROUPS = ['set', 'year', 'kind', 'type', 'color', 'state'] as const;
export type DeckGroupBy = (typeof DECK_GROUPS)[number];
export const DECK_GROUP_LABEL: Record<DeckGroupBy, string> = { set: 'Set', year: 'Year', kind: 'Source', type: 'Deck type', color: 'Color', state: 'Status' };

export type RecipeOrigin = (typeof RECIPE_ORIGINS)[number];
export const SOURCE_LABEL: Record<RecipeOrigin, string> = { precon: 'Wizards', import: 'Imported', custom: 'Custom' };
/** Jumpstart is a deck type, not a source. */
export const isJumpstart = (r: Pick<RecipeOut, 'deck_type'>): boolean => r.deck_type === 'Jumpstart';
/** The deck types shown until the list is narrowed to a set or the type picker is used. */
const DEFAULT_DECK_TYPES = ['Commander'];
const ALL_TYPES = 'all';
/** The deck-type filter in effect (null = every type): `['all']` = every type; a chosen list is
 *  that list; untouched = Commander, unless a set is chosen. */
export function effectiveTypes(f: Pick<DecksSearch, 'types' | 'sets'>): string[] | null {
  if (f.types.includes(ALL_TYPES)) return null;
  if (f.types.length) return f.types;
  return f.sets.length ? null : DEFAULT_DECK_TYPES;
}
/** The picker's value → the URL's `types` ("show all" is stored so it sticks). */
export const typesToSearch = (v: string[]): string[] => (v.length ? v : [ALL_TYPES]);
const STATUS_LABEL: Record<DeckStatus, string> = { built: 'Built', buildable: 'Buildable', unbuilt: 'Unbuilt' };
/** How many cards short a recipe may be and still count as Buildable (Settings → Decks; the engine's CLOSE_SHORT). */
export const DEFAULT_BUILDABLE_SHORT = 3;

export type RecipeFilters = Pick<DecksSearch, 'q' | 'origins' | 'status' | 'types' | 'sets'>;

/** A recipe's decklist status: Built (an assembled copy), Buildable (not built, read, and your unused
 *  cards leave it at most `threshold` cards short) or Unbuilt (everything else, incl. unread recipes). */
export function deckStatus(r: Pick<RecipeOut, 'built' | 'read' | 'short'>, threshold: number = DEFAULT_BUILDABLE_SHORT): DeckStatus {
  if (r.built > 0) return 'built';
  return r.read && r.short != null && r.short <= threshold ? 'buildable' : 'unbuilt';
}
/** How far your unused cards get a read recipe: ready (nothing short), close (at most `threshold` short) or far;
 *  null when its card list hasn't been read. Derived from `short` and the user's threshold, never the server's status. */
export function readiness(r: Pick<RecipeOut, 'read' | 'short'>, threshold: number = DEFAULT_BUILDABLE_SHORT): 'ready' | 'close' | 'far' | null {
  if (!r.read || r.short == null) return null;
  return r.short === 0 ? 'ready' : r.short <= threshold ? 'close' : 'far';
}
/** Not built and ready to build from unused cards, whatever the threshold. */
const readyFromUnused = (r: Pick<RecipeOut, 'built' | 'read' | 'short'>) => r.built === 0 && readiness(r) === 'ready';

/** One predicate per recipe filter (see `core/facets`). */
function recipeFacets(f: RecipeFilters, threshold: number): Facets<RecipeOut, keyof RecipeFilters> {
  const q = f.q.trim().toLowerCase();
  const types = effectiveTypes(f);
  return {
    origins: (r) => !f.origins.length || f.origins.includes(r.origin),
    status: (r) => f.status.includes(deckStatus(r, threshold)),
    types: (r) => types == null || types.includes(r.deck_type),
    sets: (r) => !f.sets.length || (!!r.set_code && f.sets.includes(r.set_code)),
    q: (r) => !q || [r.name, r.set_name, r.set_code, r.source, r.author, r.deck_type, SOURCE_LABEL[r.origin]].some((v) => v?.toLowerCase().includes(q)),
  };
}

export function filterRecipes(rs: readonly RecipeOut[], f: RecipeFilters, threshold: number = DEFAULT_BUILDABLE_SHORT): RecipeOut[] {
  const facets = recipeFacets(f, threshold);
  return rs.filter((r) => passes(r, facets));
}

type Count = { value: string; label: string; count: number };

/** Deck-type options: most decks first, then by name. */
const typeOptions = (counts: [string, number][]): Count[] =>
  [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([v, n]): Count => ({ value: v, label: v, count: n }));

/** Deck-type options with their deck counts. */
export function deckTypeCounts(rows: readonly { deck_type: string }[]): Count[] {
  const n = new Map<string, number>();
  for (const r of rows) n.set(r.deck_type, (n.get(r.deck_type) ?? 0) + 1);
  return typeOptions([...n]);
}

/** Counts per option of one control, under every OTHER filter. */
export function optionCounts(rs: readonly RecipeOut[], f: RecipeFilters, threshold: number = DEFAULT_BUILDABLE_SHORT) {
  const facets = recipeFacets(f, threshold);
  const by = (skip: keyof RecipeFilters, key: (r: RecipeOut) => string | null) => facetCounts(rs, facets, skip, key);
  const origins = by('origins', (r) => r.origin);
  const status = by('status', (r) => deckStatus(r, threshold));
  const types = by('types', (r) => r.deck_type);
  // Choosing a set lifts the Commander default, so sets are counted without it — a
  // Jumpstart-only set must stay listed to be pickable.
  const setFacets = f.types.length ? facets : recipeFacets({ ...f, types: [ALL_TYPES] }, threshold);
  const sets = facetCounts(rs, setFacets, 'sets', (r) => r.set_code);
  const names = new Map<string, { name: string; released: string }>();
  for (const r of rs) if (r.set_code && !names.has(r.set_code)) names.set(r.set_code, { name: r.set_name ?? r.set_code.toUpperCase(), released: r.released ?? '' });
  const sorted = (m: Map<string, number>, keepKeys: readonly string[] = []): [string, number][] =>
    [...new Set([...m.keys(), ...keepKeys])].map((k) => [k, m.get(k) ?? 0] as [string, number]);
  return {
    origins: RECIPE_ORIGINS.map((k) => ({ value: k, label: SOURCE_LABEL[k], count: origins.get(k) ?? 0 })),
    status: DECK_STATUS.map((k) => ({ value: k, label: STATUS_LABEL[k], count: status.get(k) ?? 0 })),
    types: typeOptions(sorted(types, f.types.filter((t) => t !== ALL_TYPES))),
    sets: sorted(sets, f.sets)
      .sort((a, b) => (names.get(b[0])?.released ?? '').localeCompare(names.get(a[0])?.released ?? '') || a[0].localeCompare(b[0]))
      .map(([v, n]): Count => ({ value: v, label: `${names.get(v)?.name ?? v.toUpperCase()} · ${v.toUpperCase()}`, count: n })),
  };
}

const COLOR_NAME: Record<string, string> = { C: 'Colorless', W: 'White', U: 'Blue', B: 'Black', R: 'Red', G: 'Green' };
const MULTI = 'Multicolor';
const COLOR_ORDER = ['Colorless', 'White', 'Blue', 'Black', 'Red', 'Green', MULTI];
/** "White" for mono, the letters ("WU") for multicolor recipes. */
export const colorLabel = (code: string): string => COLOR_NAME[code] ?? code;

export type DeckGroup = { key: string; label: string; decks: RecipeOut[]; ready: number };

const ORIGIN_RANK: Record<RecipeOrigin, string> = { precon: '2', import: '1', custom: '0' };
const STATUS_RANK: Record<DeckStatus, string> = { built: '2', buildable: '1', unbuilt: '0' };

/** Group recipes; groups newest first for set/year, a fixed order otherwise. Recipes keep input order. */
export function groupRecipes(rs: readonly RecipeOut[], by: DeckGroupBy, threshold: number = DEFAULT_BUILDABLE_SHORT): DeckGroup[] {
  const keyOf = (r: RecipeOut): [string, string, string] => {
    switch (by) {
      case 'set':
        return [r.set_code ?? '~', r.set_name ?? r.set_code?.toUpperCase() ?? 'No set', r.released ?? ''];
      case 'year': {
        const y = r.released?.slice(0, 4) ?? '';
        return [y || '~', y || 'Undated', y];
      }
      case 'kind':
        return [r.origin, SOURCE_LABEL[r.origin], ORIGIN_RANK[r.origin]];
      case 'state':
        {
        const st = deckStatus(r, threshold);
        return [st, STATUS_LABEL[st], STATUS_RANK[st]];
      }
      case 'type':
        return [r.deck_type, r.deck_type, ''];
      case 'color': {
        if (!r.color) return ['~', 'Not read yet', ''];
        const g = COLOR_NAME[r.color] ?? MULTI;
        return [g, g, String(9 - COLOR_ORDER.indexOf(g))];
      }
    }
  };
  const m = new Map<string, DeckGroup & { rank: string }>();
  for (const r of rs) {
    const [key, label, rank] = keyOf(r);
    const g = m.get(key) ?? { key, label, decks: [], rank, ready: 0 };
    if (rank > g.rank) g.rank = rank;
    g.decks.push(r);
    if (readyFromUnused(r)) g.ready += 1;
    m.set(key, g);
  }
  const groups = [...m.values()];
  if (by === 'type') groups.sort((a, b) => b.decks.length - a.decks.length || a.label.localeCompare(b.label));
  else groups.sort((a, b) => (a.key === '~' ? 1 : b.key === '~' ? -1 : b.rank.localeCompare(a.rank) || a.label.localeCompare(b.label)));
  return groups.map(({ key, label, decks, ready }) => ({ key, label, decks, ready }));
}

/** What you own of a recipe: "×2 built" · "1 loose" (precons/packs) · "not built" (your decks) · "not owned". */
export function ownershipLabel(r: Pick<RecipeOut, 'ownership' | 'built' | 'loose' | 'origin'>): string {
  if (r.ownership === 'built') return `×${fmtInt(r.built)} built`;
  if (r.ownership === 'loose') return r.origin === 'import' || r.origin === 'custom' ? 'not built' : `${fmtInt(r.loose)} loose`;
  return 'not owned';
}

/** How far unused cards get you: "All 20 unused" · "2 short" · "13 of 20 unused"; '' when unknown or built. */
export function coverage(r: Pick<RecipeOut, 'have' | 'short' | 'read' | 'built'>, threshold: number = DEFAULT_BUILDABLE_SHORT): string {
  if (r.have == null || r.short == null || r.built > 0) return '';
  const total = r.have + r.short;
  const ready = readiness(r, threshold);
  if (ready === 'ready') return `All ${fmtInt(total)} unused`;
  if (ready === 'close') return `${fmtInt(r.short)} short`;
  return `${fmtInt(r.have)} of ${fmtInt(total)} unused`;
}

/** The one Jumpstart set the list is narrowed to (its shopping lists apply), else null. */
export function jumpstartSet(rs: readonly RecipeOut[], f: Pick<DecksSearch, 'sets'>): string | null {
  if (f.sets.length !== 1) return null;
  return rs.some((r) => isJumpstart(r) && r.set_code === f.sets[0]) ? f.sets[0] : null;
}

/** Catalog recipes of the one chosen set whose card lists haven't been read. */
export function unreadInSet(rs: readonly RecipeOut[], f: Pick<DecksSearch, 'sets'>): number {
  if (f.sets.length !== 1) return 0;
  return rs.filter((r) => r.set_code === f.sets[0] && !r.read).length;
}

/** The catalog fileName behind a `fn:` recipe key. */
export const recipeFileName = (key?: string): string | undefined => (key?.startsWith('fn:') ? key.slice(3) : undefined);

/** Inspector section for a deck card: board first, then type. */
export function deckSection(c: Pick<DeckCardOut, 'board' | 'type_line'>): string {
  switch (c.board) {
    case 'commander': return 'Commander';
    case 'companion': return 'Companion';
    case 'side': return 'Sideboard';
    case 'maybe': return 'Maybe';
    case 'token': return 'Tokens';
    default: return typeGroup(c.type_line);
  }
}
export const DECK_SECTIONS = ['Commander', 'Companion', ...TYPE_GROUPS, 'Sideboard', 'Maybe', 'Tokens'] as const;

/** A deck card → the shared guide view-model. Key is per row (a printing can sit on two boards).
 *  `recipe`: a catalog recipe you don't own — missing when your unused copies don't cover it. */
export function fromDeckCard(c: DeckCardOut, recipe = false): GuideCard {
  const p = c.printing;
  const owned = Object.values(p.owned ?? {}).reduce((s, n) => s + n, 0);
  const finish = c.finish === 'either' ? null : c.finish;
  return {
    key: `${p.scryfall_id}|${c.board}|${c.finish}`,
    scryfallId: p.scryfall_id,
    name: p.name,
    image: p.image_uri,
    href: `https://scryfall.com/card/${p.set_code}/${encodeURIComponent(p.collector_number)}`,
    setCode: p.set_code.toUpperCase(),
    cn: p.collector_number,
    rarity: p.rarity,
    finish,
    price: (finish === 'foil' ? p.price_usd_foil : p.price_usd) ?? p.price_usd ?? p.price_usd_foil,
    pct: null,
    bars: null,
    group: deckSection(c),
    cmc: c.cmc,
    colors: c.color_identity,
    typeGroup: typeGroup(c.type_line),
    released: p.released_at,
    owned: p.owned as GuideCard['owned'],
    missing: recipe ? c.free < c.count : owned === 0,
    tags: [`×${c.count} in deck`, ...(c.pledged_here ? [`${c.pledged_here} pledged`] : []), ...treatmentLabels(p.treatment)],
    lines: { plain: `${c.count} ${p.name}` },
    note: recipe ? (c.free >= c.count ? `${fmtInt(c.free)} unused` : c.free ? `${fmtInt(c.free)} of ${fmtInt(c.count)} unused` : 'None unused') : c.free ? `${fmtInt(c.free)} unused` : null,
    typeLine: c.type_line,
    finishes: p.finishes,
    prices: { nonfoil: p.finishes.includes('nonfoil') ? p.price_usd : null, foil: p.finishes.includes('foil') ? p.price_usd_foil : null },
  };
}

export function deckGuideGroups(cards: readonly DeckCardOut[], recipe = false): GuideGroup[] {
  const m = new Map<string, GuideCard[]>();
  for (const c of cards) {
    const g = deckSection(c);
    m.set(g, [...(m.get(g) ?? []), fromDeckCard(c, recipe)]);
  }
  return DECK_SECTIONS.filter((s) => m.has(s)).map((s) => {
    const items = m.get(s)!;
    const n = cards.filter((c) => deckSection(c) === s).reduce((t, c) => t + c.count, 0);
    return { key: s, label: n === items.length ? s : `${s} · ${n}`, items };
  });
}

/** Deck cards (optionally only `keys`) as exact add-cards review lines. Tokens excluded unless asked. */
export function deckReviewLines(cards: readonly DeckCardOut[], keys?: ReadonlySet<string>, withTokens = false): ResolvedLineOut[] {
  return cards
    .filter((c) => (withTokens || c.board !== 'token') && (!keys || keys.has(fromDeckCard(c).key)))
    .map((c) => ({
      line: 0,
      raw: `${c.count} ${c.printing.name}`,
      qty: c.count,
      name: c.printing.name,
      finish: c.finish === 'foil' ? 'foil' : 'nonfoil',
      section: c.board,
      status: 'exact',
      candidates: [c.printing],
      chosen: c.printing.scryfall_id,
      note: null,
    }));
}

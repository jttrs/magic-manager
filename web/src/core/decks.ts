// Deck Manager derivations: the recipe list (every precon / Jumpstart pack in the
// catalog plus your own decks) — filters, groups, kind + ownership markers and
// free-card coverage copy — a deck's cards as guide sections (Commander ·
// Creatures · … · Sideboard · Tokens), and the add-cards review lines for "add
// this deck / these cards to my collection". Framework-free; every number comes
// from the engine (magic_manager.recipes).
import type { DeckCardOut, RecipeOut, ResolvedLineOut } from './api';
import { TYPE_GROUPS, typeGroup } from './cardFacts';
import { fmtCount, fmtInt } from './format';
import { treatmentLabels, type GuideCard, type GuideGroup } from './guideCard';
import { COVER, OWNERSHIP, RECIPE_KINDS, type DecksSearch } from './search';

export const DECK_GROUPS = ['set', 'year', 'kind', 'type', 'color', 'state'] as const;
export type DeckGroupBy = (typeof DECK_GROUPS)[number];
export const DECK_GROUP_LABEL: Record<DeckGroupBy, string> = { set: 'Set', year: 'Year', kind: 'Kind', type: 'Deck type', color: 'Colour', state: 'Ownership' };

export type RecipeKind = (typeof RECIPE_KINDS)[number];
export type Ownership = (typeof OWNERSHIP)[number];
export type Cover = (typeof COVER)[number];
export const KIND_LABEL: Record<RecipeKind, string> = { precon: 'Precon', jumpstart: 'Jumpstart', import: 'Imported', custom: 'Custom' };
const OWNERSHIP_LABEL: Record<Ownership, string> = { built: 'Built', loose: 'Loose', none: 'Not owned' };
/** The sidebar's "You own" toggles: Built · Loose · None. */
const OWN_TOGGLE_LABEL: Record<Ownership, string> = { built: 'Built', loose: 'Loose', none: 'None' };
export const COVER_LABEL: Record<Cover, string> = { any: 'Any', build: 'Ready to build', close: 'Ready or close' };

export type RecipeFilters = Pick<DecksSearch, 'q' | 'kinds' | 'own' | 'cover' | 'types' | 'sets'>;

/** Free-card status when it applies: a built recipe's cards are pledged, so it has none. */
const coverStatus = (r: Pick<RecipeOut, 'built' | 'status'>) => (r.built === 0 ? r.status : null);
const readyFromFree = (r: Pick<RecipeOut, 'built' | 'status'>) => coverStatus(r) === 'build';

const coverKeep = (r: RecipeOut, cover: Cover) =>
  cover === 'any' || readyFromFree(r) || (cover === 'close' && coverStatus(r) === 'close');

/** Every filter except `skip` (so a control can count what each of its options would show). */
function keep(r: RecipeOut, f: RecipeFilters, skip?: keyof RecipeFilters): boolean {
  const q = f.q.trim().toLowerCase();
  return (
    (skip === 'kinds' || !f.kinds.length || f.kinds.includes(r.kind)) &&
    (skip === 'own' || f.own.includes(r.ownership)) &&
    (skip === 'cover' || coverKeep(r, f.cover)) &&
    (skip === 'types' || !f.types.length || f.types.includes(r.deck_type)) &&
    (skip === 'sets' || !f.sets.length || (!!r.set_code && f.sets.includes(r.set_code))) &&
    (skip === 'q' || !q || [r.name, r.set_name, r.set_code, r.source, r.author, r.deck_type, KIND_LABEL[r.kind]].some((v) => v?.toLowerCase().includes(q)))
  );
}

export function filterRecipes(rs: readonly RecipeOut[], f: RecipeFilters): RecipeOut[] {
  return rs.filter((r) => keep(r, f));
}

type Count = { value: string; label: string; count: number };

/** Counts per option of one control, under every OTHER filter. */
export function optionCounts(rs: readonly RecipeOut[], f: RecipeFilters) {
  const by = <K extends keyof RecipeFilters>(skip: K, key: (r: RecipeOut) => string | null) => {
    const m = new Map<string, number>();
    for (const r of rs) {
      const k = key(r);
      if (k != null && keep(r, f, skip)) m.set(k, (m.get(k) ?? 0) + 1);
    }
    return m;
  };
  const kinds = by('kinds', (r) => r.kind);
  const own = by('own', (r) => r.ownership);
  const types = by('types', (r) => r.deck_type);
  const sets = by('sets', (r) => r.set_code);
  const cover = by('cover', coverStatus);
  const names = new Map<string, { name: string; released: string }>();
  for (const r of rs) if (r.set_code && !names.has(r.set_code)) names.set(r.set_code, { name: r.set_name ?? r.set_code.toUpperCase(), released: r.released ?? '' });
  const sorted = (m: Map<string, number>, keepKeys: readonly string[] = []): [string, number][] =>
    [...new Set([...m.keys(), ...keepKeys])].map((k) => [k, m.get(k) ?? 0] as [string, number]);
  return {
    kinds: RECIPE_KINDS.map((k) => ({ value: k, label: KIND_LABEL[k], count: kinds.get(k) ?? 0 })),
    own: OWNERSHIP.map((k) => ({ value: k, label: OWN_TOGGLE_LABEL[k], count: own.get(k) ?? 0 })),
    cover: { any: null, build: cover.get('build') ?? 0, close: (cover.get('build') ?? 0) + (cover.get('close') ?? 0) },
    types: sorted(types, f.types).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([v, n]): Count => ({ value: v, label: v, count: n })),
    sets: sorted(sets, f.sets)
      .sort((a, b) => (names.get(b[0])?.released ?? '').localeCompare(names.get(a[0])?.released ?? '') || a[0].localeCompare(b[0]))
      .map(([v, n]): Count => ({ value: v, label: `${names.get(v)?.name ?? v.toUpperCase()} · ${v.toUpperCase()}`, count: n })),
  };
}

const COLOR_NAME: Record<string, string> = { C: 'Colorless', W: 'White', U: 'Blue', B: 'Black', R: 'Red', G: 'Green' };
const MULTI = 'Multicolour';
const COLOR_ORDER = ['Colorless', 'White', 'Blue', 'Black', 'Red', 'Green', MULTI];
/** "White" for mono, the letters ("WU") for multicolour recipes. */
export const colorLabel = (code: string): string => COLOR_NAME[code] ?? code;

export type DeckGroup = { key: string; label: string; decks: RecipeOut[]; ready: number };

const KIND_RANK: Record<RecipeKind, string> = { precon: '3', jumpstart: '2', import: '1', custom: '0' };
const OWN_RANK: Record<Ownership, string> = { built: '2', loose: '1', none: '0' };

/** Group recipes; groups newest first for set/year, a fixed order otherwise. Recipes keep input order. */
export function groupRecipes(rs: readonly RecipeOut[], by: DeckGroupBy): DeckGroup[] {
  const keyOf = (r: RecipeOut): [string, string, string] => {
    switch (by) {
      case 'set':
        return [r.set_code ?? '~', r.set_name ?? r.set_code?.toUpperCase() ?? 'No set', r.released ?? ''];
      case 'year': {
        const y = r.released?.slice(0, 4) ?? '';
        return [y || '~', y || 'Undated', y];
      }
      case 'kind':
        return [r.kind, KIND_LABEL[r.kind], KIND_RANK[r.kind]];
      case 'state':
        return [r.ownership, OWNERSHIP_LABEL[r.ownership], OWN_RANK[r.ownership]];
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
    if (readyFromFree(r)) g.ready += 1;
    m.set(key, g);
  }
  const groups = [...m.values()];
  if (by === 'type') groups.sort((a, b) => b.decks.length - a.decks.length || a.label.localeCompare(b.label));
  else groups.sort((a, b) => (a.key === '~' ? 1 : b.key === '~' ? -1 : b.rank.localeCompare(a.rank) || a.label.localeCompare(b.label)));
  return groups.map(({ key, label, decks, ready }) => ({ key, label, decks, ready }));
}

/** What you own of a recipe: "×2 built" · "1 loose" (precons/packs) · "not built" (your decks) · "not owned". */
export function ownershipLabel(r: Pick<RecipeOut, 'ownership' | 'built' | 'loose' | 'kind'>): string {
  if (r.ownership === 'built') return `×${fmtInt(r.built)} built`;
  if (r.ownership === 'loose') return r.kind === 'import' || r.kind === 'custom' ? 'not built' : `${fmtInt(r.loose)} loose`;
  return 'not owned';
}

/** How far free cards get you: "All 20 free" · "2 short" · "13 of 20 free"; '' when unknown or built. */
export function coverage(r: Pick<RecipeOut, 'have' | 'short' | 'status' | 'built'>): string {
  if (r.have == null || r.short == null || r.built > 0) return '';
  const total = r.have + r.short;
  if (r.status === 'build') return `All ${fmtInt(total)} free`;
  if (r.status === 'close') return `${fmtInt(r.short)} short`;
  return `${fmtInt(r.have)} of ${fmtInt(total)} free`;
}

/** The sheet summary: what's listed and what you own of it. */
export function recipeSummary(shown: readonly RecipeOut[]): string {
  const built = shown.filter((r) => r.ownership === 'built').length;
  const ready = shown.filter(readyFromFree).length;
  return [fmtCount(shown.length, 'recipe'), built ? `${fmtInt(built)} built` : '', ready ? `${fmtInt(ready)} ready from free cards` : ''].filter(Boolean).join(' · ');
}

/** The one Jumpstart set the list is narrowed to (its shopping lists apply), else null. */
export function jumpstartSet(rs: readonly RecipeOut[], f: Pick<DecksSearch, 'sets'>): string | null {
  if (f.sets.length !== 1) return null;
  return rs.some((r) => r.kind === 'jumpstart' && r.set_code === f.sets[0]) ? f.sets[0] : null;
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
 *  `recipe`: a catalog recipe you don't own — missing when your free copies don't cover it. */
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
    lines: { plain: `${c.count} ${p.name}`, manapool: '', tcgplayer: '' },
    note: recipe ? (c.free >= c.count ? `${fmtInt(c.free)} free` : c.free ? `${fmtInt(c.free)} of ${fmtInt(c.count)} free` : 'None free') : c.free ? `${c.free} free to use` : null,
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

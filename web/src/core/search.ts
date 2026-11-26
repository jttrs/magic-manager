// URL state contracts (zod). Every filter/sort/visibility the views expose lives in
// the URL so any view is a shareable deep link. Framework-free: the router only
// binds these schemas.
import { z } from 'zod';
import { BASES, DEAL_SORTS, PRODUCT_TYPES } from './deals';
import { SLD_BASES, SLD_EDITIONS, SLD_SORTS } from './secretLair';

/** Default sort hierarchies (URL form) — the schema defaults and the header SortControl's "changed" baseline. */
export const COMPARE_SORT_DEFAULT = 'inclusion,name';
/** Newest family first, then set name, then collector number. */
export const COLLECTION_SORT_DEFAULT = 'released,set,cn';

export const BUCKETS = ['a_only', 'both', 'b_only'] as const;
export type Bucket = (typeof BUCKETS)[number];

/** A URL list: an array (old JSON links), a comma list (`dft,tla` — app/urlCodec.ts writes
 *  these), or one bare value. */
export const list = <T extends z.ZodTypeAny>(item: T) =>
  z.preprocess(
    (v) => (v == null ? undefined : Array.isArray(v) ? v : typeof v === 'string' ? splitList(v) : [v]),
    z.array(item),
  );
const splitList = (v: string): string[] => (v === '' ? [] : v.split(','));

const VIEW_TYPES = ['grid', 'list'] as const;
const view = z.enum(VIEW_TYPES).catch('grid').default('grid');

const GROUP_BYS = ['lists', 'function'] as const;
export type GroupBy = (typeof GROUP_BYS)[number];

const ROLES = ['commander', 'card'] as const;
export type Role = (typeof ROLES)[number];

const EXPLORE_MODES = ['card', 'rankings', 'earmarked', 'surf'] as const;
export const EARMARK_REASONS = ['all', 'collect', 'deck', 'none'] as const;
export type EarmarkReasonFilter = (typeof EARMARK_REASONS)[number];
export type ExploreMode = (typeof EXPLORE_MODES)[number];
export const RANK_SCOPES = ['commanders', 'cards'] as const;
export type RankScope = (typeof RANK_SCOPES)[number];
export const RANK_TIMEFRAMES = ['week', 'month', 'year'] as const;
export type RankTimeframe = (typeof RANK_TIMEFRAMES)[number];
/** Ownership filter; `unused` = a copy not in a built deck (old links said `free`). */
export const RANK_OWN = ['all', 'owned', 'unused'] as const;
export type RankOwn = (typeof RANK_OWN)[number];

export const compareSearch = z.object({
  /** Explore mode; unset = a card when one is picked, else rankings. */
  mode: z.enum(EXPLORE_MODES).optional().catch(undefined),
  /** Rankings: which list; color / tag / set narrow commander lists and combine; timeframe. */
  rank: z.enum(RANK_SCOPES).catch('commanders').default('commanders'),
  color: z.string().optional().catch(undefined),
  tag: z.string().optional().catch(undefined),
  fam: z.string().optional().catch(undefined),
  tf: z.enum(RANK_TIMEFRAMES).catch('week').default('week'),
  own: z.preprocess((v) => (v === 'free' ? 'unused' : v), z.enum(RANK_OWN)).catch('all').default('all'),
  rq: z.string().catch('').default(''),
  rview: z.enum(['grid', 'list']).catch('grid').default('grid'),
  /** Earmarked: reason and deck filters. */
  er: z.enum(EARMARK_REASONS).catch('all').default('all'),
  ed: z.string().optional().catch(undefined),
  a: z.string().optional().catch(undefined),
  b: z.string().optional().catch(undefined),
  /** Explore role; unset = commander when A can lead, else card. */
  role: z.enum(ROLES).optional().catch(undefined),
  show: list(z.enum(BUCKETS)).catch([...BUCKETS]).default([...BUCKETS]),
  q: z.string().catch('').default(''),
  tags: list(z.string()).catch([]).default([]),
  /** Encoded sort rules (core/sort.ts), e.g. `inclusion,name`. */
  sort: z.string().catch(COMPARE_SORT_DEFAULT).default(COMPARE_SORT_DEFAULT),
  groupBy: z.enum(GROUP_BYS).catch('lists').default('lists'),
  view,
  /** Card surfer (the Surfer tab): its source + filters (core/surf.ts codec). */
  surf: z.string().optional().catch(undefined),
});
export type CompareSearch = z.infer<typeof compareSearch>;

export const SHOW = ['owned', 'missing'] as const;

export const collectionSearch = z.object({
  /** Set families to look at; empty = every family you own. */
  families: list(z.string()).catch([]).default([]),
  /** Owned only by default: the collection you have. Add `missing` for the gaps. */
  show: list(z.enum(SHOW)).catch(['owned']).default(['owned']),
  /** Unchecked card-type traits (core/collection.ts TRAITS keys). */
  exclude: list(z.string()).catch([]).default([]),
  q: z.string().catch('').default(''),
  /** Scryfall Tagger function roots to keep (OR); empty = all. */
  fn: list(z.string()).catch([]).default([]),
  /** Only cards you earmarked (any printing). */
  em: z.boolean().catch(false).default(false),
  sort: z.string().catch(COLLECTION_SORT_DEFAULT).default(COLLECTION_SORT_DEFAULT),
  view,
  /** Checklist mode: count owned copies inline (views/collection/Checklist*). */
  count: z.boolean().catch(false).default(false),
});
export type CollectionSearch = z.infer<typeof collectionSearch>;

const DECK_GROUPS = ['set', 'year', 'kind', 'type', 'color', 'state'] as const;
export const RECIPE_ORIGINS = ['precon', 'import', 'custom'] as const;
/** Decklist status: built (an assembled copy), buildable (not built, your unused cards cover it
 *  within the Settings → Decks threshold) or unbuilt (everything else, incl. unread catalog recipes). */
export const DECK_STATUS = ['built', 'buildable', 'unbuilt'] as const;
export type DeckStatus = (typeof DECK_STATUS)[number];
const SHOPS = ['buildable', 'packs'] as const;

export const decksSearch = z.object({
  /** The recipe open in the inspector: your deck's slug, or `fn:<fileName>` for a catalog recipe. */
  deck: z.string().optional().catch(undefined),
  /** `origin` (old links) groups by kind now. */
  group: z.preprocess((v) => (v === 'origin' ? 'kind' : v), z.enum(DECK_GROUPS)).catch('set').default('set'),
  /** Where the recipe comes from (Wizards / Imported / Custom); empty = all. */
  origins: list(z.enum(RECIPE_ORIGINS)).catch([]).default([]),
  /** Decklist status to keep; built only by default. */
  status: list(z.enum(DECK_STATUS)).catch(['built']).default(['built']),
  /** Deck types to keep (deck_view.deck_type labels). Absent = the default (Commander, unless a set
   *  is chosen); `['all']` = every type (core/decks.ts effectiveTypes). */
  types: list(z.string()).catch([]).default([]),
  /** Set codes to keep; empty = all. One Jumpstart set opens its shopping lists. */
  sets: list(z.string()).catch([]).default([]),
  q: z.string().catch('').default(''),
  /** Jumpstart shopping list for the one chosen set. */
  shop: z.enum(SHOPS).catch('buildable').default('buildable'),
  /** Open the "add deck cards to collection" review once (after an import). */
  add: z.boolean().optional().catch(undefined),
  /** Legacy `built=true` links; the route turns them into `status=built`. */
  built: z.boolean().optional().catch(undefined),
  view,
});
export type DecksSearch = z.infer<typeof decksSearch>;

/** Old `/decks` links: `source=` (the old key) → `origins`; `kinds=` precon|import|custom → `origins`,
 *  `jumpstart` → the Jumpstart deck type. The route applies this before validating. */
export function legacyDecksSearch(raw: Record<string, unknown>): Record<string, unknown> {
  let next = legacyStatus(raw);
  if ('source' in next) {
    const { source, ...rest } = next;
    next = 'origins' in rest ? rest : { ...rest, origins: source };
  }
  if (!('kinds' in next)) return next;
  const { kinds, ...rest } = next;
  const old = (Array.isArray(kinds) ? kinds : kinds == null ? [] : [kinds]).map(String);
  const origins = old.filter((k) => (RECIPE_ORIGINS as readonly string[]).includes(k));
  const types = Array.isArray(rest.types) ? rest.types.map(String) : [];
  const jumpstart = old.includes('jumpstart');
  if (jumpstart && !origins.length) {
    // jumpstart alone: the Jumpstart deck type
    if (!types.includes('Jumpstart')) types.push('Jumpstart');
  } else if (jumpstart && !origins.includes('precon')) {
    origins.push('precon'); // jumpstart + others widened: Jumpstart packs are Wizards products
  }
  // An old link showed every deck type; keep that rather than the newer Commander default.
  if (old.length && !types.length) types.push('all');
  const out: Record<string, unknown> = { ...rest };
  if (origins.length && !('origins' in rest)) out.origins = origins;
  if (types.length) out.types = types;
  return out;
}

/** Old `own=` (built|loose|none) + `cover=` (any|build|close) links → `status`. A cover filter meant
 *  "ready to build", so it becomes Buildable; otherwise built stays Built and loose / not owned became
 *  the not-built buckets. */
function legacyStatus(raw: Record<string, unknown>): Record<string, unknown> {
  if (!('own' in raw) && !('cover' in raw)) return raw;
  const { own, cover, ...rest } = raw;
  if ('status' in rest) return rest;
  const owned = (Array.isArray(own) ? own : typeof own === 'string' ? splitList(own) : own == null ? ['built', 'loose'] : []).map(String);
  const status: DeckStatus[] = [];
  if (cover === 'build' || cover === 'close') status.push('buildable');
  else {
    if (owned.includes('built')) status.push('built');
    if (owned.includes('loose') || owned.includes('none')) status.push('buildable', 'unbuilt');
  }
  return status.length ? { ...rest, status } : rest;
}

/** The `/decks` route's search validator: `decksSearch` after the legacy keys are mapped. A Standard Schema
 *  that keeps `decksSearch`'s input/output types, so the router's key-level link types are unchanged. */
export const decksSearchValidator = {
  '~standard': {
    ...decksSearch['~standard'],
    validate: (value: unknown) =>
      decksSearch['~standard'].validate(value && typeof value === 'object' ? legacyDecksSearch(value as Record<string, unknown>) : value),
  },
};

const MARKET_SUBJECTS = ['family', 'deck', 'sld', 'deals'] as const;
const MARKET_TABS = ['products', 'cards'] as const;
const CARD_PRICE_SORTS = ['savings', 'price', 'foil', 'set'] as const;
const FOIL_MAX = ['any', 'cheaper', '25', '50', '100'] as const;
const PRICE_BASES = ['floor', 'exact'] as const;

export const marketSearch = z.object({
  subject: z.enum(MARKET_SUBJECTS).catch('family').default('family'),
  /** Set family (any member code). */
  code: z.string().optional().catch(undefined),
  /** Deck slug. */
  deck: z.string().optional().catch(undefined),
  /** Deck types offered in the Deck picker (Decks' rule: empty = the default, Commander; ['all'] = every type). */
  dtypes: list(z.string()).catch([]).default([]),
  tab: z.enum(MARKET_TABS).catch('products').default('products'),
  q: z.string().catch('').default(''),
  /** Cards: only printings that cost more than the card's cheapest printing. */
  cheaper: z.boolean().catch(false).default(false),
  sort: z.enum(CARD_PRICE_SORTS).catch('savings').default('savings'),
  /** Cards: only printings whose plain foil costs at most this much over nonfoil. */
  foilMax: z.preprocess((v) => (typeof v === 'number' ? String(v) : v), z.enum(FOIL_MAX)).catch('any').default('any'),
  /** Deck: cheapest printings checked across every set on Scryfall (else local prices). */
  live: z.boolean().catch(false).default(false),
  /** Deck buy list: the cheapest printing of each card, or the deck's exact printing. */
  buyAt: z.enum(PRICE_BASES).catch('floor').default('floor'),
  /** Legacy Deals mode (`tabs` | `watching`): Deals is one watchlist now, with your open tabs pinned
   *  on top, so old links land there either way. Accepted and ignored. */
  deals: z.string().optional().catch(undefined),
  /** Deals: name or set code. */
  dq: z.string().catch('').default(''),
  /** Deals: only products offered by these stores; empty = all. */
  stores: list(z.string()).catch([]).default([]),
  /** Deals: product types to keep; empty = all. */
  types: list(z.enum(PRODUCT_TYPES)).catch([]).default([]),
  /** Deals: only products at least this % under the compared price. */
  minOff: z.union([z.literal(0), z.literal(10), z.literal(20), z.literal(30)]).catch(0).default(0),
  /** Deals: what the best price is compared to. */
  basis: z.enum(BASES).catch('market').default('market'),
  dsort: z.enum(DEAL_SORTS).catch('gap_pct').default('gap_pct'),
  inStock: z.boolean().catch(false).default(false),
  /** Deals: only products whose best in-stock price meets their target. */
  atTarget: z.boolean().catch(false).default(false),
  /** Secret Lair: the edition each drop is valued at. */
  edition: z.enum(SLD_EDITIONS).catch('nonfoil').default('nonfoil'),
  /** Secret Lair: how many of the newest drops to list. */
  sldN: z.number().int().min(1).max(200).catch(30).default(30),
  /** Secret Lair: what the sealed price is compared to. */
  sbasis: z.enum(SLD_BASES).catch('exact').default('exact'),
  ssort: z.enum(SLD_SORTS).catch('gap_pct').default('gap_pct'),
  /** Deals: the product open in the inspector (its key). */
  item: z.string().optional().catch(undefined),
});
export type MarketSearch = z.infer<typeof marketSearch>;

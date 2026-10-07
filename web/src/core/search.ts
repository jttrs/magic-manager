// URL state contracts (zod). Every filter/sort/visibility the views expose lives in
// the URL so any view is a shareable deep link. Framework-free: the router only
// binds these schemas.
import { z } from 'zod';
import { BASES, DEAL_SORTS, PRODUCT_TYPES } from './deals';
import { SLD_BASES, SLD_EDITIONS, SLD_SORTS } from './secretLair';

export const BUCKETS = ['a_only', 'both', 'b_only'] as const;
export type Bucket = (typeof BUCKETS)[number];

const list = <T extends z.ZodTypeAny>(item: T) =>
  z.preprocess((v) => (v == null ? undefined : Array.isArray(v) ? v : [v]), z.array(item));

const VIEW_TYPES = ['grid', 'list'] as const;
const view = z.enum(VIEW_TYPES).catch('grid').default('grid');

const GROUP_BYS = ['lists', 'function'] as const;
export type GroupBy = (typeof GROUP_BYS)[number];

const ROLES = ['commander', 'card'] as const;
export type Role = (typeof ROLES)[number];

const EXPLORE_MODES = ['card', 'rankings'] as const;
export type ExploreMode = (typeof EXPLORE_MODES)[number];
export const RANK_SCOPES = ['commanders', 'cards', 'salt'] as const;
export type RankScope = (typeof RANK_SCOPES)[number];
export const RANK_BYS = ['any', 'color', 'tag', 'set'] as const;
export type RankBy = (typeof RANK_BYS)[number];
export const RANK_TIMEFRAMES = ['week', 'month', 'year'] as const;
export type RankTimeframe = (typeof RANK_TIMEFRAMES)[number];
export const RANK_OWN = ['all', 'owned', 'free'] as const;
export type RankOwn = (typeof RANK_OWN)[number];

export const compareSearch = z.object({
  /** Explore mode; unset = a card when one is picked, else rankings. */
  mode: z.enum(EXPLORE_MODES).optional().catch(undefined),
  /** Rankings: which list, one narrowing axis (filters don't stack), its value, timeframe. */
  rank: z.enum(RANK_SCOPES).catch('commanders').default('commanders'),
  by: z.enum(RANK_BYS).catch('any').default('any'),
  color: z.string().optional().catch(undefined),
  tag: z.string().optional().catch(undefined),
  fam: z.string().optional().catch(undefined),
  tf: z.enum(RANK_TIMEFRAMES).catch('week').default('week'),
  own: z.enum(RANK_OWN).catch('all').default('all'),
  rq: z.string().catch('').default(''),
  rview: z.enum(['list', 'grid']).catch('list').default('list'),
  a: z.string().optional().catch(undefined),
  b: z.string().optional().catch(undefined),
  /** Explore role; unset = commander when A can lead, else card. */
  role: z.enum(ROLES).optional().catch(undefined),
  show: list(z.enum(BUCKETS)).catch([...BUCKETS]).default([...BUCKETS]),
  q: z.string().catch('').default(''),
  tags: list(z.string()).catch([]).default([]),
  /** Encoded sort rules (core/sort.ts), e.g. `inclusion,name`. */
  sort: z.string().catch('inclusion,name').default('inclusion,name'),
  groupBy: z.enum(GROUP_BYS).catch('lists').default('lists'),
  view,
  /** Card surfer: open when set; its source + filters (core/surf.ts codec). */
  surf: z.string().optional().catch(undefined),
});
export type CompareSearch = z.infer<typeof compareSearch>;

export const SHOW = ['owned', 'missing'] as const;

export const collectionSearch = z.object({
  families: list(z.string()).catch([]).default([]),
  show: list(z.enum(SHOW)).catch([...SHOW]).default([...SHOW]),
  /** Missing = only cards you own in no printing at all (functional gaps). */
  gaps: z.boolean().catch(false).default(false),
  /** Unchecked card-type traits (core/collection.ts TRAITS keys). */
  exclude: list(z.string()).catch([]).default([]),
  q: z.string().catch('').default(''),
  /** Scryfall Tagger function roots to keep (OR); empty = all. */
  fn: list(z.string()).catch([]).default([]),
  /** Acquisition sources to keep (OR): `kind:<k>` or a source key (core/collection.ts sourceMatch). */
  src: list(z.string()).catch([]).default([]),
  sort: z.string().catch('set,cn').default('set,cn'),
  view,
  /** Checklist mode: count owned copies inline (views/collection/Checklist*). */
  count: z.boolean().catch(false).default(false),
});
export type CollectionSearch = z.infer<typeof collectionSearch>;

const DECK_GROUPS = ['set', 'year', 'type', 'state', 'origin'] as const;

export const decksSearch = z.object({
  deck: z.string().optional().catch(undefined),
  group: z.enum(DECK_GROUPS).catch('set').default('set'),
  /** Only decks with a physically built copy. */
  built: z.boolean().catch(false).default(false),
  /** Deck types to keep (deck_view.deck_type labels); empty = all. Commander by default. */
  types: list(z.string()).catch(['Commander']).default(['Commander']),
  q: z.string().catch('').default(''),
  /** Open the "add deck cards to collection" review once (after an import). */
  add: z.boolean().optional().catch(undefined),
  view,
});
export type DecksSearch = z.infer<typeof decksSearch>;

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
  /** Deals: the product pages open in your browser, or the products you watch. */
  deals: z.enum(['tabs', 'watching']).catch('tabs').default('tabs'),
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
  /** Deals → Watching: only products whose best in-stock price meets their target. */
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

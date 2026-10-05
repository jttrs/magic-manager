// URL state contracts (zod). Every filter/sort/visibility the views expose lives in
// the URL so any view is a shareable deep link. Framework-free: the router only
// binds these schemas.
import { z } from 'zod';

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

export const compareSearch = z.object({
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

const MARKET_SUBJECTS = ['family', 'deck'] as const;
const MARKET_TABS = ['products', 'cards'] as const;
const CARD_PRICE_SORTS = ['savings', 'price', 'set'] as const;
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
  /** Deck buy list: the cheapest printing of each card, or the deck's exact printing. */
  buyAt: z.enum(PRICE_BASES).catch('floor').default('floor'),
});
export type MarketSearch = z.infer<typeof marketSearch>;

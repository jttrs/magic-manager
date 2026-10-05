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

export const compareSearch = z.object({
  a: z.string().optional().catch(undefined),
  b: z.string().optional().catch(undefined),
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
  /** Unchecked card-type traits (core/collection.ts TRAITS keys). */
  exclude: list(z.string()).catch([]).default([]),
  q: z.string().catch('').default(''),
  /** Scryfall Tagger function roots to keep (OR); empty = all. */
  fn: list(z.string()).catch([]).default([]),
  sort: z.string().catch('set,cn').default('set,cn'),
  view,
});
export type CollectionSearch = z.infer<typeof collectionSearch>;

const DECK_GROUPS = ['set', 'year', 'type', 'state', 'origin'] as const;
const DECK_STATES = ['built', 'deconstructed'] as const;

export const decksSearch = z.object({
  deck: z.string().optional().catch(undefined),
  group: z.enum(DECK_GROUPS).catch('set').default('set'),
  states: list(z.enum(DECK_STATES)).catch([...DECK_STATES]).default([...DECK_STATES]),
  /** Deck types to keep (deck_view.deck_type labels); empty = all. */
  types: list(z.string()).catch([]).default([]),
  q: z.string().catch('').default(''),
  view,
});
export type DecksSearch = z.infer<typeof decksSearch>;

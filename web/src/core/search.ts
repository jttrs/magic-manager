// URL state contracts (zod). Every filter/sort/visibility the views expose lives in
// the URL so any view is a shareable deep link. Framework-free: the router only
// binds these schemas.
import { z } from 'zod';

export const BUCKETS = ['a_only', 'both', 'b_only'] as const;
export type Bucket = (typeof BUCKETS)[number];

export const POOLS = ['printing', 'functional', 'variant-chase'] as const;
export type Pool = (typeof POOLS)[number];

const list = <T extends z.ZodTypeAny>(item: T) =>
  z.preprocess((v) => (v == null ? undefined : Array.isArray(v) ? v : [v]), z.array(item));

const densities = ['grid', 'rows'] as const;
const density = z.enum(densities).catch('grid').default('grid');

const compareSortKeys = ['inclusion', 'delta', 'synergy', 'price', 'name', 'mv'] as const;
export type CompareSort = (typeof compareSortKeys)[number];

export const compareSearch = z.object({
  a: z.string().optional().catch(undefined),
  b: z.string().optional().catch(undefined),
  show: list(z.enum(BUCKETS)).catch([...BUCKETS]).default([...BUCKETS]),
  q: z.string().catch('').default(''),
  tags: list(z.string()).catch([]).default([]),
  sort: z.enum(compareSortKeys).catch('inclusion').default('inclusion'),
  density,
});
export type CompareSearch = z.infer<typeof compareSearch>;

const cardDiffSortKeys = ['value', 'name', 'cn'] as const;
export type CardDiffSort = (typeof cardDiffSortKeys)[number];

export const cardDiffSearch = z.object({
  families: list(z.string()).catch([]).default([]),
  show: list(z.enum(POOLS)).catch([...POOLS]).default([...POOLS]),
  chase: z.enum(['exclude', 'include', 'only']).catch('exclude').default('exclude'),
  q: z.string().catch('').default(''),
  sort: z.enum(cardDiffSortKeys).catch('value').default('value'),
  density,
});
export type CardDiffSearch = z.infer<typeof cardDiffSearch>;

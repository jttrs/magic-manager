// Faceted filtering, framework-free: a list narrowed by several independent
// filters, where each filter's options are counted under every OTHER filter —
// "how many would I see if I picked this?" — never under their own (an option
// that's switched off would always read 0) and never over the raw list (counts
// would ignore everything else you chose).

/** One predicate per filter, keyed by the filter's name. */
export type Facets<T, K extends string> = Record<K, (x: T) => boolean>;

/** True when `x` passes every facet except `skip`. */
export function passes<T, K extends string>(x: T, facets: Facets<T, K>, skip?: K): boolean {
  for (const k in facets) if (k !== skip && !facets[k](x)) return false;
  return true;
}

/**
 * Counts for one filter's options: items passing every OTHER facet, tallied under
 * each option key `keys(x)` returns (one key, several for a multi-valued field, or
 * none).
 */
export function facetCounts<T, K extends string>(
  items: readonly T[],
  facets: Facets<T, K>,
  skip: K,
  keys: (x: T) => Iterable<string> | string | null | undefined,
): Map<string, number> {
  const out = new Map<string, number>();
  for (const x of items) {
    if (!passes(x, facets, skip)) continue;
    const k = keys(x);
    if (k == null) continue;
    for (const key of typeof k === 'string' ? [k] : new Set(k)) out.set(key, (out.get(key) ?? 0) + 1);
  }
  return out;
}

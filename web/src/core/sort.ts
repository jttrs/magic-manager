// Hierarchical sort rules — framework-free. A view supplies a registry of keys
// (label, accessor, natural direction, optional section label); the user builds
// an ordered list of rules (key + direction). Rules compose into ONE comparator;
// the first rule's section labels become the guide's subheads.

export type SortDir = 'asc' | 'desc';
export type SortRule<K extends string = string> = { key: K; dir: SortDir };

type SortValue = number | string | null | undefined;

type SortKeyDef<T> = {
  label: string;
  /** Primitive to compare; null/undefined always sorts last regardless of direction. */
  get: (t: T) => SortValue;
  /** Direction applied when the key is first added. */
  defaultDir: SortDir;
  /** Section label when this key leads the hierarchy (omit = not groupable). */
  section?: (t: T) => string;
};

export type SortRegistry<T, K extends string = string> = Record<K, SortKeyDef<T>>;

export type SortPreset<K extends string = string> = { label: string; rules: SortRule<K>[] };

function cmpValues(a: SortValue, b: SortValue): number {
  const an = a == null || (typeof a === 'number' && Number.isNaN(a));
  const bn = b == null || (typeof b === 'number' && Number.isNaN(b));
  if (an || bn) return an === bn ? 0 : an ? 1 : -1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
}

/** One comparator from an ordered rule list; nulls last in every direction. */
export function composeSort<T, K extends string>(rules: readonly SortRule<K>[], registry: SortRegistry<T, K>) {
  const active = rules.filter((r) => registry[r.key]);
  return (x: T, y: T): number => {
    for (const r of active) {
      const def = registry[r.key];
      const a = def.get(x);
      const b = def.get(y);
      const aNull = a == null;
      const bNull = b == null;
      if (aNull || bNull) {
        if (aNull !== bNull) return aNull ? 1 : -1;
        continue;
      }
      const c = cmpValues(a, b);
      if (c !== 0) return r.dir === 'asc' ? c : -c;
    }
    return 0;
  };
}

export function sortBy<T, K extends string>(items: readonly T[], rules: readonly SortRule<K>[], registry: SortRegistry<T, K>): T[] {
  return [...items].sort(composeSort(rules, registry));
}

/** `set,rarity:desc,cn` ⇄ rules. Unknown keys and duplicates are dropped. */
type KeyDirs<K extends string> = Record<K, { defaultDir: SortDir }>;

export function encodeSort<K extends string>(rules: readonly SortRule<K>[], registry: KeyDirs<K>): string {
  return rules.map((r) => (r.dir === registry[r.key].defaultDir ? r.key : `${r.key}:${r.dir}`)).join(',');
}

export function decodeSort<K extends string>(raw: string | undefined, registry: KeyDirs<K>): SortRule<K>[] {
  const out: SortRule<K>[] = [];
  const seen = new Set<string>();
  for (const part of (raw ?? '').split(',')) {
    const [key, dir] = part.trim().split(':');
    if (!key || seen.has(key) || !(key in registry)) continue;
    seen.add(key);
    const def = registry[key as K];
    out.push({ key: key as K, dir: dir === 'asc' || dir === 'desc' ? dir : def.defaultDir });
  }
  return out;
}

/** Section label for an item under the leading rule, or null when not groupable. */
export function leadSection<T, K extends string>(rules: readonly SortRule<K>[], registry: SortRegistry<T, K>) {
  const lead = rules[0] ? registry[rules[0].key] : undefined;
  return lead?.section ?? null;
}

// "Group by" derivations for the commander compare view. Framework-free.
// `lists` = EDHREC's type-based lists (Creatures, Instants, …); `function` =
// Scryfall Tagger function roots (Ramp, Removal, …). Ranking inside a group is
// whatever order the caller sorted the cards in (EDHREC inclusion by default).
import type { CompareCardOut, FunctionRootOut } from './api';
import { fromCompare, groupCards, TYPE_GROUPS, type GuideCard, type GuideGroup } from './guideCard';
import type { GroupBy } from './search';

/** Group key for cards no function root covers (or before tags are synced). */
export const NO_FUNCTION = '_none';
const NO_FUNCTION_LABEL = 'No tagged function';

function functionLabels(roots: readonly FunctionRootOut[]): Record<string, string> {
  return Object.fromEntries(roots.map((r) => [r.key, r.label]));
}

/** True once the tag cache has produced at least one function for these cards. */
export function hasFunctionData(cards: readonly CompareCardOut[]): boolean {
  return cards.some((c) => (c.functions?.length ?? 0) > 0);
}

/**
 * One bucket's guide sections. In `function` mode a card serving several
 * functions appears under EACH of them, annotated "also: <the others>".
 */
export function compareSections(
  cards: readonly CompareCardOut[],
  groupBy: GroupBy,
  roots: readonly FunctionRootOut[],
): GuideGroup[] {
  const labels = functionLabels(roots);
  if (groupBy === 'lists') return groupCards(cards.map((c) => fromCompare(c, labels)), TYPE_GROUPS);

  const items: GuideCard[] = [];
  for (const c of cards) {
    const base = fromCompare(c, labels);
    const fns = c.functions ?? [];
    if (!fns.length) {
      items.push({ ...base, group: NO_FUNCTION });
      continue;
    }
    for (const fn of fns) {
      const others = fns.filter((f) => f !== fn).map((f) => labels[f] ?? f);
      items.push({ ...base, group: fn, note: others.length ? `also: ${others.join(', ')}` : null });
    }
  }
  return groupCards(items, [...roots.map((r) => r.key), NO_FUNCTION], { ...labels, [NO_FUNCTION]: NO_FUNCTION_LABEL });
}

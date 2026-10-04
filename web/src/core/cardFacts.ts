// Leaf facts about cards (type groups, color and rarity orders). No imports:
// everything else in core may depend on this module.

/** Price-guide subhead for a card, from its type line (front face). */
export const TYPE_GROUPS = [
  'Creatures', 'Planeswalkers', 'Battles', 'Instants', 'Sorceries', 'Artifacts', 'Enchantments', 'Lands', 'Other',
] as const;
export function typeGroup(typeLine: string | null | undefined): string {
  const t = (typeLine ?? '').split('//')[0];
  const has = (w: string) => new RegExp(`\\b${w}\\b`).test(t);
  if (has('Creature')) return 'Creatures';
  if (has('Planeswalker')) return 'Planeswalkers';
  if (has('Battle')) return 'Battles';
  if (has('Instant')) return 'Instants';
  if (has('Sorcery')) return 'Sorceries';
  if (has('Artifact')) return 'Artifacts';
  if (has('Enchantment')) return 'Enchantments';
  if (has('Land')) return 'Lands';
  return 'Other';
}

export const RARITY_RANK: Record<string, number> = { mythic: 5, special: 4, bonus: 4, rare: 3, uncommon: 2, common: 1 };
export const RARITY_NAME: Record<string, string> = { mythic: 'Mythic', special: 'Special', bonus: 'Bonus', rare: 'Rare', uncommon: 'Uncommon', common: 'Common' };
const WUBRG = ['W', 'U', 'B', 'R', 'G'];
const COLOR_NAME: Record<string, string> = { W: 'White', U: 'Blue', B: 'Black', R: 'Red', G: 'Green' };

/** WUBRG mono first, then multicolor by count, then colorless. */
export function colorRank(colors: readonly string[]): number {
  if (!colors.length) return 100;
  if (colors.length === 1) return WUBRG.indexOf(colors[0]);
  return 10 + colors.length;
}
export function colorSection(colors: readonly string[]): string {
  if (!colors.length) return 'Colorless';
  if (colors.length === 1) return COLOR_NAME[colors[0]] ?? colors[0];
  return 'Multicolor';
}

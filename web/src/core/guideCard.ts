// The ONE card view-model every guide component renders. Each domain view maps
// into it with a pure function, so card-diff and commander-compare share every
// component (tile, row, grid, preview) and differ only in their mapper.
import type { CardDiffTile, CompareCardOut } from './api';
import { bucketInclusion } from './compare';

export type GuideCard = {
  key: string;
  name: string;
  image: string | null;
  href: string | null;
  setCode: string | null;
  cn: string | null;
  rarity: string | null;
  finish: string | null;
  price: number | null;
  /** Primary metric shown in the guide line (e.g. inclusion %). */
  pct: number | null;
  /** Two-sided inclusion (compare 'both' bucket). */
  bars: { a: number | null; b: number | null } | null;
  /** Checklist stamps (card-diff pools: P / F / V). */
  stamps: string[];
  group: string;
  lines: { plain: string; manapool: string; tcgplayer: string };
  /** Function roots the card serves (Scryfall Tagger roll-up), display labels. */
  functions?: string[];
  /** Top Scryfall Tagger oracle tags, display labels. */
  tags?: string[];
  /** Short guide-line annotation, e.g. "also: Removal, Lifegain". */
  note?: string | null;
};

const RARITY_LETTER: Record<string, string> = {
  common: 'C', uncommon: 'U', rare: 'R', mythic: 'M', special: 'S', bonus: 'B',
};
export const rarityLetter = (r: string | null): string => (r ? RARITY_LETTER[r] ?? r[0].toUpperCase() : '');

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

/** `fnLabels` maps function root keys → display labels (from the compare payload). */
export function fromCompare(c: CompareCardOut, fnLabels: Readonly<Record<string, string>> = {}): GuideCard {
  return {
    key: c.oracle_id ?? `slug:${c.slug}`,
    name: c.name,
    image: c.image_uri,
    href: c.scryfall_url,
    setCode: c.set_code?.toUpperCase() ?? null,
    cn: c.collector_number,
    rarity: c.rarity,
    finish: null,
    price: c.lowest_usd,
    pct: bucketInclusion(c) >= 0 ? bucketInclusion(c) : null,
    bars: c.bucket === 'both' ? { a: c.a_pct, b: c.b_pct } : null,
    stamps: [],
    group: typeGroup(c.type_line),
    lines: { plain: `1 ${c.name}`, manapool: `1 ${c.name}`, tcgplayer: `1 ${c.name}` },
    functions: (c.functions ?? []).map((k) => fnLabels[k] ?? k),
    tags: (c.oracle_tags ?? []).map((t) => t.label),
    note: null,
  };
}

const POOL_STAMP: Record<string, string> = { printing: 'P', functional: 'F', 'variant-chase': 'V' };

export function fromCardDiff(t: CardDiffTile): GuideCard {
  return {
    key: `${t.family}|${t.key}`,
    name: t.name,
    image: t.image_uri,
    href: t.scryfall_url,
    setCode: t.set_code,
    cn: t.collector_number,
    rarity: t.rarity,
    finish: t.finish,
    price: t.usd,
    pct: null,
    bars: null,
    stamps: t.pools.map((p) => POOL_STAMP[p] ?? p[0].toUpperCase()),
    group: t.family,
    lines: {
      plain: `1 ${t.name}`,
      manapool: t.manapool_line || `1 ${t.name}`,
      tcgplayer: t.tcgplayer_line || `1 ${t.name}`,
    },
  };
}

export type GuideGroup = { key: string; label: string; items: GuideCard[] };

/** Group cards preserving item order; groups ordered by `order` (unknown keys last, first-seen). */
export function groupCards(cards: GuideCard[], order: readonly string[] = [], labels: Record<string, string> = {}): GuideGroup[] {
  const m = new Map<string, GuideCard[]>();
  for (const c of cards) m.set(c.group, [...(m.get(c.group) ?? []), c]);
  const rank = (k: string) => {
    const i = order.indexOf(k);
    return i === -1 ? order.length : i;
  };
  return [...m.keys()]
    .sort((a, b) => rank(a) - rank(b))
    .map((k) => ({ key: k, label: labels[k] ?? k, items: m.get(k)! }));
}

export function exportLines(cards: GuideCard[], target: 'plain' | 'manapool' | 'tcgplayer'): string {
  return cards.map((c) => c.lines[target]).filter(Boolean).join('\n');
}

// The ONE card view-model every guide component renders. Each domain view maps
// into it with a pure function, so card-diff and commander-compare share every
// component (tile, row, grid, preview) and differ only in their mapper.
import type { CollectionCardOut, CompareCardOut } from './api';
import { bucketInclusion } from './compare';
import { typeGroup } from './cardFacts';

export { TYPE_GROUPS } from './cardFacts';

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
  group: string;
  /** Sort/section facts shared by every view. */
  cmc: number | null;
  colors: string[];
  typeGroup: string;
  released: string | null;
  /** Owned copies per finish (collection); null when ownership isn't shown. */
  owned: Partial<Record<'nonfoil' | 'foil', number>> | null;
  /** True when the printing is a gap under the active missing basis. */
  missing: boolean;
  /** Short facts printed in the guide line, never over the art (e.g. Chase, Borderless). */
  tags: string[];
  lines: { plain: string; manapool: string; tcgplayer: string };
  /** Function roots the card serves (Scryfall Tagger roll-up), display labels. */
  functions?: string[];
  /** Top Scryfall Tagger oracle tags, display labels (hover preview only). */
  oracleTags?: string[];
  /** Short guide-line annotation, e.g. "also: Removal, Lifegain". */
  note?: string | null;
};

const RARITY_LETTER: Record<string, string> = {
  common: 'C', uncommon: 'U', rare: 'R', mythic: 'M', special: 'S', bonus: 'B',
};
export const rarityLetter = (r: string | null): string => (r ? RARITY_LETTER[r] ?? r[0].toUpperCase() : '');

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
    group: typeGroup(c.type_line),
    cmc: c.cmc,
    colors: c.color_identity ?? [],
    typeGroup: typeGroup(c.type_line),
    released: null,
    owned: null,
    missing: false,
    tags: [],
    lines: { plain: `1 ${c.name}`, manapool: `1 ${c.name}`, tcgplayer: `1 ${c.name}` },
    functions: (c.functions ?? []).map((k) => fnLabels[k] ?? k),
    oracleTags: (c.oracle_tags ?? []).map((t) => t.label),
    note: null,
  };
}

const TREATMENT_LABEL: Record<string, string> = {
  b: 'Borderless', fa: 'Full art', shw: 'Showcase', ext: 'Ext. art', sm: 'Reskin', ff: 'Fancy foil',
};
export const treatmentLabels = (codes: string): string[] =>
  codes ? codes.split('|').map((c) => TREATMENT_LABEL[c] ?? c) : [];

/** Collection mapper. `missing` is decided by the caller's missing basis. */
export function fromCollection(c: CollectionCardOut, missing: boolean, fnLabels: Readonly<Record<string, string>> = {}): GuideCard {
  return {
    key: c.scryfall_id,
    name: c.name,
    image: c.image_uri,
    href: c.scryfall_url,
    setCode: c.set_code.toUpperCase(),
    cn: c.collector_number,
    rarity: c.rarity,
    finish: null,
    price: c.price_usd ?? c.price_usd_foil,
    pct: null,
    bars: null,
    group: c.family,
    cmc: c.cmc,
    colors: c.color_identity,
    typeGroup: typeGroup(c.type_line),
    released: c.released_at,
    owned: c.owned as GuideCard['owned'],
    missing,
    tags: [...(c.is_chase ? ['Chase'] : []), ...treatmentLabels(c.treatment)],
    lines: { plain: `1 ${c.name}`, manapool: '', tcgplayer: '' },
    functions: (c.functions ?? []).map((k) => fnLabels[k] ?? k),
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

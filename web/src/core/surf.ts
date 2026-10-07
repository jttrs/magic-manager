// Card surfer view-model: the filter model, its one-key URL codec, the feed's
// dedupe/stop rules and the small text facts the feed prints. Framework-free.
import type { SurfCardOut, SurfDrawIn, SurfDrawOut, SurfFiltersIn } from './api';

export type SurfSource = 'scryfall' | 'owned';
export type SurfFilters = Required<SurfFiltersIn>;
export type SurfState = { source: SurfSource; filters: SurfFilters };

export const EMPTY_FILTERS: SurfFilters = {
  art: [], families: [], colors: '', color_match: 'exact', flavor: 'any', types: [], legendary: 'any', rarity: [], artist: '', treatments: [],
};
export const COLORS = ['w', 'u', 'b', 'r', 'g', 'c'] as const;
export const COLOR_NAME: Record<(typeof COLORS)[number], string> = { w: 'White', u: 'Blue', b: 'Black', r: 'Red', g: 'Green', c: 'Colourless' };
const BATCH = 3;

const csv = (v: string | null) => (v ? v.split(',').map((s) => s.trim()).filter(Boolean) : []);
const oneOf = <T extends string>(v: string | null, opts: readonly T[], d: T): T => (opts.includes(v as T) ? (v as T) : d);

/** `surf` URL value → state. Unknown keys and bad values fall back to defaults. */
export function decodeSurf(raw: string | undefined): SurfState {
  const p = new URLSearchParams(raw && raw !== 'on' ? raw : '');
  return {
    source: oneOf(p.get('src'), ['scryfall', 'owned'] as const, 'scryfall'),
    filters: {
      art: csv(p.get('art')),
      families: csv(p.get('fam')),
      colors: (p.get('ci') ?? '').toLowerCase().replace(/[^wubrgc]/g, ''),
      color_match: oneOf(p.get('cm'), ['exact', 'within'] as const, 'exact'),
      flavor: oneOf(p.get('fl'), ['any', 'has', 'none'] as const, 'any'),
      types: csv(p.get('t')),
      legendary: oneOf(p.get('lg'), ['any', 'only', 'not'] as const, 'any'),
      rarity: csv(p.get('r')),
      artist: p.get('ar') ?? '',
      treatments: csv(p.get('tr')),
    },
  };
}

/** State → `surf` URL value (only non-defaults; `on` when nothing is set). */
export function encodeSurf(s: SurfState): string {
  const f = s.filters;
  const p = new URLSearchParams();
  if (s.source !== 'scryfall') p.set('src', s.source);
  if (f.art.length) p.set('art', f.art.join(','));
  if (f.families.length) p.set('fam', f.families.join(','));
  if (f.colors) p.set('ci', f.colors);
  if (f.colors && f.color_match !== 'exact') p.set('cm', f.color_match);
  if (f.flavor !== 'any') p.set('fl', f.flavor);
  if (f.types.length) p.set('t', f.types.join(','));
  if (f.legendary !== 'any') p.set('lg', f.legendary);
  if (f.rarity.length) p.set('r', f.rarity.join(','));
  if (f.artist.trim()) p.set('ar', f.artist.trim());
  if (f.treatments.length) p.set('tr', f.treatments.join(','));
  return p.toString() || 'on';
}

/** How many filters narrow the feed (the source is not a filter). */
export function activeFilters(f: SurfFilters): number {
  return [f.art.length, f.families.length, f.colors, f.flavor !== 'any', f.types.length, f.legendary !== 'any', f.rarity.length, f.artist.trim(), f.treatments.length]
    .filter(Boolean).length;
}

/** Toggle one colour letter; colourless and colours exclude each other. */
export function toggleColor(colors: string, letter: string): string {
  const has = colors.includes(letter);
  if (letter === 'c') return has ? '' : 'c';
  const next = has ? colors.replace(letter, '') : colors.replace('c', '') + letter;
  return COLORS.filter((c) => next.includes(c)).join('');
}

export type Page = { offset: number; first: boolean };

/** The draw request for one page of the feed. */
export function drawRequest(s: SurfState, seed: number, page: Page): SurfDrawIn {
  return {
    filters: { ...s.filters, artist: s.filters.artist.trim() },
    source: s.source,
    n: BATCH,
    seed,
    offset: page.offset,
    with_total: page.first && s.source === 'scryfall',
  };
}

/** Every page's cards, each printing once, in draw order. */
export function feedCards(pages: SurfDrawOut[]): SurfCardOut[] {
  const seen = new Set<string>();
  const out: SurfCardOut[] = [];
  for (const p of pages) for (const c of p.cards) if (!seen.has(c.scryfall_id)) { seen.add(c.scryfall_id); out.push(c); }
  return out;
}

/** Random draws repeat: stop after this many pages in a row brought nothing new. */
const DRY_PAGES = 3;

/** The next page to draw, or undefined when the feed has run out. */
export function nextPage(pages: SurfDrawOut[]): Page | undefined {
  const last = pages.at(-1);
  if (!last || last.exhausted) return undefined;
  if (last.source === 'owned') return last.next_offset != null ? { offset: last.next_offset, first: false } : undefined;
  const total = pages[0]?.total;
  const shown = feedCards(pages).length;
  if (total != null && shown >= total) return undefined;
  let dry = 0;
  const seen = new Set<string>();
  for (const p of pages) {
    const fresh = p.cards.filter((c) => !seen.has(c.scryfall_id));
    p.cards.forEach((c) => seen.add(c.scryfall_id));
    dry = fresh.length ? 0 : dry + 1;
  }
  return dry >= DRY_PAGES ? undefined : { offset: 0, first: false };
}

const RARITY: Record<string, string> = { common: 'Common', uncommon: 'Uncommon', rare: 'Rare', mythic: 'Mythic', special: 'Special', bonus: 'Bonus' };

/** `Bloomburrow · BLB #12 · Rare · 2024` */
export function printingLine(c: SurfCardOut): string {
  return [c.set_name, [c.set_code.toUpperCase(), c.collector_number && `#${c.collector_number}`].filter(Boolean).join(' '), c.rarity && (RARITY[c.rarity] ?? c.rarity), c.released_at?.slice(0, 4)]
    .filter(Boolean).join(' · ');
}

/** `You own 2 of this printing · 5 in every printing` (null when you own none). */
export function ownedLine(c: SurfCardOut): string | null {
  if (!c.owned && !c.owned_any) return null;
  if (!c.owned) return `You own ${c.owned_any} in other printings`;
  return c.owned_any > c.owned ? `You own ${c.owned} of this printing · ${c.owned_any} in every printing` : `You own ${c.owned} of this printing`;
}

/** The text faces to print: a DFC's faces, else the card itself. */
export function textFaces(c: SurfCardOut): { name: string; type_line?: string | null; flavor_text?: string | null; oracle_text?: string | null }[] {
  return c.faces.length ? c.faces : [{ name: c.name, type_line: c.type_line, flavor_text: c.flavor_text, oracle_text: c.oracle_text }];
}

/** The artists credited (a DFC can have two). */
export function artists(c: SurfCardOut): string {
  const names = [...new Set([c.artist, ...c.faces.map((f) => f.artist)].filter(Boolean))];
  return names.join(' & ');
}

/** Sheet summary: `1,470 match · 12 seen`, or for your cards `214 of your cards · 12 seen`. */
export function feedSummary(source: SurfSource, total: number | null | undefined, seen: number, fmt: (n: number) => string): string {
  const pool = total == null ? null : source === 'owned' ? `up to ${fmt(total)} of your cards` : `${fmt(total)} match`;
  return [pool, `${fmt(seen)} seen`].filter(Boolean).join(' · ');
}

export const scryfallSearchUrl = (query: string) => `https://scryfall.com/search?q=${encodeURIComponent(query)}&unique=prints`;

// Jumpstart view-model (Collection → Jumpstart). Framework-free: the URL state,
// the pack filters and colour groups, the inspector's card groups, and the copy
// for the sheet summary and the Buy strip. Every number comes from the engine.
import { z } from 'zod';
import type { JumpstartOut, JumpstartPackCardOut, JumpstartPackOut } from './api';
import { typeGroup, TYPE_GROUPS } from './cardFacts';
import { fmtCount, fmtInt, fmtUsd } from './format';
import { fromPrinting, groupCards, type GuideCard, type GuideGroup } from './guideCard';

export const PACK_SHOW = ['all', 'build', 'close', 'own'] as const;
export type PackShow = (typeof PACK_SHOW)[number];
const SHOPS = ['buildable', 'packs'] as const;
export type Shop = (typeof SHOPS)[number];

export const jumpstartSearch = z.object({
  /** Jumpstart set code (e.g. j25); unset = last used / newest. */
  set: z.string().optional().catch(undefined),
  show: z.enum(PACK_SHOW).catch('all').default('all'),
  q: z.string().catch('').default(''),
  /** The pack version open in the inspector (MTGJSON fileName). */
  pack: z.string().optional().catch(undefined),
  shop: z.enum(SHOPS).catch('buildable').default('buildable'),
  view: z.enum(['grid', 'list']).catch('list').default('list'),
});
export type JumpstartSearch = z.infer<typeof jumpstartSearch>;

export const SHOW_LABEL: Record<PackShow, string> = { all: 'Every pack', build: 'Ready to build', close: 'Close', own: 'Packs you own' };

const isOwned = (p: Pick<JumpstartPackOut, 'built' | 'deconstructed'>) => p.built + p.deconstructed > 0;

function keep(p: JumpstartPackOut, show: PackShow): boolean {
  switch (show) {
    case 'build': return p.status === 'build';
    case 'close': return p.status === 'close';
    case 'own': return isOwned(p);
    default: return true;
  }
}

export function filterPacks(packs: readonly JumpstartPackOut[], f: Pick<JumpstartSearch, 'show' | 'q'>): JumpstartPackOut[] {
  const q = f.q.trim().toLowerCase();
  return packs.filter((p) => keep(p, f.show) && (!q || [p.name, p.top_card, p.front_card].some((s) => s?.toLowerCase().includes(q))));
}

export function showCounts(packs: readonly JumpstartPackOut[]): Record<PackShow, number> {
  return Object.fromEntries(PACK_SHOW.map((s) => [s, packs.filter((p) => keep(p, s)).length])) as Record<PackShow, number>;
}

const COLOR_NAME: Record<string, string> = { C: 'Colorless', W: 'White', U: 'Blue', B: 'Black', R: 'Red', G: 'Green' };
const MULTI = 'Multicolour';
const COLOR_ORDER = ['Colorless', 'White', 'Blue', 'Black', 'Red', 'Green', MULTI];

const colorGroup = (code: string): string => COLOR_NAME[code] ?? MULTI;
/** "White" for mono, the letters ("WU") for multicolour packs. */
export const colorLabel = (code: string): string => COLOR_NAME[code] ?? code;

export type PackGroup = { key: string; label: string; packs: JumpstartPackOut[]; ready: number };

/** Colour sections (mono C→W→U→B→R→G, then every multicolour pack); pack order kept. */
export function groupPacks(packs: readonly JumpstartPackOut[]): PackGroup[] {
  const m = new Map<string, JumpstartPackOut[]>();
  for (const p of packs) m.set(colorGroup(p.color), [...(m.get(colorGroup(p.color)) ?? []), p]);
  return COLOR_ORDER.filter((k) => m.has(k)).map((k) => {
    const ps = m.get(k)!;
    return { key: k, label: k, packs: ps, ready: ps.filter((p) => p.status === 'build').length };
  });
}

/** How far your free cards get you: "All 20 free" · "2 short" · "13 of 20 free". */
export function coverage(p: Pick<JumpstartPackOut, 'have' | 'short' | 'status'>): string {
  const total = p.have + p.short;
  if (p.status === 'build') return `All ${fmtInt(total)} free`;
  if (p.status === 'close') return `${fmtInt(p.short)} short`;
  return `${fmtInt(p.have)} of ${fmtInt(total)} free`;
}

/** "×1 built · 1 broken down" — copies of this version you own; '' when none. */
export function ownedLabel(p: Pick<JumpstartPackOut, 'built' | 'deconstructed'>): string {
  return [p.built ? `×${fmtInt(p.built)} built` : '', p.deconstructed ? `${fmtInt(p.deconstructed)} broken down` : ''].filter(Boolean).join(' · ');
}

export function summaryLine(d: Pick<JumpstartOut, 'packs' | 'themes'>): string {
  const packs = d.packs ?? [];
  const c = showCounts(packs);
  return [
    `${fmtCount(packs.length, 'pack version')} of ${fmtCount(d.themes ?? 0, 'theme')}`,
    `you own ${fmtInt(c.own)}`,
    `${fmtInt(c.build)} ready to build from free cards`,
    c.close ? `${fmtInt(c.close)} close` : '',
  ].filter(Boolean).join(' · ');
}

/** The Buy strip's label line for the chosen shopping list. */
export function shopLead(shop: Shop, d: Pick<JumpstartOut, 'buildable' | 'whole' | 'whole_packs'>): string {
  if (shop === 'buildable') {
    const b = d.buildable;
    return b && b.copies ? `Copy bulk lists · ${fmtCount(b.copies, 'card')} to build every theme · ≈ ${fmtUsd(b.usd)} at market` : 'Every theme is buildable from cards you own';
  }
  const w = d.whole;
  return w && d.whole_packs ? `Copy bulk lists · ${fmtCount(d.whole_packs, 'pack')} you don’t own · ${fmtCount(w.copies, 'card')} · ≈ ${fmtUsd(w.usd)} at market` : 'You own every pack version';
}

/** One pack card → the shared guide card: missing when you have fewer free copies than the pack needs. */
export function fromPackCard(c: JumpstartPackCardOut): GuideCard {
  const base = fromPrinting(c.printing);
  const finish = c.foil ? 'foil' : 'nonfoil';
  const enough = c.free >= c.count;
  return {
    ...base,
    key: `${c.printing.scryfall_id}|${finish}`,
    finish,
    price: c.unit_usd,
    missing: !enough,
    tags: [...(c.count > 1 ? [`×${c.count} in pack`] : []), ...base.tags],
    lines: { plain: `${c.count} ${c.printing.name}`, manapool: '', tcgplayer: '' },
    note: enough ? `${fmtInt(c.free)} free` : c.free ? `${fmtInt(c.free)} of ${fmtInt(c.count)} free` : 'None free',
  };
}

/** The inspector's cards, sectioned by card type; a section counts copies when they differ from lines. */
export function packCardGroups(cards: readonly JumpstartPackCardOut[]): GuideGroup[] {
  const items = cards.map((c) => ({ ...fromPackCard(c), group: typeGroup(c.printing.type_line ?? null) }));
  return groupCards(items, TYPE_GROUPS).map((g) => {
    const n = cards.filter((c) => typeGroup(c.printing.type_line ?? null) === g.key).reduce((t, c) => t + c.count, 0);
    return { ...g, label: n === g.items.length ? g.label : `${g.label} · ${n}` };
  });
}

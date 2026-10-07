import type { ProductCostOut, SldDropOut } from './api';

/** Secret Lair in Market: one row per drop at the chosen edition, valued sealed vs the cards inside. */

export const SLD_EDITIONS = ['nonfoil', 'foil'] as const;
export type SldEdition = (typeof SLD_EDITIONS)[number];
export const SLD_SORTS = ['gap_pct', 'gap_usd', 'price', 'release', 'name'] as const;
export type SldSort = (typeof SLD_SORTS)[number];
export const SLD_BASES = ['exact', 'floor'] as const;
export type SldBasis = (typeof SLD_BASES)[number];
export const SLD_LIMITS = [10, 30, 60, 120] as const;

export const SLD_BASIS_LABEL: Record<SldBasis, string> = { exact: 'cards, exact printings', floor: 'cards, cheapest printings' };

export type SldRow = {
  key: string;
  name: string;
  release_date: string | null;
  finish: SldEdition;
  /** The drop doesn't ship in the chosen edition; this row is its only one. */
  otherEdition: boolean;
  sealed_name: string | null;
  tcgplayer_url: string | null;
};

export const sldKey = (name: string, finish: string) => `sld|${name}|${finish}`;

/** Each drop at the chosen edition — or at its only edition when it doesn't ship in that one. */
export function sldRows(drops: SldDropOut[], edition: SldEdition): SldRow[] {
  return drops.flatMap((d) => {
    const e = d.editions.find((x) => x.finish === edition) ?? d.editions[0];
    if (!e) return [];
    return [{
      key: sldKey(d.name, e.finish), name: d.name, release_date: d.release_date ?? null, finish: e.finish,
      otherEdition: e.finish !== edition, sealed_name: e.sealed_name ?? null, tcgplayer_url: e.tcgplayer_url ?? null,
    }];
  });
}

/** Sealed price vs the cards inside: negative ⇒ the sealed drop costs less than its cards. */
export function sldGap(cost: ProductCostOut | undefined, basis: SldBasis): { usd: number; pct: number } | null {
  const cards = cost?.[basis];
  const sealed = cost?.market;
  if (cards == null || cards === 0 || sealed == null) return null;
  const usd = sealed - cards;
  return { usd, pct: (usd / cards) * 100 };
}

export type SldFilters = { q: string; minOff: number; basis: SldBasis; sort: SldSort };

export function filterSortDrops(rows: SldRow[], costs: Map<string, ProductCostOut | undefined>, o: SldFilters): SldRow[] {
  const q = o.q.trim().toLowerCase();
  const kept = rows.filter((r) => {
    if (q && !r.name.toLowerCase().includes(q)) return false;
    if (o.minOff > 0) {
      const g = sldGap(costs.get(r.key), o.basis);
      if (!g || g.pct > -o.minOff) return false;
    }
    return true;
  });
  const value = (r: SldRow): number | string | null => {
    const cost = costs.get(r.key);
    switch (o.sort) {
      case 'gap_pct': return sldGap(cost, o.basis)?.pct ?? null;
      case 'gap_usd': return sldGap(cost, o.basis)?.usd ?? null;
      case 'price': return cost?.market ?? null;
      case 'release': return r.release_date;
      case 'name': return null;
    }
  };
  const dir = o.sort === 'release' ? -1 : 1;
  return kept
    .map((r) => ({ r, v: value(r) }))
    .sort((a, b) => {
      if (a.v !== b.v) {
        if (a.v == null) return 1;
        if (b.v == null) return -1;
        return (a.v < b.v ? -1 : 1) * dir;
      }
      return a.r.name.localeCompare(b.r.name);
    })
    .map((x) => x.r);
}

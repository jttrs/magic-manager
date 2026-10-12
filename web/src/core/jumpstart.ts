// Jumpstart view-model: Jumpstart packs are deck recipes now (Decks, core/decks.ts).
// This keeps what is Jumpstart-only — the two shopping lists of one set and the
// mapping of old /collection/jumpstart links onto Decks. Framework-free.
import { z } from 'zod';
import type { JumpstartOut } from './api';
import { fmtCount, fmtUsd } from './format';
import type { DecksSearch } from './search';

const SHOPS = ['buildable', 'packs'] as const;
export type Shop = (typeof SHOPS)[number];

/** The old Collection → Jumpstart URL (kept only to redirect old links). */
export const legacyJumpstartSearch = z.object({
  set: z.string().optional().catch(undefined),
  show: z.enum(['all', 'build', 'close', 'own']).catch('all').default('all'),
  q: z.string().catch('').default(''),
  pack: z.string().optional().catch(undefined),
  shop: z.enum(SHOPS).catch('buildable').default('buildable'),
  view: z.enum(['grid', 'list']).catch('list').default('list'),
});
export type LegacyJumpstartSearch = z.infer<typeof legacyJumpstartSearch>;

/** An old Jumpstart sheet link → the same packs in Decks. */
export function jumpstartToDecks(s: LegacyJumpstartSearch): Partial<DecksSearch> {
  return {
    kinds: ['jumpstart'],
    own: s.show === 'own' ? ['built', 'loose'] : ['built', 'loose', 'none'],
    cover: s.show === 'build' ? 'build' : s.show === 'close' ? 'close' : 'any',
    sets: s.set ? [s.set] : [],
    deck: s.pack ? `fn:${s.pack}` : undefined,
    group: 'color',
    q: s.q,
    shop: s.shop,
    view: s.view,
  };
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

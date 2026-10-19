// Earmarked cards: singles you're interested in (to collect, or a deck idea).
// Framework-free view-model shared by the inspector toggle, Explore's
// Earmarked tab, the deck editor's Earmarked tab and Collection's mark.
import type { CardEarmarkOut, DeckEarmarkOut, EarmarkEntryOut } from './api';
import { fromPrinting, type GuideCard, type GuideGroup } from './guideCard';

export type EarmarkReason = NonNullable<CardEarmarkOut['reason']>;

export const REASON_LABEL: Record<EarmarkReason, string> = { collect: 'To collect', deck: 'Deck idea' };

const fold = (s: string) => s.toLowerCase().replace(/[’']/g, "'").trim();

/** The earmark for a card by name; a double-faced name matches its front face too. */
export function findEarmark(entries: readonly EarmarkEntryOut[] | undefined, name: string): EarmarkEntryOut | undefined {
  if (!entries?.length) return undefined;
  const want = new Set([fold(name), fold(name.split(' // ')[0])]);
  return entries.find((e) => want.has(fold(e.earmark.name)) || want.has(fold(e.earmark.name.split(' // ')[0])));
}

/** "To collect · for Squall Deck · alt art" — the facts an earmark records, in order. */
export function earmarkLine(e: CardEarmarkOut): string {
  return [e.reason && REASON_LABEL[e.reason], e.deck_name && `for ${e.deck_name}`, e.note].filter(Boolean).join(' · ');
}

export type EarmarkFilter = { reason?: EarmarkReason | 'none'; deck?: string; own?: 'all' | 'owned' | 'free'; q?: string };

/** Explore's Earmarked list, narrowed (order kept: newest first from the server). */
export function filterEarmarks(entries: readonly EarmarkEntryOut[], f: EarmarkFilter): EarmarkEntryOut[] {
  const q = fold(f.q ?? '');
  return entries.filter((e) => {
    const m = e.earmark;
    if (f.reason && (f.reason === 'none' ? m.reason != null : m.reason !== f.reason)) return false;
    if (f.deck && m.deck_slug !== f.deck) return false;
    if (f.own === 'owned' && e.owned === 0) return false;
    if (f.own === 'free' && e.free === 0) return false;
    if (q && !fold(m.name).includes(q) && !fold(m.note ?? '').includes(q)) return false;
    return true;
  });
}

/** The decks earmarks point at, once each, by name — the deck filter's options. */
export function earmarkDecks(entries: readonly EarmarkEntryOut[]): { slug: string; name: string }[] {
  const m = new Map<string, string>();
  for (const e of entries) if (e.earmark.deck_slug) m.set(e.earmark.deck_slug, e.earmark.deck_name ?? e.earmark.deck_slug);
  return [...m].map(([slug, name]) => ({ slug, name })).sort((a, b) => a.name.localeCompare(b.name));
}

type BlockerCode = DeckEarmarkOut['reasons'][number]['code'];

const BLOCKER_SHORT: Record<BlockerCode, string> = {
  colour_identity: 'outside the commander’s colours',
  banned: 'banned',
  not_legal: 'not legal in this format',
  no_legality: 'no legality data',
  not_in_catalog: 'not in your card catalog',
};

/** "3 hidden · 2 outside the commander’s colours · 1 banned" — why earmarked
 *  cards are missing from a deck's tab, counted by reason, most common first. */
export function hiddenSummary(hidden: readonly DeckEarmarkOut[]): string {
  if (!hidden.length) return '';
  const counts = new Map<BlockerCode, number>();
  for (const e of hidden) for (const r of e.reasons) counts.set(r.code, (counts.get(r.code) ?? 0) + 1);
  const parts = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([k, n]) => `${n} ${BLOCKER_SHORT[k]}`);
  return [`${hidden.length} hidden`, ...parts].join(' · ');
}

/** A card's blockers in plain words. */
export const reasonsText = (e: Pick<DeckEarmarkOut, 'reasons'>): string => e.reasons.map((r) => r.message).join(' · ');

/** An earmark as a guide card (its printing to show), keyed on the card. */
export function earmarkCard(e: EarmarkEntryOut): GuideCard | null {
  if (!e.printing) return null;
  return { ...fromPrinting(e.printing), key: e.earmark.oracle_id };
}

const SECTION_ORDER = ['collect', 'deck', 'none'] as const;
const SECTION_LABEL: Record<(typeof SECTION_ORDER)[number], string> = { collect: 'To collect', deck: 'Deck ideas', none: 'No reason given' };

/** Explore's grid: earmarks grouped by reason (To collect · Deck ideas · No reason given). */
export function earmarkSections(entries: readonly EarmarkEntryOut[]): GuideGroup[] {
  return SECTION_ORDER.map((k) => ({
    key: k,
    label: SECTION_LABEL[k],
    items: entries.filter((e) => (e.earmark.reason ?? 'none') === k).map(earmarkCard).filter((c): c is GuideCard => c != null),
  })).filter((g) => g.items.length > 0);
}

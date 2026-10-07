// Commander Spellbook combos: pure view-model helpers shared by the deck
// editor's Combos tab, the Deck Manager's combos dialog and Explore.
import type { ComboOut, DeckCombosOut, MissingCardOut, PieceOut } from './api';
import { fmtCount, fmtInt } from './format';

export type OwnNote = { text: string; free: boolean };

/** What you own of a combo piece, across every printing. */
export function ownNote(p: PieceOut): OwnNote {
  const owned = p.facts.owned ?? 0;
  const free = p.facts.free ?? 0;
  if (free > 0) return { text: `${fmtInt(free)} free`, free: true };
  if (owned > 0) return { text: 'owned, all pledged', free: false };
  return { text: 'not in your collection', free: false };
}

/** "Infinite mana · Infinite storm count +2 more" */
export function producesLine(c: ComboOut, max = 2): string {
  const head = c.produces.slice(0, max).join(' · ');
  const rest = c.produces.length - max;
  return rest > 0 ? `${head} +${rest} more` : head;
}

/** The combo's steps, one per line, blanks dropped. */
export const steps = (c: ComboOut): string[] => c.description.split('\n').map((s) => s.trim()).filter(Boolean);

/** "in 106,164 decks" — EDHREC decks that run every piece. */
export const decksLine = (c: ComboOut): string | null => (c.popularity ? `in ${fmtCount(c.popularity, 'deck')}` : null);

/** Pieces you own at least one copy of (Explore: "You own 2 of 3"). */
export function piecesOwned(c: ComboOut): { owned: number; total: number } {
  return { owned: c.pieces.filter((p) => (p.facts.owned ?? 0) > 0).length, total: c.pieces.length };
}

export type NearMiss = { card: MissingCardOut; combos: ComboOut[] };

/** One-card-away combos grouped under the card that completes them. */
export function nearMisses(d: DeckCombosOut): NearMiss[] {
  const byId = new Map(d.almost.map((c) => [c.id, c]));
  return d.missing_cards.map((card) => ({ card, combos: card.combos.map((id) => byId.get(id)).filter((c): c is ComboOut => Boolean(c)) }));
}

/** "2 in this deck · 6 one card away" (+ off-colour count). */
export function deckCombosSummary(d: DeckCombosOut): string {
  const parts = [`${fmtInt(d.included.length)} in this deck`, `${fmtInt(d.almost.length)} one card away`];
  if (d.off_color > 0) parts.push(`${fmtInt(d.off_color)} more need another colour`);
  return parts.join(' · ');
}


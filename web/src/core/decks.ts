// Deck Manager derivations: deck-list grouping/filtering, a deck's cards as
// guide sections (Commander · Creatures · … · Sideboard · Tokens), and the
// add-cards review lines for "add this deck / these cards to my collection".
// Framework-free.
import type { DeckCardOut, DeckSummaryOut, ResolvedLineOut } from './api';
import { TYPE_GROUPS, typeGroup } from './cardFacts';
import { treatmentLabels, type GuideCard, type GuideGroup } from './guideCard';

export const DECK_GROUPS = ['set', 'year', 'state', 'format', 'origin'] as const;
export type DeckGroupBy = (typeof DECK_GROUPS)[number];
export const DECK_GROUP_LABEL: Record<DeckGroupBy, string> = { set: 'Set', year: 'Year', state: 'Built / loose', format: 'Format', origin: 'Source' };

const ORIGIN_LABEL: Record<DeckSummaryOut['origin'], string> = { precon: 'Preconstructed', import: 'Imported', custom: 'Built by hand' };
const titleCase = (s: string) => s.replace(/\b\w/g, (c) => c.toUpperCase());

export type DeckFilters = { q: string; states: readonly DeckSummaryOut['state'][] };

export function filterDecks(decks: readonly DeckSummaryOut[], f: DeckFilters): DeckSummaryOut[] {
  const q = f.q.trim().toLowerCase();
  return decks.filter(
    (d) =>
      f.states.includes(d.state) &&
      (!q || [d.name, d.set_name, d.set_code, d.source, d.author].some((v) => v?.toLowerCase().includes(q))),
  );
}

export type DeckGroup = { key: string; label: string; decks: DeckSummaryOut[] };

/** Group decks; groups ordered newest first for set/year, fixed order otherwise. Decks keep input order. */
export function groupDecks(decks: readonly DeckSummaryOut[], by: DeckGroupBy): DeckGroup[] {
  const keyOf = (d: DeckSummaryOut): [string, string, string] => {
    switch (by) {
      case 'set':
        return [d.set_code ?? '~', d.set_name ?? d.set_code?.toUpperCase() ?? 'No set', d.released ?? ''];
      case 'year': {
        const y = d.released?.slice(0, 4) ?? '';
        return [y || '~', y || 'Undated', y];
      }
      case 'state':
        return [d.state, d.state === 'built' ? 'Built' : 'Loose (deconstructed)', d.state === 'built' ? '1' : '0'];
      case 'format':
        return [d.format ?? '~', d.format ? titleCase(d.format) : 'No format', d.format ?? ''];
      case 'origin':
        return [d.origin, ORIGIN_LABEL[d.origin], { precon: '2', import: '1', custom: '0' }[d.origin]];
    }
  };
  const m = new Map<string, DeckGroup & { rank: string }>();
  for (const d of decks) {
    const [key, label, rank] = keyOf(d);
    const g = m.get(key) ?? { key, label, decks: [], rank };
    if (rank > g.rank) g.rank = rank;
    g.decks.push(d);
    m.set(key, g);
  }
  const groups = [...m.values()];
  if (by === 'format') groups.sort((a, b) => b.decks.length - a.decks.length);
  else groups.sort((a, b) => (a.key === '~' ? 1 : b.key === '~' ? -1 : b.rank.localeCompare(a.rank) || a.label.localeCompare(b.label)));
  return groups.map(({ key, label, decks: ds }) => ({ key, label, decks: ds }));
}

/** Inspector section for a deck card: board first, then type. */
export function deckSection(c: Pick<DeckCardOut, 'board' | 'type_line'>): string {
  switch (c.board) {
    case 'commander': return 'Commander';
    case 'companion': return 'Companion';
    case 'side': return 'Sideboard';
    case 'maybe': return 'Maybe';
    case 'token': return 'Tokens';
    default: return typeGroup(c.type_line);
  }
}
export const DECK_SECTIONS = ['Commander', 'Companion', ...TYPE_GROUPS, 'Sideboard', 'Maybe', 'Tokens'] as const;

/** A deck card → the shared guide view-model. Key is per row (a printing can sit on two boards). */
export function fromDeckCard(c: DeckCardOut): GuideCard {
  const p = c.printing;
  const owned = Object.values(p.owned ?? {}).reduce((s, n) => s + n, 0);
  const finish = c.finish === 'either' ? null : c.finish;
  return {
    key: `${p.scryfall_id}|${c.board}|${c.finish}`,
    name: p.name,
    image: p.image_uri,
    href: `https://scryfall.com/card/${p.set_code}/${encodeURIComponent(p.collector_number)}`,
    setCode: p.set_code.toUpperCase(),
    cn: p.collector_number,
    rarity: p.rarity,
    finish,
    price: (finish === 'foil' ? p.price_usd_foil : p.price_usd) ?? p.price_usd ?? p.price_usd_foil,
    pct: null,
    bars: null,
    group: deckSection(c),
    cmc: c.cmc,
    colors: c.color_identity,
    typeGroup: typeGroup(c.type_line),
    released: p.released_at,
    owned: p.owned as GuideCard['owned'],
    missing: owned === 0,
    tags: [`×${c.count} in deck`, ...(c.pledged_here ? [`${c.pledged_here} pledged`] : []), ...treatmentLabels(p.treatment)],
    lines: { plain: `${c.count} ${p.name}`, manapool: '', tcgplayer: '' },
    note: c.free ? `${c.free} free to use` : null,
    typeLine: c.type_line,
    prices: { nonfoil: p.finishes.includes('nonfoil') ? p.price_usd : null, foil: p.finishes.includes('foil') ? p.price_usd_foil : null },
  };
}

export function deckGuideGroups(cards: readonly DeckCardOut[]): GuideGroup[] {
  const m = new Map<string, GuideCard[]>();
  for (const c of cards) {
    const g = deckSection(c);
    m.set(g, [...(m.get(g) ?? []), fromDeckCard(c)]);
  }
  return DECK_SECTIONS.filter((s) => m.has(s)).map((s) => {
    const items = m.get(s)!;
    const n = cards.filter((c) => deckSection(c) === s).reduce((t, c) => t + c.count, 0);
    return { key: s, label: n === items.length ? s : `${s} · ${n}`, items };
  });
}

/** Deck cards (optionally only `keys`) as exact add-cards review lines. Tokens excluded unless asked. */
export function deckReviewLines(cards: readonly DeckCardOut[], keys?: ReadonlySet<string>, withTokens = false): ResolvedLineOut[] {
  return cards
    .filter((c) => (withTokens || c.board !== 'token') && (!keys || keys.has(fromDeckCard(c).key)))
    .map((c) => ({
      line: 0,
      raw: `${c.count} ${c.printing.name}`,
      qty: c.count,
      name: c.printing.name,
      finish: c.finish === 'foil' ? 'foil' : 'nonfoil',
      section: c.board,
      status: 'exact',
      candidates: [c.printing],
      chosen: c.printing.scryfall_id,
      note: null,
    }));
}

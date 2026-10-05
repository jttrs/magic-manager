// Explore (card role) derivations: EDHREC card-page entries → the shared guide
// view-model and guide sections. Framework-free; the view only renders these.
import type { CardExploreOut, CardProfileOut, EntryOut, FactsOut, PairedOut } from './api';
import { typeGroup } from './cardFacts';
import type { GuideCard, GuideGroup } from './guideCard';
import type { Role } from './search';

type Section = GuideGroup & { level: 1 | 2; noun?: string };

/** Role when none is chosen: lead with the commander view when the card can lead. */
export const defaultRole = (eligible: boolean | undefined): Role => (eligible ? 'commander' : 'card');

const fmtLift = (l: number | null | undefined) => (l == null ? null : `${l.toFixed(l >= 10 ? 0 : 2)}× lift`);

function base(name: string, slug: string, f: FactsOut): GuideCard {
  return {
    key: f.oracle_id ?? `slug:${slug}`,
    scryfallId: f.scryfall_id ?? null,
    name,
    image: f.image_uri ?? null,
    href: f.scryfall_url ?? null,
    setCode: f.set_code?.toUpperCase() ?? null,
    cn: f.collector_number ?? null,
    rarity: null,
    finish: null,
    price: f.lowest_usd ?? null,
    pct: null,
    bars: null,
    group: typeGroup(f.type_line),
    cmc: f.cmc ?? null,
    colors: f.color_identity ?? [],
    typeGroup: typeGroup(f.type_line),
    released: null,
    owned: null,
    missing: false,
    tags: f.owned ? [`${f.owned} owned · ${f.free} free`] : [],
    lines: { plain: `1 ${name}`, manapool: `1 ${name}`, tcgplayer: `1 ${name}` },
    typeLine: f.type_line ?? null,
    prices: { nonfoil: f.lowest_usd ?? null, foil: null },
  };
}

/** The explored card itself (plate → inspector). */
export const profileCard = (p: CardProfileOut): GuideCard => base(p.name, p.slug, p.facts);

/** One commander / co-played / similar card from a single profile. */
export function fromEntry(e: EntryOut): GuideCard {
  return { ...base(e.name, e.slug, e.facts), pct: e.share ?? null, note: fmtLift(e.lift) };
}

/** A paired entry (comparison): both shares as the two bars, both lifts in the note. */
export function fromPaired(p: PairedOut): GuideCard {
  const lifts = p.bucket === 'both' && (p.a?.lift != null || p.b?.lift != null)
    ? `lift ${p.a?.lift?.toFixed(2) ?? '—'}× / ${p.b?.lift?.toFixed(2) ?? '—'}×`
    : fmtLift((p.a ?? p.b)?.lift);
  return {
    ...base(p.name, p.slug, p.facts),
    pct: (p.a ?? p.b)?.share ?? null,
    bars: p.bucket === 'both' ? { a: p.a?.share ?? null, b: p.b?.share ?? null } : null,
    note: lifts,
  };
}

const matchQ = (q: string) => {
  const ql = q.trim().toLowerCase();
  return (c: GuideCard) => !ql || c.name.toLowerCase().includes(ql);
};

const groupBy = <T,>(items: T[], key: (t: T) => string): [string, T[]][] => {
  const m = new Map<string, T[]>();
  for (const t of items) m.set(key(t), [...(m.get(key(t)) ?? []), t]);
  return [...m];
};

/** Single card: Commanders that run it · Played alongside (by type, lift order) · Similar cards. */
export function profileSections(p: CardProfileOut, q: string, groups: readonly string[]): Section[] {
  const keep = matchQ(q);
  const out: Section[] = [];
  const cmd = [...p.commanders].sort((x, y) => (y.share ?? 0) - (x.share ?? 0));
  const cmdCards = cmd.map((e) => ({ e, c: fromEntry(e) })).filter(({ c }) => keep(c));
  if (cmdCards.length) {
    out.push({ key: 'cmd', label: 'Commanders that run it', level: 1, items: [], noun: 'section' });
    for (const [g, xs] of groupBy(cmdCards, ({ e }) => e.group ?? 'top')) {
      out.push({ key: `cmd:${g}`, label: g === 'new' ? 'New commanders' : 'Top commanders', level: 2, items: xs.map(({ c }) => c), noun: 'group' });
    }
  }
  const co = p.coplayed.filter((e) => !groups.length || groups.includes(e.group ?? ''));
  const coGroups = groupBy(co, (e) => e.group ?? 'Other')
    .map(([g, es]) => [g, [...es].sort((x, y) => (y.lift ?? 0) - (x.lift ?? 0)).map(fromEntry).filter(keep)] as const)
    .filter(([, cs]) => cs.length);
  if (coGroups.length) {
    out.push({ key: 'co', label: 'Played alongside', level: 1, items: [], noun: 'section' });
    for (const [g, cs] of coGroups) out.push({ key: `co:${g}`, label: g, level: 2, items: cs, noun: 'card type' });
  }
  const sim = p.similar.map(fromEntry).filter(keep);
  if (sim.length) {
    out.push({ key: 'sim', label: 'Similar cards', level: 1, items: [], noun: 'section' });
    out.push({ key: 'sim:all', label: 'Cards like it', level: 2, items: sim, noun: 'group' });
  }
  return out;
}

export type PairBucket = PairedOut['bucket'];

/** Comparison column: Commanders (largest share gap first) · Played alongside (largest lift gap first, by type). */
export function pairedSections(r: CardExploreOut, bucket: PairBucket, q: string, groups: readonly string[]): Section[] {
  const keep = matchQ(q);
  const out: Section[] = [];
  const cmd = (r.commanders ?? []).filter((p) => p.bucket === bucket).map(fromPaired).filter(keep);
  if (cmd.length) out.push({ key: `${bucket}:cmd`, label: 'Commanders that run it', level: 2, items: cmd, noun: 'section' });
  const co = (r.coplayed ?? []).filter((p) => p.bucket === bucket && (!groups.length || groups.includes((p.a ?? p.b)?.group ?? '')));
  for (const [g, ps] of groupBy(co, (p) => (p.a ?? p.b)?.group ?? 'Other')) {
    const cs = ps.map(fromPaired).filter(keep);
    if (cs.length) out.push({ key: `${bucket}:co:${g}`, label: `Played alongside · ${g}`, level: 2, items: cs, noun: 'card type' });
  }
  return out;
}

/** Co-play groups present (for the type filter), in EDHREC order. */
export function coplayGroups(r: CardExploreOut): [string, number][] {
  const all = r.b ? (r.coplayed ?? []).map((p) => (p.a ?? p.b)?.group ?? 'Other') : r.a.coplayed.map((e) => e.group ?? 'Other');
  const m = new Map<string, number>();
  for (const g of all) m.set(g, (m.get(g) ?? 0) + 1);
  return [...m];
}

/** "8.5M of 10.2M decks (83%)" — how widely EDHREC decks run the card. */
export function deckShare(p: Pick<CardProfileOut, 'num_decks' | 'potential_decks'>): string | null {
  if (p.num_decks == null) return null;
  const n = new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 });
  const pct = p.potential_decks ? ` (${Math.round((100 * p.num_decks) / p.potential_decks)}%)` : '';
  return `${n.format(p.num_decks)} of ${p.potential_decks != null ? n.format(p.potential_decks) : '?'} possible decks${pct}`;
}

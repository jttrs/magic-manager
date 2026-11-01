import { describe, expect, it } from 'vitest';
import type { HistoryEntryOut, HistoryLineOut, PurchaseOut, RevertPlanOut } from './api';
import { datedNote, filterHistory, filterOrders, fromHistoryLine, groupTimeline, historySearch, kindCounts, mergeOrders, movesSummary, planFromError, revertActionLabel, revertBlockNote, revertLead } from './history';

const e = (o: Partial<HistoryEntryOut>): HistoryEntryOut => ({
  ingest_id: 1, at: '2026-10-01T03:00:00+00:00', method: 'precon', kind: 'deck', title: 'Party Time', detail: null, dated: 'acquired',
  ledgered: true, copies_in: 10, copies_out: 0, held: 10, printings: 8, value_usd: 5, lines: 8, product: null, set_code: 'clb', deck_slug: null, ...o,
});

const ENTRIES = [
  e({ ingest_id: 6, kind: 'move', method: 'deck-assign', title: 'Built A', held: 0, value_usd: 0 }),
  e({ ingest_id: 5, title: 'A' }),
  e({ ingest_id: 4, kind: 'move', method: 'deck-unassign', title: 'Broke down B', held: 0, value_usd: 0 }),
  e({ ingest_id: 3, kind: 'pool', title: 'Land Pack', at: '2026-09-23T00:00:00+00:00', set_code: 'tmt', value_usd: 2.5, held: 30 }),
  e({ ingest_id: 2, kind: 'move', method: 'deck-assign', title: 'Built C', at: '2026-09-22T00:00:00+00:00', held: 0, value_usd: 0 }),
  e({ ingest_id: 1, kind: 'checklist', title: 'Checklist · The Hobbit', detail: 'the-hobbit-add-checklist.xlsx', at: '2026-09-01T00:00:00+00:00', ledgered: false, held: 0, value_usd: 0 }),
];

describe('history view-model', () => {
  it('filters by kind, day range and text (title, detail, set)', () => {
    const f = { q: '', kinds: [], from: undefined, to: undefined };
    expect(filterHistory(ENTRIES, { ...f, kinds: ['pool'] }).map((x) => x.ingest_id)).toEqual([3]);
    expect(filterHistory(ENTRIES, { ...f, from: '2026-09-22', to: '2026-09-23' }).map((x) => x.ingest_id)).toEqual([3, 2]);
    expect(filterHistory(ENTRIES, { ...f, q: 'hobbit-add' }).map((x) => x.ingest_id)).toEqual([1]);
    expect(filterHistory(ENTRIES, { ...f, q: 'TMT' }).map((x) => x.ingest_id)).toEqual([3]);
  });

  it('groups by month; gathers a day of deck moves into one run; a lone move stays a row', () => {
    const g = groupTimeline(ENTRIES);
    expect(g.map((m) => m.label)).toEqual(['October 2026', 'September 2026']);
    expect(g[0].rows.map((r) => r.type)).toEqual(['moves', 'entry']);
    const run = g[0].rows[0];
    expect(run.type === 'moves' && run.entries.map((x) => x.ingest_id)).toEqual([6, 4]);
    expect(run.type === 'moves' && movesSummary(run.entries)).toBe('Built 1 deck · broke down 1');
    expect(g[1].rows.map((r) => r.key)).toEqual(['3', '2', '1']);
    expect([g[0].copiesIn, g[0].valueUsd, g[1].valueUsd]).toEqual([10, 5, 2.5]);
  });

  it('counts kinds in canonical order and parses URL state', () => {
    expect(kindCounts(ENTRIES).map((k) => [k.value, k.count])).toEqual([['deck', 1], ['pool', 1], ['checklist', 1], ['move', 3]]);
    expect(historySearch.parse({ entry: '540', kinds: 'pool', from: 'nope' })).toMatchObject({ entry: 540, kinds: ['pool'], from: undefined, view: 'list' });
    expect(datedNote({ dated: 'identified' })).toMatch(/not the purchase date/);
    expect(datedNote({ dated: 'acquired' })).toBeNull();
  });

  it('maps a drill-in line to an exact-finish card with its held copies', () => {
    const l: HistoryLineOut = {
      finish: 'foil', copies_in: 3, copies_out: 1, held: 2, unit_usd: 4.5,
      printing: { scryfall_id: 's', oracle_id: 'o', name: 'Alpha', set_code: 'fin', set_name: 'Final Fantasy', collector_number: '7', rarity: 'rare', finishes: ['nonfoil', 'foil'], treatment: '', image_uri: null, price_usd: 1, price_usd_foil: 4.5, released_at: null, type_line: 'Creature — Elf', cmc: 2, owned: {}, free: 0 },
    };
    const c = fromHistoryLine(l);
    expect([c.key, c.finish, c.price, c.owned, c.missing]).toEqual(['s|foil', 'foil', 4.5, { foil: 2 }, false]);
    expect(c.tags).toEqual(['+3 in', '−1 out']);
  });
});

describe('store orders in the timeline', () => {
  const o = (x: Partial<PurchaseOut>): PurchaseOut => ({
    purchase_id: 1, store: 'manapool', store_name: 'Mana Pool', order_id: 'MP-1', ordered_at: '2026-09-20', read_at: '2026-09-21', lines: 1, copies: 2,
    assigned: 0, assignable: 2, unresolved: 0, status: 'new', paid_usd: 10, worth_usd: 12, compared_paid_usd: 10, gain_usd: 2, ingest_id: null, ...x,
  });
  const done = o({ purchase_id: 2, order_id: 'MP-2', status: 'done', ingest_id: 20, ordered_at: '2026-09-10' });
  const partial = o({ purchase_id: 3, order_id: 'MP-3', status: 'partial', ingest_id: 30, ordered_at: '2026-09-15' });
  const fresh = o({ purchase_id: 4, order_id: 'MP-4', status: 'new', ordered_at: '2026-09-25' });
  const recorded = o({ purchase_id: 5, order_id: 'MP-5', status: 'nothing', ordered_at: '2026-09-23' });
  const entries = [
    ...ENTRIES.slice(0, 3),
    e({ ingest_id: 30, kind: 'purchase', method: 'purchase', title: 'Mana Pool order #MP-3', at: '2026-09-28T00:00:00+00:00', purchase_id: 3 }),
    ...ENTRIES.slice(3),
    e({ ingest_id: 20, kind: 'purchase', method: 'purchase', title: 'Mana Pool order #MP-2', at: '2026-08-30T00:00:00+00:00', purchase_id: 2 }),
  ];

  it('shows every order once: undecided ones under Needs review, an applied one on its ledger entry, a recorded-only one on its own', () => {
    const m = mergeOrders(entries, [done, partial, fresh, recorded]);
    expect(m.review.map((p) => p.purchase_id)).toEqual([4, 3]);
    expect(m.entries.map((x) => x.ingest_id)).not.toContain(30);
    expect(m.orderOf.get(20)?.purchase_id).toBe(2);
    expect(m.orders.map((p) => p.purchase_id)).toEqual([5]);
    expect(kindCounts(m.entries, m.review.length + m.orders.length).find((k) => k.value === 'purchase')).toMatchObject({ label: 'Store order', count: 4 });
    expect(mergeOrders(entries).entries).toHaveLength(entries.length);
  });

  it('interleaves recorded-only orders by date and filters orders like entries', () => {
    const m = mergeOrders(entries, [recorded]);
    const sep = groupTimeline(m.entries, m.orders).find((g) => g.key === '2026-09')!;
    expect(sep.rows.map((r) => r.key)).toEqual(['30', '3', 'order:5', '2', '1']);
    const f = { q: '', kinds: [], from: undefined, to: undefined };
    expect(filterOrders([fresh, recorded], { ...f, kinds: ['pool'] })).toEqual([]);
    expect(filterOrders([fresh, recorded], { ...f, kinds: ['purchase'], from: '2026-09-24' }).map((p) => p.purchase_id)).toEqual([4]);
    expect(filterOrders([fresh, recorded], { ...f, q: 'mp-5' }).map((p) => p.purchase_id)).toEqual([5]);
    expect(filterOrders([fresh, recorded], { ...f, q: 'not added' }).map((p) => p.purchase_id)).toEqual([4]);
  });
});

describe('revert one import', () => {
  const printing = { scryfall_id: 's1', name: 'Alpha', set_code: 'fin', collector_number: '1' } as RevertPlanOut['lines'][number]['printing'];
  const line = (o: Partial<RevertPlanOut['lines'][number]> = {}) => ({ printing, finish: 'nonfoil' as const, remove: 2, restore: 0, held: 2, owned: 2, pledged: 0, blocker: null, pledged_to: [], ...o });
  const plan = (o: Partial<RevertPlanOut> = {}): RevertPlanOut => ({ ingest_id: 1, ok: true, copies_removed: 2, copies_restored: 0, lines: [line()], decks: [], ...o });

  it('says what leaves in one sentence and names the action', () => {
    expect(revertLead(plan())).toBe('This removes 2 copies (1 printing) from your collection.');
    expect(revertLead(plan({ decks: [{ slug: 'g', name: 'Goblins', built: false, pledged: 0 }] }))).toBe(
      'This removes 2 copies (1 printing) from your collection and deletes the decklist Goblins it saved.');
    expect(revertLead(plan({ copies_removed: 0, copies_restored: 1, lines: [line({ remove: 0, restore: 1 })] }))).toBe(
      'This puts back 1 copy (1 printing) it took out.');
    expect(revertActionLabel(plan())).toBe('Remove 2 copies');
    expect(revertActionLabel(plan({ copies_removed: 0, copies_restored: 1 }))).toBe('Put back 1 copy');
  });

  it('explains each blocker with its way out', () => {
    expect(revertBlockNote(line())).toBeNull();
    expect(revertBlockNote(line({ blocker: 'removed', held: 1 }))).toBe('Only 1 of 2 copies still came from this import — the rest were removed or moved since.');
    expect(revertBlockNote(line({ blocker: 'pledged', pledged: 2, pledged_to: ['A', 'B'] }))).toBe('2 copies are in A, B — break those decks down first.');
  });

  it('reads the plan a refused revert answered with', () => {
    expect(planFromError({ message: 'x', plan: plan({ ok: false }) })?.ok).toBe(false);
    expect(planFromError('nope')).toBeNull();
  });
});

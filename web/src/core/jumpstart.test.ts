import { describe, expect, it } from 'vitest';
import type { JumpstartPackCardOut, JumpstartPackOut, PrintingOut } from './api';
import { coverage, filterPacks, fromPackCard, groupPacks, jumpstartSearch, ownedLabel, packCardGroups, shopLead, showCounts, summaryLine } from './jumpstart';

const p = (o: Partial<JumpstartPackOut>): JumpstartPackOut => ({
  file_name: 'Angels1_J25', name: 'Angels (1)', theme: 'Angels', version: 1, color: 'W', card_count: 20, usd_total: 5, top_card: 'Giada, Font of Hope',
  top_card_usd: 0.5, top_card_image: null, front_card: 'Angels', built: 0, deconstructed: 0, deck_slug: null, have: 20, short: 0, status: 'build', ...o,
});

const PACKS = [
  p({}),
  p({ file_name: 'Angels2_J25', name: 'Angels (2)', version: 2, have: 18, short: 2, status: 'close', built: 1, deconstructed: 1 }),
  p({ file_name: 'Pirates1_J25', name: 'Pirates (1)', theme: 'Pirates', color: 'U', have: 9, short: 11, status: 'far', top_card: 'Spyglass Siren' }),
  p({ file_name: 'Wizards_J25', name: 'Wizards', theme: 'Wizards', version: null, color: 'UR', have: 4, short: 16, status: 'far', deconstructed: 1 }),
  p({ file_name: 'Golems_J25', name: 'Golems', theme: 'Golems', version: null, color: 'C', status: 'build' }),
];

const printing = (o: Partial<PrintingOut>): PrintingOut => ({
  scryfall_id: 's1', oracle_id: null, name: 'Giada, Font of Hope', set_code: 'j25', set_name: null, collector_number: '7', rarity: 'rare', finishes: ['nonfoil', 'foil'],
  treatment: '', image_uri: null, price_usd: 0.5, price_usd_foil: 1, released_at: null, type_line: 'Legendary Creature — Angel', cmc: 2, owned: { nonfoil: 1 }, free: 1, ...o,
});
const card = (o: Partial<JumpstartPackCardOut>): JumpstartPackCardOut => ({ printing: printing({}), count: 1, foil: false, unit_usd: 0.5, free: 1, ...o });

describe('jumpstart view-model', () => {
  it('parses URL state with defaults', () => {
    expect(jumpstartSearch.parse({})).toEqual({ show: 'all', q: '', shop: 'buildable', view: 'list' });
    expect(jumpstartSearch.parse({ show: 'nope', shop: 'packs', set: 'j25' })).toMatchObject({ show: 'all', shop: 'packs', set: 'j25' });
  });

  it('filters by readiness, ownership and text (name, top card, front card)', () => {
    const f = (show: 'all' | 'build' | 'close' | 'own', q = '') => filterPacks(PACKS, { show, q }).map((x) => x.file_name);
    expect(f('build')).toEqual(['Angels1_J25', 'Golems_J25']);
    expect(f('close')).toEqual(['Angels2_J25']);
    expect(f('own')).toEqual(['Angels2_J25', 'Wizards_J25']);
    expect(f('all', 'siren')).toEqual(['Pirates1_J25']);
    expect(showCounts(PACKS)).toEqual({ all: 5, build: 2, close: 1, own: 2 });
  });

  it('groups mono colours in WUBRG order with colorless first and multicolour last', () => {
    const g = groupPacks([PACKS[3], PACKS[2], PACKS[0], PACKS[4], PACKS[1]]);
    expect(g.map((x) => [x.label, x.packs.length, x.ready])).toEqual([['Colorless', 1, 1], ['White', 2, 1], ['Blue', 1, 0], ['Multicolour', 1, 0]]);
  });

  it('says how far free cards go and what you own', () => {
    expect(coverage(PACKS[0])).toBe('All 20 free');
    expect(coverage(PACKS[1])).toBe('2 short');
    expect(coverage(PACKS[2])).toBe('9 of 20 free');
    expect(ownedLabel(PACKS[1])).toBe('×1 built · 1 broken down');
    expect(ownedLabel(PACKS[0])).toBe('');
    expect(summaryLine({ packs: PACKS, themes: 4 })).toBe('5 pack versions of 4 themes · you own 2 · 2 ready to build from free cards · 1 close');
  });

  it('labels both shopping lists, and their empty states', () => {
    const d = { buildable: { cards: 3, copies: 4, usd: 2.5 }, whole: { cards: 40, copies: 60, usd: 30 }, whole_packs: 3 };
    expect(shopLead('buildable', d)).toMatch(/^Copy bulk lists · 4 cards to build every theme · ≈ \$2\.50 at market$/);
    expect(shopLead('packs', d)).toMatch(/3 packs you don’t own · 60 cards · ≈ \$30\.00/);
    expect(shopLead('buildable', { ...d, buildable: { cards: 0, copies: 0, usd: 0 } })).toBe('Every theme is buildable from cards you own');
    expect(shopLead('packs', { ...d, whole_packs: 0 })).toBe('You own every pack version');
  });

  it('maps pack cards: shipped finish, copies in the pack, free copies; missing when short', () => {
    const ok = fromPackCard(card({ count: 2, free: 3 }));
    expect([ok.missing, ok.note, ok.tags[0], ok.finish]).toEqual([false, '3 free', '×2 in pack', 'nonfoil']);
    const short = fromPackCard(card({ count: 2, free: 1, foil: true, unit_usd: 1 }));
    expect([short.missing, short.note, short.finish, short.price, short.key]).toEqual([true, '1 of 2 free', 'foil', 1, 's1|foil']);
    expect(fromPackCard(card({ free: 0 })).note).toBe('None free');
  });

  it('sections pack cards by type, counting copies when they differ from lines', () => {
    const g = packCardGroups([
      card({}),
      card({ printing: printing({ scryfall_id: 'p', name: 'Plains', type_line: 'Basic Land — Plains' }), count: 7 }),
    ]);
    expect(g.map((x) => x.label)).toEqual(['Creatures', 'Lands · 7']);
  });
});

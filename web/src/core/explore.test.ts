import { describe, expect, it } from 'vitest';
import type { CardExploreOut, CardProfileOut, EntryOut, FactsOut, PairedOut } from './api';
import { coplayGroups, deckShare, defaultRole, fromEntry, fromPaired, pairedSections, profileSections } from './explore';

const facts = (o: Partial<FactsOut> = {}): FactsOut => ({ oracle_id: null, type_line: 'Artifact', cmc: 1, color_identity: [], lowest_usd: 1, scryfall_id: null, image_uri: null, set_code: 'cmd', collector_number: '1', scryfall_url: null, owned: 0, free: 0, ...o });
const entry = (name: string, o: Partial<EntryOut> = {}): EntryOut => ({ name, slug: name.toLowerCase(), facts: facts({ oracle_id: `o-${name}` }), num_decks: 10, potential_decks: 100, share: 10, lift: 1, group: null, ...o });
const profile = (o: Partial<CardProfileOut> = {}): CardProfileOut => ({
  name: 'Sol Ring', slug: 'sol-ring', facts: facts(), commander_eligible: false, num_decks: 8_400_000, potential_decks: 10_200_000, salt: 1.4,
  functions: [], tags: [], commanders: [], coplayed: [], similar: [], deck_mix: [], ...o,
});

describe('explore (card role)', () => {
  it('picks the commander role only for cards that can lead', () => {
    expect(defaultRole(true)).toBe('commander');
    expect(defaultRole(false)).toBe('card');
    expect(defaultRole(undefined)).toBe('card');
  });

  it('maps entries: share is the guide %, lift the note, ownership a tag', () => {
    const c = fromEntry(entry('Birds', { share: 30.8, lift: 1.09, facts: facts({ oracle_id: 'o-b', owned: 3, free: 1 }) }));
    expect([c.key, c.pct, c.note, c.tags]).toEqual(['o-b', 30.8, '1.09× lift', ['3 owned · 1 free']]);
    const p: PairedOut = { name: 'X', slug: 'x', facts: facts({ oracle_id: 'o-x' }), bucket: 'both', a: entry('X', { share: 40, lift: 2 }), b: entry('X', { share: 10, lift: 1.5 }), gap: 30 };
    expect(fromPaired(p)).toMatchObject({ bars: { a: 40, b: 10 }, note: 'lift 2.00× / 1.50×' });
  });

  it('sections a profile: commanders by share, co-played by type in lift order, similar; filters apply', () => {
    const p = profile({
      commanders: [entry('Low', { share: 5, group: 'top' }), entry('High', { share: 90, group: 'top' }), entry('Fresh', { group: 'new' })],
      coplayed: [entry('A', { group: 'Creatures', lift: 1 }), entry('B', { group: 'Creatures', lift: 3 }), entry('L', { group: 'Lands', lift: 2 })],
      similar: [entry('Mana Vault')],
    });
    const s = profileSections(p, '', []);
    expect(s.map((x) => [x.label, x.items.map((c) => c.name)])).toEqual([
      ['Commanders that run it', []], ['Top commanders', ['High', 'Low']], ['New commanders', ['Fresh']],
      ['Played alongside', []], ['Creatures', ['B', 'A']], ['Lands', ['L']],
      ['Similar cards', []], ['Cards like it', ['Mana Vault']],
    ]);
    expect(profileSections(p, '', ['Lands']).filter((x) => x.key.startsWith('co:')).map((x) => x.label)).toEqual(['Lands']);
    expect(profileSections(p, 'mana', []).map((x) => x.label)).toEqual(['Similar cards', 'Cards like it']);
  });

  it('sections a comparison column and counts co-play groups', () => {
    const pair = (name: string, bucket: PairedOut['bucket'], group: string | null): PairedOut => ({ name, slug: name, facts: facts({ oracle_id: name }), bucket, a: bucket !== 'b_only' ? entry(name, { group }) : null, b: bucket !== 'a_only' ? entry(name, { group }) : null, gap: null });
    const r: CardExploreOut = { a: profile(), b: profile({ name: 'Arcane Signet' }), commanders: [pair('Cmd', 'both', 'top')], coplayed: [pair('Elf', 'both', 'Creatures'), pair('Land', 'a_only', 'Lands')], tags: {} };
    expect(pairedSections(r, 'both', '', []).map((x) => x.label)).toEqual(['Commanders that run it', 'Played alongside · Creatures']);
    expect(pairedSections(r, 'a_only', '', []).map((x) => x.label)).toEqual(['Played alongside · Lands']);
    expect(coplayGroups(r)).toEqual([['Creatures', 1], ['Lands', 1]]);
  });

  it('formats deck share compactly', () => {
    expect(deckShare({ num_decks: 8_400_000, potential_decks: 10_200_000 })).toMatch(/^8\.4M of 10\.2M possible decks \(82%\)$/);
    expect(deckShare({ num_decks: null, potential_decks: null })).toBeNull();
  });
});

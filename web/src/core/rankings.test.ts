import { describe, expect, it } from 'vitest';
import type { FactsOut, RankedOut, RankingOut } from './api';
import { cardType, creatureType, edhrecUrl, emptyRankingNote, exploreMode, failureText, rankedTypes, fetchedAgo, fmtMetric, nextPage, partialRankingNote, rankedCard, rankingPage, rankingRequest, rankingSummary, roleFor, timeframeApplies, type RankingsState } from './rankings';

const state = (o: Partial<RankingsState> = {}): RankingsState => ({ rank: 'commanders', tf: 'week', own: 'all', rq: '', ...o });
const facts = (o: Partial<FactsOut> = {}): FactsOut => ({ oracle_id: 'o', type_line: 'Legendary Creature', cmc: 3, color_identity: ['R'], lowest_usd: 2, scryfall_id: 's', image_uri: null, set_code: 'm13', collector_number: '1', scryfall_url: null, owned: 0, free: 0, ...o });
const row = (name: string, o: Partial<RankedOut> = {}): RankedOut => ({ rank: 1, name, slug: name.toLowerCase(), facts: facts({ oracle_id: `o-${name}` }), num_decks: 1234, salt: null, trend: null, ...o });

describe('rankings', () => {
  it('names a short pool honestly, and stays quiet when the list was read in full', () => {
    expect(partialRankingNote({ base: 100, pool_complete: true, pool_partial_reason: null })).toBeNull();
    expect(partialRankingNote({ base: 200, pool_complete: false, pool_partial_reason: 'rate_limited' }))
      .toBe('Showing the first 200 — EDHREC limited the read. Refresh to fetch the rest.');
    expect(partialRankingNote({ base: 1300, pool_complete: false, pool_partial_reason: 'read_failed' }))
      .toBe('Showing the first 1,300 — EDHREC stopped answering partway through. Refresh to fetch the rest.');
  });

  it('opens on rankings until a card is picked; an explicit mode wins', () => {
    expect(exploreMode(undefined, undefined)).toBe('rankings');
    expect(exploreMode(undefined, 'Sol Ring')).toBe('card');
    expect(exploreMode('rankings', 'Sol Ring')).toBe('rankings');
    expect(exploreMode(undefined, undefined, 'art=moon')).toBe('surf');
    expect(exploreMode('surf', 'Sol Ring')).toBe('surf');
    expect(exploreMode(undefined, 'Sol Ring', 'on')).toBe('surf');
    expect(exploreMode('card', 'Sol Ring', 'on')).toBe('card');
  });

  it('builds one request with every filter set (they combine)', () => {
    expect(rankingRequest(state())).toEqual({ scope: 'commanders', timeframe: 'week' });
    expect(rankingRequest(state({ color: 'azorius', tag: '  goblins ', fam: 'fin' }))).toEqual({ scope: 'commanders', timeframe: 'week', color: 'azorius', tag: 'goblins', set_family: 'fin' });
    expect(rankingRequest(state({ color: '', tag: ' ' }))).toEqual({ scope: 'commanders', timeframe: 'week' });
    // filters only narrow commanders: stale ones are ignored for cards / salt
    expect(rankingRequest(state({ rank: 'salt', color: 'azorius' }))).toEqual({ scope: 'salt', timeframe: 'week' });
  });

  it('offers a timeframe only where EDHREC has one', () => {
    expect(timeframeApplies(state())).toBe(true);
    expect(timeframeApplies(state({ color: 'azorius' }))).toBe(true);
    expect(timeframeApplies(state({ color: 'azorius', tag: 'goblins' }))).toBe(true);
    expect(timeframeApplies(state({ tag: 'goblins' }))).toBe(false);
    expect(timeframeApplies(state({ fam: 'fin', color: 'azorius' }))).toBe(false);
    expect(timeframeApplies(state({ rank: 'salt' }))).toBe(false);
    expect(timeframeApplies(state({ rank: 'cards', tag: 'goblins' }))).toBe(true);
  });

  it('pages the ranking: 100 first, then 50 at a time', () => {
    const req = rankingRequest(state({ color: 'azorius' }));
    expect(rankingPage(req, { own: 'unused', rq: ' kren ' }, 150)).toEqual({ ...req, q: 'kren', own: 'unused', offset: 0, limit: 150 });
    expect(nextPage(100, 312)).toBe(50);
    expect(nextPage(300, 312)).toBe(12);
    expect(nextPage(312, 312)).toBe(0);
  });

  it('never shows an exception name, and an empty set reads calmly', () => {
    expect(failureText('EdhrecError: EDHREC has no “gobblinz” tag.')).toBe('EDHREC has no “gobblinz” tag.');
    expect(failureText(null)).toBe('EDHREC didn’t answer.');
    expect(emptyRankingNote(state({ fam: 'acr' }), 'Assassin’s Creed')).toBe('EDHREC lists no commanders from Assassin’s Creed yet.');
  });

  it('opens commanders as commanders and cards / salt as cards', () => {
    expect(roleFor('commanders')).toBe('commander');
    expect(roleFor('cards')).toBe('card');
    expect(roleFor('salt')).toBe('card');
  });

  it('maps a ranked row to the guide card with rank + metric in the note', () => {
    const c = rankedCard('commanders', row('Krenko', { rank: 3, num_decks: 5084, facts: facts({ oracle_id: 'o-k', owned: 2, free: 1 }) }));
    expect(c.key).toBe('o-k');
    expect(c.note).toMatch(/^#3 · 5\.1K decks$/);
    expect(c.tags).toEqual(['2 owned · 1 unused']);
    expect(fmtMetric('salt', row('Stasis', { salt: 3.0572 }))).toBe('3.06');
  });

  it('links each ranking to its EDHREC page', () => {
    const r = (o: Partial<RankingOut>) => ({ scope: 'commanders', timeframe: 'week', filter: '', ...o }) as RankingOut;
    expect(edhrecUrl(r({}))).toBe('https://edhrec.com/commanders/week');
    expect(edhrecUrl(r({ scope: 'cards', timeframe: 'month' }))).toBe('https://edhrec.com/top/month');
    expect(edhrecUrl(r({ scope: 'salt', timeframe: 'all' }))).toBe('https://edhrec.com/top/salt');
    expect(edhrecUrl(r({ filter: 'color:mono-red' }))).toBe('https://edhrec.com/commanders/mono-red/week');
    expect(edhrecUrl(r({ filter: 'tag:goblins', timeframe: 'all' }))).toBe('https://edhrec.com/tags/goblins');
    expect(edhrecUrl(r({ filter: 'set:fin', timeframe: '' }))).toBe('https://edhrec.com/sets/fin');
  });

  it('says when the list was read and how much of it you own', () => {
    const now = new Date('2026-10-06T12:00:00');
    expect(fetchedAgo('2026-10-06T08:00:00', now)).toBe('today');
    expect(fetchedAgo('2026-10-05T23:00:00', now)).toBe('yesterday');
    expect(fetchedAgo('2026-10-01T12:00:00', now)).toBe('5 days ago');
    expect(fetchedAgo(null, now)).toBeNull();
    expect(rankingSummary({ total: 2, pool: 2, owned: 1, unused: 1 })).toBe('2 ranked · you own 1 · 1 unused');
    expect(rankingSummary({ total: 1, pool: 480, owned: 9, unused: 4 })).toBe('1 of 480 match · you own 9 · 4 unused');
  });

  it('splits the type line into card type and creature type', () => {
    expect(cardType('Legendary Creature — Goblin Warrior', 'commanders')).toBe('Creature');
    expect(cardType('Legendary Planeswalker — Jace', 'commanders')).toBe('Planeswalker');
    expect(cardType('Legendary Artifact Creature — Golem', 'cards')).toBe('Legendary Artifact Creature');
    expect(cardType('Instant', 'cards')).toBe('Instant');
    expect(creatureType('Legendary Creature — Elf Druid // Legendary Land')).toBe('Elf Druid');
    expect(creatureType('Instant')).toBeNull();
    expect(cardType(null, 'cards')).toBeNull();
  });

  it('shows both partners in the type columns, once when they agree', () => {
    const pair = row('Kraum // Tymna', { facts: facts({ oracle_id: null, type_line: 'Legendary Creature — Zombie Horror', partner: facts({ type_line: 'Legendary Creature — Human Cleric' }) }) });
    expect(rankedTypes('commanders', pair)).toEqual({ card: 'Creature', sub: 'Zombie Horror / Human Cleric' });
  });

  it('a partner pairing is one guide card with both names and the partner behind it', () => {
    const pair = row('Kraum, Ludevic’s Opus // Tymna the Weaver', { facts: facts({ oracle_id: null, image_uri: 'a.jpg', partner: facts({ image_uri: 'b.jpg' }) }) });
    const c = rankedCard('commanders', pair);
    expect(c.key).toBe('slug:kraum, ludevic’s opus // tymna the weaver');
    expect(c.partner).toEqual({ name: 'Tymna the Weaver', image: 'b.jpg', href: null, scryfallId: 's', setCode: 'M13', cn: '1' });
    expect(c.prices).toBeUndefined();
    expect(c.lines.plain).toBe('1 Kraum, Ludevic’s Opus\n1 Tymna the Weaver');
    expect(rankedCard('commanders', row('Sol Ring')).partner).toBeNull();
  });
});

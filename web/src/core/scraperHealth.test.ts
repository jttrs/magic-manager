import { describe, expect, it } from 'vitest';
import { deckKey, deckSourceOf, downAmong, isReportable, noticeFor, sinceText, storeHealthLookup, type ScraperHealth } from './scraperHealth';

const h = (over: Partial<ScraperHealth>): ScraperHealth => ({
  key: 'deck-import/archidekt', scraper: 'deck-import', site: 'archidekt', site_name: 'Archidekt', label: 'Archidekt deck import',
  where: 'Add cards', canary: 'http', status: 'ok', since: null, checked_at: null, last_ok: null, code: null, message: null, fix: null, via: null,
  ...over,
});

describe('scraper health', () => {
  it('maps deck links to their builder like decksource.source_of', () => {
    expect(deckSourceOf('https://www.moxfield.com/decks/abc')).toBe('moxfield');
    expect(deckSourceOf(' https://archidekt.com/decks/1-x ')).toBe('archidekt');
    expect(deckSourceOf('https://manabox.app/decks/x')).toBe('manabox');
    expect(deckSourceOf('https://scryfall.com/@u/decks/1')).toBe('scryfall');
    expect(deckSourceOf('https://notmoxfield.com/decks/1')).toBeNull();
    expect(deckSourceOf('not a url')).toBeNull();
    expect(deckKey('mtggoldfish')).toBe('deck-import/mtggoldfish');
  });

  it('finds only the down scrapers asked about, in order', () => {
    const all = [h({ key: 'a', status: 'down' }), h({ key: 'b', status: 'ok' }), h({ key: 'c', status: 'down' })];
    expect(downAmong(all, ['c', 'b', 'a', 'zz']).map((x) => x.key)).toEqual(['c', 'a']);
    expect(downAmong(undefined, ['a'])).toEqual([]);
  });

  it('looks stores up by vendor key or the name offers carry', () => {
    const look = storeHealthLookup([h({ key: 'store-price/manyrealms', scraper: 'store-price', site: 'manyrealms', site_name: 'Many Realms', status: 'down' })]);
    expect(look('manyrealms')?.status).toBe('down');
    expect(look('Many Realms')?.key).toBe('store-price/manyrealms');
    expect(look('TCGplayer market')).toBeUndefined();
    expect(look(null)).toBeUndefined();
  });

  it('says since when in plain words', () => {
    const now = new Date(2026, 9, 10, 12, 0);
    expect(sinceText(new Date(2026, 9, 10, 6, 30).toISOString(), now)).toBe('today 6:30 AM');
    expect(sinceText(new Date(2026, 9, 9, 6, 30).toISOString(), now)).toBe('yesterday 6:30 AM');
    expect(sinceText(new Date(2026, 9, 2, 6, 30).toISOString(), now)).toBe('Oct 2');
    expect(sinceText(new Date(2025, 9, 2).toISOString(), now)).toBe('Oct 2, 2025');
    expect(sinceText(null, now)).toBe('');
  });

  it('builds the notice: what, why, since when, how found, the code', () => {
    const now = new Date(2026, 9, 10, 12, 0);
    const n = noticeFor(h({ status: 'down', since: new Date(2026, 9, 10, 6, 30).toISOString(), code: 'scrape.no_cards',
      message: 'The deck page returned no cards — its format changed.', via: 'canary' }), now);
    expect(n.title).toBe('Archidekt deck import — temporarily down');
    expect(n.meta).toBe('Since today 6:30 AM · found by the daily check · Code scrape.no_cards');
    expect(n.tip).toContain('You can still try.');
    expect(noticeFor(h({ status: 'down', via: 'use' }), now).meta).toBe('found while reading');
  });

  it('only reports page-changed companion codes', () => {
    expect(isReportable('cart.page_changed')).toBe(true);
    expect(isReportable('moxfield.changed')).toBe(true);
    expect(isReportable('cart.empty')).toBe(false);
  });
});

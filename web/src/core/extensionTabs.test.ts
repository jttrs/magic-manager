import { describe, expect, it } from 'vitest';

// Which open tab the companion's readers reuse (extension/src/protocol.js pickTab, behind withTab in
// background.js). A session-restored tab Chrome hasn't loaded (`status: 'unloaded'` — not `discarded`)
// can't be scripted: reusing one made a live Archidekt read fail as archidekt.blocked (companion 0.5.2).
// protocol.js is plain browser ESM with no types, so it is loaded by path at run time.
type Tab = { id: number; url: string; status?: string; incognito?: boolean; discarded?: boolean };
type Protocol = {
  pickTab: (tabs: Tab[], target: string) => Tab | null;
  samePage: (tabUrl: string, target: string) => boolean;
  summarize: (kind: string, data: unknown) => string;
};

const MODULE = new URL('../../../extension/src/protocol.js', import.meta.url).pathname;
const load = () => import(/* @vite-ignore */ MODULE) as Promise<Protocol>;

const DECK = 'https://archidekt.com/decks/26677169';
const ARTICLE = 'https://archidekt.com/articles/edhrec/some-article?utm_source=edhrec';

describe('companion pickTab', () => {
  it('skips an unloaded first tab for a loaded one showing the deck', async () => {
    const { pickTab } = await load();
    const tabs = [
      { id: 1, url: ARTICLE, status: 'unloaded' },
      { id: 2, url: `${DECK}/yuna_summoner_optimized`, status: 'complete' },
    ];
    expect(pickTab(tabs, DECK)?.id).toBe(2);
  });

  it('opens its own tab when every match is unloaded, discarded or incognito', async () => {
    const { pickTab } = await load();
    const tabs = [
      { id: 1, url: DECK, status: 'unloaded' },
      { id: 3, url: DECK, status: 'complete', discarded: true },
      { id: 4, url: DECK, status: 'complete', incognito: true },
    ];
    expect(pickTab(tabs, DECK)).toBeNull();
    expect(pickTab([], DECK)).toBeNull();
  });

  it('reuses a tab still loading (the reader waits for it), but a loaded one wins', async () => {
    const { pickTab } = await load();
    const loading = { id: 1, url: DECK, status: 'loading' };
    expect(pickTab([{ id: 0, url: DECK, status: 'unloaded' }, loading], DECK)?.id).toBe(1);
    expect(pickTab([loading, { id: 2, url: ARTICLE, status: 'complete' }], DECK)?.id).toBe(2);
  });

  it('prefers the target page, else any loaded tab on the site', async () => {
    const { pickTab } = await load();
    const other = { id: 1, url: ARTICLE, status: 'complete' };
    const deck = { id: 2, url: `https://www.archidekt.com/decks/26677169?tab=cards`, status: 'complete' };
    expect(pickTab([other, deck], DECK)?.id).toBe(2);
    expect(pickTab([other], DECK)?.id).toBe(1);
  });

  it('matches pages by host and path, not by prefix of another id', async () => {
    const { samePage } = await load();
    expect(samePage(`${DECK}/`, DECK)).toBe(true);
    expect(samePage('https://archidekt.com/decks/266771690', DECK)).toBe(false);
    expect(samePage('https://moxfield.com/decks/abc', 'https://moxfield.com/')).toBe(false);
    expect(samePage('https://www.moxfield.com/', 'https://moxfield.com/')).toBe(true);
    expect(samePage('https://manapool.com/cart?x=1', 'https://manapool.com/cart')).toBe(true);
    expect(samePage('not a url', DECK)).toBe(false);
  });
});

describe('companion summary', () => {
  it('counts binders in the singular and plural', async () => {
    const { summarize } = await load();
    expect(summarize('moxfield_binders', { binders: [{}] })).toBe('1 Moxfield binder');
    expect(summarize('moxfield_binders', { binders: [{}, {}] })).toBe('2 Moxfield binders');
  });
});

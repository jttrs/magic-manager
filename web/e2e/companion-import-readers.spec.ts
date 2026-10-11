// Pinned behaviour of the browser companion's import readers — Archidekt decks
// and Moxfield collections / binders (extension/src/readers/{archidekt-deck,
// moxfield-api,moxfield-collection}.js) — in real Chromium against saved,
// de-personalised responses in tests/fixtures/companion/. The *.expected.json
// goldens are pushed through the server's strict models and engines by
// tests/test_companion_imports.py, so reader → app → engine stays one chain.
//
// Re-pin on purpose:  UPDATE_GOLDEN=1 npm --prefix web run e2e -- companion-import-readers
// A site changed?    .claude/skills/scrape-doctor/SKILL.md
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, test, type Page, type Route } from '@playwright/test';

const ROOT = resolve(import.meta.dirname, '../..');
const FIX = resolve(ROOT, 'tests/fixtures/companion');
const reader = (name: string) => readFileSync(resolve(ROOT, 'extension/src/readers', name), 'utf8');

function golden(name: string, actual: unknown) {
  const path = resolve(FIX, name);
  if (process.env.UPDATE_GOLDEN || !existsSync(path)) writeFileSync(path, JSON.stringify(actual, null, 2) + '\n');
  expect(actual).toEqual(JSON.parse(readFileSync(path, 'utf8')));
}

// ---------- Archidekt ----------

const ARCH_URL = 'https://archidekt.com/decks/13106730';
const archHtml = () => readFileSync(resolve(FIX, 'archidekt-deck.html'), 'utf8');

async function readArch(page: Page, body: string | null, { status = 200, id = '13106730' } = {}) {
  await page.route('https://archidekt.com/**', (r) => (body == null
    ? r.fulfill({ status, contentType: 'text/html', body: '<!doctype html><title>Not found</title>' })
    : r.fulfill({ status, contentType: 'text/html; charset=utf-8', body })));
  await page.route('https://archidekt.com/', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>Archidekt</title>' }));
  await page.goto('https://archidekt.com/');
  await page.addScriptTag({ content: reader('archidekt-deck.js') });
  return page.evaluate((deckId) => (window as unknown as { readArchidektDeck: (id: string) => Promise<unknown> }).readArchidektDeck(deckId), id);
}

test.describe('Archidekt deck reader', () => {
  test('reads the deck the page embeds: name, owner, each card’s printing, quantity, finish and category — nothing else', async ({ page }) => {
    const out = await readArch(page, archHtml()) as { ok: boolean; deck: { id: number; name: string; owner: { username: string }; cards: { quantity: number; modifier: string; categories: string[]; card: { oracleCard: { name: string } } }[] } };
    expect(out.ok).toBe(true);
    expect(out.deck.id).toBe(13106730);
    expect(out.deck.cards).toHaveLength(24);   // 25 in the map, one at quantity 0 (removed) is dropped
    const by = Object.fromEntries(out.deck.cards.map((c) => [c.card.oracleCard.name, c]));
    expect(by['Terra, Herald of Hope'].categories).toEqual(['Commander']);
    expect(by['Demolition Field'].modifier).toBe('Foil');
    expect(by['Angel of the Ruins'].categories).toEqual(['Maybeboard']);
    expect(by.Anger).toBeUndefined();
    const all = JSON.stringify(out);
    for (const dropped of ['203.0.113.7', 'jwt-should-never-be-read', 'fixture@example.invalid', 'prices', 'avatar', 'oracleCardUid', 'deckRelationId']) expect(all).not.toContain(dropped);
    golden('archidekt-deck.expected.json', out);
  });

  for (const [what, body, status, code] of [
    ['a deleted deck', null, 404, 'archidekt.not_found'],
    ['a server error', null, 500, 'archidekt.http'],
    ['a page without the deck data', '<!doctype html><title>Archidekt</title><div id="__next"></div>', 200, 'archidekt.changed'],
    ['a deck it won’t show this browser (private, signed out)', '<!doctype html><script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"redux":{"deck":{"name":"","cardMap":{}}}}}}</script>', 200, 'archidekt.private'],
  ] as const) {
    test(`names ${what} (${code})`, async ({ page }) => {
      expect(await readArch(page, body, { status })).toMatchObject({ ok: false, code });
    });
  }

  test('refuses an id that isn’t a deck id', async ({ page }) => {
    expect(await readArch(page, archHtml(), { id: '../account' })).toMatchObject({ ok: false, code: 'archidekt.bad_url' });
  });
});

// ---------- Moxfield (shared API helper, collection, binders, private deck) ----------

const COLL = JSON.parse(readFileSync(resolve(FIX, 'moxfield-collection.json'), 'utf8')) as { page1: unknown; page2: unknown };
const BINDER = readFileSync(resolve(FIX, 'moxfield-binder.json'), 'utf8');
const TOKEN = 'tok-never-leaves-the-reader';
const cors = { 'access-control-allow-origin': 'https://moxfield.com', 'access-control-allow-credentials': 'true', 'access-control-allow-headers': 'authorization, content-type' };
const json = (r: Route, status: number, body: unknown) => r.fulfill({ status, contentType: 'application/json', headers: cors, body: typeof body === 'string' ? body : JSON.stringify(body) });

type Api = { signedIn?: boolean; private?: boolean; binders?: unknown; seen?: string[] };

/** A fake api2.moxfield.com: public pages answer anyone; private ones need the bearer token the refresh hands a signed-in browser. */
async function moxApi(page: Page, api: Api) {
  await page.route('https://api2.moxfield.com/**', async (r) => {
    const req = r.request();
    if (req.method() === 'OPTIONS') return r.fulfill({ status: 204, headers: { ...cors, 'access-control-allow-methods': 'GET, POST' } });
    const u = new URL(req.url());
    const authed = req.headers().authorization === `Bearer ${TOKEN}`;
    api.seen?.push(`${req.method()} ${u.pathname}${authed ? ' (signed in)' : ''}`);
    if (u.pathname === '/v1/account/token/refresh') return api.signedIn ? json(r, 200, { access_token: TOKEN, expiration: '2099-01-01' }) : json(r, 400, { '': ['A refresh token is required.'] });
    const gated = api.private || u.pathname === '/v1/collections/search' || u.pathname === '/v1/trade-binders';
    if (gated && !authed) return json(r, 401, { title: 'Unauthorized' });
    if (u.pathname === '/v1/trade-binders') return json(r, 200, api.binders ?? []);
    if (u.pathname.endsWith('/search') && u.pathname.startsWith('/v1/trade-binders/')) return json(r, 200, BINDER);
    if (u.pathname.startsWith('/v1/collections/search')) return json(r, 200, u.searchParams.get('pageNumber') === '2' ? COLL.page2 : COLL.page1);
    if (u.pathname.startsWith('/v3/decks/all/')) return json(r, 200, readFileSync(resolve(FIX, 'moxfield-deck.json'), 'utf8'));
    return json(r, 404, {});
  });
  await page.route('https://moxfield.com/', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>Moxfield</title>' }));
  await page.goto('https://moxfield.com/');
  await page.addScriptTag({ content: reader('moxfield-api.js') });
  await page.addScriptTag({ content: reader('moxfield-collection.js') });
  await page.addScriptTag({ content: reader('moxfield-deck.js') });
}

const readColl = (page: Page, opts: { what: string; id?: string | null }) =>
  page.evaluate((o) => (window as unknown as { readMoxfieldCollection: (o: unknown) => Promise<unknown> }).readMoxfieldCollection(o), opts);

type Coll = { ok: boolean; code?: string; collection: { scope: string; id: string | null; name: string | null; signed_in: boolean; entries: number; lines: { name: string; finish: string; quantity: number; proxy?: boolean; digital?: boolean }[] } };

test.describe('Moxfield collection reader', () => {
  test('a shared collection link: every page, anonymously, copies of a printing summed, only what an import needs', async ({ page }) => {
    const seen: string[] = [];
    await moxApi(page, { seen });
    const out = await readColl(page, { what: 'collection', id: 'hgsItGBwRUybHyN0WZR41w' }) as Coll;
    expect(out.ok).toBe(true);
    expect(seen.filter((s) => s.includes('search'))).toEqual(['GET /v1/collections/search/hgsItGBwRUybHyN0WZR41w', 'GET /v1/collections/search/hgsItGBwRUybHyN0WZR41w']);
    expect(seen.some((s) => s.includes('refresh'))).toBe(false);   // never signs in for a public link
    const c = out.collection;
    expect([c.scope, c.id, c.signed_in, c.entries]).toEqual(['collection', 'hgsItGBwRUybHyN0WZR41w', false, 25]);
    expect(c.lines).toHaveLength(20);   // 25 entries: other conditions / languages of a printing are summed into one line
    expect(c.lines[0].quantity).toBe(3);
    expect(c.lines.map((l) => l.finish).slice(0, 3)).toEqual(['nonfoil', 'foil', 'etched']);
    expect(c.lines[3].proxy).toBe(true);
    expect(c.lines[4].digital).toBe(true);
    const all = JSON.stringify(out);
    for (const dropped of ['bought at FNM', 'lightlyPlayed', 'nearMint', 'Japanese', 'purchasePrice', 'fixture-user', 'createdAtUtc', 'usd', 'tcgplayer_id']) expect(all).not.toContain(dropped);
    golden('moxfield-collection.expected.json', out);
  });

  test('your own collection signs in the way moxfield.com does — the token is used, never returned', async ({ page }) => {
    const seen: string[] = [];
    await moxApi(page, { signedIn: true, seen });
    const out = await readColl(page, { what: 'collection' }) as Coll;
    expect(out.ok).toBe(true);
    expect(out.collection.signed_in).toBe(true);
    expect(seen).toEqual(['POST /v1/account/token/refresh', 'GET /v1/collections/search (signed in)', 'GET /v1/collections/search (signed in)']);
    expect(JSON.stringify(out)).not.toContain(TOKEN);
  });

  test('a private shared link: asks anonymously, then signed in', async ({ page }) => {
    const seen: string[] = [];
    await moxApi(page, { signedIn: true, private: true, seen });
    expect(await readColl(page, { what: 'collection', id: 'PrivAteId1' })).toMatchObject({ ok: true, collection: { signed_in: true } });
    expect(seen.slice(0, 3)).toEqual(['GET /v1/collections/search/PrivAteId1', 'POST /v1/account/token/refresh', 'GET /v1/collections/search/PrivAteId1 (signed in)']);
  });

  test('a binder: its name comes along for the import label', async ({ page }) => {
    await moxApi(page, {});
    const out = await readColl(page, { what: 'binder', id: 'LbwVB1hSiU2THiRQeR2QlQ' }) as Coll;
    expect(out.ok).toBe(true);
    expect([out.collection.scope, out.collection.name, out.collection.lines.length]).toEqual(['binder', 'Trade Box 1', 8]);
    golden('moxfield-binder.expected.json', out);
  });

  test('your binder list: names and ids only', async ({ page }) => {
    await moxApi(page, { signedIn: true, binders: [
      { id: 'RB2mJ', publicId: 'LbwVB1hSiU2THiRQeR2QlQ', name: 'Trade Box 1', description: 'my address is 1 Main St', visibility: 'private', totalCards: 2095 },
      { id: 'x', publicId: '../evil', name: 'bad id' },
    ] });
    const out = await readColl(page, { what: 'binders' });
    expect(out).toEqual({ ok: true, binders: [{ id: 'LbwVB1hSiU2THiRQeR2QlQ', name: 'Trade Box 1', cards: 2095 }] });
  });

  for (const [what, api, opts, code] of [
    ['your collection while signed out', {}, { what: 'collection' }, 'moxfield.signed_out'],
    ['your binders while signed out', {}, { what: 'binders' }, 'moxfield.signed_out'],
    ['a private link you can’t see', { private: true }, { what: 'collection', id: 'PrivAteId1' }, 'moxfield.private'],
    ['a link that isn’t an id', {}, { what: 'binder', id: '../users/me' }, 'moxfield.bad_url'],
    ['an unknown request', {}, { what: 'decks' }, 'moxfield.bad_url'],
  ] as const) {
    test(`names ${what} (${code})`, async ({ page }) => {
      await moxApi(page, api);
      expect(await readColl(page, opts)).toMatchObject({ ok: false, code });
    });
  }

  test('names Moxfield’s bot check and a changed format', async ({ page }) => {
    await page.route('https://api2.moxfield.com/**', (r) => r.fulfill({ status: 403, contentType: 'text/html', headers: cors, body: '<title>Just a moment...</title>' }));
    await page.route('https://moxfield.com/', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html>' }));
    await page.goto('https://moxfield.com/');
    await page.addScriptTag({ content: reader('moxfield-api.js') });
    await page.addScriptTag({ content: reader('moxfield-collection.js') });
    expect(await readColl(page, { what: 'collection', id: 'hgsItGBwRUybHyN0WZR41w' })).toMatchObject({ ok: false, code: 'moxfield.blocked' });
    await page.unroute('https://api2.moxfield.com/**');
    await page.route('https://api2.moxfield.com/**', (r) => json(r, 200, { results: [] }));
    expect(await readColl(page, { what: 'collection', id: 'hgsItGBwRUybHyN0WZR41w' })).toMatchObject({ ok: false, code: 'moxfield.changed' });
  });
});

test.describe('Moxfield deck reader — your private deck', () => {
  test('signs in only after Moxfield says private, and still returns just the deck', async ({ page }) => {
    const seen: string[] = [];
    await moxApi(page, { signedIn: true, private: true, seen });
    const out = await page.evaluate(() => (window as unknown as { readMoxfieldDeck: (id: string) => Promise<unknown> }).readMoxfieldDeck('AbCd1234'));
    expect(out).toMatchObject({ ok: true, deck: { publicId: 'AbCd1234' } });
    expect(seen).toEqual(['GET /v3/decks/all/AbCd1234', 'POST /v1/account/token/refresh', 'GET /v3/decks/all/AbCd1234 (signed in)']);
    expect(JSON.stringify(out)).not.toContain(TOKEN);
  });
});

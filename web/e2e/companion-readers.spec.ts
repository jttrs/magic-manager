// Pinned behaviour of the browser companion's page readers (extension/src/readers/*),
// run in real Chromium against saved pages in tests/fixtures/companion/. The
// expected outputs (*.expected.json) are also fed to the server's models and
// parsers by tests/test_companion.py, so reader → app → engine stays one chain.
//
// A reader changed on purpose? Re-pin with:  UPDATE_GOLDEN=1 npm --prefix web run e2e -- companion-readers
// A site changed its page? Follow .claude/skills/scrape-doctor/SKILL.md.
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ROOT = resolve(import.meta.dirname, '../..');
const FIX = resolve(ROOT, 'tests/fixtures/companion');
const READERS = resolve(ROOT, 'extension/src/readers');
const reader = (name: string) => readFileSync(resolve(READERS, name), 'utf8');

function golden(name: string, actual: unknown) {
  const path = resolve(FIX, name);
  if (process.env.UPDATE_GOLDEN || !existsSync(path)) writeFileSync(path, JSON.stringify(actual, null, 2) + '\n');
  expect(actual).toEqual(JSON.parse(readFileSync(path, 'utf8')));
}

async function servePage(page: Page, url: string, html: string) {
  await page.route(url, (r) => r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html }));
  await page.route('https://images.manapool.com/**', (r) => r.fulfill({ status: 404, body: '' }));
  await page.goto(url);
}

const cartHtml = () => readFileSync(resolve(FIX, 'manapool-cart.html'), 'utf8');
const readCart = (page: Page) => page.evaluate(() => (window as unknown as { readManaPoolCart: (d: Document) => unknown }).readManaPoolCart(document));

test.describe('Mana Pool cart reader', () => {
  test('reads the saved cart page: exact printing, finish, condition, quantity, unit price', async ({ page }) => {
    await servePage(page, 'https://manapool.com/cart', cartHtml());
    await page.addScriptTag({ content: reader('manapool-cart.js') });
    const out = await readCart(page) as { ok: boolean; items: { name: string; finish: string; quantity: number; price: number }[] };
    expect(out.ok).toBe(true);
    // Pinned facts a human checked against the page (the golden carries the rest):
    expect(out.items.map((i) => [i.name, i.finish, i.quantity, i.price])).toEqual([
      ['Sire of Seven Deaths', 'nonfoil', 1, 17],
      ['Ajani, Nacatl Pariah // Ajani, Nacatl Avenger', 'nonfoil', 1, 13],
      ['Sire of Seven Deaths', 'foil', 2, 20.5],
    ]);
    golden('manapool-cart.expected.json', out);
  });

  test('a row it can’t fully read is kept and flagged, never dropped silently', async ({ page }) => {
    await servePage(page, 'https://manapool.com/cart', cartHtml());
    await page.evaluate(() => document.querySelector('section[aria-labelledby="cart-heading"] li img')?.setAttribute('src', '/x.jpg'));
    await page.addScriptTag({ content: reader('manapool-cart.js') });
    const out = await readCart(page) as { items: { scryfall_id: string | null }[]; warnings: { code: string; row: number; missing: string[] }[] };
    expect(out.items[0].scryfall_id).toBeNull();
    expect(out.warnings).toContainEqual({ code: 'cart.row_unreadable', row: 1, missing: ['printing'] });
  });

  for (const [what, html, code] of [
    ['an empty cart', '<main><h1>Cart</h1><p>Your cart is empty</p></main>', 'cart.empty'],
    ['a page that isn’t a cart', '<main><h1>Sign in</h1></main>', 'cart.page_changed'],
    ['a redesigned cart with no recognisable rows', '<main><h1>Cart</h1><section aria-labelledby="cart-heading"><div>Sol Ring $1.00</div></section></main>', 'cart.page_changed'],
  ] as const) {
    test(`says so for ${what} (${code})`, async ({ page }) => {
      await servePage(page, 'https://manapool.com/cart', `<!doctype html><html><body>${html}</body></html>`);
      await page.addScriptTag({ content: reader('manapool-cart.js') });
      expect(await readCart(page)).toMatchObject({ ok: false, code });
    });
  }

  test('the real empty cart page reads as empty (cart.empty), not as a changed page', async ({ page }) => {
    await servePage(page, 'https://manapool.com/cart', readFileSync(resolve(FIX, 'manapool-cart-empty.html'), 'utf8'));
    await page.addScriptTag({ content: reader('manapool-cart.js') });
    expect(await readCart(page)).toMatchObject({ ok: false, code: 'cart.empty', warnings: [{ code: 'cart.signed_out' }] });
  });

  test('being sent to the sign-in page is named (cart.sign_in)', async ({ page }) => {
    await servePage(page, 'https://manapool.com/auth?next=%2Fcart', '<!doctype html><title>Mana Pool</title><main><h1>Sign in</h1></main>');
    await page.addScriptTag({ content: reader('manapool-cart.js') });
    expect(await readCart(page)).toMatchObject({ ok: false, code: 'cart.sign_in' });
  });

  test('flags a guest (signed-out) cart', async ({ page }) => {
    await servePage(page, 'https://manapool.com/cart', cartHtml().replace('<main>', '<header><a href="/auth?next=%2Fcart">Sign In</a></header><main>'));
    await page.addScriptTag({ content: reader('manapool-cart.js') });
    expect(await readCart(page)).toMatchObject({ ok: true, warnings: [{ code: 'cart.signed_out' }] });
  });

  test('the bookmarklet (built from the same reader) copies only the cart lines', async ({ page, context }) => {
    const href = execFileSync('uv', ['run', 'python', 'scripts/build_extension.py', '--bookmarklet'], { cwd: ROOT, encoding: 'utf8' }).trim();
    expect(href.startsWith('javascript:')).toBe(true);
    await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: 'https://manapool.com' });
    await servePage(page, 'https://manapool.com/cart', cartHtml());
    const alerts: string[] = [];
    page.on('dialog', (d) => { alerts.push(d.message()); void d.accept(); });
    await page.evaluate((src) => { new Function(src)(); }, decodeURIComponent(href.slice('javascript:'.length)));
    await expect.poll(() => alerts.length).toBe(1);
    expect(alerts[0]).toContain('copied 3 cart lines');
    const copied = JSON.parse(await page.evaluate(() => navigator.clipboard.readText()));
    expect(Object.keys(copied).sort()).toEqual(['items', 'source', 'version', 'warnings']);
    expect(copied.source).toBe('manapool-cart-page');
    expect(copied.items).toEqual(JSON.parse(readFileSync(resolve(FIX, 'manapool-cart.expected.json'), 'utf8')).items);
  });
});

test.describe('open-tab store page reader', () => {
  test('keeps the title, price tags, product data and price/stock lines — nothing personal', async ({ page }) => {
    await servePage(page, 'https://www.bestbuy.com/site/foundations/6589123.p', readFileSync(resolve(FIX, 'store-rendered.html'), 'utf8'));
    await page.addScriptTag({ content: reader('store-page.js') });
    const out = await page.evaluate(() => (window as unknown as { readStorePage: (d: Document) => { title: string; head: string; ld: string[]; text: string } }).readStorePage(document));
    const all = JSON.stringify(out);
    for (const secret of ['Jared', 'Main St', 'Springfield', 'secret-csrf-value', 'Organization', 'Orders']) expect(all).not.toContain(secret);
    expect(out.ld).toHaveLength(1);
    expect(out.text.split('\n')[0]).toBe('$144.99');
    golden('store-rendered.expected.json', out);
  });

  test('reads the price tags of real store pages the server already parses', async ({ page }) => {
    const out: Record<string, unknown> = {};
    for (const vendor of ['coolstuff', 'starcity', 'cardkingdom', 'miniaturemarket']) {
      const html = gunzipSync(readFileSync(resolve(ROOT, `tests/fixtures/vendors/${vendor}.html.gz`))).toString('utf8');
      await page.route('https://store.example/p', (r) => r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html.replace(/<script(?![^>]*ld\+json)[\s\S]*?<\/script>/gi, '') }));
      await page.goto('https://store.example/p');
      await page.addScriptTag({ content: reader('store-page.js') });
      out[vendor] = await page.evaluate(() => (window as unknown as { readStorePage: (d: Document) => unknown }).readStorePage(document));
      await page.unroute('https://store.example/p');
    }
    golden('store-extracts.expected.json', out);
  });
});

test.describe('Moxfield deck reader', () => {
  const deckUrl = 'https://moxfield.com/decks/AbCd1234';
  async function readDeck(page: Page, api: { status: number; contentType: string; body: string }, id = 'AbCd1234') {
    await page.route('https://api2.moxfield.com/**', (r) => r.fulfill({ ...api, headers: { 'access-control-allow-origin': 'https://moxfield.com', 'access-control-allow-credentials': 'true' } }));
    await servePage(page, deckUrl, '<!doctype html><title>Moxfield</title>');
    await page.addScriptTag({ content: reader('moxfield-deck.js') });
    return page.evaluate((deckId) => (window as unknown as { readMoxfieldDeck: (id: string) => Promise<unknown> }).readMoxfieldDeck(deckId), id);
  }

  test('keeps only the deck’s name, author and each card’s printing, quantity, finish and board', async ({ page }) => {
    const body = readFileSync(resolve(FIX, 'moxfield-deck.json'), 'utf8');
    const out = await readDeck(page, { status: 200, contentType: 'application/json', body }) as { ok: boolean };
    expect(out.ok).toBe(true);
    const all = JSON.stringify(out);
    for (const dropped of ['profileImageUrl', 'likeCount', 'prices', 'internal-123', 'Goblin Fan']) expect(all).not.toContain(dropped);
    golden('moxfield-deck.expected.json', out);
  });

  for (const [what, api, code] of [
    ['a private deck', { status: 403, contentType: 'application/json', body: '{"title":"Forbidden"}' }, 'moxfield.private'],
    ['the bot check', { status: 403, contentType: 'text/html', body: '<title>Just a moment...</title>' }, 'moxfield.blocked'],
    ['a deleted deck', { status: 404, contentType: 'application/json', body: '{}' }, 'moxfield.not_found'],
    ['a server error', { status: 500, contentType: 'application/json', body: '{}' }, 'moxfield.http'],
    ['a changed format', { status: 200, contentType: 'application/json', body: '{"mainboard":[]}' }, 'moxfield.changed'],
  ] as const) {
    test(`names ${what} (${code})`, async ({ page }) => {
      expect(await readDeck(page, api)).toMatchObject({ ok: false, code });
    });
  }

  test('refuses an id that isn’t a deck id', async ({ page }) => {
    expect(await readDeck(page, { status: 200, contentType: 'application/json', body: '{}' }, '../users/me')).toMatchObject({ ok: false, code: 'moxfield.bad_url' });
  });
});

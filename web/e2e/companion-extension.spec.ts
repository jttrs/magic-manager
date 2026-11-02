// The REAL extension, loaded unpacked into Chromium, against the app (API mocked)
// and a saved Mana Pool cart page. Proves the security model end to end:
// only the paired app can ask, nothing reaches the app until Send is pressed in
// the extension's own window, and other pages (another site, another port) get
// no answer at all.
//
// Harness-only change: the test copy of the manifest grants http://localhost/*
// (and www.tcgplayer.com + moxfield.com, the TCGplayer cart and Moxfield switches) up front, because Chrome's
// permission prompts (what users see when pairing / switching a feature on)
// can't be clicked by automation. Everything else is the shipped extension.
import { randomBytes } from 'node:crypto';
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { chromium, expect, test as base, type BrowserContext, type Page, type Worker } from '@playwright/test';
import { mockApi } from './support';

const ROOT = resolve(import.meta.dirname, '../..');
const PORT = Number(process.env.MM_E2E_PORT ?? 5174);
const APP = `http://localhost:${PORT}`;
const CART_HTML = readFileSync(resolve(ROOT, 'tests/fixtures/companion/manapool-cart.html'), 'utf8');
const EXPECTED = JSON.parse(readFileSync(resolve(ROOT, 'tests/fixtures/companion/manapool-cart.expected.json'), 'utf8'));
const TCG_HTML = readFileSync(resolve(ROOT, 'tests/fixtures/companion/tcgplayer-cart.html'), 'utf8');
const TCG_EXPECTED = JSON.parse(readFileSync(resolve(ROOT, 'tests/fixtures/companion/tcgplayer-cart.expected.json'), 'utf8'));

type Fixtures = { ext: { context: BrowserContext; worker: Worker; id: string } };

/** A copy of the shipped extension with the harness grants (see the header). */
function extensionCopy(extra: string[] = []): string {
  const dir = mkdtempSync(join(tmpdir(), 'mm-companion-'));
  cpSync(resolve(ROOT, 'extension'), dir, { recursive: true });
  const manifest = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8'));
  manifest.host_permissions.push('http://localhost/*', 'https://www.tcgplayer.com/*', 'https://moxfield.com/*', 'https://*.moxfield.com/*', ...extra);
  writeFileSync(join(dir, 'manifest.json'), JSON.stringify(manifest));
  return dir;
}

/** Chromium with the unpacked extension. Launching again with the same profile reinstalls it from
 *  disk, like pressing ↻ in chrome://extensions: storage stays, dynamically registered scripts go. */
async function launch(dir: string, profile = '') {
  const context = await chromium.launchPersistentContext(profile, {
    channel: 'chromium',
    headless: true,
    args: [`--disable-extensions-except=${dir}`, `--load-extension=${dir}`],
  });
  const worker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
  return { context, worker, id: new URL(worker.url()).host };
}

const test = base.extend<Fixtures>({
  // eslint-disable-next-line no-empty-pattern
  ext: async ({}, use) => {
    const dir = extensionCopy();
    const { context, worker, id } = await launch(dir);
    // What pressing Pair does after Chrome's prompt (see src/options.js).
    await worker.evaluate(async (origin) => {
      await chrome.storage.local.set({ appOrigin: origin });
      await chrome.scripting.registerContentScripts([{ id: 'mm-bridge', matches: ['http://localhost/*'], js: ['src/bridge.js'], runAt: 'document_start', allFrames: false }]);
    }, APP);
    await use({ context, worker, id });
    await context.close();
    rmSync(dir, { recursive: true, force: true });
  },
});

async function appPage(context: BrowserContext): Promise<{ page: Page; bodies: unknown[] }> {
  const page = await context.newPage();
  const bodies: unknown[] = [];
  await mockApi(page, {
    '/api/features': () => ({ json: { flags: { cart_check: true, companion: true } } }),
    '/api/cart/setup': () => ({ json: { account: false } }),
  });
  await page.route('**/api/cart/lines', (r) => {
    bodies.push(r.request().postDataJSON());
    return r.fulfill({ json: { lines: 3, copies: 4, total: 71, unidentified: [], family: null, families: [], dupes: [], owned: [], missing: [], overpay: [], no_market: [] } });
  });
  await page.goto(`${APP}/collection?families=%5B%22blb%22%5D`);
  return { page, bodies };
}

/** Your Mana Pool cart, open in a tab (Playwright can't intercept tabs the
 *  extension opens itself, so the test always has the cart open already). */
async function openCartTab(context: BrowserContext) {
  const tab = await context.newPage();
  await tab.route('https://manapool.com/cart*', (r) => r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: CART_HTML }));
  await tab.route('https://images.manapool.com/**', (r) => r.fulfill({ status: 404, body: '' }));
  await tab.goto('https://manapool.com/cart');
  return tab;
}

async function startCartRead(context: BrowserContext, page: Page) {
  await openCartTab(context);
  await page.bringToFront();
  await page.getByRole('button', { name: 'Check my cart' }).click();
  const dialog = page.getByRole('dialog', { name: 'Check my cart' });
  const approval = context.waitForEvent('page', (p) => p.url().includes('/src/approve.html'));
  await dialog.getByRole('button', { name: 'Read my cart' }).click();
  return { dialog, approve: await approval };
}

test('read the cart, review exactly what will be sent, approve — only then the app gets the lines', async ({ ext }) => {
  const { page, bodies } = await appPage(ext.context);
  await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();
  const { dialog, approve } = await startCartRead(ext.context, page);
  await expect(dialog.getByText('Waiting for you to approve in the companion window')).toBeVisible();
  await expect(approve.locator('#origin')).toHaveText(APP);
  await expect(approve.locator('#summary')).toHaveText('Mana Pool cart · 3 lines · 4 items · $71.00');
  await expect(approve.locator('#table')).toContainText('Ajani, Nacatl Pariah // Ajani, Nacatl Avenger');
  expect(bodies).toEqual([]);                                     // nothing sent yet
  const send = approve.getByRole('button', { name: 'Send to magic-manager' });
  expect(await approve.evaluate(() => document.activeElement?.id)).toBe('deny');   // the safe choice has focus
  await expect(send).toBeEnabled();
  await send.click();
  await expect(dialog).toContainText('Mana Pool cart · read in this browser by the companion.');
  expect(bodies).toEqual([{ items: EXPECTED.items, source: 'extension', store: 'manapool', family: 'blb' }]);
  const tabs = await ext.worker.evaluate(() => chrome.tabs.query({ url: 'https://manapool.com/*' }));
  expect(tabs).toHaveLength(1);                                   // your own cart tab is left alone
});

test('a TCGplayer cart: the real extension reads your cart tab, you approve, the app gets only its lines', async ({ ext }) => {
  const { page, bodies } = await appPage(ext.context);
  const tab = await ext.context.newPage();
  await tab.route('https://www.tcgplayer.com/**', (r) => (r.request().url() === 'https://www.tcgplayer.com/cart'
    ? r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: TCG_HTML })
    : r.fulfill({ status: 404, body: '' })));
  await tab.goto('https://www.tcgplayer.com/cart', { waitUntil: 'domcontentloaded' });
  await page.bringToFront();
  await page.getByRole('button', { name: 'Check my cart' }).click();
  const dialog = page.getByRole('dialog', { name: 'Check my cart' });
  await dialog.getByRole('radio', { name: 'TCGplayer' }).click();
  const approval = ext.context.waitForEvent('page', (p) => p.url().includes('/src/approve.html'));
  await dialog.getByRole('button', { name: 'Read my cart' }).click();
  const approve = await approval;
  await expect(approve.locator('#title')).toHaveText('Send your TCGplayer cart?');
  await expect(approve.locator('#summary')).toHaveText('TCGplayer cart · 8 lines · 9 items · $128.54');
  await expect(approve.locator('#table')).toContainText('Tales of Middle-earth #246');
  await expect(approve.locator('#table')).not.toContainText('487805');   // store ids only in the raw data
  await expect(approve.locator('#table')).toContainText('LP');
  expect(bodies).toEqual([]);
  await approve.getByRole('button', { name: 'Send to magic-manager' }).click();
  await expect(dialog).toContainText('TCGplayer cart · read in this browser by the companion.');
  expect(bodies).toEqual([{ items: TCG_EXPECTED.items, source: 'extension', store: 'tcgplayer', family: 'blb' }]);
  expect(JSON.stringify(bodies)).not.toContain('Addicted2packz');   // never the sellers
});

test('a Moxfield collection: the real extension reads every page in your Moxfield tab, you approve, the app previews only the lines', async ({ ext }) => {
  const COLL = JSON.parse(readFileSync(resolve(ROOT, 'tests/fixtures/companion/moxfield-collection.json'), 'utf8'));
  const GOLD = JSON.parse(readFileSync(resolve(ROOT, 'tests/fixtures/companion/moxfield-collection.expected.json'), 'utf8')).collection;
  const cors = { 'access-control-allow-origin': 'https://moxfield.com', 'access-control-allow-credentials': 'true' };
  await ext.context.route('https://api2.moxfield.com/**', (r) => {
    const u = new URL(r.request().url());
    if (!u.pathname.startsWith('/v1/collections/search/')) return r.fulfill({ status: 404, headers: cors, contentType: 'application/json', body: '{}' });
    return r.fulfill({ status: 200, headers: cors, contentType: 'application/json', body: JSON.stringify(u.searchParams.get('pageNumber') === '2' ? COLL.page2 : COLL.page1) });
  });
  const tab = await ext.context.newPage();
  await tab.route('https://moxfield.com/', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>Moxfield</title>' }));
  await tab.goto('https://moxfield.com/');
  const { page } = await appPage(ext.context);
  const previews: unknown[] = [];
  await page.route('**/api/collection/import/preview', (r) => {
    previews.push(r.request().postDataJSON());
    return r.fulfill({ json: { label: 'web:moxfield shared collection', rows: [], not_found: [], skipped: { proxy: 1, digital: 1 }, not_in_read: 0, already_imported_at: null, warnings: [] } });
  });
  await page.getByRole('button', { name: 'Add cards' }).click();
  const d = page.getByRole('dialog', { name: 'Add cards' });
  await d.getByRole('tab', { name: 'Import a collection' }).click();
  await d.getByRole('textbox', { name: /collection or binder link/ }).fill('https://moxfield.com/collection/hgsItGBwRUybHyN0WZR41w');
  const approval = ext.context.waitForEvent('page', (p) => p.url().includes('/src/approve.html'));
  await d.getByRole('button', { name: 'Read link' }).click();
  const approve = await approval;
  await expect(approve.locator('#title')).toHaveText('Send your Moxfield cards?');
  const copies = GOLD.lines.reduce((t: number, l: { quantity: number }) => t + l.quantity, 0);
  await expect(approve.locator('#summary')).toHaveText(`Moxfield collection (shared link) · 20 printings · ${copies} cards`);
  await expect(approve.locator('#table')).toContainText('proxy, skipped');
  expect(previews).toEqual([]);
  await approve.getByRole('button', { name: 'Send to magic-manager' }).click();
  await expect(d.getByRole('heading', { name: 'Moxfield collection (shared link)' })).toBeVisible();
  expect(previews).toEqual([{ source: 'moxfield', scope: 'collection', id: 'hgsItGBwRUybHyN0WZR41w', name: null, lines: GOLD.lines }]);
  expect(await ext.worker.evaluate(() => chrome.tabs.query({ url: 'https://moxfield.com/*' }))).toHaveLength(1);   // your tab, nothing extra left open
});

/** Moxfield answering for a signed-in user with a collection of `n` distinct printings (5,000 a page),
 *  and your Moxfield tab open. `name(i)` makes each card's name. */
async function bigMoxfieldCollection(ext: Fixtures['ext'], n: number, name: (i: number) => string) {
  const COLL = JSON.parse(readFileSync(resolve(ROOT, 'tests/fixtures/companion/moxfield-collection.json'), 'utf8'));
  const tmpl = COLL.page1.data[0];
  const cors = { 'access-control-allow-origin': 'https://moxfield.com', 'access-control-allow-credentials': 'true' };
  const asked: string[] = [];
  await ext.context.route('https://api2.moxfield.com/**', (r) => {
    const u = new URL(r.request().url());
    asked.push(u.pathname);
    if (u.pathname === '/v1/account/token/refresh') return r.fulfill({ status: 200, headers: cors, contentType: 'application/json', body: '{"access_token":"short-lived"}' });
    if (u.pathname !== '/v1/collections/search') return r.fulfill({ status: 404, headers: cors, contentType: 'application/json', body: '{}' });
    const p = Number(u.searchParams.get('pageNumber'));
    const data = [];
    for (let i = (p - 1) * 5000; i < Math.min(n, p * 5000); i++) {
      data.push({ ...tmpl, id: `e${i}`, quantity: 1 + (i % 3), card: { ...tmpl.card, scryfall_id: `${i.toString(16).padStart(8, '0')}-4a1b-4c2d-8e3f-0123456789ab`, cn: String(i % 400), name: name(i) } });
    }
    return r.fulfill({ status: 200, headers: cors, contentType: 'application/json', body: JSON.stringify({ ...COLL.page1, pageNumber: p, totalResults: n, totalPages: Math.ceil(n / 5000), data }) });
  });
  const tab = await ext.context.newPage();
  await tab.route('https://moxfield.com/', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>Moxfield</title>' }));
  await tab.goto('https://moxfield.com/');
  return asked;
}

async function openImport(page: Page) {
  await page.getByRole('button', { name: 'Add cards' }).click();
  const d = page.getByRole('dialog', { name: 'Add cards' });
  await d.getByRole('tab', { name: 'Import a collection' }).click();
  return d;
}

test('Read my collection: a real-sized collection (40,000 printings) is read, listed in full for approval, and previewed', async ({ ext }) => {
  test.setTimeout(180_000);
  const N = 40_000;
  const asked = await bigMoxfieldCollection(ext, N, (i) => `Collected Card Number ${i}`);
  const { page } = await appPage(ext.context);
  const previews: { scope: string; id: unknown; lines: unknown[] }[] = [];
  await page.route('**/api/collection/import/preview', (r) => {
    previews.push(r.request().postDataJSON());
    return r.fulfill({ json: { label: 'web:moxfield collection', rows: [], not_found: [], skipped: { proxy: 0, digital: 0 }, not_in_read: 0, already_imported_at: null, warnings: [] } });
  });
  const d = await openImport(page);
  const approval = ext.context.waitForEvent('page', { predicate: (p) => p.url().includes('/src/approve.html'), timeout: 120_000 });
  await d.getByRole('button', { name: 'Read my collection' }).click();
  const approve = await approval;
  await expect(approve.locator('#summary')).toHaveText(`Your Moxfield collection · ${N} printings · 79999 cards`);
  // Every line is listed (rows are added in batches), not cut off.
  await expect(approve.locator('#table tbody tr')).toHaveCount(N, { timeout: 60_000 });
  await expect(approve.locator('#table')).toContainText(`Collected Card Number ${N - 1}`);
  expect(previews).toEqual([]);
  await approve.getByRole('button', { name: 'Send to magic-manager' }).click();
  await expect(d.getByRole('heading', { name: 'Your Moxfield collection' })).toBeVisible({ timeout: 60_000 });
  expect(previews).toHaveLength(1);
  expect(previews[0]).toMatchObject({ scope: 'collection', id: null });
  expect(previews[0].lines).toHaveLength(N);
  expect(previews[0].lines[N - 1]).toMatchObject({ quantity: 1 + ((N - 1) % 3), scryfall_id: `${(N - 1).toString(16).padStart(8, '0')}-4a1b-4c2d-8e3f-0123456789ab`, cn: String((N - 1) % 400), name: `Collected Card Number ${N - 1}` });
  expect(asked.filter((p) => p === '/v1/collections/search')).toHaveLength(N / 5000);
});

test('a read too big to hand over says so (request.too_large, with its size) — never “a request it doesn’t understand”', async ({ ext }) => {
  test.setTimeout(180_000);
  // Names that don't compress: 60,000 of them are more than the companion can hold while you decide.
  await bigMoxfieldCollection(ext, 60_000, () => randomBytes(150).toString('base64').slice(0, 190));
  const { page } = await appPage(ext.context);
  const d = await openImport(page);
  await d.getByRole('button', { name: 'Read my collection' }).click();
  const alert = d.getByRole('alert');
  await expect(alert).toContainText('That read is too big for the companion to hand over in one go.', { timeout: 120_000 });
  await expect(alert).toContainText(/MB of card data · Code request\.too_large/);
  expect(await ext.worker.evaluate(async () => (await chrome.storage.session.get('pending')).pending ?? null)).toBeNull();
  expect(ext.context.pages().filter((p) => p.url().includes('/src/approve.html'))).toHaveLength(0);
});

test('the bridge passes which collection read to the worker: one of your binders, by id', async ({ ext }) => {
  const asked = await bigMoxfieldCollection(ext, 10, (i) => `Card ${i}`);
  const { page } = await appPage(ext.context);
  await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();
  const ack = await page.evaluate(() => new Promise((resolve) => {
    window.addEventListener('message', (ev) => { if (ev.data?.from === 'companion' && ev.data.id === 'binder-read-01' && ev.data.type === 'ack') resolve(ev.data); });
    window.postMessage({ channel: 'magic-manager/companion', from: 'app', type: 'request', id: 'binder-read-01', kind: 'moxfield_collection', params: { what: 'binder', binder: 'Bnd3r_id' } }, location.origin);
  }));
  expect(asked).toContain('/v1/trade-binders/Bnd3r_id/search');   // not refused as request.invalid before reading
  expect(ack).toMatchObject({ ok: false, code: 'moxfield.not_found' });   // this stub has no binders
});

test('a request while a long read is still reading (no window yet) is refused as busy, and the read still completes', async ({ ext }) => {
  const COLL = JSON.parse(readFileSync(resolve(ROOT, 'tests/fixtures/companion/moxfield-collection.json'), 'utf8'));
  const cors = { 'access-control-allow-origin': 'https://moxfield.com', 'access-control-allow-credentials': 'true' };
  let release: () => void = () => {};
  const gate = new Promise<void>((r) => { release = r; });
  await ext.context.route('https://api2.moxfield.com/**', async (r) => {
    await gate;
    const u = new URL(r.request().url());
    return r.fulfill({ status: 200, headers: cors, contentType: 'application/json', body: JSON.stringify(u.searchParams.get('pageNumber') === '2' ? COLL.page2 : COLL.page1) });
  });
  const tab = await ext.context.newPage();
  await tab.route('https://moxfield.com/', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>Moxfield</title>' }));
  await tab.goto('https://moxfield.com/');
  const { page } = await appPage(ext.context);
  await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();
  const ask = (id: string, kind: string, params: object) => page.evaluate(([id, kind, params]) => new Promise((resolve) => {
    window.addEventListener('message', (ev) => { if (ev.data?.from === 'companion' && ev.data.id === id && ev.data.type === 'ack') resolve(ev.data); });
    window.postMessage({ channel: 'magic-manager/companion', from: 'app', type: 'request', id, kind, params }, location.origin);
  }), [id, kind, params] as const);
  const first = ask('long-read-0001', 'moxfield_collection', { url: 'https://moxfield.com/collection/hgsItGBwRUybHyN0WZR41w' });
  await expect.poll(() => ext.worker.evaluate(async () => (await chrome.storage.session.get('pending')).pending?.stage)).toBe('reading');
  expect(await ask('second-request-2', 'cart', {})).toMatchObject({ ok: false, code: 'request.busy' });
  const approval = ext.context.waitForEvent('page', (p) => p.url().includes('/src/approve.html'));
  release();
  expect(await first).toMatchObject({ ok: true, status: 'awaiting_approval' });
  await (await approval).getByRole('button', { name: 'Don’t send' }).click();
});

test('Don’t send: the app is told, and gets nothing', async ({ ext }) => {
  const { page, bodies } = await appPage(ext.context);
  const { dialog, approve } = await startCartRead(ext.context, page);
  await approve.getByRole('button', { name: 'Don’t send' }).click();
  await expect(dialog.getByRole('status').filter({ hasText: 'You chose not to send it' })).toContainText('Nothing was sent.');
  expect(bodies).toEqual([]);
});

test('closing the approval window counts as no', async ({ ext }) => {
  const { page, bodies } = await appPage(ext.context);
  const { dialog, approve } = await startCartRead(ext.context, page);
  await approve.close();
  await expect(dialog.getByRole('alert')).toContainText('Nothing was sent');
  expect(bodies).toEqual([]);
});

test('a second request while one waits is refused as busy', async ({ ext }) => {
  const { page } = await appPage(ext.context);
  await startCartRead(ext.context, page);
  const second = await page.evaluate(() => new Promise((resolve) => {
    window.addEventListener('message', (ev) => { if (ev.data?.from === 'companion' && ev.data.id === 'second-request-1') resolve(ev.data); });
    window.postMessage({ channel: 'magic-manager/companion', from: 'app', type: 'request', id: 'second-request-1', kind: 'cart', params: {} }, location.origin);
  }));
  expect(second).toMatchObject({ type: 'ack', ok: false, code: 'request.busy' });
});

test('two requests sent back to back: the second is busy, and Send in the one window delivers the FIRST request’s data', async ({ ext }) => {
  const { page } = await appPage(ext.context);
  await openCartTab(ext.context);
  await page.bringToFront();
  await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();
  const approval = ext.context.waitForEvent('page', (p) => p.url().includes('/src/approve.html'));
  // Both posted in the same tick, so the second reaches the worker while the first is still reading.
  const acks = await page.evaluate(() => new Promise<{ id: string; ok: boolean; code?: string; status?: string }[]>((resolve) => {
    const got: { id: string; ok: boolean; code?: string; status?: string }[] = [];
    window.addEventListener('message', (ev) => {
      if (ev.data?.from !== 'companion' || ev.data.type !== 'ack') return;
      got.push({ id: ev.data.id, ok: ev.data.ok, code: ev.data.code, status: ev.data.status });
      if (got.length === 2) resolve(got);
    });
    for (const id of ['back-to-back-A1', 'back-to-back-B2']) {
      window.postMessage({ channel: 'magic-manager/companion', from: 'app', type: 'request', id, kind: 'cart', params: {} }, location.origin);
    }
  }));
  expect(acks.find((a) => a.id === 'back-to-back-A1')).toMatchObject({ ok: true, status: 'awaiting_approval' });
  expect(acks.find((a) => a.id === 'back-to-back-B2')).toMatchObject({ ok: false, code: 'request.busy' });
  const approve = await approval;
  expect(new URL(approve.url()).searchParams.get('id')).toBe('back-to-back-A1');   // the window is bound to its own request
  const result = page.evaluate(() => new Promise<{ id: string; ok: boolean; data: { items: unknown[] } }>((resolve) => {
    window.addEventListener('message', (ev) => { if (ev.data?.from === 'companion' && ev.data.type === 'result') resolve(ev.data); });
  }));
  await expect(approve.getByRole('button', { name: 'Send to magic-manager' })).toBeEnabled();
  await approve.getByRole('button', { name: 'Send to magic-manager' }).click();
  const delivered = await result;
  expect(delivered).toMatchObject({ id: 'back-to-back-A1', ok: true });
  expect(delivered.data.items).toEqual(EXPECTED.items);
});

const forgedRequest = (page: Page) => page.evaluate(() => new Promise((resolve) => {
  window.addEventListener('message', (ev) => { if (ev.data?.from === 'companion') resolve(ev.data); });
  window.postMessage({ channel: 'magic-manager/companion', from: 'app', type: 'ping' }, '*');
  window.postMessage({ channel: 'magic-manager/companion', from: 'app', type: 'request', id: 'forged-request-1', kind: 'cart', params: {} }, '*');
  setTimeout(() => resolve('no answer'), 2500);
}));

test('another website gets no answer and opens nothing', async ({ ext }) => {
  const evil = await ext.context.newPage();
  await evil.route('https://evil.example/', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<title>evil</title>' }));
  await evil.goto('https://evil.example/');
  const opened: string[] = [];
  ext.context.on('page', (p) => opened.push(p.url()));
  expect(await forgedRequest(evil)).toBe('no answer');
  expect(opened).toEqual([]);
});

test('another app on this computer (a different port) gets no answer either', async ({ ext }) => {
  const other = await ext.context.newPage();
  await other.route('http://localhost:5999/', (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<title>other</title>' }));
  await other.goto('http://localhost:5999/');
  expect(await forgedRequest(other)).toBe('no answer');
});

test('the settings page says whether the paired app has checked in', async ({ ext }) => {
  const opts = await ext.context.newPage();
  await opts.goto(`chrome-extension://${ext.id}/src/options.html`);
  await expect(opts.locator('#pair-status')).toContainText('hasn’t checked in yet');
  await expect(opts.locator('#pair-status')).toHaveClass('warn');
  const { page } = await appPage(ext.context);
  await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();
  await expect(opts.locator('#pair-status')).toContainText(`Paired with ${APP}. The app last checked in just now.`);   // live, no reload
  await expect(opts.getByRole('textbox', { name: 'App address' })).toHaveValue(APP);
});

test('one Allow access switch covers every optional site; Mana Pool stays always on', async ({ ext }) => {
  const opts = await ext.context.newPage();
  await opts.goto(`chrome-extension://${ext.id}/src/options.html`);
  const access = opts.getByRole('switch', { name: 'Allow access' });
  expect(await opts.getByRole('switch').count()).toBe(1);
  await expect(opts.locator('#cart-state')).toHaveText('Always on');
  // The harness grants www.tcgplayer.com and moxfield.com only: partly allowed reads Off, with a note.
  await expect(access).toHaveAttribute('aria-checked', 'false');
  await expect(access).toContainText('Off');
  await expect(opts.locator('#access-partial')).toBeVisible();
  await opts.getByText('What it covers').click();
  for (const name of ['TCGplayer cart', 'Card Kingdom cart', 'Deals', 'Moxfield', 'Archidekt', 'Order history']) {
    await expect(opts.locator('ul.covers')).toContainText(name);
  }
  // Chrome's prompt can't be clicked by automation: record what the click asks for, and grant it.
  const optional = await ext.worker.evaluate(() => chrome.runtime.getManifest().optional_host_permissions ?? []);
  await opts.evaluate(() => {
    // A fake Chrome permission store: request() grants, remove() revokes, contains() reads it.
    const w = window as unknown as { asked: unknown[] };
    w.asked = [];
    const granted = new Set<string>();
    Object.defineProperty(chrome, 'permissions', { configurable: true, value: {
      contains: (p: chrome.permissions.Permissions) => Promise.resolve((p.origins ?? []).every((o) => granted.has(o))),
      request: (p: chrome.permissions.Permissions) => { w.asked.push(p); (p.origins ?? []).forEach((o) => granted.add(o)); return Promise.resolve(true); },
      remove: (p: chrome.permissions.Permissions) => { w.asked.push({ removed: p }); (p.origins ?? []).forEach((o) => granted.delete(o)); return Promise.resolve(true); },
    } });
  });
  await access.click();
  await expect(access).toHaveAttribute('aria-checked', 'true');
  await expect(access).toContainText('On');
  await expect(opts.locator('#access-partial')).toBeHidden();
  const asked = await opts.evaluate(() => (window as unknown as { asked: { origins: string[] }[] }).asked);
  expect(asked).toHaveLength(1);
  const origins = asked[0].origins;
  // Every optional site except the app addresses (those are pairing), and nothing else.
  expect(new Set(origins)).toEqual(new Set(optional.filter((o: string) => !/^http:\/\/(localhost|127\.0\.0\.1)\/|^https:\/\/\*\/\*$/.test(o))));
  expect(origins).not.toContain('https://*/*');
  await access.click();
  await expect(access).toHaveAttribute('aria-checked', 'false');
  await expect(access).toContainText('Off');
  await expect(opts.locator('#access-partial')).toBeHidden();
  const removed = await opts.evaluate(() => (window as unknown as { asked: { removed?: { origins: string[] } }[] }).asked[1]?.removed?.origins);
  expect(removed).toEqual(origins);
});

test('pair, then the extension is reloaded: the app still connects (the worker re-registers its bridge)', async () => {
  const dir = extensionCopy();
  const profile = mkdtempSync(join(tmpdir(), 'mm-profile-'));
  try {
    let ext = await launch(dir, profile);
    await ext.worker.evaluate((origin) => chrome.storage.local.set({ appOrigin: origin }), APP);
    const opts = await ext.context.newPage();
    await opts.goto(`chrome-extension://${ext.id}/src/options.html`);
    expect(await opts.evaluate(() => chrome.runtime.sendMessage({ type: 'bridge' }))).toEqual({ ok: true });   // what Pair does
    let { page } = await appPage(ext.context);
    await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();
    await ext.context.close();

    ext = await launch(dir, profile);   // ↻: Chrome drops dynamically registered scripts
    const w = ext.worker;
    await expect.poll(() => w.evaluate(() => chrome.scripting.getRegisteredContentScripts())).toMatchObject([{ id: 'mm-bridge', matches: ['http://localhost/*'] }]);
    ({ page } = await appPage(ext.context));
    await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();
    await ext.context.close();
  } finally {
    rmSync(dir, { recursive: true, force: true });
    rmSync(profile, { recursive: true, force: true });
  }
});

test('an app tab already open when you pair connects without a reload, and answers once', async ({ ext }) => {
  await ext.worker.evaluate(() => chrome.scripting.unregisterContentScripts({ ids: ['mm-bridge'] }));
  const { page } = await appPage(ext.context);
  await page.getByRole('button', { name: 'Browser companion · set up' }).waitFor();
  const opts = await ext.context.newPage();
  await opts.goto(`chrome-extension://${ext.id}/src/options.html`);
  for (let i = 0; i < 2; i++) expect(await opts.evaluate(() => chrome.runtime.sendMessage({ type: 'bridge' }))).toEqual({ ok: true });
  await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();
  // A ping and a (refused) request: exactly one hello and one ack, not one per injected copy.
  const counts = await page.evaluate(() => new Promise<{ hello: number; ack: number }>((resolve) => {
    const n = { hello: 0, ack: 0 };
    window.addEventListener('message', (ev) => {
      if (ev.data?.from !== 'companion') return;
      if (ev.data.type === 'hello') n.hello += 1;
      if (ev.data.type === 'ack' && ev.data.id === 'x') n.ack += 1;
    });
    window.postMessage({ channel: 'magic-manager/companion', from: 'app', type: 'ping' }, location.origin);
    window.postMessage({ channel: 'magic-manager/companion', from: 'app', type: 'request', id: 'x', kind: 'cart', params: {} }, location.origin);
    setTimeout(() => resolve(n), 1500);
  }));
  const hellos = counts.hello;
  expect(counts.ack).toBe(1);   // the bad id is refused (request.invalid), once
  expect(hellos).toBe(1);   // injected twice, one live bridge
});

test('paired with the wrong address: the app never checks in, and the settings page says so', async ({ ext }) => {
  await ext.worker.evaluate(() => chrome.storage.local.set({ appOrigin: 'http://localhost:5999' }));
  const { page } = await appPage(ext.context);
  await page.getByRole('button', { name: 'Browser companion · set up' }).click();
  await expect(page.getByRole('dialog').getByRole('status')).toContainText('Not connected');
  await expect(page.getByRole('dialog').getByRole('status')).toContainText(APP);
  const opts = await ext.context.newPage();
  await opts.goto(`chrome-extension://${ext.id}/src/options.html`);
  await expect(opts.locator('#pair-status')).toContainText('Paired with http://localhost:5999, but the app hasn’t checked in yet');
});

test('the settings page refuses addresses it may not pair with', async ({ ext }) => {
  const opts = await ext.context.newPage();
  await opts.goto(`chrome-extension://${ext.id}/src/options.html`);
  for (const [addr, code] of [
    ['http://example.com', 'pair.insecure_http'],
    ['http://192.168.1.10:8765', 'pair.insecure_http'],
    ['https://192.168.1.10', 'pair.host'],
    ['https://[::1]:8443', 'pair.host'],
    ['https://cards', 'pair.host'],
    ['https://*.example.com', 'pair.host'],
    ['https://*.com', 'pair.host'],
    ['https://moxfield.com', 'pair.reader_site'],
    ['https://www.cardkingdom.com', 'pair.reader_site'],
    ['ftp://cards.example.com', 'pair.bad_address'],
    ['not an address', 'pair.bad_address'],
    ['http://localhost:8765/app', 'pair.has_path'],
    ['https://cards.example.com/?x=1', 'pair.has_path'],
    ['https://u:p@cards.example.com', 'pair.credentials'],
  ] as const) {
    await opts.getByRole('textbox', { name: 'App address' }).fill(addr);
    await opts.getByRole('button', { name: 'Pair', exact: true }).click();
    await expect(opts.locator('#pair-status')).toHaveAttribute('data-code', code);
    await expect(opts.locator('#pair-status')).toHaveClass('error');
    if (addr === 'http://example.com') await expect(opts.locator('#pair-status')).toContainText('Plain http is only allowed for this computer');
  }
  expect(await ext.worker.evaluate(() => chrome.storage.local.get('appOrigin'))).toEqual({ appOrigin: APP });   // still the old pairing
});

test('pairs with any https app address: Chrome is asked for that one origin, and re-pairing revokes it', async () => {
  const A = 'https://mm-app.example', B = 'https://mm-other.example:8443';
  // Harness grant (the prompt can't be clicked): both test origins, as Chrome would after the prompt.
  const dir = extensionCopy(['https://mm-app.example/*', 'https://mm-other.example/*']);
  const ext = await launch(dir);
  try {
    const opts = await ext.context.newPage();
    await opts.goto(`chrome-extension://${ext.id}/src/options.html`);
    await opts.evaluate(() => {
      // Record what Pair asks Chrome for (contains() stays Chrome's own).
      const w = window as unknown as { asked: unknown[] };
      w.asked = [];
      const real = chrome.permissions;
      Object.defineProperty(chrome, 'permissions', { configurable: true, value: {
        contains: (p: chrome.permissions.Permissions) => real.contains(p),
        request: (p: chrome.permissions.Permissions) => { w.asked.push({ request: p.origins }); return Promise.resolve(true); },
        remove: (p: chrome.permissions.Permissions) => { w.asked.push({ remove: p.origins }); return Promise.resolve(true); },
      } });
    });
    const asked = () => opts.evaluate(() => (window as unknown as { asked: unknown[] }).asked);
    const field = opts.getByRole('textbox', { name: 'App address' });
    await field.fill(`${A}/`);
    await opts.getByRole('button', { name: 'Pair', exact: true }).click();
    await expect(opts.locator('#pair-status')).toContainText(`Paired with ${A}`);
    expect(await asked()).toEqual([{ request: ['https://mm-app.example/*'] }]);   // exactly this origin, never https://*/*
    expect(await ext.worker.evaluate(() => chrome.scripting.getRegisteredContentScripts())).toMatchObject([{ id: 'mm-bridge', matches: ['https://mm-app.example/*'] }]);
    expect(await ext.worker.evaluate(() => chrome.permissions.getAll())).not.toMatchObject({ origins: expect.arrayContaining(['https://*/*']) });

    // The app served at the https address connects.
    const app = await hostedApp(ext.context, A);
    await expect(app.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();

    await field.fill(B);
    await opts.getByRole('button', { name: 'Pair', exact: true }).click();
    await expect(opts.locator('#pair-status')).toContainText(`Paired with ${B}`);
    expect(await asked()).toEqual([{ request: ['https://mm-app.example/*'] }, { request: ['https://mm-other.example/*'] }, { remove: ['https://mm-app.example/*'] }]);
    expect(await ext.worker.evaluate(() => chrome.scripting.getRegisteredContentScripts())).toMatchObject([{ id: 'mm-bridge', matches: ['https://mm-other.example/*'] }]);
    // The old address's open tab can't read any more: no approval window, nothing awaiting.
    const opened: string[] = [];
    ext.context.on('page', (p) => opened.push(p.url()));
    const answer = await forgedRequest(app);
    expect(answer === 'no answer' || (answer as { ok?: boolean }).ok === false).toBe(true);
    expect(opened).toEqual([]);
  } finally {
    await ext.context.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

/** The app (dev server, API mocked) served at an https origin, as a hosted address would be. */
async function hostedApp(context: BrowserContext, origin: string): Promise<Page> {
  const page = await context.newPage();
  await mockApi(page, { '/api/features': () => ({ json: { flags: { companion: true } } }) });
  await page.route(`${origin}/**`, async (r) => {
    const u = new URL(r.request().url());
    if (u.pathname.startsWith('/api/')) return r.fallback();
    return r.fulfill({ response: await r.fetch({ url: `${APP}${u.pathname}${u.search}` }) });
  });
  await page.goto(`${origin}/collection?families=%5B%22blb%22%5D`);
  return page;
}

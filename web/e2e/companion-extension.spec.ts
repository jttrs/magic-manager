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

const test = base.extend<Fixtures>({
  // eslint-disable-next-line no-empty-pattern
  ext: async ({}, use) => {
    const dir = mkdtempSync(join(tmpdir(), 'mm-companion-'));
    cpSync(resolve(ROOT, 'extension'), dir, { recursive: true });
    const manifest = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8'));
    manifest.host_permissions.push('http://localhost/*', 'https://www.tcgplayer.com/*', 'https://moxfield.com/*', 'https://*.moxfield.com/*');
    writeFileSync(join(dir, 'manifest.json'), JSON.stringify(manifest));
    const context = await chromium.launchPersistentContext('', {
      channel: 'chromium',
      headless: true,
      args: [`--disable-extensions-except=${dir}`, `--load-extension=${dir}`],
    });
    const worker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
    const id = new URL(worker.url()).host;
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
  await expect(approve.locator('#table')).toContainText('TCGplayer #487805');
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
  await d.getByRole('tab', { name: 'Moxfield collection' }).click();
  await d.getByRole('radio', { name: /A shared link/ }).check();
  await d.getByRole('textbox', { name: /collection or binder link/ }).fill('https://moxfield.com/collection/hgsItGBwRUybHyN0WZR41w');
  const approval = ext.context.waitForEvent('page', (p) => p.url().includes('/src/approve.html'));
  await d.getByRole('button', { name: 'Read from Moxfield' }).click();
  const approve = await approval;
  await expect(approve.locator('#title')).toHaveText('Send your Moxfield cards?');
  const copies = GOLD.lines.reduce((t: number, l: { quantity: number }) => t + l.quantity, 0);
  await expect(approve.locator('#summary')).toHaveText(`Moxfield collection (shared link) · 20 printings · ${copies} cards`);
  await expect(approve.locator('#table')).toContainText('proxy — skipped');
  expect(previews).toEqual([]);
  await approve.getByRole('button', { name: 'Send to magic-manager' }).click();
  await expect(d.getByRole('heading', { name: 'Moxfield collection (shared link)' })).toBeVisible();
  expect(previews).toEqual([{ source: 'moxfield', scope: 'collection', id: 'hgsItGBwRUybHyN0WZR41w', name: null, lines: GOLD.lines }]);
  expect(await ext.worker.evaluate(() => chrome.tabs.query({ url: 'https://moxfield.com/*' }))).toHaveLength(1);   // your tab, nothing extra left open
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

test('the settings page refuses addresses it may not pair with', async ({ ext }) => {
  const opts = await ext.context.newPage();
  await opts.goto(`chrome-extension://${ext.id}/src/options.html`);
  for (const [addr, why] of [
    ['http://example.com', 'Plain http is only allowed for this computer'],
    ['https://example.com', 'Tailscale address'],
    ['http://localhost:8765/app', 'no path'],
    ['https://user:pw@x.ts.net', 'user name or password'],
  ] as const) {
    await opts.getByRole('textbox', { name: 'App address' }).fill(addr);
    await opts.getByRole('button', { name: 'Pair', exact: true }).click();
    await expect(opts.locator('#pair-status')).toContainText(why);
  }
  await expect(opts.locator('#pair-status')).toHaveClass('error');
});

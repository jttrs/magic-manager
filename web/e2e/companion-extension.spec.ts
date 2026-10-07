// The REAL extension, loaded unpacked into Chromium, against the app (API mocked)
// and a saved Mana Pool cart page. Proves the security model end to end:
// only the paired app can ask, nothing reaches the app until Send is pressed in
// the extension's own window, and other pages (another site, another port) get
// no answer at all.
//
// Harness-only change: the test copy of the manifest grants http://localhost/*
// up front, because Chrome's permission prompt (what users see when pairing)
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

type Fixtures = { ext: { context: BrowserContext; worker: Worker; id: string } };

const test = base.extend<Fixtures>({
  // eslint-disable-next-line no-empty-pattern
  ext: async ({}, use) => {
    const dir = mkdtempSync(join(tmpdir(), 'mm-companion-'));
    cpSync(resolve(ROOT, 'extension'), dir, { recursive: true });
    const manifest = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8'));
    manifest.host_permissions.push('http://localhost/*');
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
  await page.getByRole('button', { name: 'Check my Mana Pool cart' }).click();
  const dialog = page.getByRole('dialog', { name: 'Check my Mana Pool cart' });
  const approval = context.waitForEvent('page', (p) => p.url().endsWith('/src/approve.html'));
  await dialog.getByRole('button', { name: 'Read my cart' }).click();
  return { dialog, approve: await approval };
}

test('read the cart, review exactly what will be sent, approve — only then the app gets the lines', async ({ ext }) => {
  const { page, bodies } = await appPage(ext.context);
  await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();
  const { dialog, approve } = await startCartRead(ext.context, page);
  await expect(dialog.getByText('Waiting for you to approve in the companion window')).toBeVisible();
  await expect(approve.locator('#origin')).toHaveText(APP);
  await expect(approve.locator('#summary')).toHaveText('3 cart lines · 4 cards · $71.00');
  await expect(approve.locator('#table')).toContainText('Ajani, Nacatl Pariah // Ajani, Nacatl Avenger');
  expect(bodies).toEqual([]);                                     // nothing sent yet
  const send = approve.getByRole('button', { name: 'Send to magic-manager' });
  expect(await approve.evaluate(() => document.activeElement?.id)).toBe('deny');   // the safe choice has focus
  await expect(send).toBeEnabled();
  await send.click();
  await expect(dialog).toContainText('Read in this browser by the companion.');
  expect(bodies).toEqual([{ items: EXPECTED.items, source: 'extension', family: 'blb' }]);
  const tabs = await ext.worker.evaluate(() => chrome.tabs.query({ url: 'https://manapool.com/*' }));
  expect(tabs).toHaveLength(1);                                   // your own cart tab is left alone
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

// The REAL extension reading WATCHED open-tab store pages (Deals → Watching → Read watched prices).
// Proves the two-step approval: the extension re-checks the app's list, you approve the list
// BEFORE any tab is opened, a page that isn't open is read from a background tab that is always
// closed again, your own tab is left alone, and the app gets the readings only after Send.
//
// Harness-only change (like companion-extension.spec.ts): the test copy of the manifest grants
// the app address and the Deals store sites up front, because Chrome's permission prompts can't
// be clicked by automation. Store pages are served from a saved Best Buy page.
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { chromium, expect, test as base, type BrowserContext, type Worker } from '@playwright/test';
import { mockApi } from './support';

const ROOT = resolve(import.meta.dirname, '../..');
const PORT = Number(process.env.MM_E2E_PORT ?? 5174);
const APP = `http://localhost:${PORT}`;
const STORE_HTML = readFileSync(resolve(ROOT, 'tests/fixtures/companion/store-rendered.html'), 'utf8');
const MINE = 'https://www.bestbuy.com/site/foundations/6589123.p';     // open in your browser
const OPENED = 'https://www.target.com/p/foundations/-/A-1';           // watched, but not open
const NOT_A_STORE = 'https://evil.example/p/x';                        // never read, never opened
const PLAIN_HTTP = 'http://www.bestbuy.com/site/foundations/1.p';

type Fixtures = { ext: { context: BrowserContext; worker: Worker } };

const test = base.extend<Fixtures>({
  // eslint-disable-next-line no-empty-pattern
  ext: async ({}, use) => {
    const dir = mkdtempSync(join(tmpdir(), 'mm-companion-'));
    cpSync(resolve(ROOT, 'extension'), dir, { recursive: true });
    const manifest = JSON.parse(readFileSync(join(dir, 'manifest.json'), 'utf8'));
    const stores = (manifest.optional_host_permissions as string[]).filter((o) => !/localhost|127\.0\.0\.1|ts\.net|moxfield|^https:\/\/\*\/\*$/.test(o));
    manifest.host_permissions.push('http://localhost/*', ...stores);
    writeFileSync(join(dir, 'manifest.json'), JSON.stringify(manifest));
    const context = await chromium.launchPersistentContext('', {
      channel: 'chromium',
      headless: true,
      args: [`--disable-extensions-except=${dir}`, `--load-extension=${dir}`],
    });
    await context.route(/^https:\/\/www\.(bestbuy|target)\.com\//, (r) => r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: STORE_HTML }));
    await context.route(/^https:\/\/(?!www\.(bestbuy|target)\.com\/)/, (r) => r.abort());   // nothing else leaves the test
    const worker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
    await worker.evaluate(async (origin) => {
      await chrome.storage.local.set({ appOrigin: origin });
      await chrome.scripting.registerContentScripts([{ id: 'mm-bridge', matches: ['http://localhost/*'], js: ['src/bridge.js'], runAt: 'document_start', allFrames: false }]);
    }, APP);
    await use({ context, worker });
    await context.close();
    rmSync(dir, { recursive: true, force: true });
  },
});

const store = (url: string, name: string) => ({
  url, store: name, price: 150, available: true, read_at: '2026-09-10T12:00:00', read: true, read_in_browser: true,
  first_price: 150, first_at: '2026-09-10T12:00:00', change: null, low: 150, high: 150, history: [],
});
const WATCHED = [{
  product_id: 7, set_code: 'fdc', name: 'Foundations Commander', kind: 'sealed', finish: null, category: 'deck', subtype: null, release_date: '2024-11-15',
  best_price: 150, best_store: 'Best Buy', best_url: MINE, target: null, target_price: null, target_met: null,
  // The app only asks for read_in_browser links; two bogus ones prove the extension re-checks anyway.
  stores: [store(MINE, 'Best Buy'), store(OPENED, 'Target'), store(NOT_A_STORE, 'Evil'), store(PLAIN_HTTP, 'Best Buy')],
}];

const tabsAt = (worker: Worker, host: string) => worker.evaluate(
  async (h) => (await chrome.tabs.query({})).filter((t) => t.url && new URL(t.url).hostname === h).length, host);

test('approve the list, then the readings — only then the read gets the pages; opened tabs close', async ({ ext }) => {
  const { context, worker } = ext;
  const mine = await context.newPage();
  await mine.goto(MINE);
  const page = await context.newPage();
  const jobs: Record<string, unknown>[] = [];
  await mockApi(page, {
    '/api/features': () => ({ json: { flags: { deals: true, companion: true } } }),
    '/api/deals/watched': () => ({ json: WATCHED }),
    '/api/market/product-cost': () => ({ status: 404, json: { detail: 'n/a' } }),
  });
  await page.route('**/api/jobs/deals.watchlist', (r) => { jobs.push(r.request().postDataJSON()); return r.fulfill({ status: 500, json: { detail: 'stop here' } }); });
  await page.goto(`${APP}/market?subject=deals&deals=watching`);
  await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();

  const approval = context.waitForEvent('page', (p) => p.url().includes('/src/approve.html'));
  await page.getByRole('button', { name: 'Read watched prices' }).click();
  const approve = await approval;

  // Step 1: the list — nothing opened or read yet; the bogus links were dropped by the extension.
  await expect(approve.locator('#title')).toHaveText('Read your watched store pages?');
  await expect(approve.locator('#summary')).toHaveText('2 watched store pages · 1 to open in a background tab');
  const table = approve.locator('#table');
  await expect(table).toContainText(MINE);
  await expect(table).toContainText('your open tab');
  await expect(table).toContainText(OPENED);
  await expect(table).toContainText('opens in a background tab, then closes');
  await expect(table).not.toContainText('evil.example');
  await expect(table).not.toContainText(PLAIN_HTTP);
  expect(await tabsAt(worker, 'www.target.com')).toBe(0);
  expect(jobs).toEqual([]);
  expect(await approve.evaluate(() => document.activeElement?.id)).toBe('deny');
  await approve.getByRole('button', { name: 'Read these pages' }).click();

  // Step 2: exactly what will be sent; the background tab is gone, yours is still there.
  await expect(approve.locator('#title')).toHaveText('Send your watched store prices?', { timeout: 20_000 });   // reads the pages first
  await expect(approve.locator('#summary')).toHaveText('2 of 2 watched store pages read');
  await expect.poll(() => tabsAt(worker, 'www.target.com')).toBe(0);
  expect(await tabsAt(worker, 'www.bestbuy.com')).toBe(1);
  expect(jobs).toEqual([]);
  await approve.getByRole('button', { name: 'Send to magic-manager' }).click();

  await expect.poll(() => jobs.length).toBe(1);
  const body = jobs[0] as { refresh: boolean; in_browser: boolean; pages: Record<string, { title: string; text: string }> };
  expect([body.refresh, body.in_browser]).toEqual([true, true]);
  expect(Object.keys(body.pages).sort()).toEqual([MINE, OPENED].sort());
  expect(body.pages[MINE].text).toContain('$');
});

test('Don’t read at the list: nothing is opened, read or sent', async ({ ext }) => {
  const { context, worker } = ext;
  const page = await context.newPage();
  const jobs: unknown[] = [];
  await mockApi(page, {
    '/api/features': () => ({ json: { flags: { deals: true, companion: true } } }),
    '/api/deals/watched': () => ({ json: WATCHED }),
    '/api/market/product-cost': () => ({ status: 404, json: { detail: 'n/a' } }),
  });
  await page.route('**/api/jobs/deals.watchlist', (r) => { jobs.push(r.request().postDataJSON()); return r.fulfill({ status: 500, json: { detail: 'stop here' } }); });
  await page.goto(`${APP}/market?subject=deals&deals=watching`);
  await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();
  const approval = context.waitForEvent('page', (p) => p.url().includes('/src/approve.html'));
  await page.getByRole('button', { name: 'Read watched prices' }).click();
  const approve = await approval;
  await approve.getByRole('button', { name: 'Don’t read' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'You chose not to send it' })).toBeVisible();
  expect(await tabsAt(worker, 'www.target.com')).toBe(0);
  expect(jobs).toEqual([]);
});

test('a forged "send" of the list itself is refused — the plan is never delivered as data', async ({ ext }) => {
  const { context, worker } = ext;
  const page = await context.newPage();
  await mockApi(page, {
    '/api/features': () => ({ json: { flags: { deals: true, companion: true } } }),
    '/api/deals/watched': () => ({ json: WATCHED }),
    '/api/market/product-cost': () => ({ status: 404, json: { detail: 'n/a' } }),
  });
  await page.goto(`${APP}/market?subject=deals&deals=watching`);
  await expect(page.getByRole('button', { name: 'Browser companion · connected' })).toBeVisible();
  const approval = context.waitForEvent('page', (p) => p.url().includes('/src/approve.html'));
  await page.getByRole('button', { name: 'Read watched prices' }).click();
  const approve = await approval;
  await expect(approve.locator('#title')).toHaveText('Read your watched store pages?');
  const r = await approve.evaluate(async () => {
    const { pending } = await chrome.storage.session.get('pending');
    return chrome.runtime.sendMessage({ type: 'decision', id: pending.id, approve: true });
  });
  expect(r).toMatchObject({ ok: false, code: 'request.invalid' });
  expect(await tabsAt(worker, 'www.target.com')).toBe(0);
});

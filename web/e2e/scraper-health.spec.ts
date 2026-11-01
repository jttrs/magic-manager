// "Temporarily down" notices (docs/scraper-health.md): wherever a site read is
// offered and the daily canary (or a real read) flagged it, the app says what,
// why, since when and the code — and still lets you try.
import type { Page } from '@playwright/test';
import { COLLECTION_URL, expect, test } from './support';

const row = (key: string, label: string, site_name: string, over: Record<string, unknown> = {}) => ({
  key, scraper: key.split('/')[0], site: key.split('/')[1], site_name, label, where: '', canary: 'http',
  status: 'down', since: new Date(Date.now() - 3 * 3600_000).toISOString(), checked_at: null, last_ok: null,
  code: 'scrape.no_cards', message: 'The deck page returned no cards — its format changed.', fix: 'Fix the parser.', via: 'canary', ...over,
});

async function health(page: Page, rows: unknown[]) {
  await page.route('**/api/scrapers/health', (r) => r.fulfill({ json: { scrapers: rows, down: rows.length } }));
}

test('deck import: the notice follows the pasted link’s builder and never blocks', async ({ page }) => {
  await health(page, [row('deck-import/archidekt', 'Archidekt deck import', 'Archidekt')]);
  await page.goto('/decks');
  await page.getByRole('toolbar', { name: 'Deck list actions' }).getByRole('button', { name: 'Import a deck from a link' }).click();
  const dialog = page.getByRole('dialog', { name: 'Import a deck' });
  const notice = dialog.getByRole('status', { name: 'Temporarily down' });
  await dialog.getByRole('textbox').fill('https://moxfield.com/decks/abc');
  await expect(notice).toHaveCount(0);
  await dialog.getByRole('textbox').fill('https://archidekt.com/decks/42/x');
  await expect(notice).toContainText('Archidekt deck import — temporarily down');
  await expect(notice).toContainText('its format changed. You can still try');
  await expect(notice).toContainText(/Since today .* · found by the daily check · Code scrape\.no_cards/);
  await expect(dialog.getByRole('button', { name: 'Import deck' })).toBeEnabled();
  await dialog.screenshot({ path: test.info().outputPath('import-notice.png') });
});

test('cart check: a changed Mana Pool cart page is flagged above the ways to read it', async ({ page }) => {
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { cart_check: true } } }));
  await page.route('**/api/cart/setup', (r) => r.fulfill({ json: { account: false } }));
  await health(page, [row('companion-cart/manapool', 'Mana Pool cart read in your browser', 'Mana Pool',
    { code: 'cart.page_changed', message: 'Mana Pool’s cart page changed — the reader found no cart.', via: 'use' })]);
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Check my cart' }).click();
  const notice = page.getByRole('dialog', { name: 'Check my cart' }).getByRole('status', { name: 'Temporarily down' });
  await expect(notice).toContainText('Mana Pool cart read in your browser — temporarily down');
  await expect(notice).toContainText('found while reading · Code cart.page_changed');
});

test('explore rankings: EDHREC’s ranking read is flagged on the sheet', async ({ page }) => {
  await health(page, [row('edhrec-rankings/edhrec', 'EDHREC rankings', 'EDHREC', { code: 'scrape.shape_changed', message: 'The page’s data no longer has the fields we read.' })]);
  await page.goto('/explore?mode=rankings');
  await expect(page.getByRole('status', { name: 'Temporarily down' })).toContainText('EDHREC rankings — temporarily down');
});

test('deals: a down store carries a DOWN mark whose tooltip explains it', async ({ page }) => {
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/tabs?*', (r) => r.fulfill({ json: {
    browser: 'chrome', windows: 1, windows_read: 1, warnings: [], uncatalogued: [], store_pages: 0, other: 0, dropped_local: 0, duplicates: 0,
    stores: [
      { key: 'manyrealms', name: 'Many Realms', mode: 'shopify', no_sales_tax: true, tabs: [{ url: 'https://manyrealms.com/products/a', title: 'A', window: 1, tab: 1 }] },
      { key: 'bestbuy', name: 'Best Buy', mode: 'rendered', no_sales_tax: false, tabs: [{ url: 'https://www.bestbuy.com/product/x/1', title: 'B', window: 1, tab: 2 }] },
    ],
  } }));
  await health(page, [row('store-price/manyrealms', 'Many Realms prices', 'Many Realms', { code: 'scrape.no_price', message: 'The page no longer shows a price where the recipe looks.' })]);
  const read = (url: string, vendor: string) => ({ url, vendor, price: 10, currency: 'USD', available: true, title: null, signal: 'shopify', error: null });
  const sse = [['status', { status: 'running' }], ['result', { summary: 'read', artifacts: [{ kind: 'json', label: 'prices', data: [read('https://manyrealms.com/products/a', 'manyrealms'), read('https://www.bestbuy.com/product/x/1', 'bestbuy')] }] }], ['status', { status: 'succeeded' }]]
    .map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
  await page.route('**/api/deals/watched', (r) => r.fulfill({ json: [] }));
  await page.route('**/api/jobs/deals.read_prices', (r) => r.fulfill({ status: 202, json: { id: 'p1', name: 'deals.read_prices', title: 'x', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } }));
  await page.route('**/api/jobs/p1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse }));
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  const pinned = page.getByRole('rowgroup', { name: 'From your open tabs' });
  const mark = pinned.getByRole('row', { name: /^A/ }).getByLabel(/Many Realms is temporarily down/);
  await expect(mark).toHaveText('Down');
  await expect(pinned.getByRole('row', { name: /^B/ }).getByText('Down', { exact: true })).toHaveCount(0);
  await mark.focus();
  await expect(page.getByRole('tooltip')).toContainText('Code scrape.no_price');
});

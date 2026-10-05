import { expect, test } from './support';

const tabs = {
  browser: 'chrome', windows: 3, windows_read: 3, warnings: [],
  stores: [
    { key: 'manyrealms', name: 'Many Realms', mode: 'shopify', no_sales_tax: true, tabs: [{ url: 'https://manyrealms.com/products/fdn-set', title: 'Foundations Commander Set of 5', window: 1, tab: 1 }] },
    { key: 'bestbuy', name: 'Best Buy', mode: 'rendered', no_sales_tax: false, tabs: [{ url: 'https://www.bestbuy.com/product/x/JJ8', title: 'Reign of Dragons', window: 2, tab: 1 }] },
  ],
  uncatalogued: [{ host: 'shop.example', tabs: [{ url: 'https://shop.example/products/a', title: 'A', window: 3, tab: 1 }] }],
  store_pages: 1, other: 12, dropped_local: 1, duplicates: 0,
};

test('Deals is hidden unless its flag is on', async ({ page }) => {
  await page.goto('/market');
  await expect(page.getByRole('radio', { name: 'Set family' })).toBeVisible();
  await expect(page.getByRole('radio', { name: 'Deals' })).toHaveCount(0);
});

test('with the flag on: read open tabs, grouped by store', async ({ page }) => {
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/tabs?*', (r) => r.fulfill({ json: tabs }));
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  const realms = page.getByRole('region', { name: 'Many Realms' });
  await expect(realms).toContainText('price read from the store · no sales tax');
  await expect(realms.getByRole('link', { name: /Foundations Commander Set of 5/ })).toHaveAttribute('href', 'https://manyrealms.com/products/fdn-set');
  await expect(page.getByRole('region', { name: 'Best Buy' })).toContainText('price read from your open tab');
  await expect(page.getByRole('region', { name: 'Stores without a recipe yet' })).toContainText('shop.example');
  await expect(page.getByText('3 of 3 windows read')).toBeVisible();
});

test('a warning from the reader is shown plainly', async ({ page }) => {
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/tabs?*', (r) => r.fulfill({ json: { ...tabs, windows_read: 1, warnings: ['Only 1 of 3 windows returned tabs. Click into the window with your shopping tabs to bring it to the front, then read again.'] } }));
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  await expect(page.getByText('Only 1 of 3 windows returned tabs.')).toBeVisible();
});

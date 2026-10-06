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

test('read prices: fills price + stock per page, shows setup errors once', async ({ page }) => {
  const js = 'Chrome blocks reading open tabs. Turn on Chrome → View → Developer → Allow JavaScript from Apple Events (once), then read again.';
  const prices = [
    { url: 'https://manyrealms.com/products/fdn-set', vendor: 'manyrealms', price: 199.99, currency: 'USD', available: true, title: 'Foundations Commander Set of 5', signal: 'shopify', error: null },
    { url: 'https://www.bestbuy.com/product/x/JJ8', vendor: 'bestbuy', price: null, currency: null, available: null, title: null, signal: '', error: js },
  ];
  const sse = [
    ['status', { status: 'running' }],
    ['result', { summary: '1 of 2 prices read', artifacts: [{ kind: 'json', label: 'prices', data: prices }] }],
    ['status', { status: 'succeeded' }],
  ].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
  let sent: { urls: string[] } | null = null;
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/tabs?*', (r) => r.fulfill({ json: tabs }));
  await page.route('**/api/jobs/deals.read_prices', (r) => { sent = r.request().postDataJSON(); return r.fulfill({ status: 202, json: { id: 'p1', name: 'deals.read_prices', title: 'Read store prices', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } }); });
  await page.route('**/api/jobs/p1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse }));
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  await page.getByRole('button', { name: 'Read 2 prices' }).click();
  const realms = page.getByRole('region', { name: 'Many Realms' });
  await expect(realms).toContainText('$199.99');
  await expect(realms).toContainText('In stock');
  await expect(page.getByRole('alert').filter({ hasText: 'Allow JavaScript from Apple Events' })).toHaveCount(1);
  expect(sent).toEqual({ urls: ['https://manyrealms.com/products/fdn-set', 'https://www.bestbuy.com/product/x/JJ8'] });
});

test('deals: below-market first, match lines, and confirming an ambiguous listing', async ({ page }) => {
  const prices = [
    { url: 'https://manyrealms.com/products/fdn-set', vendor: 'manyrealms', price: 149.99, currency: 'USD', available: true, title: 'The Hobbit - Play Booster Display', signal: 'shopify', error: null,
      kind: 'sealed', status: 'matched', match: { kind: 'sealed', set_code: 'hob', name: 'The Hobbit Play Booster Box', scryfall_id: null, finish: null, price: null },
      candidates: [], note: '', market: 152.92, contents: 154.08, partial: false, delta: -2.93, pct: -1.9 },
    { url: 'https://www.bestbuy.com/product/x/JJ8', vendor: 'bestbuy', price: 23.99, currency: 'USD', available: true, title: 'Exemplar of Light (11) (Secrets of Strixhaven)', signal: 'pattern', error: null,
      kind: 'single', status: 'ambiguous', match: null, note: 'The store says Secrets of Strixhaven #11, but that printing is Eager Glyphmage — pick the right printing of Exemplar of Light.',
      candidates: [
        { kind: 'single', set_code: 'pfdn', name: 'Exemplar of Light (PFDN 11p)', scryfall_id: 'pfdn11p', finish: 'nonfoil', price: 21.47 },
        { kind: 'single', set_code: 'fdn', name: 'Exemplar of Light (FDN 297)', scryfall_id: 'fdn297', finish: 'nonfoil', price: 7.06 },
      ], market: null, contents: null, partial: false, delta: null, pct: null },
  ];
  const sse = [
    ['status', { status: 'running' }],
    ['result', { summary: '2 of 2 prices read · 1 compared to market', artifacts: [{ kind: 'json', label: 'prices', data: prices }] }],
    ['status', { status: 'succeeded' }],
  ].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
  let confirmed: { url: string; choice: { scryfall_id: string } } | null = null;
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/tabs?*', (r) => r.fulfill({ json: tabs }));
  await page.route('**/api/jobs/deals.read_prices', (r) => r.fulfill({ status: 202, json: { id: 'p2', name: 'deals.read_prices', title: 'Read store prices', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } }));
  await page.route('**/api/jobs/p2/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse }));
  await page.route('**/api/deals/match', (r) => {
    confirmed = r.request().postDataJSON();
    return r.fulfill({ json: { ...prices[1], status: 'confirmed', match: prices[1].candidates[0], candidates: [], note: '', market: 21.47, delta: 2.52, pct: 11.7 } });
  });
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  await page.getByRole('button', { name: 'Read 2 prices' }).click();
  const best = page.getByRole('region', { name: 'Below market' });
  await expect(best).toContainText('The Hobbit Play Booster Box');
  await expect(best).toContainText('$2.93 under market (−2%)');
  await expect(page.getByRole('region', { name: 'Many Realms' })).toContainText('cards inside $154.08');
  const bb = page.getByRole('region', { name: 'Best Buy' });
  await expect(bb).toContainText('that printing is Eager Glyphmage');
  await bb.getByRole('button', { name: 'This one' }).click();
  await expect(bb).toContainText('$2.52 over market (+12%)');
  await expect(bb.getByRole('button', { name: 'you confirmed this · change' })).toBeVisible();
  expect(confirmed!.url).toBe('https://www.bestbuy.com/product/x/JJ8');
  expect(confirmed!.choice.scryfall_id).toBe('pfdn11p');
});

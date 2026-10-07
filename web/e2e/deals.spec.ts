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
  const look = page.getByRole('region', { name: 'Needs a look' });
  await expect(look).toContainText('$199.99');
  await expect(look).toContainText('In stock');
  await expect(page.getByRole('alert').filter({ hasText: 'Allow JavaScript from Apple Events' })).toHaveCount(1);
  expect(sent).toEqual({ urls: ['https://manyrealms.com/products/fdn-set', 'https://www.bestbuy.com/product/x/JJ8'], pages: {} });
});

const sealedCost = (over: Record<string, unknown> = {}) => ({
  kind: 'sealed', set_code: 'hob', name: 'The Hobbit Play Booster Box', finish: null, category: 'booster_box', subtype: null, release_date: '2023-06-23',
  market: 152.92, market_source: 'tcgplayer', contents: 154.08, exact: 154.08, floor: 140, known_exact: 154.08, known_floor: 140, booster_ev: 0, booster_only: false,
  total_cards: 10, unpriced: 0, notes: [], lines: [], ...over,
});
const tree = { name: 'The Hobbit Play Booster Box', kind: 'box', count: 1, market: 152.92, contents_value: 154.08, contents_kind: 'cards', children: [{ name: 'Play Booster', kind: 'booster_pack', count: 36, market: 4, contents_value: 4.2, contents_kind: 'booster', children: [] }] };

test('deals: the table after prices, and confirming an ambiguous listing under Needs a look', async ({ page }) => {
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
  let confirmed: { url: string; choice: { scryfall_id: string } } | null = null;
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/tabs?*', (r) => r.fulfill({ json: tabs }));
  await page.route('**/api/market/product-cost?*', (r) => r.fulfill({ json: sealedCost() }));
  await page.route('**/api/jobs/deals.read_prices', (r) => r.fulfill({ status: 202, json: jobStub('p2', 'deals.read_prices') }));
  await page.route('**/api/jobs/p2/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sseOf('2 of 2 prices read', [{ kind: 'json', label: 'prices', data: prices }]) }));
  await page.route('**/api/deals/match', (r) => {
    confirmed = r.request().postDataJSON();
    return r.fulfill({ json: { ...prices[1], status: 'confirmed', match: prices[1].candidates![0], candidates: [], note: '', market: 21.47, delta: 2.52, pct: 11.7 } });
  });
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  await page.getByRole('button', { name: 'Read 2 prices' }).click();
  const table = page.getByRole('table', { name: 'Products' });
  const row = table.getByRole('row', { name: /The Hobbit Play Booster Box/ });
  await expect(row).toContainText('$149.99');
  await expect(row).toContainText('−2%');
  await expect(row).toContainText('$2.93');
  await expect(row).toContainText('$154.08');
  const look = page.getByRole('region', { name: 'Needs a look' });
  await expect(look).toContainText('that printing is Eager Glyphmage');
  await look.getByRole('button', { name: 'This one' }).click();
  await expect(table.getByRole('row', { name: /Exemplar of Light \(PFDN 11p\)/ })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Needs a look' })).toHaveCount(0);
  expect(confirmed!.url).toBe('https://www.bestbuy.com/product/x/JJ8');
  expect(confirmed!.choice.scryfall_id).toBe('pfdn11p');
});

const jobStub = (id: string, name: string) => ({ id, name, title: name, inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null });
const sseOf = (summary: string, artifacts: unknown[]) => [
  ['status', { status: 'running' }],
  ['result', { summary, artifacts }],
  ['status', { status: 'succeeded' }],
].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');

test('watch a matched sealed product from the inspector; two stores are one row', async ({ page }) => {
  const match = { kind: 'sealed', set_code: 'hob', name: 'The Hobbit Play Booster Box', scryfall_id: null, finish: null, price: null };
  const mk = (url: string, price: number, extra = {}) => ({ url, vendor: 'v', price, currency: 'USD', available: true, title: 'The Hobbit - Play Booster Display', signal: 'shopify', error: null,
    kind: 'sealed', status: 'matched', match, candidates: [], note: '', market: 152.92, contents: 154.08, partial: false, delta: -2.93, pct: -1.9, watching: false, ...extra });
  const prices = [mk('https://manyrealms.com/products/fdn-set', 149.99), mk('https://www.bestbuy.com/product/x/JJ8', 139.5)];
  let body: unknown = null;
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/tabs?*', (r) => r.fulfill({ json: tabs }));
  await page.route('**/api/market/product-cost?*', (r) => r.fulfill({ json: sealedCost() }));
  await page.route('**/api/market/product-tree?*', (r) => r.fulfill({ json: tree }));
  await page.route('**/api/jobs/deals.read_prices', (r) => r.fulfill({ status: 202, json: jobStub('p2', 'deals.read_prices') }));
  await page.route('**/api/jobs/p2/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sseOf('2 of 2', [{ kind: 'json', label: 'prices', data: prices }]) }));
  await page.route('**/api/deals/watch', (r) => { body = r.request().postDataJSON(); return r.fulfill({ json: { watching: true, message: 'Watching' } }); });
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  await page.getByRole('button', { name: 'Read 2 prices' }).click();
  const table = page.getByRole('table', { name: 'Products' });
  await expect(table.getByRole('row')).toHaveCount(2);
  await table.getByRole('button', { name: 'The Hobbit Play Booster Box' }).click();
  const inspector = page.getByRole('region', { name: 'The Hobbit Play Booster Box' });
  await expect(inspector.getByRole('link', { name: /Many Realms/ })).toHaveAttribute('href', 'https://manyrealms.com/products/fdn-set');
  await expect(inspector.getByRole('link', { name: /Best Buy/ })).toHaveAttribute('href', 'https://www.bestbuy.com/product/x/JJ8');
  await expect(inspector).toContainText('Read from your open tab');
  await expect(inspector).toContainText('Play Booster');
  await inspector.getByRole('button', { name: 'Watch', exact: true }).click();
  await expect(inspector.getByRole('button', { name: 'Stop watching' })).toBeVisible();
  expect(body).toEqual({ url: 'https://www.bestbuy.com/product/x/JJ8', choice: match, price: 139.5, currency: 'USD' });
});

test('Watching: a filterable table with an inspector; read prices again', async ({ page }) => {
  const store = { url: 'https://cashcards.example/c13', store: 'Cash Cards Unlimited', price: 59.99, available: true, read_at: '2026-09-10T12:00:00', read: true,
    first_price: 64.99, first_at: '2026-09-05T12:00:00', change: -5, history: [{ price: 64.99, at: '2026-09-05T12:00:00' }, { price: 59.99, at: '2026-09-10T12:00:00' }] };
  const watched = [
    { set_code: 'c13', name: 'Commander 2013 Deck: Nature of the Beast', kind: 'sealed', finish: null, category: 'deck', subtype: null, release_date: '2013-11-01',
      best_price: 59.99, best_store: 'Cash Cards Unlimited', best_url: store.url, stores: [store] },
    { set_code: 'sld', name: 'Secret Lair Drop: Frogs', kind: 'sld', finish: 'foil', category: null, subtype: null, release_date: '2024-01-01',
      best_price: 30, best_store: 'Frog Shop', best_url: 'https://frogs.example/x', stores: [{ ...store, url: 'https://frogs.example/x', store: 'Frog Shop', price: 30, history: [], change: null }] },
  ];
  const costs: Record<string, unknown> = {
    'Commander 2013 Deck: Nature of the Beast': { kind: 'sealed', set_code: 'c13', name: 'Commander 2013 Deck: Nature of the Beast', category: 'deck', release_date: '2013-11-01',
      market: 75.5, market_source: 'tcgplayer', contents: 90, exact: 90, floor: 70, known_exact: 80, known_floor: 62, booster_ev: 10, total_cards: 100, unpriced: 2, notes: [],
      lines: [
        { scryfall_id: 'a', finish: 'nonfoil', name: 'Sol Ring', set_code: 'c13', collector_number: '1', need: 1, free: 0, buy: 1, unit_usd: 2, floor_usd: 1, floor_set_code: 'c21', floor_collector_number: '5', floor_scryfall_id: 'b' },
        { scryfall_id: 'c', finish: 'nonfoil', name: 'Rhystic Study', set_code: 'c13', collector_number: '2', need: 1, free: 0, buy: 1, unit_usd: 30, floor_usd: 25, floor_set_code: 'c13', floor_collector_number: '2', floor_scryfall_id: 'c' },
      ] },
    'Secret Lair Drop: Frogs': { kind: 'sld', set_code: 'sld', name: 'Secret Lair Drop: Frogs', category: null, market: 40, exact: 45, floor: 35, known_exact: 45, known_floor: 35, booster_ev: 0, total_cards: 3, unpriced: 0, notes: [], lines: [] },
  };
  const sent: unknown[] = [];
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/watched', (r) => r.fulfill({ json: watched }));
  await page.route('**/api/market/product-cost?*', (r) => r.fulfill({ json: costs[new URL(r.request().url()).searchParams.get('name')!] }));
  await page.route('**/api/market/product-tree?*', (r) => r.fulfill({ json: tree }));
  await page.route('**/api/jobs/deals.watchlist', (r) => { sent.push(r.request().postDataJSON()); return r.fulfill({ status: 202, json: jobStub('w1', 'deals.watchlist') }); });
  await page.route('**/api/jobs/w1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sseOf('2 watched products', [{ kind: 'json', label: 'watchlist', data: watched }, { kind: 'json', label: 'errors', data: [] }]) }));
  await page.goto('/market?subject=deals&deals=watching');
  const table = page.getByRole('table', { name: 'Products' });
  const row = table.getByRole('row', { name: /Nature of the Beast/ });
  await expect(row).toContainText('Cash Cards Unlimited');
  await expect(row).toContainText('$59.99');
  await expect(row).toContainText('−21%');
  await expect(row).toContainText('$15.51');
  await expect(row).toContainText('$90.00+');
  await expect(row).toContainText('cheapest $70.00');
  await expect(row).toContainText('$80.00 cards + $10.00 boosters');
  await expect(page.getByText('2 of 2 products · compared to sealed price')).toBeVisible();

  // Search and type filters.
  await page.getByLabel('Search', { exact: true }).fill('frogs');
  await expect(table.getByRole('row')).toHaveCount(2);
  await expect(row).toHaveCount(0);
  await page.getByLabel('Search', { exact: true }).fill('');
  await page.getByRole('button', { name: /^Decks/ }).click();
  await expect(table.getByRole('row', { name: /Frogs/ })).toHaveCount(0);
  await expect(row).toBeVisible();
  await page.getByRole('button', { name: /^Decks/ }).click();

  // Inspector.
  await row.getByRole('button', { name: 'Commander 2013 Deck: Nature of the Beast' }).click();
  const inspector = page.getByRole('region', { name: 'Commander 2013 Deck: Nature of the Beast' });
  await expect(inspector.getByRole('link', { name: /Cash Cards Unlimited/ })).toHaveAttribute('href', store.url);
  await expect(inspector).toContainText('↓ $5.00 since Sep 5');
  await expect(inspector.getByText('Sealed price')).toBeVisible();
  await expect(inspector.getByText('Cards inside, exact printings')).toBeVisible();
  await expect(inspector).toContainText('$80.00');
  await expect(inspector).toContainText('Total, cheapest');
  await expect(inspector).toContainText('2 of 100 cards have no price at their exact printing');
  await expect(inspector.getByRole('row', { name: /Rhystic Study/ })).toBeVisible();
  await expect(inspector.getByRole('button', { name: 'Stop watching' })).toBeVisible();

  // Compare to the cards' cheapest printings.
  await page.getByRole('radio', { name: 'Cheapest' }).click();
  await expect(row).toContainText('−14%');
  await expect(row).toContainText('$10.01');

  await page.getByRole('button', { name: 'Read watched prices' }).click();
  await expect.poll(() => sent).toEqual([{ refresh: true }]);
});

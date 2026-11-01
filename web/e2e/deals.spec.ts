import type { Page } from '@playwright/test';
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
  const modes = page.getByRole('navigation', { name: 'Market views' });
  await expect(modes.getByRole('link', { name: 'Set family' })).toBeVisible();
  await expect(modes.getByRole('link', { name: 'Deals' })).toHaveCount(0);
  // A Deals link without the flag falls back to the default mode.
  await page.goto('/market?subject=deals&code=blb');
  await expect(modes.getByRole('link', { name: 'Set family' })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('searchbox', { name: 'Product name' })).toBeVisible();
});

const jobStub = (id: string, name: string) => ({ id, name, title: name, inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null });
const sseOf = (summary: string, artifacts: unknown[]) => [
  ['status', { status: 'running' }],
  ['result', { summary, artifacts }],
  ['status', { status: 'succeeded' }],
].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');

/** Deals on, nothing watched, the tabs above; `prices` = what reading them returns. */
async function tabsRoutes(page: Page, prices: unknown[] | null, { onJob = (_: unknown) => {}, tabsJson = tabs as unknown, watched = (): unknown[] => [] } = {}) {
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/watched', (r) => r.fulfill({ json: watched() }));
  await page.route('**/api/deals/tabs?*', (r) => r.fulfill({ json: tabsJson }));
  await page.route('**/api/jobs/deals.read_prices', (r) => {
    onJob(r.request().postDataJSON());
    return prices ? r.fulfill({ status: 202, json: jobStub('p1', 'deals.read_prices') }) : r.fulfill({ status: 500, json: { detail: 'stop here' } });
  });
  await page.route('**/api/jobs/p1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sseOf('read', [{ kind: 'json', label: 'prices', data: prices ?? [] }]) }));
}

test('Deals is the watchlist: no mode switch; old ?deals=tabs links land on it', async ({ page }) => {
  await tabsRoutes(page, null);
  await page.goto('/market?subject=deals&deals=tabs');
  await expect(page.getByText('Nothing watched yet')).toBeVisible();
  await expect(page.getByRole('radio', { name: 'Open tabs' })).toHaveCount(0);
  const actions = page.getByRole('toolbar', { name: 'Deals actions' });
  await expect(actions.getByRole('button', { name: 'Read my open tabs' })).toBeVisible();
  await expect(actions.getByRole('button', { name: 'Read watched prices' })).toHaveAttribute('aria-disabled', 'true');
});

test('Read my open tabs: one action reads the tabs, then their prices', async ({ page }) => {
  let sent: unknown = null;
  await tabsRoutes(page, [], { onJob: (b) => { sent = b; } });
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  await expect.poll(() => sent).toEqual({ urls: ['https://manyrealms.com/products/fdn-set', 'https://www.bestbuy.com/product/x/JJ8'], pages: {} });
  const summary = page.getByRole('status').filter({ hasText: '3 of 3 windows read' });
  await expect(summary).toContainText('2 product pages');
  await expect(summary).toContainText('1 page at stores without a recipe yet (shop.example)');
});

test('a warning from the reader is shown plainly', async ({ page }) => {
  await tabsRoutes(page, null, { tabsJson: { ...tabs, windows_read: 1, warnings: ['Only 1 of 3 windows returned tabs. Click into the window with your shopping tabs to bring it to the front, then read again.'] } });
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  await expect(page.getByText('Only 1 of 3 windows returned tabs.')).toBeVisible();
});

test('pages that aren\'t a known product are pinned to look at; a setup error shows once', async ({ page }) => {
  const js = 'Chrome blocks reading open tabs. Turn on Chrome → View → Developer → Allow JavaScript from Apple Events (once), then read again.';
  const prices = [
    { url: 'https://manyrealms.com/products/fdn-set', vendor: 'manyrealms', price: 199.99, currency: 'USD', available: true, title: 'Foundations Commander Set of 5', signal: 'shopify', error: null },
    { url: 'https://www.bestbuy.com/product/x/JJ8', vendor: 'bestbuy', price: null, currency: null, available: null, title: null, signal: '', error: js },
  ];
  await tabsRoutes(page, prices);
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  const pinned = page.getByRole('rowgroup', { name: 'From your open tabs' });
  const set = pinned.getByRole('row', { name: /Foundations Commander Set of 5/ });
  await expect(set).toContainText('$199.99');
  await expect(set).toContainText('Not a product we know');
  await expect(pinned.getByRole('row', { name: /Reign of Dragons/ })).toContainText('Couldn’t read this page');
  await expect(page.getByRole('alert').filter({ hasText: 'Allow JavaScript from Apple Events' })).toHaveCount(1);
  // Dismiss hides a row until the next read; Dismiss all clears the group.
  await set.getByRole('button', { name: /^Dismiss/ }).click();
  await expect(set).toHaveCount(0);
  await pinned.getByRole('button', { name: 'Dismiss all' }).click();
  await expect(pinned).toHaveCount(0);
  await expect(page.getByText('Nothing watched yet')).toBeVisible();
});

const sealedCost = (over: Record<string, unknown> = {}) => ({
  kind: 'sealed', set_code: 'hob', name: 'The Hobbit Play Booster Box', finish: null, category: 'booster_box', subtype: null, release_date: '2023-06-23',
  market: 152.92, market_source: 'tcgplayer', contents: 154.08, exact: 154.08, floor: 140, known_exact: 154.08, known_floor: 140, booster_ev: 0, booster_only: false,
  total_cards: 10, unpriced: 0, notes: [], lines: [], ...over,
});
const tree = { name: 'The Hobbit Play Booster Box', kind: 'box', count: 1, market: 152.92, contents_value: 154.08, contents_kind: 'cards', children: [{ name: 'Play Booster', kind: 'booster_pack', count: 36, market: 4, contents_value: 4.2, contents_kind: 'booster', children: [] }] };

test('pinned products show price vs value; an ambiguous listing is settled in the detail', async ({ page }) => {
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
  await tabsRoutes(page, prices);
  await page.route('**/api/market/product-cost?*', (r) => r.fulfill({ json: sealedCost() }));
  await page.route('**/api/deals/match', (r) => {
    confirmed = r.request().postDataJSON();
    return r.fulfill({ json: { ...prices[1], status: 'confirmed', match: prices[1].candidates![0], candidates: [], note: '', market: 21.47, delta: 2.52, pct: 11.7 } });
  });
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  const pinned = page.getByRole('rowgroup', { name: 'From your open tabs' });
  const row = pinned.getByRole('row', { name: /The Hobbit Play Booster Box/ });
  await expect(row).toContainText('$149.99');
  await expect(row).toContainText('−2%');
  await expect(row).toContainText('$2.93');
  await expect(row).toContainText('$154.08');
  await expect(row.getByRole('button', { name: /^Watch/ })).toBeVisible();
  const ambiguous = pinned.getByRole('row', { name: /Exemplar of Light \(11\)/ });
  await expect(ambiguous).toContainText('Which product is this? Pick it in the detail');
  await ambiguous.getByRole('button', { name: 'Exemplar of Light (11) (Secrets of Strixhaven)', exact: true }).click();
  const detail = page.getByRole('region', { name: 'Exemplar of Light (11) (Secrets of Strixhaven)' });
  await expect(detail).toContainText('that printing is Eager Glyphmage');
  await detail.getByRole('button', { name: 'This one' }).click();
  await expect(pinned.getByRole('row', { name: /Exemplar of Light \(PFDN 11p\)/ })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Exemplar of Light (PFDN 11p)' })).toContainText('you confirmed this');
  expect(confirmed!.url).toBe('https://www.bestbuy.com/product/x/JJ8');
  expect(confirmed!.choice.scryfall_id).toBe('pfdn11p');
});

test('Watch moves a pinned product into the watchlist; two stores are one row', async ({ page }) => {
  const match = { kind: 'sealed', set_code: 'hob', name: 'The Hobbit Play Booster Box', scryfall_id: null, finish: null, price: null };
  const mk = (url: string, price: number, extra = {}) => ({ url, vendor: 'v', price, currency: 'USD', available: true, title: 'The Hobbit - Play Booster Display', signal: 'shopify', error: null,
    kind: 'sealed', status: 'matched', match, candidates: [], note: '', market: 152.92, contents: 154.08, partial: false, delta: -2.93, pct: -1.9, watching: false, ...extra });
  const prices = [mk('https://manyrealms.com/products/fdn-set', 149.99), mk('https://www.bestbuy.com/product/x/JJ8', 139.5)];
  const store = (url: string, name: string, price: number) => ({ url, store: name, price, available: true, read_at: '2026-09-10T12:00:00', read: true, first_price: price, first_at: '2026-09-10T12:00:00', change: null, history: [] });
  const after = [{ product_id: 3, set_code: 'hob', name: 'The Hobbit Play Booster Box', kind: 'sealed', finish: null, category: 'booster_box', subtype: null, release_date: '2023-06-23',
    best_price: 139.5, best_store: 'Best Buy', best_url: prices[1].url, stores: [store(prices[1].url, 'Best Buy', 139.5)] }];
  let body: unknown = null;
  await tabsRoutes(page, prices, { watched: () => (body ? after : []) });
  await page.route('**/api/market/product-cost?*', (r) => r.fulfill({ json: sealedCost() }));
  await page.route('**/api/market/product-tree?*', (r) => r.fulfill({ json: tree }));
  await page.route('**/api/deals/watch', (r) => { body = r.request().postDataJSON(); return r.fulfill({ json: { watching: true, message: 'Watching' } }); });
  await page.goto('/market?subject=deals');
  await page.getByRole('button', { name: 'Read my open tabs' }).click();
  const pinned = page.getByRole('rowgroup', { name: 'From your open tabs' });
  await expect(pinned.getByRole('row')).toHaveCount(2);   // the group heading + one product
  await pinned.getByRole('button', { name: 'The Hobbit Play Booster Box', exact: true }).click();
  const inspector = page.getByRole('region', { name: 'The Hobbit Play Booster Box' });
  await expect(inspector.getByRole('link', { name: /Many Realms/ })).toHaveAttribute('href', 'https://manyrealms.com/products/fdn-set');
  await expect(inspector.getByRole('link', { name: /Best Buy/ })).toHaveAttribute('href', 'https://www.bestbuy.com/product/x/JJ8');
  await expect(inspector).toContainText('Read from your open tab');
  await expect(inspector).toContainText('Play Booster');
  await pinned.getByRole('button', { name: /^Watch/ }).click();
  await expect(pinned).toHaveCount(0);
  const watching = page.getByRole('rowgroup', { name: 'Watching' });
  await expect(watching.getByRole('row', { name: /The Hobbit Play Booster Box/ })).toContainText('$139.50');
  // The other store read from your tabs stays on the watched row, marked as not watched there.
  await expect(inspector.getByRole('button', { name: 'Stop watching' })).toBeVisible();
  await expect(inspector).toContainText('From your open tabs — not watched at this store');
  expect(body).toEqual({ url: 'https://www.bestbuy.com/product/x/JJ8', choice: match, price: 139.5, currency: 'USD' });
});

test('the watchlist: a filterable table with an inspector; read prices again', async ({ page }) => {
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
  await page.goto('/market?subject=deals');
  const table = page.getByRole('table', { name: 'Products' });
  const row = table.getByRole('row', { name: /Nature of the Beast/ });
  await expect(row).toContainText('Cash Cards Unlimited');
  await expect(row).toContainText('$59.99');
  await expect(row).toContainText('−21%');
  await expect(row).toContainText('$15.51');
  await expect(row).toContainText('$90.00+');
  await expect(row).toContainText('cheapest $70.00');
  await expect(row).toContainText('$80.00 cards + $10.00 boosters');
  await expect(page.getByText('2 of 2 watched products · compared to sealed value')).toBeVisible();

  // Search and type filters.
  await page.getByLabel('Product name or set', { exact: true }).fill('frogs');
  await expect(table.getByRole('row')).toHaveCount(2);
  await expect(row).toHaveCount(0);
  await page.getByLabel('Product name or set', { exact: true }).fill('');
  const types = page.getByRole('button', { name: /^Product type/ });
  await expect(types).toContainText('All types');
  await types.click();
  await page.getByRole('checkbox', { name: /^Decks/ }).check();
  await page.keyboard.press('Escape');
  await expect(table.getByRole('row', { name: /Frogs/ })).toHaveCount(0);
  await expect(row).toBeVisible();
  await types.click();
  await page.getByRole('checkbox', { name: /^Decks/ }).uncheck();
  await page.keyboard.press('Escape');

  // Inspector.
  await row.getByRole('button', { name: 'Commander 2013 Deck: Nature of the Beast' }).click();
  const inspector = page.getByRole('region', { name: 'Commander 2013 Deck: Nature of the Beast' });
  await expect(inspector.getByRole('link', { name: /Cash Cards Unlimited/ })).toHaveAttribute('href', store.url);
  await expect(inspector).toContainText('↓ $5.00 since Sep 5');
  await expect(inspector.getByText('Sealed value')).toBeVisible();
  await expect(inspector.getByText('Cards inside, exact printings')).toBeVisible();
  await expect(inspector).toContainText('$80.00');
  await expect(inspector).toContainText('Total, cheapest');
  await expect(inspector).toContainText('2 of 100 cards have no value at their exact printing');
  await expect(inspector.getByRole('row', { name: /Rhystic Study/ })).toBeVisible();
  await expect(inspector.getByRole('button', { name: 'Stop watching' })).toBeVisible();

  // Compare to the cards' cheapest printings.
  await page.getByRole('radio', { name: 'Cheapest' }).click();
  await expect(row).toContainText('−14%');
  await expect(row).toContainText('$10.01');

  await page.getByRole('button', { name: 'Read watched prices' }).click();
  await expect.poll(() => sent).toEqual([{ refresh: true }]);
});

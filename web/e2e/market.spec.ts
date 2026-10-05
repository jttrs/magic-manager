import { expect, fixtures, test } from './support';

const products = {
  code: 'blb', name: 'Bloomburrow',
  products: [
    { set_code: 'blb', name: 'Bloomburrow Play Booster Box', category: 'booster_box', subtype: 'play', release_date: null, tcgplayer_url: null },
    { set_code: 'blb', name: 'Bloomburrow Bundle', category: 'bundle', subtype: null, release_date: null, tcgplayer_url: 'https://example.test/bundle' },
  ],
};
const values = [
  { set_code: 'blb', name: 'Bloomburrow Play Booster Box', sealed_market: 120, market_source: 'tcgcsv', contents_value: 100, exact_singles: 100, floor_singles: 100, booster_only: true, coverage: 1, notes: [], error: null },
  { set_code: 'blb', name: 'Bloomburrow Bundle', sealed_market: 40, market_source: 'tcgcsv', contents_value: 55.5, exact_singles: 3, floor_singles: 2, booster_only: false, coverage: 1, notes: [], error: null },
];
const tree = {
  name: 'Bloomburrow Bundle', kind: 'sealed', count: 1, market: 40, contents_value: 55.5, contents_kind: 'sum-of-children',
  children: [{ name: 'Bloomburrow Play Booster Pack', kind: 'sealed', count: 9, market: 4.5, contents_value: 5, contents_kind: 'ev', children: [] }],
};

test('sealed products are priced by a job and drill into their contents', async ({ page }) => {
  const sse = [
    ['status', { status: 'running' }],
    ['progress', { done: 1, total: 2, message: 'Bloomburrow Bundle', level: 'info' }],
    ['result', { summary: 'Bloomburrow · 2 products valued', artifacts: [{ kind: 'json', label: 'values', data: values }] }],
    ['status', { status: 'succeeded' }],
  ].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
  let submitted: unknown = null;
  await page.route('**/api/jobs/market.value_family', (r) => {
    submitted = r.request().postDataJSON();
    return r.fulfill({ status: 202, json: { id: 'mv1', name: 'market.value_family', title: 'Value sealed products', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } });
  });
  await page.route('**/api/jobs/mv1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse }));
  await page.route('**/api/market/products?*', (r) => r.fulfill({ json: products }));
  await page.route('**/api/market/product-tree?*', (r) => r.fulfill({ json: tree }));

  await page.goto('/market?code=blb');
  await expect(page.getByRole('heading', { level: 1, name: 'Bloomburrow' })).toBeVisible();
  const bundle = page.getByRole('row', { name: /Bloomburrow Bundle/ });
  await expect(bundle).toContainText('$40.00');
  await expect(bundle).toContainText('$55.50');
  await expect(bundle).toContainText('+$15.50');
  await expect(page.getByRole('row', { name: /Play Booster Box/ })).toContainText('−$20.00');
  expect(submitted).toEqual({ code: 'blb' });

  await page.getByRole('button', { name: 'Bloomburrow Bundle' }).click();
  await expect(page.getByRole('list', { name: 'Bloomburrow Bundle contents' })).toContainText('9× Bloomburrow Play Booster Pack');
  await expect(page.getByText('Fixed cards: $3.00')).toBeVisible();
});

test('a deck costs out three ways and its buy list uses the cheapest printings', async ({ page }) => {
  const deck = fixtures.decks[0];
  await page.route('**/api/market/deck?*', (r) => r.fulfill({ json: {
    slug: deck.slug, sealed_product: 'The Precon', sealed: 30, scratch: 50, with_collection: 12, scratch_floor: 40, with_collection_floor: 9, coverage: 1, unpriced: 0, total_need: 3,
    lines: [
      { scryfall_id: 'deck-print', finish: 'nonfoil', name: 'Pricey Card', set_code: 'abc', collector_number: '1', need: 2, free: 0, buy: 2, unit_usd: 6, floor_usd: 4.5, floor_set_code: 'xyz', floor_collector_number: '9', floor_scryfall_id: 'cheap-print' },
      { scryfall_id: 'owned', finish: 'nonfoil', name: 'Owned Card', set_code: 'abc', collector_number: '2', need: 1, free: 3, buy: 0, unit_usd: 1, floor_usd: 1, floor_set_code: 'abc', floor_collector_number: '2', floor_scryfall_id: 'owned' },
    ],
  } }));
  await page.goto(`/market?subject=deck&deck=${deck.slug}`);
  const ledger = page.getByRole('table', { name: 'Three ways to get this deck' });
  await expect(ledger.getByRole('row', { name: /Buy it sealed/ })).toContainText('$30.00');
  await expect(ledger.getByRole('row', { name: /free cards first/ })).toContainText('$9.00lowest');
  await expect(page.getByRole('table', { name: /To buy/ })).toContainText('XYZ 9');
  await page.getByRole('button', { name: 'Copy ManaPool list' }).click();
  await expect(page.getByText('Copied 1 line', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe('1 cheap-print [manapool]');
});

test('Decks links a deck to its cost in Market', async ({ page }) => {
  const detail = fixtures.deckDetail;
  await page.route('**/api/market/deck?*', (r) => r.fulfill({ json: { slug: detail.deck.slug, sealed_product: null, sealed: null, scratch: 1, with_collection: 1, scratch_floor: 1, with_collection_floor: 1, coverage: 1, unpriced: 0, total_need: 1, lines: [] } }));
  await page.goto(`/decks?deck=${detail.deck.slug}`);
  await page.getByRole('toolbar', { name: 'Deck actions' }).getByRole('button', { name: 'Cost to build' }).click();
  await expect(page).toHaveURL(new RegExp(`/market\\?subject=deck&deck=${detail.deck.slug}`));
  await expect(page.getByRole('table', { name: 'Three ways to get this deck' })).toBeVisible();
});

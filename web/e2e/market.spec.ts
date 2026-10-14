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
  await expect(page.getByText('At the cheapest printing of each card: $2.00')).toBeVisible();
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

test('cards show the foil premium, filter under a cap and sort smallest first', async ({ page }) => {
  const base = { oracle_id: 'o', rarity: 'rare', type_line: null, image_uri: null, is_chase: false, floor_usd: 1, floor_set_code: 'blb', floor_collector_number: '1', owned: 0, treatment: '' };
  const cards = [
    { ...base, scryfall_id: 'p1', name: 'Pricey Foil', set_code: 'blb', collector_number: '1', finishes: ['nonfoil', 'foil'], price_usd: 1, price_usd_foil: 5, foil_gap_status: 'ok', foil_gap_pct: 4, foil_gap_usd: 4 },
    { ...base, scryfall_id: 'p2', name: 'Cheap Foil', set_code: 'blb', collector_number: '2', finishes: ['nonfoil', 'foil'], price_usd: 2, price_usd_foil: 2.2, foil_gap_status: 'ok', foil_gap_pct: 0.1, foil_gap_usd: 0.2 },
    { ...base, scryfall_id: 'p3', name: 'Surge Card', set_code: 'blb', collector_number: '3', finishes: ['nonfoil', 'foil'], price_usd: 1, price_usd_foil: 9, foil_gap_status: 'fancy', foil_gap_pct: null, foil_gap_usd: null, treatment: 'ff' },
  ];
  await page.route('**/api/market/cards?*', (r) => r.fulfill({ json: { code: 'blb', name: 'Bloomburrow', cards } }));
  await page.goto('/market?code=blb&tab=cards');
  await expect(page.getByRole('row', { name: /Pricey Foil/ })).toContainText('+400%');
  await expect(page.getByRole('row', { name: /Surge Card/ })).toContainText('fancy foil');

  await page.goto('/market?code=blb&tab=cards&foilMax=25&sort=foil');
  const rows = page.getByRole('table').getByRole('row');
  await expect(rows).toHaveCount(2); // header + Cheap Foil
  await expect(page.getByRole('row', { name: /Cheap Foil/ })).toContainText('+10%');
  await expect(page.getByRole('radio', { name: 'Under 25%' })).toBeChecked();
});

test('the inspector shows the cheapest printing among synced sets and can recheck all printings', async ({ page }) => {
  const bodies: unknown[] = [];
  await page.route('**/api/cards/floors', (r) => {
    const body = r.request().postDataJSON() as { scryfall_ids: string[]; live: boolean };
    bodies.push(body);
    const nonfoil = body.live ? { usd: 0.1, set_code: 'sld', collector_number: '7', scryfall_id: 'any' } : { usd: 0.5, set_code: 'm21', collector_number: '3', scryfall_id: 'loc' };
    return r.fulfill({ json: { live: body.live, floors: [{ scryfall_id: body.scryfall_ids[0], oracle_id: 'o', name: 'X', nonfoil, foil: null }] } });
  });
  await page.goto('/collection?families=%5B%22blb%22%5D');
  await page.getByRole('button', { name: /^Inspect / }).first().click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('$0.50 nonfoil · M21 #3');
  await expect(dialog).toContainText('among synced sets');
  await dialog.getByRole('button', { name: 'Recheck for cheapest' }).click();
  await expect(dialog).toContainText('$0.10 nonfoil · SLD #7');
  await expect(dialog).toContainText(/checked all printings · \d{1,2}:\d{2}/);
  expect(bodies.map((b) => (b as { live: boolean }).live)).toEqual([false, true]);
});

test('a deck’s cheapest printings can be checked across every set', async ({ page }) => {
  const deck = fixtures.decks[0];
  const seen: string[] = [];
  await page.route('**/api/market/deck?*', (r) => {
    const live = new URL(r.request().url()).searchParams.get('live') === 'true';
    seen.push(String(live));
    return r.fulfill({ json: { slug: deck.slug, sealed_product: null, sealed: null, scratch: 6, with_collection: 6, scratch_floor: live ? 1 : 4.5, with_collection_floor: live ? 1 : 4.5, coverage: 1, unpriced: 0, total_need: 1, live,
      lines: [{ scryfall_id: 'd', finish: 'nonfoil', name: 'Pricey Card', set_code: 'abc', collector_number: '1', need: 1, free: 0, buy: 1, unit_usd: 6, floor_usd: live ? 1 : 4.5, floor_set_code: 'xyz', floor_collector_number: '9', floor_scryfall_id: 'c' }] } });
  });
  await page.goto(`/market?subject=deck&deck=${deck.slug}`);
  await expect(page.getByText('Cheapest printings from the sets you’ve synced.')).toBeVisible();
  await page.getByRole('button', { name: 'Check every set on Scryfall' }).click();
  await expect(page.getByText('Cheapest printings checked across every set on Scryfall.')).toBeVisible();
  await expect(page).toHaveURL(/live=true/);
  await expect(page.getByRole('table', { name: 'Three ways to get this deck' })).toContainText('$1.00');
  expect(seen).toEqual(['false', 'true']);
});

const jobRow = { id: 'mv1', name: 'market.value_family', title: 'Value sealed products', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null };
const sseBody = (rows: unknown) =>
  [
    ['status', { status: 'running' }],
    ['result', { summary: 'done', artifacts: [{ kind: 'json', label: 'values', data: rows }] }],
    ['status', { status: 'succeeded' }],
  ].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');

test('switching to Cards mid-pricing keeps following the same job instead of starting another', async ({ page }) => {
  let submits = 0;
  let streams = 0;
  let release: () => void = () => {};
  const held = new Promise<void>((r) => (release = r));
  await page.route('**/api/jobs/market.value_family', (r) => {
    submits += 1;
    return r.fulfill({ status: 202, json: { ...jobRow, id: `mv${submits}` } });
  });
  await page.route('**/api/jobs/mv1/events', async (r) => {
    streams += 1;
    if (streams === 1) {
      await held; // the first visit never sees the result
      return r.abort().catch(() => {});
    }
    return r.fulfill({ status: 200, contentType: 'text/event-stream', body: sseBody(values) });
  });
  await page.route('**/api/market/products?*', (r) => r.fulfill({ json: products }));
  await page.route('**/api/market/cards?*', (r) => r.fulfill({ json: { code: 'blb', name: 'Bloomburrow', cards: [] } }));

  await page.goto('/market?code=blb');
  await expect.poll(() => streams).toBe(1);
  await page.getByRole('radio', { name: 'Cards' }).click();
  await expect(page).toHaveURL(/tab=cards/);
  await page.getByRole('radio', { name: 'Sealed' }).click();
  await expect(page.getByRole('row', { name: /Bloomburrow Bundle/ })).toContainText('$55.50');
  expect(submits).toBe(1);
  release();
});

test('products that failed to price can be priced again, and are not kept across reloads', async ({ page }) => {
  let submits = 0;
  const failedOnce = [values[0], { set_code: 'blb', name: 'Bloomburrow Bundle', error: 'timeout' }];
  await page.route('**/api/jobs/market.value_family', (r) => {
    submits += 1;
    return r.fulfill({ status: 202, json: { ...jobRow, id: `mv${submits}` } });
  });
  await page.route('**/api/jobs/mv1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sseBody(failedOnce) }));
  await page.route('**/api/jobs/mv2/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sseBody(values) }));
  await page.route('**/api/market/products?*', (r) => r.fulfill({ json: products }));

  await page.goto('/market?code=blb');
  await expect(page.getByRole('row', { name: /Bloomburrow Bundle/ })).toContainText('Couldn’t price: timeout');
  expect(await page.evaluate(() => localStorage.getItem('mm.market.values.v3.blb'))).toBeNull();
  await page.getByRole('button', { name: 'Price again' }).click();
  await expect(page.getByRole('row', { name: /Bloomburrow Bundle/ })).toContainText('$55.50');
  expect(submits).toBe(2);
  expect(await page.evaluate(() => localStorage.getItem('mm.market.values.v3.blb'))).not.toBeNull();
});

test('a deck total with unpriced cards is marked partial and never the lowest', async ({ page }) => {
  const deck = fixtures.decks[0];
  await page.route('**/api/market/deck?*', (r) => r.fulfill({ json: {
    slug: deck.slug, sealed_product: null, sealed: null, scratch: 3, with_collection: 3, scratch_floor: 5, with_collection_floor: 5, coverage: 0.5, unpriced: 1, floor_unpriced: 0, total_need: 2,
    lines: [{ scryfall_id: 'x', finish: 'foil', name: 'Foil Only', set_code: 'sld', collector_number: '1', need: 1, free: 0, buy: 1, unit_usd: null, floor_usd: 2, floor_set_code: 'abc', floor_collector_number: '2', floor_scryfall_id: 'y', floor_finish: 'nonfoil' }],
  } }));
  await page.goto(`/market?subject=deck&deck=${deck.slug}`);
  const row = page.getByRole('table', { name: 'Three ways to get this deck' }).getByRole('row', { name: /Buy every card/ });
  await expect(row).toContainText('$3.00+');
  await expect(row).toContainText('$5.00lowest');
  await expect(page.getByText(/1 card without a price at the deck’s printing/)).toBeVisible();
});

test('Try again after a failed pricing job, or one the server lost, starts a new job', async ({ page }) => {
  let submits = 0;
  await page.route('**/api/jobs/market.value_family', (r) => {
    submits += 1;
    return r.fulfill({ status: 202, json: { ...jobRow, id: `mv${submits}` } });
  });
  const failedSse = [['status', { status: 'running' }], ['error', { error: 'MTGJSON is down' }], ['status', { status: 'failed' }]]
    .map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
  await page.route('**/api/jobs/mv1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: failedSse }));
  await page.route('**/api/jobs/mv2/events', (r) => r.fulfill({ status: 404, json: { detail: 'unknown job' } }));
  await page.route('**/api/jobs/mv3/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sseBody(values) }));
  await page.route('**/api/market/products?*', (r) => r.fulfill({ json: products }));

  await page.goto('/market?code=blb');
  const alert = page.getByRole('alert');
  await expect(alert).toContainText('MTGJSON is down');
  await alert.getByRole('button', { name: 'Try again' }).click();
  await expect(alert).toContainText('the server lost track of this job');
  await alert.getByRole('button', { name: 'Try again' }).click();
  await expect(page.getByRole('row', { name: /Bloomburrow Bundle/ })).toContainText('$55.50');
  expect(submits).toBe(3);
});

test('product detail shows both printings’ totals, marks a partial one, and names booster EV only when there are boosters', async ({ page }) => {
  const rows = [
    { set_code: 'blb', name: 'Bloomburrow Bundle', sealed_market: 40, contents_value: 55.5, exact_singles: 30, floor_singles: 20, booster_ev: 25, booster_only: false, unpriced_cards: 2, total_cards: 10, coverage: 1, notes: [], error: null },
    { set_code: 'blb', name: 'Bloomburrow Play Booster Box', sealed_market: 50, contents_value: 45, exact_singles: 45, floor_singles: 30, booster_ev: null, booster_only: false, unpriced_cards: 0, total_cards: 60, coverage: 1, notes: [], error: null },
  ];
  await page.route('**/api/jobs/market.value_family', (r) => r.fulfill({ status: 202, json: jobRow }));
  await page.route('**/api/jobs/mv1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sseBody(rows) }));
  await page.route('**/api/market/products?*', (r) => r.fulfill({ json: products }));
  await page.route('**/api/market/product-tree?*', (r) => r.fulfill({ json: tree }));

  await page.goto('/market?code=blb');
  await page.getByRole('button', { name: 'Bloomburrow Bundle' }).click();
  const bundle = page.getByText(/At each card’s own printing/);
  await expect(bundle).toContainText('$30.00+');
  await expect(bundle).toContainText('At the cheapest printing of each card: $20.00');
  await expect(bundle).toContainText('(boosters at their expected value)');
  await page.getByRole('button', { name: 'Bloomburrow Play Booster Box' }).click();
  const box = page.getByText(/At each card’s own printing: \$45\.00/);
  await expect(box).not.toContainText('boosters');
  await expect(box).not.toContainText('+');
});

import { expect, test } from './support';

const jobStub = (id: string, name: string) => ({ id, name, title: name, inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null });
const sseOf = (summary: string, artifacts: unknown[]) => [
  ['status', { status: 'running' }],
  ['result', { summary, artifacts }],
  ['status', { status: 'succeeded' }],
].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');

const NAME = 'Commander 2013 Deck: Nature of the Beast';
const cash = {
  url: 'https://cashcards.example/c13', store: 'Cash Cards Unlimited', price: 59.99, available: true, read_at: '2026-09-10T12:00:00', read: true,
  first_price: 64.99, first_at: '2026-09-05T12:00:00', change: -5, low: 59.99, high: 69.99,
  history: [{ price: 64.99, at: '2026-09-05T12:00:00' }, { price: 69.99, at: '2026-09-07T12:00:00' }, { price: 59.99, at: '2026-09-10T12:00:00' }],
};
const realms = {
  url: 'https://manyrealms.example/c13', store: 'Many Realms', price: 66, available: true, read_at: '2026-09-10T12:00:00', read: true,
  first_price: 70, first_at: '2026-09-06T12:00:00', change: -4, low: 66, high: 70,
  history: [{ price: 70, at: '2026-09-06T12:00:00' }, { price: 66, at: '2026-09-10T12:00:00' }],
};
const product = (over: Record<string, unknown> = {}) => ({
  product_id: 7, set_code: 'c13', name: NAME, kind: 'sealed', finish: null, category: 'deck', subtype: null, release_date: '2013-11-01',
  best_price: 59.99, best_store: cash.store, best_url: cash.url, stores: [cash, realms], target: null, target_price: null, target_met: null, ...over,
});
const other = { ...product(), product_id: 8, name: 'Secret Lair Drop: Frogs', kind: 'sld', set_code: 'sld', category: null, best_price: 30, best_store: 'Frog Shop', best_url: 'https://frogs.example/x',
  stores: [{ ...cash, url: 'https://frogs.example/x', store: 'Frog Shop', price: 30, history: [], change: null }] };
const cost = { kind: 'sealed', set_code: 'c13', name: NAME, category: 'deck', release_date: '2013-11-01', market: 75.5, market_source: 'tcgplayer', contents: 90, exact: 90, floor: 70,
  known_exact: 80, known_floor: 62, booster_ev: 0, total_cards: 100, unpriced: 0, notes: [], lines: [] };

test('Watching: set a target, see rows that meet it, filter to them, and read the history', async ({ page }) => {
  let watched = [product(), other];
  const puts: unknown[] = [];
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/watched', (r) => r.fulfill({ json: watched }));
  await page.route('**/api/market/product-cost?*', (r) => r.fulfill({ json: cost }));
  await page.route('**/api/market/product-tree?*', (r) => r.fulfill({ json: { name: NAME, kind: 'deck', count: 1, market: 75.5, contents_value: 90, contents_kind: 'cards', children: [] } }));
  await page.route('**/api/deals/target', async (r) => {
    const body = r.request().postDataJSON() as { mode: 'price' | 'pct_under'; value: number };
    puts.push(body);
    watched = [product({ target: { ...body, set_at: '2026-09-10' }, target_price: body.mode === 'price' ? body.value : null }), other];
    return r.fulfill({ json: { ...body, set_at: '2026-09-10' } });
  });
  await page.goto(`/market?subject=deals&deals=watching&item=${encodeURIComponent(`sealed|c13|${NAME}|`)}`);

  const inspector = page.getByRole('region', { name: NAME });
  await expect(inspector.getByText('No target yet.')).toBeVisible();

  // History: a chart with an accessible summary, per-store first/low/high/now, and every reading.
  await expect(inspector.getByRole('img', { name: /Prices at 2 stores from Sep 5 to Sep 10; lowest \$59\.99 at Cash Cards Unlimited/ })).toBeVisible();
  const stats = inspector.getByRole('table', { name: 'First, lowest, highest and latest price at each store' });
  await expect(stats.getByRole('row', { name: /Cash Cards Unlimited/ })).toContainText('$64.99$59.99$69.99$59.99');
  await inspector.getByText('All 5 readings').click();
  await expect(inspector.getByRole('table', { name: 'Every price read, newest first' }).getByRole('row')).toHaveCount(6);

  // A % target is worked out from the sealed price: 20% under $75.50 = $60.40 → met by $59.99.
  await inspector.getByLabel('% under sealed price').check();
  await inspector.getByLabel('Percent under').fill('20');
  await inspector.getByRole('button', { name: 'Set target' }).click();
  await expect.poll(() => puts).toEqual([{ product_id: 7, mode: 'pct_under', value: 20 }]);
  await expect(inspector.getByText('Target met')).toBeVisible();
  await expect(inspector).toContainText('Cash Cards Unlimited has it at $59.99. Your target is $60.40 (20% under the sealed price).');
  await expect(inspector.getByText('target $60.40')).toBeVisible();

  const table = page.getByRole('table', { name: 'Products' });
  await expect(table.getByRole('row', { name: /Nature of the Beast/ })).toContainText('at target $60.40');
  await page.getByRole('button', { name: 'At or under target' }).click();
  await expect(table.getByRole('row', { name: /Frogs/ })).toHaveCount(0);
  await expect(table.getByRole('row', { name: /Nature of the Beast/ })).toBeVisible();
});

test('Watching: reading prices reports targets it newly met', async ({ page }) => {
  const watched = [product({ target: { mode: 'price', value: 60, set_at: '2026-09-10' }, target_price: 60, target_met: true }), other];
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/watched', (r) => r.fulfill({ json: watched }));
  await page.route('**/api/market/product-cost?*', (r) => r.fulfill({ json: cost }));
  await page.route('**/api/jobs/deals.watchlist', (r) => r.fulfill({ status: 202, json: jobStub('w1', 'deals.watchlist') }));
  const met = [{ product_id: 7, name: NAME, kind: 'sealed', set_code: 'c13', price: 59.99, store: cash.store, url: cash.url, target_price: 60 }];
  await page.route('**/api/jobs/w1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream',
    body: sseOf('2 watched products · 3 of 3 prices read · 1 hit its target', [{ kind: 'json', label: 'watchlist', data: watched }, { kind: 'json', label: 'errors', data: [] }, { kind: 'json', label: 'newly_met', data: met }]) }));
  await page.goto('/market?subject=deals&deals=watching');
  await page.getByRole('button', { name: 'Read watched prices' }).click();
  const notice = page.getByRole('status').filter({ hasText: '1 product hit its target' });
  await expect(notice).toContainText('$59.99');
  await expect(notice.getByRole('link', { name: /at Cash Cards Unlimited/ })).toHaveAttribute('href', cash.url);
  await notice.getByRole('button', { name: NAME }).click();
  await expect(page.getByRole('region', { name: NAME }).getByText('Target met')).toBeVisible();
  await notice.getByRole('button', { name: 'Dismiss' }).click();
  await expect(page.getByText('1 product hit its target')).toHaveCount(0);
});

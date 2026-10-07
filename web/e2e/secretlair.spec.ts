import { expect, test } from './support';

const drops = {
  total: 423,
  drops: [
    { name: 'Garfield: As Intended', release_date: '2026-06-16', editions: [
      { finish: 'nonfoil', sealed_name: 'Secret Lair Drop Garfield As Intended', tcgplayer_url: 'https://www.tcgplayer.com/product/694967' },
      { finish: 'foil', sealed_name: 'Secret Lair Drop Garfield As Intended Foil', tcgplayer_url: 'https://www.tcgplayer.com/product/694968' },
    ] },
    { name: 'Cats of Chaos', release_date: '2026-06-16', editions: [{ finish: 'nonfoil', sealed_name: null, tcgplayer_url: null }] },
  ],
};

const line = (name: string, cn: string, unit: number, floor: number, bonus = false) => ({
  scryfall_id: `id-${cn}`, finish: 'nonfoil', name, set_code: 'sld', collector_number: cn, need: 1, free: 0, buy: 1,
  unit_usd: unit, floor_usd: floor, floor_set_code: null, floor_collector_number: null, floor_scryfall_id: `id-${cn}`, bonus,
});

const costs: Record<string, object> = {
  'Garfield: As Intended': {
    kind: 'sld', set_code: 'sld', name: 'Garfield: As Intended', finish: 'nonfoil', category: 'secret_lair', release_date: '2026-06-16',
    market: 30, market_source: 'tcgcsv', contents: 45, exact: 45, floor: 10, known_exact: 45, known_floor: 10, booster_ev: null,
    total_cards: 2, unpriced: 0, notes: [], sealed_name: 'Secret Lair Drop Garfield As Intended',
    lines: [line('Counterspell', '2664', 42, 8), line('Clone', '7164', 3, 2, true)],
  },
  'Cats of Chaos': {
    kind: 'sld', set_code: 'sld', name: 'Cats of Chaos', finish: 'nonfoil', category: 'secret_lair', release_date: '2026-06-16',
    market: 50, market_source: 'tcgcsv', contents: 40, exact: 40, floor: 20, known_exact: 40, known_floor: 20, booster_ev: null,
    total_cards: 1, unpriced: 0, notes: [], sealed_name: null, lines: [line('Sol Ring', '1', 40, 20)],
  },
};

test.beforeEach(async ({ page }) => {
  await page.route('**/api/market/secret-lair?*', (r) => r.fulfill({ json: drops }));
  await page.route('**/api/market/product-cost?*', (r) => {
    const name = new URL(r.request().url()).searchParams.get('name')!;
    return r.fulfill({ json: costs[name] });
  });
});

test('Secret Lair lists drops by biggest discount vs the cards inside', async ({ page }) => {
  await page.goto('/market?subject=sld');
  await expect(page.getByRole('heading', { name: 'Secret Lair', exact: true })).toBeVisible();
  const rows = page.locator('tbody th[scope="row"] button[data-drop]');
  await expect(rows).toHaveText(['Garfield: As Intended', 'Cats of Chaos']);
  await expect(page.getByRole('row', { name: /Garfield/ })).toContainText('−33%');
  await expect(page.getByRole('row', { name: /Cats of Chaos/ })).toContainText('+25%');

  await page.getByRole('radio', { name: 'Cheapest' }).click();
  await expect(page.getByRole('row', { name: /Garfield/ })).toContainText('+200%');
  await expect(rows).toHaveText(['Cats of Chaos', 'Garfield: As Intended']);

  await page.getByRole('searchbox', { name: 'Search' }).fill('garf');
  await expect(rows).toHaveText(['Garfield: As Intended']);
});

test('a drop opens its worth, bonus card and cards; Watch needs the deals flag', async ({ page }) => {
  await page.goto('/market?subject=sld');
  await page.getByRole('button', { name: 'Garfield: As Intended' }).click();
  const worth = page.getByRole('region', { name: 'What it’s worth' });
  await expect(worth).toContainText('Sealed price');
  await expect(worth).toContainText('Includes the bonus card: Clone.');
  await expect(page.getByRole('row', { name: /Clone/ })).toContainText('bonus');
  await expect(page.getByRole('link', { name: /TCGplayer/ })).toHaveAttribute('href', 'https://www.tcgplayer.com/product/694967');
  await expect(page.getByRole('button', { name: 'Watch' })).toHaveCount(0);
});

test('with the deals flag: Watch tracks the drop at its TCGplayer page', async ({ page }) => {
  let body: { url: string; choice: { kind: string; name: string; finish: string }; price: number } | null = null;
  let watched: object[] = [];
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/deals/watched', (r) => r.fulfill({ json: watched }));
  await page.route('**/api/deals/watch', (r) => {
    body = r.request().postDataJSON();
    watched = [{ set_code: 'sld', name: 'Garfield: As Intended', kind: 'sld', finish: 'nonfoil', scryfall_id: null, category: 'secret_lair', subtype: 'nonfoil', release_date: null, market: null, contents: null, partial: false, best_price: 30, best_store: 'tcgplayer.com', best_url: body!.url, delta: null, pct: null, stores: [{ url: body!.url, store: 'tcgplayer.com', price: 30, available: null, read_at: '2026-10-06', read: false, first_price: 30, first_at: '2026-10-06', change: 0, history: [] }], error: null }];
    return r.fulfill({ json: { watching: true, message: 'Watching' } });
  });
  await page.goto('/market?subject=sld');
  await expect(page.getByRole('radio', { name: 'Deals' })).toBeVisible();
  await page.getByRole('button', { name: 'Garfield: As Intended' }).click();
  await page.getByRole('button', { name: 'Watch' }).click();
  await expect(page.getByRole('button', { name: 'Stop watching' })).toBeVisible();
  expect(body).toMatchObject({ url: 'https://www.tcgplayer.com/product/694967', choice: { kind: 'sld', name: 'Garfield: As Intended', finish: 'nonfoil' }, price: 30 });
  await expect(page.getByRole('row', { name: /Garfield/ })).toContainText('watching');
});

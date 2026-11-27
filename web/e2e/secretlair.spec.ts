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

const line = (name: string, cn: string, unit: number, floor: number, bonus: 'named' | null = null) => ({
  scryfall_id: `id-${cn}`, finish: 'nonfoil', name, set_code: 'sld', collector_number: cn, need: 1, free: 0, buy: 1,
  unit_usd: unit, floor_usd: floor, floor_set_code: null, floor_collector_number: null, floor_scryfall_id: `id-${cn}`, bonus,
});

const costs: Record<string, object> = {
  'Garfield: As Intended': {
    kind: 'sld', set_code: 'sld', name: 'Garfield: As Intended', finish: 'nonfoil', category: 'secret_lair', release_date: '2026-06-16',
    market: 30, market_source: 'tcgcsv', contents: 45, exact: 45, floor: 10, known_exact: 45, known_floor: 10, booster_ev: null,
    total_cards: 2, unpriced: 0, floor_unpriced: 0, has_bonus: true, prices_at: '2026-11-12T08:00:00', preorder: false, notes: [], sealed_name: 'Secret Lair Drop Garfield As Intended',
    lines: [line('Counterspell', '2664', 42, 8), line('Clone', '7164', 3, 2, 'named')],
  },
  'Cats of Chaos': {
    kind: 'sld', set_code: 'sld', name: 'Cats of Chaos', finish: 'nonfoil', category: 'secret_lair', release_date: '2026-06-16',
    market: 50, market_source: 'tcgcsv', contents: 40, exact: 40, floor: 20, known_exact: 40, known_floor: 20, booster_ev: null,
    total_cards: 1, unpriced: 0, floor_unpriced: 0, has_bonus: false, prices_at: '2026-11-14T08:00:00', preorder: true, notes: [], sealed_name: null, lines: [line('Sol Ring', '1', 40, 20)],
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

  await page.getByRole('searchbox', { name: 'Drop name' }).fill('garf');
  await expect(rows).toHaveText(['Garfield: As Intended']);
});

test('Secret Lair: the live count sits in the sheet header, and the header sort reorders the drops', async ({ page }) => {
  await page.goto('/market?subject=sld');
  const rows = page.locator('tbody th[scope="row"] button[data-drop]');
  await expect(rows).toHaveCount(2);
  // the header prints no count line, and no tagline
  await expect(page.getByText('The newest drops: sealed value')).toHaveCount(0);
  await page.getByRole('button', { name: /^Sort: Biggest discount %/ }).click();
  await page.getByRole('menuitemradio', { name: 'Name' }).click();
  await expect(rows).toHaveText(['Cats of Chaos', 'Garfield: As Intended']);
  await expect(page).toHaveURL(/ssort=name/);
});

test('a drop opens its worth, bonus card and cards; Watch needs the deals flag', async ({ page }) => {
  await page.goto('/market?subject=sld');
  await page.getByRole('button', { name: 'Garfield: As Intended' }).click();
  const worth = page.getByRole('region', { name: 'What it’s worth' });
  await expect(worth).toContainText('Sealed value');
  await expect(worth).toContainText('Guaranteed cards, exact printings');
  await expect(worth).toContainText('Guaranteed cards, cheapest printings');
  await expect(worth).toContainText('Bonus cards aren’t counted.');
  await expect(page.getByRole('region', { name: 'Bonus' })).toContainText('Clone');
  await expect(page.getByRole('region', { name: 'Bonus' })).toContainText('isn’t in any total');
  await expect(page.getByRole('link', { name: /TCGplayer/ })).toHaveAttribute('href', 'https://www.tcgplayer.com/product/694967');
  await expect(page.getByRole('button', { name: 'Watch' })).toHaveCount(0);
});

test('Secret Lair: Exact and Cheapest columns, the compared one marked; header says when prices are from', async ({ page }) => {
  await page.goto('/market?subject=sld');
  const head = page.getByRole('columnheader');
  await expect(head).toContainText(['Drop', 'Sealed', 'Exact', 'Cheapest', 'Gap']);
  await expect(page.getByRole('columnheader', { name: /Exact/ })).toContainText('the Gap is measured against');
  await expect(page.getByRole('columnheader', { name: /Cheapest/ })).not.toContainText('the Gap is measured against');
  const garfield = page.getByRole('row', { name: /Garfield/ });
  await expect(garfield).toContainText('$45.00');
  await expect(garfield).toContainText('$10.00');
  await expect(garfield).toContainText('+ bonus');
  await expect(page.getByRole('row', { name: /Cats of Chaos/ })).not.toContainText('+ bonus');
  await page.getByRole('radio', { name: 'Cheapest' }).click();
  await expect(page.getByRole('columnheader', { name: /Cheapest/ })).toContainText('the Gap is measured against');
});

test('Secret Lair: a preorder cost is tagged under the drop name', async ({ page }) => {
  await page.goto('/market?subject=sld');
  await expect(page.getByRole('row', { name: /Cats of Chaos/ })).toContainText('preorder');
  await expect(page.getByRole('row', { name: /Garfield/ })).not.toContainText('preorder');
});

test('Secret Lair: a row twirls open to its card tiles, bonus apart', async ({ page }) => {
  await page.goto('/market?subject=sld');
  const garfield = page.getByRole('row', { name: /Garfield/ });
  const toggle = garfield.getByRole('button', { name: 'Show cards' });
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await toggle.click();
  await expect(garfield.getByRole('button', { name: 'Hide cards' })).toHaveAttribute('aria-expanded', 'true');
  const tiles = page.getByRole('region', { name: 'Guaranteed cards' });
  await expect(tiles.getByText('Counterspell')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Bonus' }).getByText('Clone')).toBeVisible();
  await garfield.getByRole('button', { name: 'Hide cards' }).click();
  await expect(tiles).toHaveCount(0);
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
  await expect(page.getByRole('navigation', { name: 'Market views' }).getByRole('link', { name: 'Deals' })).toBeVisible();
  await page.getByRole('button', { name: 'Garfield: As Intended' }).click();
  await page.getByRole('button', { name: 'Watch' }).click();
  await expect(page.getByRole('button', { name: 'Stop watching' })).toBeVisible();
  expect(body).toMatchObject({ url: 'https://www.tcgplayer.com/product/694967', choice: { kind: 'sld', name: 'Garfield: As Intended', finish: 'nonfoil' }, price: 30 });
  await expect(page.getByRole('row', { name: /Garfield/ })).toContainText('watching');
});

test('a watched foil-only drop shows as watched (the watchlist drops its " Foil Edition")', async ({ page }) => {
  const foilOnly = { total: 1, drops: [{ name: 'Alien Auroras Galaxy Foil Edition', release_date: '2026-05-01', editions: [{ finish: 'foil', sealed_name: 'SLD Alien Auroras Galaxy Foil', tcgplayer_url: 'https://www.tcgplayer.com/product/5' }] }] };
  const url = 'https://www.tcgplayer.com/product/5';
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { deals: true } } }));
  await page.route('**/api/market/secret-lair?*', (r) => r.fulfill({ json: foilOnly }));
  await page.route('**/api/deals/watched', (r) => r.fulfill({ json: [{ set_code: 'sld', name: 'Alien Auroras Galaxy', kind: 'sld', finish: 'foil', scryfall_id: null, category: 'secret_lair', subtype: 'foil', release_date: null, market: null, contents: null, partial: false, best_price: 30, best_store: 'TCGplayer market', best_url: url, delta: null, pct: null, stores: [{ url, store: 'TCGplayer market', price: 30, available: null, read_at: '2026-10-06', read: true, first_price: 30, first_at: '2026-10-06', change: 0, history: [] }], error: null }] }));
  await page.goto('/market?subject=sld&edition=foil');
  await expect(page.getByRole('row', { name: /Alien Auroras Galaxy/ })).toContainText('watching');
  await page.getByRole('button', { name: 'Alien Auroras Galaxy Foil Edition' }).click();
  await expect(page.getByRole('button', { name: 'Stop watching' })).toBeVisible();
});

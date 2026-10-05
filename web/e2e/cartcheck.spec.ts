import { COLLECTION_URL, expect, test } from './support';

const audit = {
  lines: 3, copies: 4, total: 21.5, unidentified: [], family: 'blb', families: ['blb'],
  dupes: [{ scryfall_id: 'd1', name: 'Twice Card', set: 'BLB', num: '5', fin: '', nf_qty: 2, fo_qty: 0, nf_price: 1, fo_price: null, cheaper: null, note: '×2 nonfoil' }],
  owned: [{ scryfall_id: 'o1', name: 'Owned Card', set: 'BLB', num: '6', fin: 'nonfoil', owned_qty: 1, your: 2 }],
  missing: [{ scryfall_id: 'm1', name: 'Gap Card', set: 'blb', num: '7', fin: 'nonfoil', market: 3 }],
  overpay: [{ scryfall_id: 'p1', name: 'Pricey Card', set: 'BLB', num: '8', fin: 'foil', qty: 1, your: 15, market: 10, over: 5, pct: 50 }],
};

test('cart check is hidden unless its feature flag is on', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await expect(page.getByRole('heading', { level: 1, name: 'Collection' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Check my Mana Pool cart' })).toHaveCount(0);
});

test('with the flag on: paste the bookmarklet cart and see what to fix', async ({ page }) => {
  let sent: { cart: string; family: string | null } | null = null;
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { cart_check: true } } }));
  await page.route('**/api/cart/setup', (r) => r.fulfill({ json: { account: false } }));
  await page.route('**/api/cart/check', (r) => { sent = r.request().postDataJSON(); return r.fulfill({ json: audit }); });
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Check my Mana Pool cart' }).click();
  const dialog = page.getByRole('dialog', { name: 'Check my Mana Pool cart' });
  await expect(dialog.getByRole('link', { name: 'mm · copy cart' })).toHaveAttribute('href', /^javascript:/);
  await expect(dialog.getByRole('button', { name: 'Read my cart' })).toHaveCount(0);
  await dialog.getByRole('textbox').fill('{"items":[{"set":"blb","number":"5"}]}');
  await dialog.getByRole('button', { name: 'Check cart' }).click();
  await expect(dialog.getByRole('region', { name: 'Bought twice' })).toContainText('Twice Card');
  await expect(dialog.getByRole('region', { name: 'Already in your collection' })).toContainText('you own 1');
  await expect(dialog.getByRole('region', { name: 'Over market' })).toContainText('+50%');
  await expect(dialog.getByRole('region', { name: 'Still missing from BLB' })).toContainText('Gap Card');
  expect(sent).toEqual({ cart: '{"items":[{"set":"blb","number":"5"}]}', family: 'blb' });
});

import { COLLECTION_URL, expect, mockApi, test } from './support';

const COUNT_URL = `${COLLECTION_URL}&count=true`;

test('checklist mode: type counts, keyboard walks the column, Save sends one batch', async ({ page }) => {
  let body: { family: string; changes: { scryfall_id: string; finish: string; qty: number; expected: number }[] } | null = null;
  await mockApi(page, {
    '/api/collection/checklist': () => ({ json: { ingest_id: 7, added: 0, updated: 1, zeroed: 0, copies_added: 2, copies_removed: 0, rows: [{ scryfall_id: 'x', finish: 'nonfoil', old_qty: 1, new_qty: 3 }] } }),
  });
  await page.route('**/api/collection/checklist', async (r) => {
    body = r.request().postDataJSON();
    await r.fallback();
  });
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Count cards' }).click();
  await expect(page).toHaveURL(/count=true/);
  await expect(page.getByText(/^Counting · type how many/)).toBeVisible();

  await page.getByLabel('Azure Beastbinder BLB 41 nonfoil').click();
  await page.keyboard.type('4');
  await page.keyboard.press('Enter');
  // Enter moved down the nonfoil column to the next printing.
  await expect(page.locator('input:focus')).toHaveAttribute('aria-label', 'Eluge, the Shoreless Sea BLB 49 nonfoil');
  await page.keyboard.press('Shift+Tab');
  await expect(page.locator('input:focus')).toHaveAttribute('aria-label', 'Azure Beastbinder BLB 41 nonfoil');
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('input:focus')).toHaveAttribute('aria-label', 'Azure Beastbinder BLB 41 foil');
  await page.keyboard.type('x'); // not a number → flagged, not counted
  await expect(page.locator('input:focus')).toHaveAttribute('aria-invalid', 'true');
  await page.keyboard.press('Escape');

  await expect(page.getByText(/^Counting · 1 change · \+2 copies/)).toBeVisible();
  await page.getByRole('button', { name: 'Save 1 change' }).click();
  await expect(page.getByText('Saved 1 count · +2 copies')).toBeVisible();
  expect(body!.changes).toEqual([expect.objectContaining({ finish: 'nonfoil', qty: 4, expected: 2 })]);
  expect(body!.family).toBe('Bloomburrow');
});

test('checklist draft survives a reload; Discard asks first and clears it', async ({ page }) => {
  await page.goto(COUNT_URL);
  const cell = page.getByLabel('Alania, Divergent Storm BLB 327 nonfoil');
  await cell.click();
  await page.keyboard.type('5');
  await page.reload();
  await expect(page.getByLabel('Alania, Divergent Storm BLB 327 nonfoil')).toHaveValue('5');
  await page.getByRole('button', { name: 'Discard' }).click();
  await page.getByRole('button', { name: 'Discard counts' }).click();
  await expect(page.getByLabel('Alania, Divergent Storm BLB 327 nonfoil')).toHaveValue('1');
  await expect(page.getByRole('button', { name: 'Save' })).toBeDisabled();
});

test('checklist warns before leaving Collection with unsaved counts', async ({ page }) => {
  await page.goto(COUNT_URL);
  await page.getByLabel('Alania, Divergent Storm BLB 327 nonfoil').click();
  await page.keyboard.type('4');
  await page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name: 'Decks' }).click();
  await expect(page.getByText('Leave with unsaved counts?')).toBeVisible();
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(page).toHaveURL(/\/collection/);
});

test('checklist refuses counting below copies in built decks', async ({ page }) => {
  await page.goto(COUNT_URL);
  await page.getByLabel('Alania, Divergent Storm BLB 204 nonfoil').click();
  await page.keyboard.type('0');
  await expect(page.getByText(/in built decks — break it down before counting fewer/)).toBeVisible();
  await expect(page.getByRole('button', { name: /Save 1 change/ })).toBeDisabled();
});

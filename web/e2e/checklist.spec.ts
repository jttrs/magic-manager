import { COLLECTION_URL, expect, fixtures, mockApi, test } from './support';

const COUNT_URL = `${COLLECTION_URL}&count=true`;
const STALE_ID = fixtures.collectionBlb.cards.find((c) => c.name === 'Azure Beastbinder')!.scryfall_id;

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

test('checklist: a stale save flags the moved cells; Enter keeps your count and the retry sends the new baseline', async ({ page }) => {
  const bodies: { changes: { qty: number; expected: number }[] }[] = [];
  await mockApi(page, {
    '/api/collection/checklist': () =>
      bodies.length === 1
        ? { status: 409, json: { detail: { message: '1 count changed since you started counting', stale: [{ scryfall_id: STALE_ID, finish: 'nonfoil', expected: 2, current: 3 }] } } }
        : { json: { ingest_id: 9, added: 0, updated: 1, zeroed: 0, copies_added: 1, copies_removed: 0, rows: [{ scryfall_id: STALE_ID, finish: 'nonfoil', old_qty: 3, new_qty: 4 }] } },
  });
  await page.route('**/api/collection/checklist', async (r) => {
    bodies.push(r.request().postDataJSON());
    await r.fallback();
  });
  await page.goto(COUNT_URL);
  const cell = page.getByLabel('Azure Beastbinder BLB 41 nonfoil');
  await cell.click();
  await page.keyboard.type('4');
  await page.getByRole('button', { name: 'Save 1 change' }).click();
  await expect(page.getByText(/1 count changed in your collection since you started counting/)).toBeVisible();
  await expect(cell).toHaveValue('4');
  await expect(page.getByText('now 3')).toBeVisible();
  await expect(page.getByRole('button', { name: /^Save/ })).toBeDisabled();
  await cell.click();
  await page.keyboard.press('Enter');
  await page.getByRole('button', { name: 'Save 1 change' }).click();
  await expect(page.getByText('Saved 1 count · +1 copy')).toBeVisible();
  expect(bodies.map((b) => b.changes[0].expected)).toEqual([2, 3]);
});

test('checklist: counts typed while a save is in flight are kept', async ({ page }) => {
  let release!: () => void;
  const held = new Promise<void>((r) => (release = r));
  await mockApi(page, {
    '/api/collection/checklist': () => ({ json: { ingest_id: 9, added: 0, updated: 1, zeroed: 0, copies_added: 2, copies_removed: 0, rows: [] } }),
  });
  await page.route('**/api/collection/checklist', async (r) => {
    await held;
    await r.fallback();
  });
  await page.goto(COUNT_URL);
  await page.getByLabel('Azure Beastbinder BLB 41 nonfoil').click();
  await page.keyboard.type('4');
  await page.getByRole('button', { name: 'Save 1 change' }).click();
  await page.getByLabel('Agate-Blade Assassin BLB 82 nonfoil').click();
  await page.keyboard.type('9');
  release();
  await expect(page.getByText(/^Counting · 1 change/)).toBeVisible();
  await expect(page.getByLabel('Agate-Blade Assassin BLB 82 nonfoil')).toHaveValue('9');
});

test('checklist: typing in the Card name filter never pulls focus into a count cell', async ({ page }) => {
  await page.goto(COUNT_URL);
  await page.getByLabel('Azure Beastbinder BLB 41 nonfoil').click();
  await page.keyboard.press('Enter');
  const filter = page.getByLabel('Card name');
  await filter.click();
  await page.keyboard.type('a');
  await page.keyboard.type('g');
  await expect(filter).toBeFocused();
  await expect(filter).toHaveValue('ag');
});

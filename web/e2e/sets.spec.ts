import { expect, fixtures, SETS_URL, test } from './support';

test('empty state until a family is chosen; choosing one writes the URL', async ({ page }) => {
  await page.goto('/sets');
  await expect(page.getByText('Pick a set family')).toBeVisible();
  await page.getByRole('toolbar', { name: 'Set families' }).getByRole('button', { name: 'Final Fantasy', exact: true }).click();
  await expect(page).toHaveURL(/families=/);
  await expect(page.getByRole('heading', { name: 'Missing from Final Fantasy' })).toBeVisible();
});

test('exact printings: tiles show the precise set/CN and pool stamps (F2)', async ({ page }) => {
  await page.goto(SETS_URL);
  const t = fixtures.cardDiffFin.cards[0];
  const tile = page.getByRole('article').filter({ hasText: t.name }).first();
  await expect(tile).toContainText(`${t.collector_number} · ${t.set_code}`);
  await expect(tile.getByLabel(/^pools: /)).toBeAttached();
});

test('pool chips filter tiles', async ({ page }) => {
  await page.goto(SETS_URL);
  await expect(page.getByRole('article')).toHaveCount(fixtures.cardDiffFin.cards.length);
  const all = await page.getByRole('article').count();
  await page.getByRole('toolbar', { name: 'Pools' }).getByRole('button', { name: /Printing/ }).click();
  await page.getByRole('toolbar', { name: 'Pools' }).getByRole('button', { name: /Variant-chase/ }).click();
  const functionalOnly = fixtures.cardDiffFin.cards.filter((c) => c.pools.includes('functional')).length;
  await expect(page.getByRole('article')).toHaveCount(functionalOnly);
  expect(functionalOnly).toBeLessThan(all);
});

test('copy ManaPool list exports exact-printing lines (all shown when nothing marked)', async ({ page }) => {
  await page.goto(SETS_URL);
  await page.getByRole('button', { name: 'Copy ManaPool list' }).click();
  const text = await page.evaluate(() => navigator.clipboard.readText());
  const expected = fixtures.cardDiffFin.cards[0].manapool_line;
  expect(text.split('\n')).toContain(expected);
});

test('family running head and per-set subheads', async ({ page }) => {
  await page.goto(SETS_URL);
  await expect(page.getByRole('heading', { level: 3 }).filter({ hasText: 'Final Fantasy' })).toBeVisible();
  const sets = [...new Set(fixtures.cardDiffFin.cards.map((c) => c.set_code))];
  for (const s of sets.slice(0, 2)) await expect(page.getByRole('heading', { level: 4, name: new RegExp(`^${s}`) }).first()).toBeAttached();
});

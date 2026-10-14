import { COLLECTION_URL, COMPARE_URL, expect, test } from './support';

test.use({ viewport: { width: 390, height: 844 } });

test('phones: no horizontal overflow; one column at a time via tabs', async ({ page }) => {
  await page.goto(COMPARE_URL);
  await expect(page.getByRole('tab')).toHaveCount(3);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  await page.getByRole('tab', { name: /Both/ }).click();
  await expect(page.getByRole('tab', { name: /Both/ })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByText('Tifa Lockhart (top)')).toBeVisible();
});

test('phones: controls collapse into a disclosure once inputs are set', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  const toggle = page.getByRole('button', { name: 'Collection controls' });
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(toggle).toContainText('Bloomburrow · Owned + missing');
  await toggle.click();
  await expect(page.getByRole('button', { name: 'Copy ManaPool list' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
});

test('phones: the card inspector keeps View on to one row', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: /^Inspect / }).first().click();
  const viewOn = page.getByRole('dialog').getByRole('navigation', { name: 'View on' });
  const first = await viewOn.getByRole('link').first().boundingBox();
  const explorer = await viewOn.getByRole('link', { name: 'Explorer' }).boundingBox();
  expect(Math.abs(first!.y - explorer!.y)).toBeLessThan(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
});

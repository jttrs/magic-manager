import { COMPARE_URL, expect, SETS_URL, test } from './support';

test.use({ viewport: { width: 390, height: 844 } });

test('phones: no horizontal overflow; one column at a time via tabs', async ({ page }) => {
  await page.goto(COMPARE_URL);
  await expect(page.getByRole('tab')).toHaveCount(3);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  await page.getByRole('tab', { name: /Shared/ }).click();
  await expect(page.getByRole('tab', { name: /Shared/ })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByText('Tifa Lockhart (top)')).toBeVisible();
});

test('phones: controls collapse into a disclosure once inputs are set', async ({ page }) => {
  await page.goto(SETS_URL);
  const toggle = page.getByRole('button', { name: 'Missing-set controls' });
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await toggle.click();
  await expect(page.getByRole('button', { name: 'Copy ManaPool list' })).toBeVisible();
});

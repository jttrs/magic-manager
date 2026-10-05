import { COMPARE_URL, expect, test } from './support';

test('top nav spans the full width and the sidebar starts below it (F7)', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const header = await page.getByRole('banner').boundingBox();
  const aside = await page.getByRole('complementary').boundingBox();
  const vw = page.viewportSize()!.width;
  expect(header!.x).toBe(0);
  expect(header!.width).toBe(vw);
  expect(aside!.y).toBeGreaterThanOrEqual(header!.y + header!.height);
  await expect(page.getByRole('navigation', { name: 'Primary' }).getByRole('link')).toHaveText(['Collection', 'Decks', 'Explore']);
  await expect(page.getByRole('link', { name: 'Jobs' })).toBeVisible();
});

test('nav switches views and marks the active one', async ({ page }) => {
  await page.goto(COMPARE_URL);
  await page.getByRole('link', { name: 'Collection' }).click();
  await expect(page).toHaveURL(/\/collection/);
  await expect(page.getByRole('link', { name: 'Collection' })).toHaveAttribute('data-status', 'active');
});

test('theme override: dark sets data-theme, Auto clears it and follows the OS', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const html = page.locator('html');
  await page.getByRole('radio', { name: 'Dark' }).click();
  await expect(html).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(html).toHaveAttribute('data-theme', 'dark');
  await page.getByRole('radio', { name: 'Auto' }).click();
  await expect(html).not.toHaveAttribute('data-theme', /.*/);
});

test('light theme puts bone paper on charcoal chrome; dark is all charcoal', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto(COMPARE_URL);
  const bg = (sel: string) => page.locator(sel).first().evaluate((e) => getComputedStyle(e).backgroundColor);
  await page.getByRole('radio', { name: 'Light' }).click();
  expect(await bg('html')).toBe('rgb(22, 19, 14)');
  expect(await bg('.bg-paper')).toBe('rgb(239, 231, 214)');
  await page.getByRole('radio', { name: 'Dark' }).click();
  expect(await bg('.bg-paper')).toBe('rgb(34, 30, 23)');
});

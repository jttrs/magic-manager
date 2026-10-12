import { COMPARE_URL, expect, test } from './support';

test('top nav spans the full width and the sidebar starts below it (F7)', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const header = await page.getByRole('banner').boundingBox();
  const aside = await page.getByRole('complementary').boundingBox();
  const vw = page.viewportSize()!.width;
  expect(header!.x).toBe(0);
  expect(header!.width).toBe(vw);
  expect(aside!.y).toBeGreaterThanOrEqual(header!.y + header!.height);
  await expect(page.getByRole('navigation', { name: 'Primary' }).getByRole('link')).toHaveText(['Collection', 'Decks', 'Explore', 'Market']);
  await expect(page.getByRole('link', { name: 'Background jobs' })).toBeVisible();
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
  await page.getByRole('button', { name: 'Settings' }).click();
  await page.getByRole('dialog', { name: 'Settings' }).getByRole('radio', { name: 'Dark' }).click();
  await expect(html).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(html).toHaveAttribute('data-theme', 'dark');
  await page.getByRole('button', { name: 'Settings' }).click();
  await page.getByRole('radio', { name: 'Auto' }).click();
  await expect(html).not.toHaveAttribute('data-theme', /.*/);
});

test('light theme puts bone paper on charcoal chrome; dark is all charcoal', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await page.goto(COMPARE_URL);
  const bg = (sel: string) => page.locator(sel).first().evaluate((e) => getComputedStyle(e).backgroundColor);
  await page.getByRole('button', { name: 'Settings' }).click();
  await page.getByRole('radio', { name: 'Light' }).click();
  expect(await bg('html')).toBe('rgb(22, 19, 14)');
  expect(await bg('.bg-paper')).toBe('rgb(239, 231, 214)');
  await page.getByRole('radio', { name: 'Dark' }).click();
  expect(await bg('.bg-paper')).toBe('rgb(34, 30, 23)');
});

test('settings gear holds appearance, privacy and about; the masthead stays quiet', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const header = page.getByRole('banner');
  await expect(header.getByRole('radio')).toHaveCount(0);
  await expect(header.getByRole('button', { name: /^Privacy/ })).toHaveCount(0);
  await header.getByRole('button', { name: 'Settings' }).click();
  const dialog = page.getByRole('dialog', { name: 'Settings' });
  await expect(dialog.getByRole('heading', { name: 'Appearance' })).toBeVisible();
  await expect(dialog.getByRole('radiogroup', { name: 'Theme' })).toBeVisible();
  await expect(dialog.getByRole('heading', { name: 'Privacy' })).toBeVisible();
  await dialog.getByRole('link', { name: /Background jobs/ }).click();
  await expect(page).toHaveURL(/\/jobs/);
  await expect(dialog).toHaveCount(0);
});

test('phone masthead: every nav tab and the gear fit at 390px', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(COMPARE_URL);
  const gear = await page.getByRole('button', { name: 'Settings' }).boundingBox();
  expect(gear!.x + gear!.width).toBeLessThanOrEqual(390);
  for (const name of ['Collection', 'Decks', 'Explore', 'Market']) {
    const box = await page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name }).boundingBox();
    expect(box!.x + box!.width).toBeLessThanOrEqual(gear!.x);
  }
});

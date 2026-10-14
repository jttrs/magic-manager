import { COMPARE_URL, expect, test } from './support';

const navFitsBeside = async (page: import('@playwright/test').Page, width: number) => {
  const gear = await page.getByRole('button', { name: 'Settings' }).boundingBox();
  expect(gear!.x + gear!.width).toBeLessThanOrEqual(width);
  const icons = await page.getByRole('banner').locator('a[aria-label], button[aria-label]').evaluateAll((els) => els.filter((e) => e.getBoundingClientRect().width > 0).map((e) => e.getBoundingClientRect().left));
  const leftmost = Math.min(...icons);
  for (const name of ['Collection', 'Decks', 'Explore', 'Market']) {
    const box = await page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name }).boundingBox();
    expect(box!.x + box!.width).toBeLessThanOrEqual(leftmost);
  }
};

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
  await navFitsBeside(page, 390);
});

test('phone masthead, crowded: restore point + a running job + the gear still fit at 390px', async ({ page }) => {
  await page.route('**/api/undo', (r) => r.fulfill({ json: { taken_at: new Date().toISOString(), reason: 'before adding cards', restorable: true, current: {}, snapshot: {}, changes: {}, details: [] } }));
  await page.route('**/api/jobs', (r) => r.fulfill({ json: [{ id: 'j1', name: 'edhrec.sync_bulk', title: 'Warm EDHREC cache', inputs: {}, status: 'running', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null }] }));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(COMPARE_URL);
  await expect(page.getByRole('link', { name: 'Background jobs · 1 running' })).toBeVisible();
  await expect(page.getByRole('button', { name: /^Restore point/ })).toBeVisible();
  await navFitsBeside(page, 390);
});

test('sheet header is compact: no printed title, the meta line stays; no sub-nav strip without modes', async ({ page }) => {
  await page.goto('/jobs');
  await expect(page.getByRole('heading', { level: 1, name: 'Jobs' })).toHaveClass(/sr-only/);
  await expect(page.getByText('Long-running work runs in the background; progress streams live.')).toBeVisible();
  await expect(page.locator('[data-subnav]')).toHaveCount(0);
});

test('card inspector: Value + Cheapest rows, recheck without naming a vendor, one View on row', async ({ page }) => {
  await page.route('**/api/cards/floors', (r) => {
    const body = r.request().postDataJSON() as { scryfall_ids: string[]; live: boolean };
    return r.fulfill({ json: { live: body.live, floors: [{ scryfall_id: body.scryfall_ids[0], oracle_id: 'o', name: 'X', nonfoil: { usd: 0.5, set_code: 'm21', collector_number: '3', scryfall_id: 'loc' }, foil: null }] } });
  });
  await page.goto('/collection?families=%5B%22blb%22%5D');
  await page.getByRole('button', { name: /^Inspect / }).first().click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('term').filter({ hasText: /^Value$/ })).toBeVisible();
  await expect(dialog.getByRole('term').filter({ hasText: /^Price$/ })).toHaveCount(0);
  await expect(dialog).toContainText('among synced sets');
  await expect(dialog.getByRole('button', { name: /Scryfall/ })).toHaveCount(0);
  await expect(dialog.getByRole('button', { name: 'Recheck for cheapest' })).toBeVisible();

  const viewOn = dialog.getByRole('navigation', { name: 'View on' });
  const scryfall = await viewOn.getByRole('link', { name: /^Scryfall/ }).boundingBox();
  const tcg = await viewOn.getByRole('link', { name: /^TCGplayer/ }).boundingBox();
  const explorer = await viewOn.getByRole('link', { name: 'Explorer' }).boundingBox();
  expect(Math.abs(scryfall!.y - explorer!.y)).toBeLessThan(2);               // one row
  expect(explorer!.x - (tcg!.x + tcg!.width)).toBeGreaterThan(40);           // Explorer pushed to the right
  await expect(viewOn.getByRole('link', { name: 'Explorer' })).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
});
